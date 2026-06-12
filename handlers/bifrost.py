import subprocess
import platform
import os

def handle_bifrost_gateway(target, data):
    current_os = platform.system()
    bifrost_dir = os.path.join(os.getcwd(), 'Runes', 'bifrost-gateway')
    
    if not os.path.exists(bifrost_dir):
        return ">> ERROR: Bifrost Gateway directory not found. Please check Runes directory."

    try:
        if current_os == 'Windows':
            # Run Spring Boot backend in a new command window and keep it open on error (/k)
            subprocess.Popen('start "Bifrost Gateway [Live Logs]" cmd /k "mvn spring-boot:run"', shell=True, cwd=bifrost_dir)
        else:
            # Run in terminal using x-terminal-emulator
            subprocess.Popen(['x-terminal-emulator', '-e', 'bash -c "mvn spring-boot:run"'], cwd=bifrost_dir)
            
        return ">> INITIATING BIFROST SECURITY GATEWAY...\n>> PLEASE CHECK YOUR NEW TERMINAL WINDOW FOR LIVE TRAFFIC LOGS."
    except Exception as e:
        return f"System Error: {str(e)}"
