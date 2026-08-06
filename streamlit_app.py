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
    st.markdown("Welcome back! Use the live scraper to pull product catalogs from platforms like Jumia and Alibaba.")
    
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
    st.subheader("🔍 Multi-Platform Live Scraper")
    st.markdown("Select your target marketplace and search for any product in real-time.")

    # Platform selector
    platform = st.selectbox("Choose Marketplace", ["Jumia Kenya", "Alibaba"])
    search_term = st.text_input("What product do you want to search for?", placeholder="e.g. samsung phone, thinkpad, smartwatch")

    if st.button("Start Live Scraping", type="primary"):
        if not search_term:
            st.warning("Please enter a search term first.")
        else:
            with st.spinner(f"Scraping products from {platform} for '{search_term}'..."):
                try:
                    scraped_data = []
                    
                    # Enhanced browser-mimicking headers to bypass anti-bot checks
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1"
                    }

                    if platform == "Jumia Kenya":
                        formatted_query = search_term.replace(" ", "+")
                        target_url = f"https://www.jumia.co.ke/catalog/?q={formatted_query}"
                        
                        response = requests.get(target_url, headers=headers, timeout=15)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            items = soup.select("article.prd")
                            
                            for item in items[:15]:
                                title_elem = item.select_one(".name")
                                price_elem = item.select_one(".prc")
                                link_elem = item.select_one("a.core")
                                
                                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                                path = link_elem.get("href") if link_elem else ""
                                url = f"https://www.jumia.co.ke{path}" if path.startswith("/") else path
                                
                                if title != "N/A":
                                    scraped_data.append({
                                        "title": title,
                                        "price": price,
                                        "location": "Jumia Kenya",
                                        "url": url,
                                        "search_query": f"Jumia: {search_term}"
                                    })

                    elif platform == "Alibaba":
                        formatted_query = urllib.parse.quote_plus(search_term)
                        target_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&SearchText={formatted_query}"
                        
                        response = requests.get(target_url, headers=headers, timeout=15)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            items = soup.select(".organic-gallery-offer-item") or soup.select(".list-no-v2-item")
                            
                            for item in items[:15]:
                                title_elem = item.select_one(".elements-title-normal") or item.select_one("h2")
                                price_elem = item.select_one(".elements-price-normal") or item.select_one(".price")
                                link_elem = item.select_one("a")
                                
                                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                                path = link_elem.get("href") if link_elem else ""
                                url = f"https:{path}" if path.startswith("//") else path
                                
                                if title != "N/A":
                                    scraped_data.append({
                                        "title": title,
                                        "price": price,
                                        "location": "Alibaba Global",
                                        "url": url,
                                        "search_query": f"Alibaba: {search_term}"
                                    })

                    # Save to Database if items were found
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

                        st.success(f"Successfully scraped and saved {len(scraped_data)} items from {platform}!")
                        df = pd.DataFrame(scraped_data)
                        st.dataframe(df)
                    else:
                        st.warning(f"No items found on {platform} for '{search_term}'. Try another keyword.")

                except Exception as e:
                    st.error(f"An error occurred during scraping: {e}")

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
    st.text_input("Default Marketplace", value="Jumia Kenya")
    st.button("Save Preferences")
