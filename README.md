# Intelligent Network Configuration Assistant using MCP and Rule-Based Automation

## 1. Project Overview

The **Intelligent Network Configuration Assistant** is a command-line network administration assistant that combines a local Large Language Model (LLM), the **Model Context Protocol (MCP)**, and a rule-based policy engine.

The user interacts with the assistant using natural-language commands such as:

- `block 10.7.33.21`
- `unblock 10.7.33.21`
- `what is the ping of 10.7.33.21`
- `limit 10.7.5.27 to 5 Mbps on wlo1`
- `what is my bandwidth with 10.7.33.21`

The LLM interprets the request and selects an appropriate MCP tool. The MCP server then applies policy checks before executing controlled Linux networking commands such as `iptables`, `tc`, `ping`, and `iperf3`.

The project emphasizes **security, validation, auditability, predictable tool execution, verification, and controlled deployment**.

---

## 2. Objectives

The project aims to:

1. Provide a natural-language interface for common network administration tasks.
2. Use MCP to expose network operations as structured tools.
3. Apply a rule-based policy before allowing network changes.
4. Prevent unsafe or unauthorized network configurations.
5. Verify that requested configurations were actually applied.
6. Record command execution in an audit log.
7. Handle malformed or invalid LLM tool calls safely.
8. Support safe dry-run operation and controlled live execution.
9. Provide a containerized MCP server using Docker.
10. Demonstrate the system on a real Linux network.

---

## 3. System Architecture

```text
                        +----------------------+
                        |        User          |
                        +----------+-----------+
                                   |
                                   | Natural language
                                   v
                        +----------------------+
                        |    Qwen3:8b LLM      |
                        |   (Local Ollama)     |
                        +----------+-----------+
                                   |
                                   | Tool selection + arguments
                                   v
                        +----------------------+
                        |    FastMCP Client    |
                        |     assistant.py     |
                        +----------+-----------+
                                   |
                                   | MCP over HTTP
                                   v
                 +-----------------------------------------+
                 |          Docker Container                |
                 |                                         |
                 |       FastMCP MCP Server                 |
                 |              |                          |
                 |              v                          |
                 |         Policy Engine                    |
                 |              |                          |
                 |              v                          |
                 |        Network Tool Layer                |
                 +--------------+--------------------------+
                                |
                 +--------------+---------------------------+
                 |              |             |              |
                 v              v             v              v
              iptables          tc           ping          iperf3
                 |              |             |              |
                 +--------------+-------------+--------------+
                                |
                                v
                       Network configuration
                       and verification result
                                |
                                v
                       LLM response to user
```

### Runtime Separation

The demonstrated deployment uses:

- **Host:** `assistant.py` and the local Qwen3:8b model.
- **Docker:** FastMCP server and project dependencies.
- **MCP transport:** HTTP at `http://localhost:8000/mcp`.
- **Docker networking:** host networking in the controlled lab deployment.

The default configuration remains **dry-run** for safety.

---

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3 | Application and automation logic |
| Qwen3:8b | Local LLM used for natural-language interpretation |
| Ollama | Local LLM runtime |
| FastMCP | MCP server/client implementation |
| MCP | Structured communication between assistant and network tools |
| iptables | Firewall rule management |
| tc | Linux traffic-control bandwidth limiting |
| ping | Connectivity verification |
| iperf3 | Throughput measurement |
| YAML | Network policy configuration |
| Docker | Containerized MCP deployment |
| Docker Compose | Container lifecycle management |
| pytest | Automated testing |

---

## 5. Project Structure

```text
network-mcp-assistant/
├── .gitignore
├── README.md
├── assistant.py
├── cli.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── core/
│   ├── __init__.py
│   ├── network_tools.py
│   ├── policy.py
│   └── runner.py
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
└── logs/
    └── audit.jsonl          # created automatically at runtime
```

The `logs/` directory does not need to be committed to Git. The command runner creates it automatically when an audit record is written.

---

## 6. Installation

### 6.1 Clone the Repository

```bash
git clone https://github.com/tejas-pd/CN_Project.git
cd CN_Project
```

### 6.2 Create and Activate the Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 6.3 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6.4 Install and Verify Docker

```bash
docker --version
docker compose version
```

If the current Linux user has just been added to the Docker group, start a new login session or run:

```bash
newgrp docker
```

Then verify:

```bash
docker run hello-world
```

---

## 7. Ollama and Qwen3 Setup

Install Ollama and make sure the required model is available.

```bash
ollama pull qwen3:8b
```

Verify:

```bash
ollama list
```

The assistant expects:

```text
qwen3:8b
```

Ollama should be running before starting the assistant.

---

## 8. Network Environment

The demonstrated lab used two laptops on the same Wi-Fi network.

| Device | IP Address | Interface |
|---|---|---|
| Assistant laptop | `10.7.5.27/18` | `wlo1` |
| Peer laptop | `10.7.33.21/18` | Windows laptop |

The exact IP addresses and interface names may differ in another environment.

Check the local Linux address:

```bash
ip -4 addr show wlo1
```

Check the route:

```bash
ip route
```

Check the peer's neighbor entry:

```bash
ip neigh show 10.7.33.21
```

---

## 9. Network Policy

The policy file is:

```text
policies/network_policy.yaml
```

Current policy:

```yaml
allowed_networks:
  - 10.0.0.0/8
  - 172.16.0.0/12
  - 192.168.0.0/16

protected_ips:
  - 127.0.0.1
  - 192.168.1.1

allowed_interfaces:
  - eth0
  - ens33
  - enp0s3
  - wlo1

min_bandwidth_mbps: 1
max_bandwidth_mbps: 100
```

The policy engine validates:

- IPv4 address format
- whether an address belongs to an authorized network
- whether an IP is protected
- bandwidth range
- network interface name

The LLM is **not** the final security authority. The server-side policy engine performs the final validation before network changes are executed.

---

## 10. Dry-Run and Live Execution

The project supports two execution modes.

### Dry-Run Mode

```text
NETWORK_ASSISTANT_EXECUTE=0
```

Commands are constructed and audited but are not actually executed.

This is the default mode.

### Live Mode

```text
NETWORK_ASSISTANT_EXECUTE=1
```

Commands are actually executed.

Because the lab MCP server uses Docker host networking, live mode should only be enabled in a controlled environment where modifying firewall and traffic-control rules is acceptable.

### Switching Modes Without Editing the Compose File

You do **not** need to edit `docker-compose.yml` every time.

Dry-run:

```bash
NETWORK_ASSISTANT_EXECUTE=0 docker compose up
```

Live mode:

```bash
NETWORK_ASSISTANT_EXECUTE=1 docker compose up
```

The Compose file can safely keep:

```yaml
environment:
  NETWORK_ASSISTANT_EXECUTE: "${NETWORK_ASSISTANT_EXECUTE:-0}"
```

---

## 11. Starting the MCP Server

Build the image:

```bash
docker compose build
```

Start the MCP server:

```bash
docker compose up
```

The MCP endpoint is:

```text
http://localhost:8000/mcp
```

From another terminal, check:

```bash
docker compose ps
```

To stop the server:

```bash
docker compose down
```

To inspect server logs:

```bash
docker compose logs -f
```

---

## 12. Running the Assistant

With the Dockerized MCP server running, open another terminal:

```bash
source .venv/bin/activate
python assistant.py
```

The assistant should discover the tools exposed by the server.

Expected tools:

```text
[MCP CLIENT] Tools discovered from server:
 - block_ip
 - unblock_ip
 - list_firewall_rules
 - ping_host
 - limit_bandwidth
 - test_bandwidth
```

This demonstrates dynamic MCP tool discovery.

---

## 13. MCP Tools

The server currently exposes six tools.

### 13.1 `block_ip`

Blocks inbound traffic from a specified IP using `iptables`.

Example:

```text
block 10.7.33.21
```

Conceptually:

```bash
sudo -n iptables -I INPUT -s 10.7.33.21 -j DROP
```

The tool verifies the rule after applying it.

### 13.2 `unblock_ip`

Removes the blocking rule.

Example:

```text
unblock 10.7.33.21
```

The tool verifies that the rule is absent.

### 13.3 `list_firewall_rules`

Lists the current `INPUT` firewall rules.

Example:

```text
show my firewall rules
```

Underlying command:

```bash
sudo -n iptables -S INPUT
```

### 13.4 `ping_host`

Tests reachability of an IP address.

Example:

```text
what is the ping of 10.7.33.21
```

The result includes reachability, packet loss, and RTT statistics.

### 13.5 `limit_bandwidth`

Applies an outbound bandwidth limit using Linux `tc`.

Example:

```text
limit 10.7.5.27 to 5 Mbps on wlo1
```

The implementation uses an HTB qdisc/class and a filter matching the source IP.

**Important:** this is an outbound/source-IP based limit. For traffic sent from `10.7.5.27` to `10.7.33.21`, the IP being limited is `10.7.5.27`, not the peer IP.

The tool also inspects the resulting `tc` configuration.

### 13.6 `test_bandwidth`

Uses `iperf3` to measure throughput to a peer.

Example:

```text
what is my bandwidth with 10.7.33.21
```

The peer must run an iperf3 server:

```bash
iperf3 -s
```

The assistant can then run a client test to that peer.

---

## 14. Windows Peer Setup

If the peer is Windows, its IP can be checked using:

```powershell
ipconfig
```

For bandwidth testing, iperf3 must be available on the Windows machine.

Start the iperf3 server:

```powershell
iperf3.exe -s
```

Keep the server terminal open while the Linux machine runs the bandwidth test.

For a simple connectivity test from Windows:

```powershell
ping 10.7.5.27
```

If Windows Firewall blocks inbound ICMP, a suitable inbound ICMPv4 Echo rule can be enabled for the controlled lab.

---

## 15. Linux Sudo Configuration

Live operations use non-interactive `sudo -n`.

The demonstrated lab used a restricted sudoers rule:

```text
tejas-prasad ALL=(root) NOPASSWD: /usr/sbin/iptables, /usr/sbin/tc, /usr/bin/ping, /usr/bin/iperf3
```

This is preferable to unrestricted passwordless sudo.

Verify the configuration:

```bash
sudo -k
sudo -n iptables -S INPUT
```

The exact username and executable paths may differ on another system.

---

## 16. Security and Safety Design

The LLM does not receive unrestricted shell access.

Instead:

```text
Natural-language request
        |
        v
LLM tool selection
        |
        v
Tool-call validation
        |
        v
MCP server
        |
        v
Policy validation
        |
        v
Fixed command argument vector
        |
        v
Controlled execution
```

### Command Safety

Commands are passed as argument lists instead of shell-interpolated strings.

Example:

```python
["sudo", "-n", "iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"]
```

This prevents shell interpretation of user-controlled values.

### Validation Layers

The system validates:

1. JSON/tool-call parsing
2. Tool name
3. Required parameters
4. Unexpected parameters
5. Basic parameter types
6. IP/network policy
7. Protected IP restrictions
8. Bandwidth limits
9. Interface allow-list
10. Server-side policy before execution

---

## 17. Handling Malformed LLM Output

The assistant validates an LLM-generated tool call before sending it to the MCP server.

Rejected cases include:

- invalid JSON
- unknown tool
- missing required argument
- unexpected argument
- incorrect parameter type

The important design principle is:

```text
LLM decision != authorized network action
```

The LLM proposes an operation. Deterministic validation and policy rules decide whether that operation can be performed.

This directly supports testing of non-functional requirements such as safety and robustness against malformed model output.

---

## 18. Audit Logging

Network command execution is recorded in:

```text
logs/audit.jsonl
```

Records contain information such as:

- timestamp
- command
- success/failure
- return code
- stdout
- stderr
- dry-run status when applicable

The runner automatically creates the directory:

```python
self.audit_path.parent.mkdir(parents=True, exist_ok=True)
```

Therefore, a fresh clone does not require a committed `logs/` directory.

Runtime logs are excluded from Git because they are environment-specific execution records.

---

## 19. Verification

The system verifies operations instead of assuming success.

### Firewall Verification

After blocking an IP:

```bash
iptables -C INPUT -s <IP> -j DROP
```

### Bandwidth Verification

After applying a limit:

```bash
tc class show dev <interface>
```

### Connectivity Verification

The `ping_host` tool checks actual packet delivery.

### Throughput Verification

The `test_bandwidth` tool uses `iperf3`.

The complete workflow is:

```text
Request
  ↓
Apply configuration
  ↓
Verify configuration
  ↓
Measure network behavior
  ↓
Report result
```

---

## 20. Automated Tests

Run:

```bash
pytest -q
```

The demonstrated test suite completed with:

```text
7 passed
```

The policy tests cover validation of network addresses, protected addresses, interfaces, and bandwidth limits.

---

## 21. Real Network Validation

The project was tested using two devices on the same Wi-Fi network.

### Connectivity

Linux laptop:

```text
IP:        10.7.5.27
Interface: wlo1
```

Peer:

```text
IP: 10.7.33.21
```

A successful MCP ping test produced:

```text
Status: Reachable
Packets transmitted: 3
Packets received: 3
Packet loss: 0%
Minimum RTT: 23.061 ms
Average RTT: 23.985 ms
Maximum RTT: 24.485 ms
```

### Firewall

The assistant successfully applied a DROP rule for:

```text
10.7.33.21
```

The rule was later removed using `unblock_ip`.

### Bandwidth

Baseline `iperf3` measurement:

```text
Sender:   40.9 Mbit/sec
Receiver: 39.5 Mbit/sec
```

The assistant then applied:

```text
Source IP: 10.7.5.27
Interface: wlo1
Limit:     5 Mbps
```

Independent `tc` verification showed:

```text
class htb 1:10 root prio 0 rate 5Mbit ceil 5Mbit
```

The subsequent `iperf3` measurement produced:

```text
Sender:   5.35 Mbit/sec
Receiver: 4.66 Mbit/sec
```

Thus the experiment demonstrated a real throughput change from roughly **40 Mbps to approximately 5 Mbps** through the LLM → MCP → policy → `tc` pipeline.

---

## 22. Bandwidth Test Requirement

`iperf3` bandwidth testing is different from `ping`.

For `ping`, the peer only needs to be reachable.

For `iperf3`, the peer must normally run an iperf3 server:

```bash
iperf3 -s
```

Without the server, `test_bandwidth` can fail or time out. This is an expected operational failure, not necessarily a software failure.

---

## 23. Bandwidth Limit Cleanup

The current bandwidth implementation creates an HTB root qdisc.

For the controlled lab setup, it can be removed with:

```bash
sudo tc qdisc del dev wlo1 root
```

Then verify:

```bash
sudo tc qdisc show dev wlo1
```

A dedicated `remove_bandwidth_limit` MCP tool would improve lifecycle management. In production, teardown should track and remove only the assistant-created qdisc/class/filter rather than deleting an unrelated root qdisc.

---

## 24. Docker Deployment

The Docker image contains:

- Ubuntu 24.04
- Python 3
- Python dependencies
- iptables
- iproute2
- iputils-ping
- iperf3
- sudo

The MCP server runs inside the Docker container.

The controlled lab Compose deployment uses:

```yaml
network_mode: host
```

Host networking is important for this particular lab because ordinary Docker bridge networking gives the container a separate network namespace. Host networking allows the server's Linux network tools to operate in the host networking namespace.

The live deployment also grants the container:

```yaml
cap_add:
  - NET_ADMIN
  - NET_RAW
```

These capabilities are used only for the controlled lab configuration.

### Safety Recommendation

Keep the default:

```yaml
NETWORK_ASSISTANT_EXECUTE: "0"
```

For a controlled lab only:

```bash
NETWORK_ASSISTANT_EXECUTE=1 docker compose up
```

Host networking plus network-administration capabilities can affect the host system, so live mode should not be enabled casually on a production machine.

---

## 25. Demonstration Procedure

A clean demonstration can follow this sequence.

### Step 1 — Start the Dockerized MCP Server

```bash
docker compose up
```

### Step 2 — Start the Assistant

In another terminal:

```bash
source .venv/bin/activate
python assistant.py
```

Show the six dynamically discovered MCP tools.

### Step 3 — Check Connectivity

Ask:

```text
what is the ping of 10.7.33.21
```

Show the measured result.

### Step 4 — Block the Peer

Ask:

```text
block 10.7.33.21
```

Show the selected MCP tool and successful application.

### Step 5 — Verify the Effect

Ask:

```text
what is the ping of 10.7.33.21
```

Show the connectivity failure.

### Step 6 — Restore Connectivity

Ask:

```text
unblock 10.7.33.21
```

Then ping again.

### Step 7 — Start iperf3

On the peer:

```bash
iperf3 -s
```

### Step 8 — Measure Baseline Bandwidth

Ask:

```text
what is my bandwidth with 10.7.33.21
```

Record the result.

### Step 9 — Apply a Bandwidth Limit

Ask:

```text
limit 10.7.5.27 to 5 Mbps on wlo1
```

### Step 10 — Verify `tc`

```bash
sudo tc class show dev wlo1
```

### Step 11 — Measure Bandwidth Again

Ask:

```text
what is my bandwidth with 10.7.33.21
```

Show the reduction to approximately the configured limit.

### Step 12 — Demonstrate Safety

Try an invalid/protected IP or invalid bandwidth value and show that the policy engine rejects it.

### Step 13 — Clean Up

Remove the test bandwidth configuration if required:

```bash
sudo tc qdisc del dev wlo1 root
```

Make sure any firewall test rule has also been removed.

---

## 26. Non-Functional Requirements

### Security

- No arbitrary shell execution from the LLM.
- Fixed command argument vectors.
- Policy-based authorization.
- Protected IP addresses.
- Interface allow-list.
- Restricted sudo privileges.
- Safe dry-run default.

### Reliability

- Post-action verification.
- Explicit error handling.
- Timeout protection for network commands.
- Failure results are returned to the assistant.

### Auditability

- Commands are recorded in the audit log.
- Timestamps and command results are preserved.
- Runtime logs can be inspected after a demonstration.

### Safety

- Dry-run is the default.
- Live execution is explicitly enabled.
- Network changes are restricted by policy.
- Docker provides controlled deployment.

### Maintainability

- Network operations are separated from policy logic.
- MCP server is separated from the assistant.
- Policy is stored in YAML.
- Tests are separated from implementation.

### Usability

- Natural-language commands.
- CLI interface.
- Dynamic MCP tool discovery.
- Human-readable responses.

### Portability

- Linux networking operations use standard Linux tools.
- Docker packages the MCP server dependencies.
- The LLM runs locally through Ollama.

---

## 27. Failure Handling

### Ping Failure

Possible causes:

- peer offline
- network connectivity problem
- firewall blocking
- wrong IP address

### iperf3 Timeout

Make sure the peer is running:

```bash
iperf3 -s
```

### Docker Connection Failure

Check:

```bash
docker compose ps
docker compose logs
```

Make sure the MCP server is available at:

```text
http://localhost:8000/mcp
```

### Docker Permission Failure

Check:

```bash
groups
```

If necessary:

```bash
newgrp docker
```

For live network operations, also verify the required sudo configuration.

---

## 28. Limitations

The current implementation is intended as a controlled academic/lab project.

1. Live network operations are Linux-specific.
2. Docker host networking requires careful handling.
3. The `tc` configuration is simplified for the project use case.
4. A dedicated `remove_bandwidth_limit` MCP tool would improve lifecycle management.
5. The LLM can misunderstand natural-language requests; deterministic validation reduces unsafe execution but does not guarantee perfect intent interpretation.
6. `iperf3` requires a server on the peer.
7. The current policy file represents a lab policy and should be adapted for another network.
8. Audit logs are local and are not currently centralized.

---

## 29. Future Enhancements

- Dedicated `remove_bandwidth_limit` MCP tool.
- More comprehensive automated integration tests.
- Centralized audit logging.
- Role-based authorization.
- Richer network-context discovery.
- Persistent configuration state.
- Better rollback support.
- More detailed traffic-control policies.
- Monitoring and alerting.
- Web-based administration interface.
- Containerized multi-host test topology.

---

## 30. Quick Start

### Terminal 1 — MCP Server

```bash
cd CN_Project
docker compose up
```

### Terminal 2 — Assistant

```bash
cd CN_Project
source .venv/bin/activate
python assistant.py
```

### Example Commands

```text
what is the ping of 10.7.33.21
```

```text
block 10.7.33.21
```

```text
unblock 10.7.33.21
```

For bandwidth testing, start on the peer:

```bash
iperf3 -s
```

Then:

```text
what is my bandwidth with 10.7.33.21
```

and:

```text
limit 10.7.5.27 to 5 Mbps on wlo1
```

---

## 31. Project Results

The implemented system demonstrates:

- Natural-language network administration.
- Local LLM-based tool selection.
- MCP-based tool discovery and execution.
- Deterministic policy enforcement.
- Controlled Linux firewall configuration.
- Linux traffic shaping.
- Real connectivity verification.
- Real throughput measurement.
- Malformed/invalid tool-call rejection.
- Audit logging.
- Dockerized MCP server deployment.
- Safe dry-run and explicit live-execution modes.
- Automated policy tests.

The real-network experiment demonstrated that an approximately **40 Mbps** connection could be reduced to approximately **5 Mbps** using a natural-language request processed through the LLM → MCP → policy → `tc` pipeline.

---

## 32. Conclusion

The Intelligent Network Configuration Assistant demonstrates how an LLM can be integrated with network administration without giving the model unrestricted shell access.

The LLM understands the user's intent and selects a structured MCP operation. The MCP server exposes controlled tools, while the policy engine provides deterministic authorization and validation. Linux networking utilities perform the actual operation, and verification tools measure whether the requested change took effect.

This separation of responsibilities improves **security, reliability, auditability, maintainability, and operational safety**, making the system a practical demonstration of MCP-based intelligent network automation.
