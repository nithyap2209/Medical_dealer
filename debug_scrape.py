"""Debug script to check JustDial and IndiaMART page structure."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # ---- TEST JUSTDIAL ----
    print("=" * 50)
    print("TESTING JUSTDIAL")
    print("=" * 50)
    url_jd = "https://www.justdial.com/Chennai/medical-dealers"
    print(f"URL: {url_jd}")
    page.goto(url_jd, timeout=60000, wait_until="domcontentloaded")
    time.sleep(5)

    # Save page HTML for inspection
    html = page.content()
    with open("debug_justdial.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Page title: {page.title()}")
    print(f"Page URL after load: {page.url}")
    print(f"HTML length: {len(html)}")

    # Try various selectors
    selectors_jd = [
        'li[class*="resultbox"]',
        'div.resultbox_info',
        'div.store-details',
        'div.resultbox_content',
        'div[class*="result"]',
        'div[class*="card"]',
        'section[class*="result"]',
        'div.jsx-card',
        'a[class*="result"]',
        'div[class*="listing"]',
        'div[class*="comp"]',
    ]
    for sel in selectors_jd:
        items = page.query_selector_all(sel)
        if items:
            print(f"  FOUND: {sel} -> {len(items)} items")
            # Print first item's text
            try:
                text = items[0].inner_text()[:200]
                print(f"    First item text: {text}")
            except:
                pass

    # Also dump all class names from top-level divs
    print("\nTop-level div classes (first 30):")
    divs = page.query_selector_all("body > div, body > div > div, main div")
    seen_classes = set()
    count = 0
    for d in divs:
        cls = d.get_attribute("class") or ""
        if cls and cls not in seen_classes and count < 30:
            seen_classes.add(cls)
            count += 1
            # Check if it has multiple children (likely a list container)
            children = d.query_selector_all(":scope > *")
            if len(children) > 3:
                print(f"  class='{cls[:80]}' children={len(children)}")

    print("\n" + "=" * 50)
    print("TESTING INDIAMART")
    print("=" * 50)
    url_im = "https://dir.indiamart.com/search.mp?ss=medical+dealers&city=Chennai"
    print(f"URL: {url_im}")
    page.goto(url_im, timeout=60000, wait_until="domcontentloaded")
    time.sleep(5)

    html2 = page.content()
    with open("debug_indiamart.html", "w", encoding="utf-8") as f:
        f.write(html2)
    print(f"Page title: {page.title()}")
    print(f"Page URL after load: {page.url}")
    print(f"HTML length: {len(html2)}")

    selectors_im = [
        'div.lst-ca',
        'div[class*="cardlinks"]',
        'div.suplr-card',
        'div.ls-card',
        'div[class*="supplier"]',
        'div[class*="listing"]',
        'div[class*="result"]',
        'div[class*="card"]',
        'div[class*="comp"]',
        'div[class*="prod"]',
    ]
    for sel in selectors_im:
        items = page.query_selector_all(sel)
        if items:
            print(f"  FOUND: {sel} -> {len(items)} items")
            try:
                text = items[0].inner_text()[:200]
                print(f"    First item text: {text}")
            except:
                pass

    print("\nTop-level div classes (first 30):")
    divs2 = page.query_selector_all("body > div, body > div > div, main div")
    seen_classes2 = set()
    count2 = 0
    for d in divs2:
        cls = d.get_attribute("class") or ""
        if cls and cls not in seen_classes2 and count2 < 30:
            seen_classes2.add(cls)
            count2 += 1
            children = d.query_selector_all(":scope > *")
            if len(children) > 3:
                print(f"  class='{cls[:80]}' children={len(children)}")

    browser.close()
    print("\nDone! Check debug_justdial.html and debug_indiamart.html")
