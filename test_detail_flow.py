#!/usr/bin/env python3
"""
Test the complete detail flow
"""

import sys
import time
import re
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

def test_detail_flow(thesis_id="962889"):
    """Test the complete flow."""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    )

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    try:
        # Step 1: Search
        print(f"Step 1: Searching for thesis ID {thesis_id}")
        driver.get("https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp")
        time.sleep(2)

        wait = WebDriverWait(driver, 10)
        advanced_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
        )
        advanced_tab.click()
        time.sleep(1)

        keyword_input = driver.find_element(By.NAME, "keyword")
        keyword_input.clear()
        keyword_input.send_keys(thesis_id)
        time.sleep(0.5)

        active_tab = driver.find_element(By.ID, "tabs-2")
        submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")
        submit_button.click()
        print("✓ Submitted search")

        # Wait for page to change
        time.sleep(5)

        # Check current URL
        current_url = driver.current_url
        print(f"Current URL after search: {current_url}")

        # Save the page to see what we got
        html = driver.page_source
        with open('/tmp/search_result_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Saved page to /tmp/search_result_page.html")

        # Step 2: Parse results
        print("\nStep 2: Parsing results")
        soup = BeautifulSoup(html, 'lxml')

        table = soup.find('table', class_='watable')
        if not table:
            print("✗ No results table found")
            return

        tbody = table.find('tbody')
        if not tbody:
            print("✗ No tbody found")
            return

        # Find all spans with onclick
        spans_with_onclick = tbody.find_all('span', onclick=True)
        print(f"✓ Found {len(spans_with_onclick)} spans with onclick")

        if len(spans_with_onclick) == 0:
            print("\n✗ No clickable thesis IDs found")
            # Check all cells
            all_cells = tbody.find_all('td')
            print(f"Total cells in tbody: {len(all_cells)}")
            for idx, cell in enumerate(all_cells[:10]):
                print(f"  Cell {idx}: {cell.get_text().strip()[:50]}")
            return

        # Look for thesis ID
        target_span = None
        for idx, span in enumerate(spans_with_onclick):
            span_text = span.get_text().strip()
            onclick = span.get('onclick', '')
            print(f"\nSpan {idx}:")
            print(f"  Text: {span_text}")
            print(f"  Onclick: {onclick[:80]}...")

            if thesis_id in span_text:
                target_span = span
                print(f"  ✓ MATCH! Found thesis ID {thesis_id}")
                break

        if not target_span:
            print(f"\n✗ Thesis ID {thesis_id} not found in any span")
            return

        # Step 3: Extract encrypted params
        print("\nStep 3: Extracting encrypted parameters")
        onclick = target_span.get('onclick', '')
        match = re.search(r"tezDetay\('([^']+)','([^']+)'\)", onclick)

        if not match:
            print("✗ Could not parse onclick")
            return

        encrypted_id = match.group(1)
        encrypted_no = match.group(2)
        print(f"✓ Encrypted ID: {encrypted_id}")
        print(f"✓ Encrypted NO: {encrypted_no}")

        # Step 4: Access detail page
        print("\nStep 4: Accessing detail page")
        detail_url = f"https://tez.yok.gov.tr/UlusalTezMerkezi/tezDetay.jsp?id={encrypted_id}&no={encrypted_no}"
        driver.get(detail_url)
        time.sleep(3)

        detail_html = driver.page_source

        if "BEKLENMEDİK BİR HATA" in detail_html:
            print("✗ Error page returned")
            return

        print("✓ Detail page loaded!")

        # Save detail page
        with open(f'/tmp/detail_{thesis_id}_success.html', 'w', encoding='utf-8') as f:
            f.write(detail_html)
        print(f"✓ Saved to /tmp/detail_{thesis_id}_success.html")

        # Parse details
        detail_soup = BeautifulSoup(detail_html, 'lxml')
        detail_table = detail_soup.find('table', class_='bilgi')

        if detail_table:
            print("\n✓ Found detail table with class='bilgi'")
            rows = detail_table.find_all('tr')
            print(f"  Rows: {len(rows)}")
            for idx, row in enumerate(rows[:5]):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip()
                    value = cells[1].get_text().strip()[:50]
                    print(f"    {key}: {value}")
        else:
            print("\n✗ No detail table with class='bilgi' found")
            all_tables = detail_soup.find_all('table')
            print(f"  Total tables: {len(all_tables)}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    test_detail_flow("962889")
