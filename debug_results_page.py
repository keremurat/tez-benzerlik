#!/usr/bin/env python3
"""
Debug script to capture results page structure
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

def debug_results_page():
    """Debug results page after search."""

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
        time.sleep(1)

        # Fill keyword
        keyword_input = driver.find_element(By.NAME, "keyword")
        keyword_input.send_keys("yapay zeka")
        print("✓ Entered search query")
        time.sleep(0.5)

        # Find and click submit
        active_tab = driver.find_element(By.ID, "tabs-2")
        submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(0.5)
        submit_button.click()
        print("✓ Clicked submit button")

        # Wait for page to load (results or new page)
        time.sleep(5)

        # Get current URL
        current_url = driver.current_url
        print(f"\nCurrent URL: {current_url}")

        # Save page HTML
        html = driver.page_source
        with open('/tmp/yok_results_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Results page HTML saved to /tmp/yok_results_page.html")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        # Look for tables
        print("\n=== TABLES FOUND ===")
        tables = soup.find_all('table')
        for idx, table in enumerate(tables):
            class_attr = table.get('class', [])
            id_attr = table.get('id', '')
            rows = len(table.find_all('tr'))
            print(f"Table {idx}: class={class_attr}, id={id_attr}, rows={rows}")

        # Look for result indicators
        print("\n=== SEARCHING FOR RESULT INDICATORS ===")
        result_texts = ["sonuç", "tez", "bulunamadı", "kayıt"]
        for text in result_texts:
            elements = soup.find_all(string=lambda t: text in t.lower() if t else False)
            if elements:
                print(f"Found '{text}': {len(elements)} occurrences")
                for elem in elements[:2]:
                    print(f"  - {elem[:100]}")

        # Check for iframe or form redirects
        iframes = soup.find_all('iframe')
        if iframes:
            print(f"\n✗ Found {len(iframes)} iframes - results might be in iframe")

        print("\n✓ Debug complete!")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_results_page()
