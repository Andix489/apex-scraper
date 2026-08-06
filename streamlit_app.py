import streamlit as st
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup

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
    st.markdown("Welcome back! Use the sidebar to execute real-time scraping tasks.")
    
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
    st.subheader("🔍 Automated Live Scraper")
    st.markdown("Target online marketplaces to pull active listings in real-time.")

    search_term = st.text_input("What do you want to search for?", placeholder="e.g. thinkpad")

    if st.button("Start Live Scraping", type="primary"):
        if not search_term:
            st.warning("Please enter a search term first.")
        else:
            with st.spinner(f"Fetching listings for '{search_term}'..."):
                try:
                    formatted_query = search_term.replace(" ", "%20")
                    target_url = f"https://jiji.co.ke/search?query={formatted_query}"
                    
                    # Enhanced headers to bypass Cloudflare/403 blocks
                    headers = {
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Referer": "https://jiji.co.ke/",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    }
                    
                    session = requests.Session()
                    response = session.get(target_url, headers=headers, timeout=15)
                    
                    if response.status_code != 200:
                        st.error(f"Access blocked by target server (Status code: {response.status_code}).")
                    else:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        items = soup.select(".b-advert-list-item") or soup.select(".qa-advert-list-item")
                        
                        scraped_data = []
                        for item in items[:15]:
                            try:
                                title_elem = item.select_one(".b-advert-list-item-title") or item.select_one(".qa-advert-title")
                                price_elem = item.select_one(".b-advert-list-item-price") or item.select_one(".qa-advert-price")
                                loc_elem = item.select_one(".b-advert-list-item-region") or item.select_one(".qa-advert-location")
                                link_elem = item.select_one("a")

                                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                                location = loc_elem.get_text(strip=True) if loc_elem else "N/A"
                                
                                path = link_elem.get("href") if link_elem else ""
                                url = f"https://jiji.co.ke{path}" if path.startswith("/") else path

                                if title != "N/A":
                                    scraped_data.append({
                                        "title": title,
                                        "price": price,
                                        "location": location,
                                        "url": url,
                                        "search_query": search_term
                                    })
                            except Exception:
                                continue

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

                            st.success(f"Successfully scraped and saved {len(scraped_data)} listings!")
                            df = pd.DataFrame(scraped_data)
                            st.dataframe(df)
                        else:
                            st.warning("Connection successful, but no product elements matched. The site structure may have updated.")

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
    st.text_input("Default Scraper Target", value="https://jiji.co.ke")
    st.button("Save Preferences")
