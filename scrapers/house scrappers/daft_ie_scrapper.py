# daft_ie_scraper.py
import yaml
import re
import time
from typing import List, Dict, Set
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class DaftIEScraper:
    def __init__(self, config_path: str = "D:/Live Labor-Housing Mismatch Index 2025 (Dublin)/config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None
        self.seen_urls: Set[str] = set()
        self._init_driver()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["daft_ie"]

    def _init_driver(self):
        options = Options()
        if self.config["scraper"]["headless"]:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.config["scraper"]["timeout"])

    def _get_page_url(self, page: int) -> str:
        base = self.config["website"]["base_url"]
        path = self.config["website"]["search_path"]
        # Replace ?page=1 with ?page={page}
        path = re.sub(r'\?page=\d+', f'?page={page}', path)
        return base + path

    def _detect_furnished(self, text: str) -> str:
        t = text.lower()
        if "unfurnished" in t:
            return "No"
        elif "partially furnished" in t or "part-furnished" in t:
            return "Partially"
        elif "furnished" in t:
            return "Yes"
        else:
            return "Unknown"

    def _extract_beds_baths(self, description: str) -> tuple:
        """Extract beds and baths from description text"""
        beds = 1  # default minimum
        baths = 1  # default minimum

        desc_lower = description.lower()

        # Extract beds
        beds_match = re.search(r'(\d+)\s*bed', desc_lower)
        if beds_match:
            beds = int(beds_match.group(1))

        # Extract baths
        baths_match = re.search(r'(\d+)\s*bath', desc_lower)
        if baths_match:
            baths = int(baths_match.group(1))

        return beds, baths

    def scrap_all_pages(self) -> List[Dict]:
        all_listings = []
        page = 1
        consecutive_empty_pages = 0
        max_empty_pages = 3

        while True:
            url = self._get_page_url(page)
            print(f"\n[PAGE {page}] Loading: {url}")

            try:
                self.driver.get(url)
                time.sleep(self.config["scraper"]["delay"])
            except TimeoutException:
                print(f"[ERROR] Page {page} timed out. Stopping.")
                break

            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            homes_html = soup.find('ul', class_='sc-798c155d-4 kmVnWY')

            if not homes_html:
                consecutive_empty_pages += 1
                print(f"[INFO] No listings container on page {page}. Empty count: {consecutive_empty_pages}")
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"[DONE] Stopped after {max_empty_pages} consecutive empty pages.")
                    break
                page += 1
                continue

            homes_items = homes_html.find_all('li')

            if not homes_items:
                consecutive_empty_pages += 1
                print(f"[INFO] No listings on page {page}. Empty count: {consecutive_empty_pages}")
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"[DONE] Stopped after {max_empty_pages} consecutive empty pages.")
                    break
                page += 1
                continue

            print(f"[PAGE {page}] Found {len(homes_items)} potential listings")

            page_listings = self._parse_page(homes_items)

            if not page_listings:
                consecutive_empty_pages += 1
                print(f"[PAGE {page}] No valid listings after parsing. Empty count: {consecutive_empty_pages}")
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"[DONE] Stopped after {max_empty_pages} consecutive empty pages.")
                    break
            else:
                consecutive_empty_pages = 0
                new_count = 0
                for listing in page_listings:
                    if listing["url"] not in self.seen_urls:
                        self.seen_urls.add(listing["url"])
                        all_listings.append(listing)
                        new_count += 1
                print(f"[PAGE {page}] Added {new_count} new listings")

            page += 1
            time.sleep(1)

        print(f"\n[FINAL] Total unique listings scraped: {len(all_listings)}")
        return all_listings

    def _parse_page(self, homes_items) -> List[Dict]:
        listings = []

        for i, home in enumerate(homes_items, 1):
            try:
                # Price
                price = home.find('p', class_='sc-af41020b-0 dqCzFn')
                if not price:
                    price = home.find('p', class_='sc-af41020b-0 bfBSFC')

                # Category and location
                category = home.find('p', class_='sc-af41020b-0 btpgrM')
                location = home.find('p', class_='sc-af41020b-0 dVPJAx')

                # Skip if no category and location (might be ad)
                if not category and not location:
                    continue

                # URL
                house_url_tag = home.find('a', class_='sc-798c155d-19 cDtUBM')
                home_url = house_url_tag['href'] if house_url_tag and house_url_tag.get('href') else None

                if not home_url or home_url == 'N/A':
                    continue

                # Description
                description_div = home.find('div', class_='sc-620b3daf-1 lgLxys')
                if description_div:
                    description_spans = description_div.find_all('span')
                    if description_spans:
                        description = ' | '.join([span.text.strip() for span in description_spans])
                    else:
                        description = description_div.text.strip() if description_div.text.strip() else ''
                else:
                    description = ''

                # Extract rent from price text
                price_text = price.text if price else ''
                rent_match = re.search(r'€([\d,]+)', price_text)
                rent_value = int(rent_match.group(1).replace(',', '')) if rent_match else None

                # Check if rent is weekly or monthly
                price_lower = price_text.lower()
                if 'month' in price_lower or '/m' in price_lower or 'pm' in price_lower:
                    rent_eur = rent_value
                    rent_period = "monthly"
                    original_rent = rent_value
                elif 'week' in price_lower or '/w' in price_lower or 'pw' in price_lower:
                    # Weekly rent, convert to monthly
                    rent_period = "weekly"
                    original_rent = rent_value
                    rent_eur = round(rent_value * (52 / 12)) if rent_value else None
                else:
                    # Default to monthly if unclear
                    rent_eur = rent_value
                    rent_period = "monthly"
                    original_rent = rent_value

                # Extract beds and baths from description
                beds, baths = self._extract_beds_baths(description)

                # Build summary from category
                category_text = category.text if category else ''
                summary = category_text

                # Build address from location
                address = location.text if location else ''

                # Detect furnished status
                furnished = self._detect_furnished(description + ' ' + category_text)

                data = {
                    "source": "daft.ie",
                    "address": address,
                    "url": home_url,
                    "rent_eur": rent_eur,
                    "rent_period": rent_period,
                    "original_rent": original_rent,
                    "summary": summary,
                    "beds": beds,
                    "baths": baths,
                    "furnished": furnished,
                }

                listings.append(data)

            except Exception as e:
                print(f"  [WARN] Failed item {i}: {e}")
                continue

        return listings

    def run(self) -> List[Dict]:
        listings = self.scrap_all_pages()
        self.driver.quit()
        return listings

    def __del__(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
