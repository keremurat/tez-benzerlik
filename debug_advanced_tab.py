#!/usr/bin/env python3
"""
Debug script to find submit button in Advanced Search tab
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
from bs4 import BeautifulSoup

def debug_advanced_tab():
    """Debug Advanced Search tab."""

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
        time.sleep(2)

        # Click advanced search tab
        wait = WebDriverWait(driver, 10)
        advanced_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
        )
        advanced_tab.click()
        print("✓ Clicked Advanced Search tab")
        time.sleep(2)

        # Find all submit buttons in the page
        print("\n=== ALL SUBMIT BUTTONS ===")
        all_submits = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
        for idx, btn in enumerate(all_submits):
            name = btn.get_attribute('name')
            value = btn.get_attribute('value')
            visible = btn.is_displayed()
            enabled = btn.is_enabled()
            print(f"{idx}: Name={name}, Value={value}, Visible={visible}, Enabled={enabled}")

        # Get the HTML of tabs-2
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        tab2 = soup.find('div', id='tabs-2')

        if tab2:
            print("\n=== SUBMIT BUTTONS IN tabs-2 ===")
            submits_in_tab2 = tab2.find_all('input', type='submit')
            for btn in submits_in_tab2:
                name = btn.get('name', '')
                value = btn.get('value', '')
                print(f"Name: {name}, Value: {value}")

            # Save tab2 HTML
            with open('/tmp/yok_tabs2.html', 'w', encoding='utf-8') as f:
                f.write(str(tab2))
            print("\n✓ tabs-2 HTML saved to /tmp/yok_tabs2.html")

        # Try finding submit button inside tabs-2
        try:
            tab2_element = driver.find_element(By.ID, 'tabs-2')
            submit_in_tab = tab2_element.find_element(By.CSS_SELECTOR, "input[type='submit']")
            print(f"\n✓ Found submit in tabs-2: name={submit_in_tab.get_attribute('name')}, visible={submit_in_tab.is_displayed()}")
        except Exception as e:
            print(f"\n✗ Error finding submit in tabs-2: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_advanced_tab()
