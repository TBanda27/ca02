from bs4 import BeautifulSoup
from selenium import webdriver
from urllib.parse import urlencode
import time
import pandas as pd


def build_daft_url(city, min_price=None, max_price=None, min_beds=None, radius=None, page=1):
    base_url = f"https://www.daft.ie/property-for-rent/{city}"

    params = {}

    if min_price:
        params['rentalPrice_from'] = min_price
    if max_price:
        params['rentalPrice_to'] = max_price
    if min_beds:
        params['numBeds_from'] = min_beds
    if radius:
        params['radius'] = radius

    # Add page number
    params['page'] = page

    # Build complete URL
    if params:
        url = f"{base_url}?{urlencode(params)}"
    else:
        url = f"{base_url}?page={page}"

    return url


def scrape_daft_page(driver, url, seen_urls):
    driver.get(url)
    time.sleep(5)  # Wait for page to load

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find homes container
    homes_html = soup.find('ul', class_='sc-798c155d-4 kmVnWY')

    if not homes_html:
        return []

    homes_items = homes_html.find_all('li')
    page_homes = []
    duplicates_found = 0

    for home in homes_items:
        try:
            price = home.find('p', class_='sc-af41020b-0 dqCzFn')

            if  not price:
                price = home.find('p', class_='sc-af41020b-0 bfBSFC')
            category = home.find('p', class_='sc-af41020b-0 btpgrM')
            location = home.find('p', class_='sc-af41020b-0 dVPJAx')
            house_url_tag = home.find('a', class_='sc-798c155d-19 cDtUBM')

            if not category and not location:
                continue

            # Extract home URL
            home_url = f"{house_url_tag['href']}" if house_url_tag and house_url_tag.get(
                'href') else None

            # IMPORTANT: Check for duplicates
            if not home_url or home_url == 'N/A':
                continue

            if home_url in seen_urls:
                duplicates_found += 1
                continue

            seen_urls.add(home_url)

            # Handle description
            description_div = home.find('div', class_='sc-620b3daf-1 lgLxys')

            if description_div:
                description_spans = description_div.find_all('span')
                if description_spans:
                    description = [span.text.strip() for span in description_spans]
                    description = ' | '.join(description)
                else:
                    description = description_div.text.strip() if description_div.text.strip() else 'N/A'
            else:
                description = 'N/A'

            home_data = {
                'Category': category.text if category else 'N/A',
                'Location': location.text if location else 'N/A',
                'Price': price.text if price else 'N/A',
                'Description': description,
                'Home_Url': home_url,
            }

            page_homes.append(home_data)

        except Exception as e:
            print(f"  Error scraping a home: {e}")
            continue

    if duplicates_found > 0:
        print(f"  ⚠️ Skipped {duplicates_found} duplicate(s) on this page")

    return page_homes


def scrape_all_daft_pages(city, min_price=None, max_price=None, min_beds=None, radius=None):

    print("=" * 100)
    print("Daft.ie Property Scraper")
    print("=" * 100)
    print(f"\nSearch Criteria:")
    print(f"  City: {city}")
    print(f"  Price Range: €{min_price or 'any'} - €{max_price or 'any'}")
    print(f"  Min Bedrooms: {min_beds or 'any'}")
    print(f"  Radius: {radius or 'any'}m")
    print("\n" + "=" * 100 + "\n")

    driver = webdriver.Chrome()
    driver.maximize_window()

    all_homes = []
    seen_urls = set()  # Track URLs to avoid duplicates
    page = 1
    consecutive_empty_pages = 0
    max_empty_pages = 3  # Stop after 3 consecutive empty pages

    try:
        while True:
            url = build_daft_url(city, min_price, max_price, min_beds, radius, page)
            print(f"Scraping page {page}...")
            print(f"URL: {url}")

            page_homes = scrape_daft_page(driver, url, seen_urls)

            if not page_homes:
                consecutive_empty_pages += 1
                print(f"  ⚠️ No new homes found on page {page} (empty count: {consecutive_empty_pages})")

                if consecutive_empty_pages >= max_empty_pages:
                    print(f"\n✓ Reached end after {page} pages (no new homes for {max_empty_pages} consecutive pages)")
                    break
            else:
                consecutive_empty_pages = 0  # Reset counter
                all_homes.extend(page_homes)
                print(f"  ✓ Found {len(page_homes)} unique homes on page {page}")
                print(f"  Total unique homes so far: {len(all_homes)}")
                print(f"  Total URLs tracked: {len(seen_urls)}")

            page += 1
            time.sleep(2)  # Be nice to the server

    finally:
        driver.quit()

    return all_homes


def get_user_input():
    print("=" * 100)
    print("Daft.ie Property Scraper - User Input")
    print("=" * 100)
    print("\nEnter search criteria (press Enter to skip optional fields):\n")

    # City (required)
    city = input("City (e.g., dublin, cork, galway) [REQUIRED]: ").strip().lower()
    while not city:
        print("  ⚠️ City is required!")
        city = input("City (e.g., dublin, cork, galway) [REQUIRED]: ").strip().lower()

    min_price_input = input("Minimum price (e.g., 1000) [optional]: ").strip()
    min_price = int(min_price_input) if min_price_input else None

    max_price_input = input("Maximum price (e.g., 2000) [optional]: ").strip()
    max_price = int(max_price_input) if max_price_input else None

    min_beds_input = input("Minimum bedrooms (e.g., 1, 2, 3) [optional]: ").strip()
    min_beds = int(min_beds_input) if min_beds_input else None

    radius_input = input("Radius in meters (e.g., 1000, 5000) [optional]: ").strip()
    radius = int(radius_input) if radius_input else None

    return city, min_price, max_price, min_beds, radius


# Main program
if __name__ == "__main__":
    city, min_price, max_price, min_beds, radius = get_user_input()

    all_homes = scrape_all_daft_pages(city, min_price, max_price, min_beds, radius)

    print("\n" + "=" * 100)
    print("SCRAPING COMPLETE")
    print("=" * 100)
    print(f"Total unique homes scraped: {len(all_homes)}")

    if all_homes:
        # Double-check for duplicates in final data (shouldn't happen, but just in case)
        df = pd.DataFrame(all_homes)

        # Check for duplicate URLs
        duplicate_count = df['Home_Url'].duplicated().sum()
        if duplicate_count > 0:
            print(f"\n⚠️ Warning: Found {duplicate_count} duplicate URLs in final data, removing...")
            df = df.drop_duplicates(subset=['Home_Url'], keep='first')
            print(f"✓ After removing duplicates: {len(df)} homes")

        filename = f"daft_{city}_{min_price or 'any'}_{max_price or 'any'}.csv"
        df.to_csv(filename, index=False)
        print(f"\n✓ Saved to {filename}")

        # Display first 10 homes
        print("\nFirst 10 homes:")
        for i, home in enumerate(all_homes[:10], 1):
            print(f"{i}. {home['Category']} - {home['Location']} - {home['Price']}")
            print(f"   URL: {home['Home_Url'][:80]}...")
    else:
        print("\n⚠️ No homes found with the given criteria")