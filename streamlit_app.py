import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
import time
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Universal Scraper Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling for a polished look
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

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect('scraper_data.db', check_same_thread=False)
    return conn

# Initialize Database Table
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
    st.markdown("Welcome back! Use the sidebar to execute real-time scraping tasks, manage saved classifieds data, or adjust preferences.")
    
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

    st.markdown("---")
    st.info("💡 **Tip:** Go to **Live Scraper** to pull fresh listings from classified sites directly into your database.")

# 🔍 Live Scraper View
elif menu == "🔍 Live Scraper":
    st.subheader("🔍 Automated Live Scraper")
    st.markdown("Target online marketplaces to pull active listings in real-time.")

    search_term = st.text_input("What do you want to search for?", placeholder="e.g. thinkpad")

    if st.button("Start Live Scraping", type="primary"):
        if not search_term:
            st.warning("Please enter a search term first.")
        else:
            with st.spinner(f"Launching browser and scraping listings for '{search_term}'..."):
                options = webdriver.ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                options.binary_location = "/usr/bin/chromium"

                service = webdriver.chrome.service.Service("/usr/bin/chromedriver")
                driver = webdriver.Chrome(service=service, options=options)

                try:
                    driver.get("https://jiji.co.ke")
                    time.sleep(2)

                    wait = WebDriverWait(driver, 10)
                    search_box = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.qa-search-input"))
                    )
                    search_box.clear()
                    search_box.send_keys(search_term)
                    search_box.send_keys(Keys.RETURN)
                    time.sleep(3)

                    # Extract listings
                    items = driver.find_elements(By.CSS_SELECTOR, "div.qa-advert-list-item")
                    scraped_data = []

                    for item in items[:10]: # Limit to top 10 for performance
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, ".qa-advert-title")
                            price_elem = item.find_element(By.CSS_SELECTOR, ".qa-advert-price")
                            loc_elem = item.find_element(By.CSS_SELECTOR, ".qa-advert-location")
                            link_elem = item.find_element(By.CSS_SELECTOR, "a.qa-advert-list-item-link")

                            title = title_elem.text if title_elem else "N/A"
                            price = price_elem.text if price_elem else "N/A"
                            location = loc_elem.text if loc_elem else "N/A"
                            url = link_elem.get_attribute("href") if link_elem else "N/A"

                            scraped_data.append({
                                "title": title,
                                "price": price,
                                "location": location,
                                "url": url,
                                "search_query": search_term
                            })
                        except Exception:
                            continue

                    driver.quit()

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
                        st.warning("No listings found matching your search term.")

                except Exception as e:
                    driver.quit()
                    st.error(f"An error occurred during scraping: {e}")

# 📂 Saved Data View
elif menu == "📂 Saved Data":
    st.subheader("📂 Saved Database Records")
    st.markdown("Browse, filter, or export your historical scraped data.")

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
        st.info("No saved records in the database yet. Run a live scrape to populate data!")

# ⚙️ Preferences View
elif menu == "⚙️ Preferences":
    st.subheader("⚙️ System Preferences")
    st.markdown("Configure tool behavior and model settings.")
    st.text_input("Default Scraper Target", value="https://jiji.co.ke")
    st.selectbox("Default LLM Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
    st.button("Save Preferences")
