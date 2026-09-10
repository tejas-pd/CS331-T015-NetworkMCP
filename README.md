# Intelligent Network Configuration Assistant using MCP and Rule-Based Automation

## 1. Project Overview

This project implements an intelligent network configuration assistant that combines a local Large Language Model (LLM), the Model Context Protocol (MCP), and a rule-based network policy engine.

The assistant accepts natural-language network administration requests such as:

- "Block 10.0.0.5"
- "Can you limit 10.0.0.5 to 5 Mbps?"
- "Check whether 10.7.5.27 is reachable"
- "How fast is the connection to 10.7.5.27?"
- "Show me the current firewall rules"

The LLM interprets the user's request and selects an appropriate MCP tool. The Python assistant then invokes that tool through the MCP client.

All network operations pass through the MCP server and the policy engine before being executed.

---

## 2. System Architecture

```text
                    USER
                      |
                      v
              +---------------+
              |   Local LLM   |
              |   Qwen3:8b    |
              |    Ollama     |
              +-------+-------+
                      |
                      v
              +---------------+
              | Python        |
              | assistant.py  |
              +-------+-------+
                      |
                 MCP Client
                      |
                      v
              +---------------+
              | FastMCP Server |
              | mcp_server.py |
              +-------+-------+
                      |
                      v
              +---------------+
              | Policy Engine |
              | network_policy|
              +-------+-------+
                      |
                      v
              +---------------+
              | Network Tools |
              | iptables / tc |
              | ping / iperf3 |
              +---------------+
```

### Important Security Boundary

The LLM does not directly execute shell commands or modify the network.

The LLM only interprets the user's intent and selects an available MCP tool.

The MCP server invokes the network functionality, while the policy engine determines whether the requested operation is permitted.

---

## 3. Components

### Local LLM

Ollama runs the Qwen3:8b model locally.

This removes the need for an external LLM API key and keeps the LLM inference on the local machine.

### Python Assistant

`assistant.py` provides the user-facing command-line interface.

It:

1. Receives natural-language input.
2. Sends the request to the local LLM.
3. Provides the MCP tool definitions to the LLM.
4. Receives the selected tool and arguments.
5. Calls the MCP client.
6. Sends the MCP result back to the LLM.
7. Displays the final natural-language response.

### MCP Client

The Python assistant uses the FastMCP client to discover and invoke tools provided by the MCP server.

### MCP Server

`server/mcp_server.py` exposes the network functionality as MCP tools.

Current tools include:

- `block_ip`
- `unblock_ip`
- `list_firewall_rules`
- `ping_host`
- `limit_bandwidth`
- `test_bandwidth`

### Policy Engine

`core/policy.py` provides rule-based authorization.

The policy controls:

- Allowed IPv4 networks
- Protected IP addresses
- Allowed network interfaces
- Minimum bandwidth
- Maximum bandwidth

### Network Tools

`core/network_tools.py` implements the actual network operations.

The project uses:

- `iptables` for firewall operations
- `tc` for traffic shaping
- `ping` for connectivity testing
- `iperf3` for bandwidth testing

### Audit Logging

Network commands executed by the command runner are recorded in:

```text
logs/audit.jsonl
```

Each record contains a timestamp and command execution information.

---

## 4. Policy Configuration

The policy is defined in:

```text
policies/network_policy.yaml
```

Current configuration allows:

```text
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

Protected addresses include:

```text
127.0.0.1
192.168.1.1
```

Bandwidth limits are restricted to:

```text
1 - 100 Mbps
```

Only interfaces explicitly listed in the policy can be used.

---

## 5. Safety and Execution Modes

The project uses dry-run mode by default.

```text
NETWORK_ASSISTANT_EXECUTE=0
```

In dry-run mode, network commands are generated and logged but are not actually executed.

Live network changes require:

```bash
export NETWORK_ASSISTANT_EXECUTE=1
```

Live changes are supported only on Linux/Ubuntu and require the appropriate permissions.

For safety, live network changes should only be performed in an isolated laboratory environment.

---

## 6. Installation

### Python Environment

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

### Ollama

Install Ollama on the system.

Then download the local model:

```bash
ollama pull qwen3:8b
```

Verify the model:

```bash
ollama run qwen3:8b
```

Exit the model with:

```text
/bye
```

---

## 7. Running the Assistant

Make sure the Ollama service is running.

Then:

```bash
cd network-mcp-assistant
source .venv/bin/activate
python assistant.py
```

The assistant automatically connects to:

```text
server/mcp_server.py
```

and discovers the MCP tools exposed by the server.

---

## 8. Example Commands

### Bandwidth Limiting

```text
Can you slow down 10.0.0.5 to around 5 Mbps?
```

The LLM interprets the request and selects:

```text
limit_bandwidth
```

The request is then passed through the MCP server and policy engine.

### Connectivity Test

```text
Can you check whether 10.7.5.27 is reachable?
```

The LLM selects:

```text
ping_host
```

### Bandwidth Test

```text
How fast is the connection to 10.7.5.27?
```

The LLM selects:

```text
test_bandwidth
```

### Firewall Rules

```text
Show me the current firewall rules.
```

The LLM selects:

```text
list_firewall_rules
```

### Policy Rejection

```text
Give 10.0.0.5 a bandwidth limit of 500 Mbps.
```

The policy engine rejects the request because the permitted range is 1-100 Mbps.

Another example:

```text
Block 192.168.1.1
```

The policy engine rejects the request because the address is protected.

---

## 9. Testing

Run the automated policy tests using:

```bash
python -m pytest
```

Expected result:

```text
7 passed
```

The tests verify:

- Valid IPv4 addresses
- Protected IP rejection
- Outside-network rejection
- Invalid IP rejection
- IPv6 rejection
- Bandwidth lower-bound rejection
- Bandwidth upper-bound rejection

---

## 10. Demonstrated Results

The assistant has been tested using natural-language requests.

Example:

```text
User:
Can you slow down 10.0.0.5 to around 5 Mbps?

LLM:
Selected MCP tool: limit_bandwidth

Arguments:
ip = 10.0.0.5
mbps = 5
interface = eth0

Python Assistant:
MCP Client -> MCP Server

Result:
Request successfully processed.
```

Policy validation was also demonstrated:

```text
User:
Give 10.0.0.5 a bandwidth limit of 500 Mbps.

LLM:
Selected MCP tool: limit_bandwidth

Policy:
REJECTED

Reason:
Bandwidth must be between 1-100 Mbps.
```

Connectivity monitoring was tested using `ping`, and bandwidth monitoring was tested using `iperf3`.

---

## 11. Project Structure

```text
network-mcp-assistant/
│
├── assistant.py
├── cli.py
│
├── core/
│   ├── network_tools.py
│   ├── policy.py
│   ├── runner.py
│   └── __init__.py
│
├── server/
│   └── mcp_server.py
│
├── policies/
│   └── network_policy.yaml
│
├── tests/
│   └── test_policy.py
│
├── docs/
│   └── demo-plan.md
│
├── logs/
│   └── audit.jsonl
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 12. Key Design Principle

The project separates intelligence from authorization.

The LLM is responsible for:

```text
Natural language
      ↓
Intent understanding
      ↓
Tool selection
      ↓
Tool arguments
```

The MCP server and policy engine are responsible for:

```text
Tool request
      ↓
Policy validation
      ↓
Authorized network operation
      ↓
Verification
```

Therefore, even if the LLM misunderstands a request, it cannot bypass the network policy and directly execute arbitrary commands.

---

## 13. LLM-MCP Interaction Flow

The complete interaction follows this sequence:

```text
User enters natural-language request
              |
              v
        Local Qwen3:8b
              |
              | selects MCP tool
              v
       Python assistant.py
              |
              | MCP call
              v
        FastMCP Client
              |
              v
        FastMCP Server
              |
              v
        Policy Validation
              |
       +------+------+
       |             |
    Rejected       Allowed
       |             |
       |             v
       |       Network Tool
       |             |
       |       iptables/tc/
       |       ping/iperf3
       |             |
       +------+------+
              |
              v
        Result returned
              |
              v
        Python Assistant
              |
              v
          Local LLM
              |
              v
       Natural-language
            response
```

This architecture ensures that the LLM provides the intelligence layer while the MCP server and policy engine provide controlled and auditable access to network operations.

---

## 14. Security Considerations

The project follows several security principles:

- No external LLM API key is required.
- The LLM runs locally through Ollama.
- The LLM cannot directly execute arbitrary shell commands.
- Network operations are exposed only through predefined MCP tools.
- IP addresses are validated before network operations.
- Protected IP addresses cannot be modified through the assistant.
- Bandwidth values are restricted by policy.
- Network interfaces are restricted by policy.
- Commands are passed as fixed argument vectors rather than shell-interpolated strings.
- Dry-run mode is enabled by default.
- Network command activity is recorded in the audit log.
- Live network changes should only be performed in an isolated laboratory environment.

---

## 15. Conclusion

The Intelligent Network Configuration Assistant demonstrates how a Large Language Model can be combined with MCP and rule-based automation to provide a natural-language interface for network administration.

The LLM handles natural-language understanding and tool selection, while the Python assistant acts as the application layer and MCP client. The MCP server provides controlled network tools, and the policy engine ensures that requests remain within predefined security and configuration limits.

This separation between LLM intelligence and deterministic policy enforcement provides a safer and more controllable architecture for automated network configuration.
