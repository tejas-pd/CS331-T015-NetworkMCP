# AI Usage Declaration

AI tools were used as a development aid during this project.

## Tools Used

- **ChatGPT:** Used for discussing the project architecture, debugging code and configuration issues, and improving documentation.
- **Ollama + Qwen3:8b:** Used as the local LLM integrated into the application for interpreting natural-language network commands and selecting MCP tools.

## Areas Where AI Assistance Was Used

AI assistance was used during:
- initial architecture planning,
- implementation and debugging,
- MCP integration,
- Docker configuration,
- network testing,
- and documentation preparation.

The final implementation was tested and adapted manually to the project requirements and the actual network environment.

The LLM in the final system does not have unrestricted shell access. It can only request the predefined MCP tools, while policy validation and controlled command execution are handled by the application.

