from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from ollama import AsyncClient


ROOT = Path(__file__).resolve().parent

MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://localhost:8000/mcp"
)


SYSTEM_PROMPT = """
You are an intelligent network configuration assistant.

You help administrators manage a controlled laboratory network.

You have access to network tools through an MCP server.

Your responsibilities are:

1. Understand natural-language network requests.
2. Select the appropriate MCP tool.
3. Provide valid arguments for the selected tool.
4. Never invent tool results.
5. Never execute shell commands yourself.
6. Never bypass the network policy.
7. The MCP server and policy engine are the final authority.
8. If an operation is rejected, clearly explain why.
9. If a request cannot be safely mapped to an available tool, do not call a tool.
10. After receiving a tool result, explain it clearly to the user.

Available network operations may include:

- blocking an IP address
- unblocking an IP address
- listing firewall rules
- limiting bandwidth
- pinging a host
- testing bandwidth

Only use an MCP tool when it is appropriate for the user's request.
"""


def convert_mcp_tools(mcp_tools):
    """
    Convert FastMCP tool definitions into Ollama tool definitions.
    """

    ollama_tools = []

    for tool in mcp_tools:

        schema = getattr(tool, "inputSchema", None)

        if schema is None:
            schema = getattr(tool, "input_schema", None)

        if schema is None:
            schema = {
                "type": "object",
                "properties": {},
            }

        ollama_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": schema,
                },
            }
        )

    return ollama_tools


def get_tool_schema(mcp_tools):
    """
    Build a lookup table containing the schemas of MCP tools.
    """

    schemas = {}

    for tool in mcp_tools:

        schema = getattr(tool, "inputSchema", None)

        if schema is None:
            schema = getattr(tool, "input_schema", None)

        if schema is None:
            schema = {
                "type": "object",
                "properties": {},
            }

        schemas[tool.name] = schema

    return schemas


def validate_tool_call(tool_name, arguments, tool_schemas):
    """
    Validate an LLM-generated MCP tool call before execution.

    This is an important safety boundary.

    If the LLM generates an unknown tool or malformed/missing
    arguments, the MCP server is NOT called.
    """

    # ------------------------------------------------------
    # Check that the requested tool actually exists.
    # ------------------------------------------------------

    if tool_name not in tool_schemas:
        return False, f"Unknown MCP tool: {tool_name}"

    # ------------------------------------------------------
    # Arguments must be an object/dictionary.
    # ------------------------------------------------------

    if not isinstance(arguments, dict):
        return False, "Tool arguments are not a valid object."

    schema = tool_schemas[tool_name]

    # ------------------------------------------------------
    # Check required parameters.
    # ------------------------------------------------------

    required = schema.get("required", [])

    for parameter in required:

        if parameter not in arguments:
            return False, (
                f"Required parameter '{parameter}' "
                f"is missing from the tool arguments."
            )

    # ------------------------------------------------------
    # Basic parameter validation.
    #
    # We intentionally do not perform the actual network
    # policy validation here. That remains the responsibility
    # of the MCP server's policy engine.
    # ------------------------------------------------------

    properties = schema.get("properties", {})

    for parameter, value in arguments.items():

        if parameter not in properties:
            return False, (
                f"Unexpected parameter '{parameter}' "
                f"was supplied by the LLM."
            )

        parameter_type = properties[parameter].get("type")

        if parameter_type == "string" and not isinstance(value, str):
            return False, (
                f"Parameter '{parameter}' must be a string."
            )

        if parameter_type == "integer" and (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            return False, (
                f"Parameter '{parameter}' must be an integer."
            )

        if parameter_type == "number" and (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            return False, (
                f"Parameter '{parameter}' must be a number."
            )

    return True, "valid"


def get_mcp_result_text(result):
    """
    Convert an MCP result into text that can be returned to the LLM.
    """

    data = getattr(result, "data", None)

    if data is not None:
        return json.dumps(
            data,
            indent=2,
            default=str,
        )

    content = getattr(result, "content", None)

    if content:

        parts = []

        for item in content:

            if hasattr(item, "text"):
                parts.append(item.text)

            else:
                parts.append(str(item))

        return "\n".join(parts)

    return "{}"


async def process_request(
    user_message,
    mcp_client,
    mcp_tools,
    llm_client,
):
    """
    Process one user request.

    Flow:

        User
          ↓
        Ollama LLM
          ↓
        Validate generated MCP call
          ↓
        FastMCP client
          ↓
        MCP server running in Docker
          ↓
        Network tool
          ↓
        Result back to LLM
          ↓
        Final answer
    """

    ollama_tools = convert_mcp_tools(mcp_tools)
    tool_schemas = get_tool_schema(mcp_tools)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    while True:

        # ==================================================
        # 1. ASK THE LOCAL LLM
        # ==================================================

        response = await llm_client.chat(
            model=MODEL,
            messages=messages,
            tools=ollama_tools,
            think=False,
        )

        messages.append(response.message)

        tool_calls = response.message.tool_calls

        # ==================================================
        # 2. NO TOOL CALL
        # ==================================================

        if not tool_calls:
            return response.message.content

        # ==================================================
        # 3. PROCESS LLM TOOL CALLS
        # ==================================================

        for call in tool_calls:

            tool_name = call.function.name
            arguments = call.function.arguments

            print()
            print(f"[LLM] Selected MCP tool: {tool_name}")
            print(f"[LLM] Arguments: {arguments}")

            # ------------------------------------------------
            # Convert arguments safely if necessary.
            # ------------------------------------------------

            if isinstance(arguments, str):

                try:
                    arguments = json.loads(arguments)

                except json.JSONDecodeError:

                    print("[SAFETY] Invalid JSON tool arguments.")
                    print("[SAFETY] MCP tool was NOT executed.")

                    return (
                        "I could not safely interpret the model's "
                        "tool arguments, so no network action was performed."
                    )

            # ------------------------------------------------
            # Validate the LLM output BEFORE MCP execution.
            # ------------------------------------------------

            valid, reason = validate_tool_call(
                tool_name,
                arguments,
                tool_schemas,
            )

            if not valid:

                print()
                print("[SAFETY] LLM tool call rejected.")
                print(f"[SAFETY] Reason: {reason}")
                print("[SAFETY] No network operation was performed.")

                return (
                    "The requested operation could not be safely "
                    f"processed: {reason} No network action was performed."
                )

            print("[VALIDATION] LLM tool call is valid.")

            # =================================================
            # 4. CALL MCP SERVER
            # =================================================

            print("[MCP CLIENT] Calling Dockerized MCP server...")

            try:

                result = await mcp_client.call_tool(
                    tool_name,
                    arguments,
                )

                result_text = get_mcp_result_text(result)

                print("[MCP CLIENT] Tool completed.")

            except Exception as exc:

                print("[MCP CLIENT] Tool failed.")
                print(f"[MCP CLIENT] Error: {exc}")

                result_text = json.dumps(
                    {
                        "status": "error",
                        "error": str(exc),
                    }
                )

            # =================================================
            # 5. RETURN MCP RESULT TO THE LLM
            # =================================================

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": result_text,
                }
            )

        # Continue the loop so the LLM can produce
        # the final natural-language response.


async def main():

    print("=" * 60)
    print(" Intelligent Network Configuration Assistant")
    print("=" * 60)

    print(f"LLM: {MODEL}")
    print(f"MCP Server: {MCP_SERVER_URL}")
    print()

    # ------------------------------------------------------
    # LOCAL LLM CLIENT
    # ------------------------------------------------------

    llm_client = AsyncClient()

    # ------------------------------------------------------
    # MCP CLIENT
    # ------------------------------------------------------
    #
    # The MCP server runs separately inside Docker.
    # The assistant connects to it using Streamable HTTP.
    # ------------------------------------------------------

    mcp_transport = StreamableHttpTransport(
        url=MCP_SERVER_URL
    )

    mcp_client = Client(mcp_transport)

    async with mcp_client:

        # --------------------------------------------------
        # Discover tools from MCP server.
        # --------------------------------------------------

        mcp_tools = await mcp_client.list_tools()

        print("[MCP CLIENT] Tools discovered from server:")

        for tool in mcp_tools:
            print(f"  - {tool.name}")

        print()
        print("Type 'quit' or 'exit' to stop.")
        print()

        # --------------------------------------------------
        # Main interaction loop.
        # --------------------------------------------------

        while True:

            try:

                user_message = input("You: ").strip()

            except (KeyboardInterrupt, EOFError):

                print()
                break

            if not user_message:
                continue

            if user_message.lower() in {
                "quit",
                "exit",
            }:
                break

            try:

                answer = await process_request(
                    user_message,
                    mcp_client,
                    mcp_tools,
                    llm_client,
                )

                print()
                print(f"Assistant: {answer}")
                print()

            except Exception as exc:

                # ------------------------------------------
                # Final safety net.
                # ------------------------------------------

                print()
                print("[ERROR] Assistant request failed.")
                print(f"[ERROR] {exc}")
                print("[SAFETY] No additional network action was performed.")
                print()


if __name__ == "__main__":
    asyncio.run(main())
