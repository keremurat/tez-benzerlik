#!/usr/bin/env python3
"""
Debug script to inspect YÖK page structure
Saves the page HTML to a file for inspection
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def inspect_yok_page():
    """Inspect YÖK page and save HTML structure."""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("Loading YÖK search page...")
        driver.get("https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp")

        # Wait for page to load
        time.sleep(3)

        # Save full page HTML
        html = driver.page_source
        with open('/tmp/yok_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Page HTML saved to /tmp/yok_page.html")

        # Find all input fields
        print("\n=== INPUT FIELDS ===")
        inputs = driver.find_elements(By.TAG_NAME, 'input')
        for inp in inputs[:20]:  # First 20 inputs
            input_type = inp.get_attribute('type')
            input_name = inp.get_attribute('name')
            input_id = inp.get_attribute('id')
            input_placeholder = inp.get_attribute('placeholder')
            if input_type in ['text', 'submit']:
                print(f"Type: {input_type}, Name: {input_name}, ID: {input_id}, Placeholder: {input_placeholder}")

        # Find all select elements
        print("\n=== SELECT ELEMENTS ===")
        selects = driver.find_elements(By.TAG_NAME, 'select')
        for sel in selects:
            sel_name = sel.get_attribute('name')
            sel_id = sel.get_attribute('id')
            print(f"Name: {sel_name}, ID: {sel_id}")

        # Find tabs
        print("\n=== TABS ===")
        tabs = driver.find_elements(By.CSS_SELECTOR, 'a[href^="#tabs"], a[id^="ui-id"]')
        for tab in tabs:
            tab_href = tab.get_attribute('href')
            tab_id = tab.get_attribute('id')
            tab_text = tab.text
            print(f"ID: {tab_id}, Href: {tab_href}, Text: {tab_text}")

        # Try clicking detailed search tab
        print("\n=== CLICKING DETAILED SEARCH TAB ===")
        try:
            wait = WebDriverWait(driver, 10)
            detailed_tab = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-1']"))
            )
            detailed_tab.click()
            print("✓ Clicked tab successfully")
            time.sleep(2)

            # Save HTML after tab click
            html_after = driver.page_source
            with open('/tmp/yok_page_after_tab.html', 'w', encoding='utf-8') as f:
                f.write(html_after)
            print("✓ Page HTML after tab click saved to /tmp/yok_page_after_tab.html")

            # Find input fields in the active tab
            print("\n=== INPUT FIELDS IN DETAILED SEARCH TAB ===")
            tab_inputs = driver.find_elements(By.CSS_SELECTOR, '#tabs-1 input[type="text"]')
            for inp in tab_inputs:
                input_name = inp.get_attribute('name')
                input_id = inp.get_attribute('id')
                input_placeholder = inp.get_attribute('placeholder')
                print(f"Name: {input_name}, ID: {input_id}, Placeholder: {input_placeholder}")
        except Exception as e:
            print(f"✗ Error: {e}")

        print("\n" + "=" * 60)
        print("✓ Inspection complete!")
        print("Check /tmp/yok_page.html and /tmp/yok_page_after_tab.html for full HTML")

    finally:
        driver.quit()

if __name__ == "__main__":
    inspect_yok_page()
