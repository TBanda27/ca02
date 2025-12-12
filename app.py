import streamlit as st
import pandas as pd
import sqlite3
import os

# Page config
st.set_page_config(page_title="Dublin House Search", page_icon="🏠", layout="wide")

# Load data from SQLite database
@st.cache_data
def load_data():
    db_path = os.path.join('data', 'rentals.db')

    if not os.path.exists(db_path):
        st.error(f"Database not found at {db_path}. Please run the scrapers first: `python utils/main.py`")
        return pd.DataFrame()

    # Load from SQLite database
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query('''
            SELECT source, address, url, rent_eur, rent_period, original_rent,
                   summary, beds, baths, furnished, scraped_at, updated_at
            FROM rentals
            ORDER BY updated_at DESC
        ''', conn)
        conn.close()

        # Clean data
        df['rent_eur'] = pd.to_numeric(df['rent_eur'], errors='coerce')
        df['beds'] = pd.to_numeric(df['beds'], errors='coerce')
        df['baths'] = pd.to_numeric(df['baths'], errors='coerce')

        return df
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return pd.DataFrame()

df = load_data()

# Title
st.title("🏠 Dublin House Search")
st.markdown("Search for rental properties in Dublin from multiple sources")

# Show database info if data exists
if len(df) > 0:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Listings", len(df))
    with col2:
        weekly_count = len(df[df['rent_period'] == 'weekly']) if 'rent_period' in df.columns else 0
        st.metric("Weekly (Converted)", weekly_count)
    with col3:
        monthly_count = len(df[df['rent_period'] == 'monthly']) if 'rent_period' in df.columns else 0
        st.metric("Originally Monthly", monthly_count)
    with col4:
        sources_count = df['source'].nunique()
        st.metric("Data Sources", sources_count)
    st.markdown("---")

# Sidebar filters
st.sidebar.header("Search Filters")

# Price range
min_rent, max_rent = st.sidebar.slider(
    "Rent Range (EUR/month)",
    min_value=0,
    max_value=int(df['rent_eur'].max()) if df['rent_eur'].max() > 0 else 5000,
    value=(0, int(df['rent_eur'].max()) if df['rent_eur'].max() > 0 else 5000)
)

# Bedrooms
beds_option = st.sidebar.selectbox(
    "Bedrooms",
    options=["Any", "Studio", "1", "2", "3", "4+"]
)

# Bathrooms
baths_option = st.sidebar.selectbox(
    "Bathrooms",
    options=["Any", "1", "2", "3+"]
)

# Furnished status
furnished_option = st.sidebar.selectbox(
    "Furnished",
    options=["Any", "Yes", "No", "Unknown"]
)

# Location search
location_search = st.sidebar.text_input("Location/Address (keyword)")

# Clear filters button
if st.sidebar.button("Clear All Filters"):
    st.rerun()

# Filter data
filtered_df = df.copy()

# Apply rent filter
filtered_df = filtered_df[(filtered_df['rent_eur'] >= min_rent) & (filtered_df['rent_eur'] <= max_rent)]

# Apply bedroom filter
if beds_option != "Any":
    if beds_option == "Studio":
        filtered_df = filtered_df[filtered_df['summary'].str.contains("Studio", case=False, na=False)]
    elif beds_option == "4+":
        filtered_df = filtered_df[filtered_df['beds'] >= 4]
    else:
        filtered_df = filtered_df[filtered_df['beds'] == int(beds_option)]

# Apply bathroom filter
if baths_option != "Any":
    if baths_option == "3+":
        filtered_df = filtered_df[filtered_df['baths'] >= 3]
    else:
        filtered_df = filtered_df[filtered_df['baths'] == int(baths_option)]

# Apply furnished filter
if furnished_option != "Any":
    filtered_df = filtered_df[filtered_df['furnished'] == furnished_option]

# Apply location filter
if location_search:
    filtered_df = filtered_df[filtered_df['address'].str.contains(location_search, case=False, na=False)]

# Display results
st.subheader(f"Found {len(filtered_df)} properties")

if len(filtered_df) > 0:
    # Display as table with clickable links
    # Check if rent_period column exists (for database mode)
    if 'rent_period' in filtered_df.columns:
        display_df = filtered_df[['address', 'rent_eur', 'original_rent', 'beds', 'baths', 'furnished', 'summary', 'url']].copy()
        display_df.columns = ['Address', 'Rent (EUR/month)', 'Original Rent', 'Beds', 'Baths', 'Furnished', 'Summary', 'URL']
    else:
        display_df = filtered_df[['address', 'rent_eur', 'beds', 'baths', 'furnished', 'summary', 'url']].copy()
        display_df.columns = ['Address', 'Rent (EUR)', 'Beds', 'Baths', 'Furnished', 'Summary', 'URL']

    # Sort by rent
    display_df = display_df.sort_values(display_df.columns[1])  # Sort by rent column

    # Display with pagination
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("View Listing")
        }
    )
else:
    st.info("No properties match your search criteria. Try adjusting the filters.")

# Footer
st.markdown("---")
st.markdown("**Data sources:** property.ie, myhome.ie")
st.markdown("*Made by tbanda27*")
