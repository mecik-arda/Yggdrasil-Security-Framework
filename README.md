# ᚛᚜ Yggdrasil Security Framework ᚛᚜

This repository features an advanced security reconnaissance and vulnerability assessment framework developed to centralize offensive security operations. It integrates industry-standard tools into a unified, Norse-themed dashboard to streamline the information gathering and exploitation phases of a penetration test.

## Project Reflection & Technical Q&A

### 1. Why did I write the code this way? (XYZ Analysis)
* My objective was to eliminate the inefficiency of switching between multiple command-line tools during a security audit. 
* I accomplished a centralized, web-based management system as measured by reducing tool initialization and reporting time by integrating a Python Flask backend with a dynamic Runic Dashboard. 
* This ensures that reconnaissance data is visualized and logged in real-time within a cohesive operational environment.

### 2. What challenges did I face?
* **Subprocess Management**: Handling multiple concurrent security tools required a robust subprocess execution logic to prevent the Flask backend from hanging during intensive scans.
* **Dependency Orchestration**: I implemented a "Runic Installation Ritual" (Automated Dependency Checker) to detect missing system tools and install them dynamically without manual user intervention.
* **Output Streaming**: Implementing the typewriter effect for real-time output rendering was a challenge in managing asynchronous JavaScript data streams within a synchronous HTML environment.

### 3. How did I manage the Security Arsenal?
* **Modular Integration**: I architected a modular command execution engine that handles specialized flags for Nmap, Sqlmap, Nikto, and WPScan to ensure optimal scan accuracy.
* **Artifact Logging**: The framework includes a reporting module that sanitizes terminal output and exports it into structured TXT or JSON artifacts for professional security documentation.

## Technical Specifications
* **Language**: Python 3.x, HTML5, CSS3, JavaScript (ES6)
* **Backend**: Flask Framework
* **Integrated Arsenal**: Nmap, Sqlmap, Nikto, WPScan, Amass, Sherlock, theHarvester
* **Theming**: Runic/Nordic Aesthetic with Custom CSS Overlays and Typewriter Logic

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---
**Author**: Arda Meçik  
**Position**: Computer Engineering Student at Trakya University  
**Student ID**: 1241602620