#!/usr/bin/env python3
"""
Debug script to capture thesis detail page structure
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

def debug_detail_page(thesis_id="788139"):
    """Debug thesis detail page."""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        detail_url = f"https://tez.yok.gov.tr/UlusalTezMerkezi/tezDetay.jsp?id={thesis_id}"
        print(f"Loading thesis detail page: {detail_url}")
        driver.get(detail_url)
        time.sleep(3)

        # Get current URL
        current_url = driver.current_url
        print(f"\nCurrent URL: {current_url}")

        # Save page HTML
        html = driver.page_source
        output_file = f'/tmp/yok_detail_{thesis_id}.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ Detail page HTML saved to {output_file}")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        # Look for all tables
        print("\n=== TABLES FOUND ===")
        tables = soup.find_all('table')
        for idx, table in enumerate(tables):
            class_attr = table.get('class', [])
            id_attr = table.get('id', '')
            rows = len(table.find_all('tr'))
            print(f"Table {idx}: class={class_attr}, id={id_attr}, rows={rows}")

            # Print first few rows
            if rows > 0:
                print("  First 3 rows:")
                for row_idx, row in enumerate(table.find_all('tr')[:3]):
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        text = [c.get_text().strip()[:50] for c in cells]
                        print(f"    Row {row_idx}: {text}")

        # Look for divs with common classes
        print("\n=== DIVS WITH COMMON CLASSES ===")
        common_classes = ['detail', 'content', 'bilgi', 'thesis', 'tez', 'info', 'main']
        for cls in common_classes:
            divs = soup.find_all('div', class_=lambda c: c and cls in str(c).lower())
            if divs:
                print(f"Found {len(divs)} div(s) with '{cls}' in class")

        # Look for spans or strong tags that might contain labels
        print("\n=== POTENTIAL LABELS ===")
        labels = soup.find_all(['strong', 'b', 'th'])
        label_texts = set()
        for label in labels[:20]:
            text = label.get_text().strip()
            if text and len(text) < 50:
                label_texts.add(text)

        for text in sorted(label_texts)[:15]:
            print(f"  - {text}")

        print("\n✓ Debug complete!")

    finally:
        driver.quit()

if __name__ == "__main__":
    # Test with thesis ID 788139 (the one that failed)
    debug_detail_page("788139")
