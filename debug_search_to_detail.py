#!/usr/bin/env python3
"""
Debug script - search first, then go to detail page (natural flow)
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

def test_search_to_detail():
    """Try search first, then access detail."""

    # Setup Chrome with anti-detection
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    # User agent
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    )

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Remove webdriver property
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    try:
        # Step 1: Load search page first
        print("Step 1: Loading YÖK search page...")
        driver.get("https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp")
        time.sleep(3)
        print(f"✓ Current URL: {driver.current_url}")

        # Save cookies
        cookies = driver.get_cookies()
        print(f"✓ Got {len(cookies)} cookies")

        # Step 2: Perform a simple search
        print("\nStep 2: Performing search for 'yapay zeka'...")
        wait = WebDriverWait(driver, 10)

        # Click advanced search tab
        advanced_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
        )
        advanced_tab.click()
        print("✓ Clicked advanced search tab")
        time.sleep(1)

        # Fill keyword
        keyword_input = driver.find_element(By.NAME, "keyword")
        keyword_input.send_keys("yapay zeka")
        print("✓ Entered search query")
        time.sleep(0.5)

        # Click submit
        active_tab = driver.find_element(By.ID, "tabs-2")
        submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")
        submit_button.click()
        print("✓ Clicked submit")

        # Wait for results
        time.sleep(5)
        print(f"✓ Results page URL: {driver.current_url}")

        # Parse results to find a thesis ID
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # Find results table
        table = soup.find('table', class_='watable')
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                print(f"\n✓ Found {len(rows)} results")

                # Get first thesis ID
                if len(rows) > 0:
                    first_row = rows[0]
                    cells = first_row.find_all('td')
                    if len(cells) > 1:
                        thesis_id = cells[1].get_text().strip()
                        thesis_title = cells[4].get_text().strip()[:60] if len(cells) > 4 else "N/A"
                        print(f"\nFirst result:")
                        print(f"  ID: {thesis_id}")
                        print(f"  Title: {thesis_title}")

                        # Step 3: Now try to access detail page with session
                        print(f"\nStep 3: Accessing detail page for thesis {thesis_id}...")
                        detail_url = f"https://tez.yok.gov.tr/UlusalTezMerkezi/tezDetay.jsp?id={thesis_id}"
                        driver.get(detail_url)
                        time.sleep(3)

                        # Check if we got the detail page or error
                        detail_html = driver.page_source
                        if "BEKLENMEDİK BİR HATA" in detail_html:
                            print("✗ Still getting error on detail page")
                        else:
                            print("✓ Detail page loaded successfully!")

                            # Save detail page
                            with open(f'/tmp/yok_detail_from_search_{thesis_id}.html', 'w', encoding='utf-8') as f:
                                f.write(detail_html)
                            print(f"✓ Saved to /tmp/yok_detail_from_search_{thesis_id}.html")

                            # Parse to check if we got data
                            detail_soup = BeautifulSoup(detail_html, 'lxml')
                            tables = detail_soup.find_all('table')
                            print(f"\n✓ Found {len(tables)} tables in detail page")
                            for idx, t in enumerate(tables[:3]):
                                rows = t.find_all('tr')
                                print(f"  Table {idx}: {len(rows)} rows")
        else:
            print("✗ No results table found")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    test_search_to_detail()
