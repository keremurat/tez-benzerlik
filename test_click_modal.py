#!/usr/bin/env python3
"""
Test clicking thesis number and capturing modal content
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

def test_click_modal():
    """Test clicking thesis and capturing modal."""

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
        # Step 1: Search for "yapay zeka" to get results
        print("Step 1: Searching for 'yapay zeka'")
        driver.get("https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp")
        time.sleep(2)

        wait = WebDriverWait(driver, 15)
        advanced_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
        )
        advanced_tab.click()
        time.sleep(1)

        keyword_input = driver.find_element(By.NAME, "keyword")
        keyword_input.clear()
        keyword_input.send_keys("yapay zeka")
        time.sleep(0.5)

        active_tab = driver.find_element(By.ID, "tabs-2")
        submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")
        submit_button.click()
        print("✓ Submitted search")

        # Wait for results to load
        time.sleep(5)

        # Step 2: Find and click first thesis number
        print("\nStep 2: Finding thesis number to click")

        # Find first span with onclick
        try:
            first_thesis_span = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.watable tbody span[onclick*='tezDetay']"))
            )
            thesis_id = first_thesis_span.text.strip()
            print(f"✓ Found thesis ID: {thesis_id}")
        except:
            print("✗ Could not find thesis span")
            return

        # Click on it
        print(f"\nStep 3: Clicking on thesis {thesis_id}")
        driver.execute_script("arguments[0].click();", first_thesis_span)
        print("✓ Clicked")

        # Wait for modal to appear
        print("\nStep 4: Waiting for modal dialog")
        time.sleep(3)

        # Try to find modal dialog
        try:
            modal = wait.until(
                EC.presence_of_element_located((By.ID, "dialog-modal"))
            )
            print("✓ Modal dialog appeared")

            # Get modal content
            modal_html = modal.get_attribute('innerHTML')

            # Save it
            with open(f'/tmp/modal_content_{thesis_id}.html', 'w', encoding='utf-8') as f:
                f.write(modal_html)
            print(f"✓ Saved modal content to /tmp/modal_content_{thesis_id}.html")

            # Parse modal content
            soup = BeautifulSoup(modal_html, 'lxml')

            # Look for thesis details
            print("\n=== MODAL CONTENT ===")

            # Try to find detail table
            detail_table = soup.find('table', class_='bilgi')
            if detail_table:
                print("✓ Found detail table in modal")
                rows = detail_table.find_all('tr')
                print(f"  Rows: {len(rows)}")
                for row in rows[:10]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip()
                        value = cells[1].get_text().strip()[:60]
                        print(f"    {key}: {value}")
            else:
                print("✗ No detail table found")
                # Print first 500 chars of modal
                text = soup.get_text()[:500]
                print(f"Modal text: {text}")

        except Exception as e:
            print(f"✗ Could not find modal: {e}")

            # Check page source for any dialog/modal
            page_html = driver.page_source
            if "dialog-modal" in page_html:
                print("✓ dialog-modal exists in page source")
            else:
                print("✗ dialog-modal not found in page")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    test_click_modal()
