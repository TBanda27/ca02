# Dublin House Search

Search rental properties in Dublin scraped from property.ie and myhome.ie.

**Live App:** https://scrappedhouses.streamlit.app/

## Features

- Automatic weekly to monthly rent conversion (52/12 formula)
- SQLite database storage with duplicate handling
- Search by price, bedrooms, bathrooms, furnished status, and location
- Displays both converted monthly rent and original rent values

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run scrapers to populate database:**
```bash
python utils/main.py
```

3. **Launch Streamlit app:**
```bash
streamlit run app.py
```

## Data Sources

- property.ie
- myhome.ie

Data stored in `data/rentals.db` (SQLite) with CSV backups.

---

*Made by tbanda27*
