# myhome_ie_scraper.py
import csv
import re
import time
import yaml
from typing import List, Dict, Set
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class MyHomeIEScraper:
    def __init__(self, config_path: str = "D:/Live Labor-Housing Mismatch Index 2025 (Dublin)/config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None
        self.seen_urls: Set[str] = set()
        self._init_driver()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["myhome_ie"]

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

    def scrap_all_pages(self) -> List[Dict]:
        all_listings = []
        page = 1

        while True:
            url = self._get_page_url(page)
            print(f"\n[PAGE {page}] Loading: {url}")

            try:
                self.driver.get(url)
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.property-card")))
                time.sleep(self.config["scraper"]["delay"])
            except TimeoutException:
                print(f"[ERROR] Page {page} timed out. Stopping.")
                break

            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.property-card")
            if not cards:
                print(f"[INFO] No listings on page {page}. Stopping.")
                break

            print(f"[PAGE {page}] Found {len(cards)} listings")

            page_listings = self._parse_page(cards)
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

    def _parse_page(self, cards) -> List[Dict]:
        listings = []
        for i, card in enumerate(cards, 1):
            try:
                data = {
                    "source": "myhome.ie",
                }

                # Address & URL
                addr_elem = card.find_element(By.CSS_SELECTOR, "h3.card-text")
                data["address"] = addr_elem.text.strip()
                link_elem = card.find_element(By.CSS_SELECTOR, "a")
                data["url"] = "" + link_elem.get_attribute("href")

                # Price
                price_elem = card.find_element(By.CSS_SELECTOR, "h2.card-title")
                price_text = price_elem.text.strip()
                rent_match = re.search(r'€([\d,]+)', price_text)
                rent_value = int(rent_match.group(1).replace(',', '')) if rent_match else None

                # Check if rent is weekly or monthly
                price_lower = price_text.lower()
                if 'month' in price_lower or '/m' in price_lower or 'pm' in price_lower:
                    data["rent_eur"] = rent_value
                    data["rent_period"] = "monthly"
                    data["original_rent"] = rent_value
                elif 'week' in price_lower or '/w' in price_lower or 'pw' in price_lower:
                    # Weekly rent, convert to monthly
                    data["rent_period"] = "weekly"
                    data["original_rent"] = rent_value
                    data["rent_eur"] = round(rent_value * (52 / 12)) if rent_value else None
                else:
                    # Default to monthly if unclear
                    data["rent_eur"] = rent_value
                    data["rent_period"] = "monthly"
                    data["original_rent"] = rent_value

                # Info strip
                try:
                    info_strip = card.find_element(By.CSS_SELECTOR, "div.property-card__info-strip")
                    spans = info_strip.find_elements(By.TAG_NAME, "span")
                except NoSuchElementException:
                    spans = []

                beds = baths = size_sqm = None
                for span in spans:
                    txt = span.text.strip().lower()
                    if "bed" in txt:
                        m = re.search(r'\d+', txt)
                        beds = int(m.group()) if m else 0
                    elif "bath" in txt:
                        m = re.search(r'\d+', txt)
                        baths = int(m.group()) if m else 1
                    elif "ft" in txt or "m" in txt:
                        m = re.search(r'([\d,]+)', txt)
                        if m:
                            num = int(m.group(1).replace(",", ""))
                            size_sqm = round(num / 10.764) if "ft" in txt else num

                # Summary
                summary_parts = []
                if beds is not None:
                    summary_parts.append(f"{beds} bed{'s' if beds != 1 else ''}")
                if baths is not None:
                    summary_parts.append(f"{baths} bath{'s' if baths != 1 else ''}")
                data["summary"] = ", ".join(summary_parts)

                data["beds"] = beds or 1
                data["baths"] = baths or 1
                data["furnished"] = "Unknown"  # Not in card

                listings.append(data)
            except Exception as e:
                print(f"  [WARN] Failed card {i}: {e}")
                continue
        return listings

    def run(self) -> List[Dict]:
        listings = self.scrap_all_pages()
        self.driver.quit()
        return listings

    def __del__(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()