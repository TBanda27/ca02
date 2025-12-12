# property_ie_scraper.py
import yaml
import re
import time
from typing import List, Dict, Set
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class PropertyIEScraper:
    def __init__(self, config_path: str = "D:/Live Labor-Housing Mismatch Index 2025 (Dublin)/config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None
        self.seen_urls: Set[str] = set()
        self._init_driver()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["property_ie"]

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
        path = re.sub(r'/p_\d+/', f'/p_{page}/', path)
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

    def _get_last_page(self) -> int:
        """Detect last page from div#pages — even in '..' section."""
        try:
            pagination = self.driver.find_element(By.CSS_SELECTOR, "div#pages")
            links = pagination.find_elements(By.CSS_SELECTOR, "a")

            max_page = 1
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()

                # 1. Extract from URL: /p_44/
                match = re.search(r'/p_(\d+)/', href)
                if match:
                    page_num = int(match.group(1))
                    if page_num > max_page:
                        max_page = page_num

                # 2. Fallback: visible number
                elif text.isdigit():
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num

            print(f"[PAGINATION] Detected last page: {max_page}")
            return max_page

        except NoSuchElementException:
            print("[PAGINATION] No pagination found. Assuming page 1 only.")
            return 1

    def scrap_all_pages(self) -> List[Dict]:
        """Scrape ALL listings from page 1 to last."""
        all_listings = []
        page = 1

        while True:
            url = self._get_page_url(page)
            print(f"\n[PAGE {page}] Loading: {url}")

            try:
                self.driver.get(url)
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".search_result")))
                time.sleep(self.config["scraper"]["delay"])
            except TimeoutException:
                print(f"[ERROR] Page {page} timed out. Stopping.")
                break

            cards = self.driver.find_elements(By.CSS_SELECTOR, ".search_result")
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

            last_page = self._get_last_page()
            if page == 1:
                print(f"[INFO] Total pages to scrape: {last_page}")

            if page >= last_page:
                print(f"[DONE] Reached last page ({page}).")
                break

            page += 1
            time.sleep(1)

        print(f"\n[FINAL] Total unique listings scraped: {len(all_listings)}")
        return all_listings

    def _parse_page(self, cards) -> List[Dict]:
        listings = []
        for i, card in enumerate(cards, 1):
            try:
                data = {
                    "source": "property.ie",
                }

                addr_elem = card.find_element(By.CSS_SELECTOR, ".sresult_address h2 a")
                data["address"] = addr_elem.text.strip()
                data["url"] = addr_elem.get_attribute("href")

                rent_text = card.find_element(By.CSS_SELECTOR, ".sresult_description h3").text.strip()
                rent_match = re.search(r'€([\d,]+)', rent_text)
                rent_value = int(rent_match.group(1).replace(',', '')) if rent_match else None

                # Check if rent is weekly or monthly
                rent_lower = rent_text.lower()
                if 'monthly' in rent_lower:
                    data["rent_eur"] = rent_value
                    data["rent_period"] = "monthly"
                    data["original_rent"] = rent_value
                else:
                    # Assume weekly if not explicitly monthly, convert to monthly
                    data["rent_period"] = "weekly"
                    data["original_rent"] = rent_value
                    data["rent_eur"] = round(rent_value * (52 / 12)) if rent_value else None

                summary = card.find_element(By.CSS_SELECTOR, ".sresult_description h4").text.strip()
                data["summary"] = summary
                lower_summary = summary.lower()

                # BEDS
                paren_match = re.search(r'\((\d+)\s*(single|double|bed)', lower_summary)
                if paren_match:
                    data["beds"] = int(paren_match.group(1))
                elif "studio" in lower_summary:
                    data["beds"] = 1
                else:
                    beds_match = re.search(r'(\d)\s*bedroom', summary, re.I)
                    data["beds"] = int(beds_match.group(1)) if beds_match else 1

                # BATHS — default 1
                baths_match = re.search(r'(\d)\s*bathroom', summary, re.I)
                data["baths"] = int(baths_match.group(1)) if baths_match else 1

                data["furnished"] = self._detect_furnished(summary)

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