# Yggdrasil Security Framework v2.0.0

## New Features

### C2 & Reverse Shell Manager
- Built-in TCP listener module for catching reverse shell connections directly in the web UI
- Real-time zombie system tracking with interactive web terminal
- One-click payload generator (Python, Bash, Netcat, PHP, Ruby, Perl, PowerShell)
- Multi-listener support with independent port management
- Live output streaming from connected zombies

### Autonomous Red Team AI (Auto-Exploitation)
- Upgraded Odin AI agent with dedicated red team mode (15-step autonomous operations)
- Automatic nmap TCP scan, vulnerability detection, and service enumeration
- Conditional exploitation: auto-launches sqlmap on SQL services, hydra on SSH, nuclei for CVE detection
- Auto-populates attack graph with discovered targets, ports, subdomains, and vulnerabilities
- Fallback rule-based decision engine when Ollama is unavailable

### Metasploit & Payload Crafter Integration
- msfvenom integration for Windows/Linux/Android/macOS/Web payloads
- Encoder support (shikata_ga_nai, xor, powershell_base64)
- Standalone payload generation when msfvenom is not installed
- Built-in msfconsole command execution interface
- Payload download with automatic file management

### Network Attack Graph Visualization
- Interactive canvas-based attack graph with color-coded node types
- Manual node addition and removal via click/right-click
- Auto-population from scan history (ports, subdomains, vulnerabilities)
- Hierarchical tree layout with parent-child relationships
- Session-based graph isolation for multiple concurrent operations

## Technical Details
- 8 new backend files (handlers, routes)
- 2 new UI modal templates
- 3 new SQLite database tables (c2_sessions, payload_history, attack_graph_nodes)
- Extended agent loop with 15-step red team mode
- All features registered as Flask Blueprints
