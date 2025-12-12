
import csv
import os
import sys

# Add scrapers directory to path for imports
house_scrapers_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scrapers", "house scrappers")
sys.path.insert(0, house_scrapers_path)

from property_ie_scrapper import PropertyIEScraper
from homes_ie_scrapper import MyHomeIEScraper
from daft_ie_scrapper import DaftIEScraper

def run_scraper(scraper_class, filename):
    """Run a single scraper and save to individual CSV"""
    scraper = scraper_class()
    listings = scraper.run()

    print(f"\nSCRAPING COMPLETE: {len(listings)} listings from {scraper_class.__name__}")

    if listings:
        # Save to data folder
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        filepath = os.path.join(data_dir, filename)

        keys = listings[0].keys()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(listings)
        print(f"SAVED TO: {filepath}")

    return listings

def run_all_scrapers():
    """Run all house scrapers and create both individual and combined CSVs"""
    print("=" * 100)
    print("RUNNING ALL HOUSE SCRAPERS")
    print("=" * 100)

    all_listings = []

    # Run each scraper
    scrapers = [
        (PropertyIEScraper, "dublin_property_ie.csv"),
        (MyHomeIEScraper, "dublin_myhome_ie.csv"),
        (DaftIEScraper, "dublin_daft_ie.csv"),
    ]

    for scraper_class, filename in scrapers:
        print(f"\n{'='*100}")
        print(f"Starting {scraper_class.__name__}...")
        print(f"{'='*100}")

        listings = run_scraper(scraper_class, filename)
        if listings:
            all_listings.extend(listings)

    # Create combined CSV
    if all_listings:
        print(f"\n{'='*100}")
        print("CREATING COMBINED DATASET")
        print(f"{'='*100}")

        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        combined_filepath = os.path.join(data_dir, "dublin_all_sources.csv")

        # Use consistent field order
        fieldnames = ["source", "address", "url", "rent_eur", "summary", "beds", "baths", "furnished"]

        with open(combined_filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_listings)

        print(f"\nCOMBINED DATASET:")
        print(f"  Total listings: {len(all_listings)}")
        print(f"  Saved to: {combined_filepath}")

        # Print breakdown by source
        sources = {}
        for listing in all_listings:
            source = listing.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        print(f"\n  Breakdown by source:")
        for source, count in sources.items():
            print(f"    - {source}: {count} listings")

if __name__ == "__main__":
    run_all_scrapers()

    # Job scrapers (to be added later)