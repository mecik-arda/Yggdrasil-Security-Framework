import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_frontend():
    print("Setting up Chrome...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Navigating to http://127.0.0.1:5000/ ...")
        driver.get("http://127.0.0.1:5000/")
        
        # Wait a bit for JS to load
        time.sleep(1)

        # Login
        print("Logging in...")
        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys("yggdrasil2026")
        password_input.submit()
        
        time.sleep(2)

        print("Page scripts:", driver.execute_script("return Array.from(document.scripts).map(s => s.src);"))
        
        # Check console errors
        print("Checking for JavaScript errors...")
        logs = driver.get_log('browser')
        for log in logs:
            print(f"[{log['level']}] {log['message']}")

        # 1. Test Loki WAF Evader panel
        print("Testing 'Loki WAF Evader' panel...")
        try:
            driver.execute_script("openLokiPanel();")
            time.sleep(1)
            loki_modal = driver.find_element(By.ID, "lokiModal")
            if loki_modal.is_displayed():
                print("Loki WAF Evader panel opened successfully! ✅")
            else:
                print("Loki WAF Evader panel failed to open! ❌")
        except Exception as e:
            print(f"Error testing Loki panel: {e}")

        # 2. Test GTFOBins modal
        print("Testing 'GTFOBins' modal...")
        try:
            driver.execute_script("openGtfobinsModal();")
            time.sleep(1)
            gtfo_modal = driver.find_element(By.ID, "gtfobinsModal")
            if gtfo_modal.is_displayed():
                print("GTFOBins modal opened successfully! ✅")
            else:
                print("GTFOBins modal failed to open! ❌")
        except Exception as e:
            print(f"Error testing GTFOBins modal: {e}")

        # 3. Test random GUI modal (C2 Framework)
        print("Testing random GUI modal (C2 Framework)...")
        try:
            driver.execute_script("openC2Modal();")
            time.sleep(1)
            c2_modal = driver.find_element(By.ID, "c2Modal")
            if c2_modal.is_displayed():
                print("C2 Framework modal opened successfully! ✅")
            else:
                print("C2 Framework modal failed to open! ❌")
        except Exception as e:
            print(f"Error testing C2 Framework modal: {e}")

    finally:
        driver.quit()
        print("Test complete.")

if __name__ == '__main__':
    test_frontend()
