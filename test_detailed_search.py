#!/usr/bin/env python3
"""
Test YÖK detailed search form to find thesis ID field
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

def test_detailed_search():
    """Test detailed search form."""

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

        # Click detailed search tab (tabs-1)
        wait = WebDriverWait(driver, 10)
        detailed_tab = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-1']"))
        )
        detailed_tab.click()
        print("✓ Clicked Detailed Search tab")
        time.sleep(2)

        # Get the HTML of tabs-1
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # Find tabs-1 div
        tabs1 = soup.find('div', id='tabs-1')

        if tabs1:
            print("\n=== DETAILED SEARCH FORM FIELDS ===")

            # Find all input fields
            inputs = tabs1.find_all('input', type='text')
            for inp in inputs:
                name = inp.get('name', '')
                placeholder = inp.get('placeholder', '')
                print(f"Input: name='{name}', placeholder='{placeholder}'")

            # Find all select fields
            selects = tabs1.find_all('select')
            for sel in selects:
                name = sel.get('name', '')
                print(f"Select: name='{name}'")

            # Save the form HTML
            with open('/tmp/yok_detailed_search_form.html', 'w', encoding='utf-8') as f:
                f.write(str(tabs1))
            print("\n✓ Saved form HTML to /tmp/yok_detailed_search_form.html")

            # Try searching by year only to get many results
            print("\n=== TESTING YEAR-ONLY SEARCH ===")

            # Find year select and set to 2025
            try:
                year_select = driver.find_element(By.NAME, "yil1")
                driver.execute_script("arguments[0].value = '2025';", year_select)
                print("✓ Set year to 2025")

                # Submit
                tabs1_div = driver.find_element(By.ID, "tabs-1")
                submit_btn = tabs1_div.find_element(By.CSS_SELECTOR, "input[type='submit']")
                submit_btn.click()
                print("✓ Submitted year search")

                time.sleep(5)

                # Check if we got results
                result_html = driver.page_source
                if "979219" in result_html:
                    print("\n✓✓✓ FOUND thesis 979219 in year 2025 search!")
                else:
                    # Count results
                    result_soup = BeautifulSoup(result_html, 'lxml')
                    table = result_soup.find('table', class_='watable')
                    if table:
                        tbody = table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            print(f"\n✓ Got {len(rows)} results from 2025")

                            # Check first few thesis IDs
                            for idx, row in enumerate(rows[:10]):
                                cells = row.find_all('td')
                                if len(cells) > 1:
                                    thesis_id = cells[1].get_text().strip()
                                    print(f"  Result {idx+1}: {thesis_id}")
                    else:
                        print("\n✗ No results table found")

            except Exception as e:
                print(f"✗ Error testing year search: {e}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    test_detailed_search()
