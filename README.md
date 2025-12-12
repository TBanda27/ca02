# Dublin House Search - Streamlit App

A simple, minimal one-page application to search for rental properties in Dublin.

## Features

- Search by price range, bedrooms, bathrooms, furnished status, and location
- Clean, responsive UI with no JavaScript required
- Fast in-memory CSV filtering
- Clickable links to property listings

## Project Structure

```
├── app.py                        # Single-file Streamlit app
└── data/
    └── dublin_all_sources.csv    # Housing data
```


```

## Running Locally

1. Install dependencies:
```bash
pip install streamlit pandas
```

2. Run the app:
```bash
streamlit run app.py
```

3. Open browser at: `http://localhost:8501`

## Search Filters

- **Rent Range**: Slider to filter by monthly rent (EUR)
- **Bedrooms**: Dropdown (Any, Studio, 1, 2, 3, 4+)
- **Bathrooms**: Dropdown (Any, 1, 2, 3+)
- **Furnished**: Dropdown (Any, Yes, No, Unknown)
- **Location**: Text search for address/area keywords
- **Clear All**: Reset all filters

## Data Sources

The app uses data from:
- property.ie
- myhome.ie
- daft.ie

All data is stored in `data/dublin_all_sources.csv`
