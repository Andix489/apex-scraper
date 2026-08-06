import streamlit as st
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse

# Page Configuration
st.set_page_config(
    page_title="Universal Scraper Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: bold;
    }
    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    </style>
""", unsafe_allow_html=True)

# Database Setup
def get_db_connection():
    return sqlite3.connect('scraper_data.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            location TEXT,
            url TEXT,
            search_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Sidebar Navigation
st.sidebar.title("⚡ Control Center")
menu = st.sidebar.selectbox("Navigation", ["🏠 Dashboard", "🔍 Live Scraper", "📂 Saved Data", "⚙️ Preferences"])

# 🏠 Dashboard View
if menu == "🏠 Dashboard":
    st.subheader("Universal Scraper Control Center")
    st.markdown("Welcome back! Use the live scraper to search and pull real product items from the web.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM listings")
    total_listings = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT search_query) FROM listings")
    total_queries = cursor.fetchone()[0]
    conn.close()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Saved Listings", value=total_listings)
    with col2:
        st.metric(label="Unique Search Queries", value=total_queries)
    with col3:
        st.metric(label="System Status", value="Online 🟢")

# 🔍 Live Scraper View
elif menu == "🔍 Live Scraper":
    st.subheader("🔍 Universal Web Product Scraper")
    st.markdown("Type any product name below to fetch real online listings and prices.")

    search_term = st.text_input("What product do you want to search for?", placeholder="e.g. samsung smart tv, thinkpad laptop, nike shoes")

    if st.button("Start Live Scraping", type="primary"):
        if not search_term:
            st.warning("Please enter a search term first.")
        else:
            with st.spinner(f"Fetching real listings for '{search_term}'..."):
                try:
                    scraped_data = []
                    query = urllib.parse.quote_plus(search_term + " price buy Kenya")
                    target_url = f"https://html.duckduckgo.com/html/?q={query}"
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    
                    response = requests.get(target_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        results = soup.select(".result")
                        
                        for res in results[:12]:
                            title_elem = res.select_one(".result__title")
                            snippet_elem = res.select_one(".result__snippet")
                            link_elem = res.select_one(".result__url")
                            
                            if title_elem and link_elem:
                                title = title_elem.get_text(strip=True)
                                snippet = snippet_elem.get_text(strip=True) if snippet_elem else "Check link for details"
                                url = link_elem.get('href', '#')
                                
                                scraped_data.append({
                                    "title": title,
                                    "price": snippet[:120] + "...",
                                    "location": "Online Web Store",
                                    "url": url,
                                    "search_query": search_term
                                })

                    if scraped_data:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        for row in scraped_data:
                            cursor.execute('''
                                INSERT INTO listings (title, price, location, url, search_query)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (row['title'], row['price'], row['location'], row['url'], row['search_query']))
                        conn.commit()
                        conn.close()

                        st.success(f"Successfully fetched and saved {len(scraped_data)} real results for '{search_term}'!")
                        df = pd.DataFrame(scraped_data)
                        st.dataframe(df)
                    else:
                        st.warning(f"No results found for '{search_term}'. Try a different keyword.")

                except Exception as e:
                    st.error(f"An error occurred: {e}")

# 📂 Saved Data View
elif menu == "📂 Saved Data":
    st.subheader("📂 Saved Database Records")
    conn = get_db_connection()
    df_all = pd.read_sql("SELECT * FROM listings ORDER BY timestamp DESC", conn)
    conn.close()

    if not df_all.empty:
        st.dataframe(df_all)
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name='scraped_listings.csv',
            mime='text/csv',
        )
    else:
        st.info("No saved records in the database yet.")

# ⚙️ Preferences View
elif menu == "⚙️ Preferences":
    st.subheader("⚙️ System Preferences")
    st.text_input("Search Gateway", value="Universal Web Parser")
    st.button("Save Preferences")
