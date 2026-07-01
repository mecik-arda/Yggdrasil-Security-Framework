# Yggdrasil Security Framework v2.0.0

Yggdrasil v2.0.0 brings a massive architectural overhaul, enhancing stability, security, and the developer experience.

## Key Features & Improvements
- **Modular Architecture:** Transitioned from a monolithic `app.py` to a structured Flask Blueprints design (`auth`, `api`, `action`, `wsl`, `ai`, `rag_loki`) for ultimate scalability.
- **Enhanced Security:** Implemented brute-force protection using **Flask-Limiter** for the authentication endpoint. Dynamic generation of robust `.env` secrets.
- **Reliable Asynchronous Tasks:** Re-engineered process tracking in `tool_runner.py` and `task_manager.py` ensuring orphan processes are properly terminated upon user cancellation, effectively preventing memory leaks.
- **Odin AI & RAG Enhancements:** Centralized AI interactions, ensuring the Odin AI Node and Valkyrie AI Reporter are always reachable and stable.
- **WSL Integration:** Improved dependency checking and handling for Windows Subsystem for Linux via dedicated API routes.
- **Extensive Code Audit:** Passed a rigorous full-codebase audit resolving hidden execution discrepancies and UI bugs.

## Recent Fixes & Updates
- **Dependency Manager Evolution:** Completely rewrote the platform detection logic. The Dependency Manager now correctly identifies and displays exactly where a tool is installed: `Installed (Windows)`, `Installed (WSL)`, or `Installed (Linux)`.
- **Intelligent Tool Resolution:** Fixed `FileNotFoundError` issues for tools installed in non-standard paths (e.g., Sherlock in `venv/Scripts/` and Wireshark in `Program Files`). The framework now automatically resolves absolute paths for executions on Windows.
- **Optimized Linux Tool Execution:** Linux-exclusive tools (like Hydra, WPScan) now bypass unnecessary Windows environment checks and execute directly within the WSL boundary, boosting performance and reliability.
- **Robust Package Installations:** Solved `404 Not Found` network errors during tool installations by seamlessly integrating `apt-get update` before `apt-get install` commands. Also migrated WPScan installation to use Ruby `gem` natively on Linux.
- **Syntax Compatibility:** Resolved `CRLF` vs `LF` line-ending conflicts that caused execution failures (`\r command not found`) in custom bash scripts (e.g., Advanced SYN Scanner).
- **Startup Race Condition:** Fixed a bug where the browser opened before the Flask server was ready, preventing "Connection Refused" errors on launch.
