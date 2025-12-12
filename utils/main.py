
import csv
import os
import sys

# Add scrapers directory to path for imports
house_scrapers_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scrapers", "house scrappers")
sys.path.insert(0, house_scrapers_path)

from property_ie_scrapper import PropertyIEScraper
from homes_ie_scrapper import MyHomeIEScraper

# Import database module
utils_path = os.path.dirname(__file__)
sys.path.insert(0, utils_path)
from database import RentalDatabase

def run_scraper(scraper_class, filename, db):
    """Run a single scraper and save to database and CSV"""
    scraper = scraper_class()
    listings = scraper.run()

    print(f"\nSCRAPING COMPLETE: {len(listings)} listings from {scraper_class.__name__}")

    if listings:
        # Save to database
        inserted, updated = db.insert_many(listings)
        print(f"DATABASE: {inserted} inserted, {updated} updated")

        # Also save to CSV for backup
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        filepath = os.path.join(data_dir, filename)

        keys = listings[0].keys()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(listings)
        print(f"CSV BACKUP SAVED TO: {filepath}")

    return listings

def run_all_scrapers():
    """Run all house scrapers and save to SQLite database"""
    print("=" * 100)
    print("RUNNING ALL HOUSE SCRAPERS")
    print("=" * 100)

    # Initialize database
    db = RentalDatabase()
    print(f"Database initialized at: {db.db_path}")

    all_listings = []

    # Run each scraper
    scrapers = [
        (PropertyIEScraper, "dublin_property_ie.csv"),
        (MyHomeIEScraper, "dublin_myhome_ie.csv"),
    ]

    for scraper_class, filename in scrapers:
        print(f"\n{'='*100}")
        print(f"Starting {scraper_class.__name__}...")
        print(f"{'='*100}")

        listings = run_scraper(scraper_class, filename, db)
        if listings:
            all_listings.extend(listings)

    # Create combined CSV for backward compatibility
    if all_listings:
        print(f"\n{'='*100}")
        print("CREATING COMBINED DATASET")
        print(f"{'='*100}")

        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        combined_filepath = os.path.join(data_dir, "dublin_all_sources.csv")

        # Use consistent field order
        fieldnames = ["source", "address", "url", "rent_eur", "rent_period", "original_rent", "summary", "beds", "baths", "furnished"]

        with open(combined_filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_listings)

        print(f"\nCOMBINED CSV BACKUP:")
        print(f"  Total listings: {len(all_listings)}")
        print(f"  Saved to: {combined_filepath}")

    # Print database statistics
    print(f"\n{'='*100}")
    print("DATABASE STATISTICS")
    print(f"{'='*100}")
    stats = db.get_stats()
    print(f"Total listings in database: {stats['total']}")
    print(f"\nBreakdown by source:")
    for source, count in stats['by_source'].items():
        print(f"  - {source}: {count} listings")
    print(f"\nRent period breakdown:")
    print(f"  - Weekly (converted to monthly): {stats['weekly_converted']}")
    print(f"  - Originally monthly: {stats['monthly_original']}")

    db.close()

if __name__ == "__main__":
    run_all_scrapers()

    # Job scrapers (to be added later)