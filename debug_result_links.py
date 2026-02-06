#!/usr/bin/env python3
"""
Debug script - check how result links are structured
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

def check_result_links():
    """Check how links in results table work."""

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
        # Load and search
        print("Loading search page and searching...")
        driver.get("https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp")
        time.sleep(2)

        wait = WebDriverWait(driver, 10)
        advanced_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
        )
        advanced_tab.click()
        time.sleep(1)

        keyword_input = driver.find_element(By.NAME, "keyword")
        keyword_input.send_keys("yapay zeka")
        time.sleep(0.5)

        active_tab = driver.find_element(By.ID, "tabs-2")
        submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")
        submit_button.click()
        time.sleep(5)

        # Parse results
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        table = soup.find('table', class_='watable')
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')[:3]  # First 3 results
                print(f"\n=== FIRST 3 RESULTS ===")

                for idx, row in enumerate(rows):
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        # Check for links in the ID or title cell
                        thesis_id_cell = cells[1]
                        title_cell = cells[4] if len(cells) > 4 else None

                        thesis_id = thesis_id_cell.get_text().strip()
                        print(f"\nResult {idx + 1}: ID = {thesis_id}")

                        # Check for links
                        link_in_id = thesis_id_cell.find('a')
                        if link_in_id:
                            href = link_in_id.get('href', '')
                            onclick = link_in_id.get('onclick', '')
                            print(f"  ID cell link href: {href}")
                            print(f"  ID cell link onclick: {onclick}")

                        if title_cell:
                            link_in_title = title_cell.find('a')
                            if link_in_title:
                                href = link_in_title.get('href', '')
                                onclick = link_in_title.get('onclick', '')
                                print(f"  Title cell link href: {href}")
                                print(f"  Title cell link onclick: {onclick}")

                # Try clicking first result link
                print("\n=== TRYING TO CLICK FIRST RESULT ===")
                first_row = driver.find_element(By.CSS_SELECTOR, "table.watable tbody tr:first-child")
                links = first_row.find_elements(By.TAG_NAME, "a")

                if links:
                    print(f"Found {len(links)} links in first row")
                    first_link = links[0]
                    print(f"Clicking first link...")

                    # Click it
                    first_link.click()
                    time.sleep(4)

                    # Check current URL
                    current_url = driver.current_url
                    print(f"✓ After click, URL: {current_url}")

                    # Check if detail page loaded
                    detail_html = driver.page_source
                    if "BEKLENMEDİK BİR HATA" in detail_html:
                        print("✗ Still getting error after clicking link")
                    else:
                        print("✓ Detail page loaded successfully!")

                        # Save it
                        with open('/tmp/yok_detail_clicked.html', 'w', encoding='utf-8') as f:
                            f.write(detail_html)
                        print("✓ Saved to /tmp/yok_detail_clicked.html")

                        # Check for detail table
                        detail_soup = BeautifulSoup(detail_html, 'lxml')
                        detail_table = detail_soup.find('table', class_='bilgi')
                        if detail_table:
                            print(f"✓ Found detail table with class='bilgi'")
                            rows = detail_table.find_all('tr')
                            print(f"  {len(rows)} rows in detail table")
                        else:
                            # Try other selectors
                            all_tables = detail_soup.find_all('table')
                            print(f"  Found {len(all_tables)} tables total (no 'bilgi' class)")
                else:
                    print("✗ No links found in first row")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    check_result_links()
