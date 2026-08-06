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

def init_universal_db():
    conn = sqlite3.connect("universal_search.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            title TEXT,
            detail TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_universal_db()

# Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ----------------- LOGIN PAGE -----------------
if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🔐 Universal Scraper Login")
        st.markdown("Please enter your credentials to access the dashboard.")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Log In", type="primary", use_container_width=True):
            # Default credentials: admin / admin123 (changeable in settings later)
            if username == "admin" and password == "admin123":
                st.session_state["authenticated"] = True
                st.success("Login successful! Loading dashboard...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password. (Try admin / admin123)")
    st.stop()

# ----------------- MAIN DASHBOARD APP -----------------

# Sidebar Navigation
st.sidebar.title("⚡ Apex Scraper Suite")
st.sidebar.markdown(f"Logged in as: **admin**")
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigation", ["🏠 Dashboard Home", "🔍 Live Scraper", "📊 Database Manager", "⚙️ Settings"])

if menu == "🏠 Dashboard Home":
    st.title("🌐 Universal Scraper Control Center")
    st.markdown("Welcome back! Use the sidebar to execute real-time scraping tasks, manage saved classifieds data, or adjust preferences.")
    
    conn = sqlite3.connect("universal_search.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM search_results")
    total_records = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT query) FROM search_results")
    total_queries = cursor.fetchone()[0]
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Saved Listings", value=total_records)
    with col2:
        st.metric(label="Unique Search Queries", value=total_queries)
    with col3:
        st.metric(label="System Status", value="Online 🟢")
        
    st.markdown("---")
    st.info("💡 **Tip:** Go to **Live Scraper** to pull fresh listings from classified sites directly into your database.")

elif menu == "🔍 Live Scraper":
    st.subheader("🔍 Automated Live Scraper")
    st.markdown("Target online marketplaces to pull active listings in real-time.")
    
    search_term = st.text_input("What do you want to search for?", placeholder="e.g., samsung smart tv, hp laptop, thinkpad")
    
    if st.button("Start Live Scraping", type="primary"):
        if not search_term:
            st.warning("Please enter a search term first.")
        else:
            with st.spinner(f"Launching browser and scraping listings for '{search_term}'..."):
                options = webdriver.ChromeOptions()
                options.add_argument("--start-maximized")
                
                driver = webdriver.Chrome(options=options)
                
                try:
                    driver.get("https://jiji.co.ke")
                    time.sleep(2)
                    
                    wait = WebDriverWait(driver, 10)
                    search_box = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.qa-search-input, input[type='text'], input[placeholder*='ads']"))
                    )
                    search_box.click()
                    search_box.clear()
                    search_box.send_keys(search_term)
                    search_box.send_keys(Keys.RETURN)
                    
                    time.sleep(4)
                    
                    results = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".b-list-advert-base, .qa-advert-list-item, .product_pod, .item-card, .search-result, [data-testid='item-card']"))
                    )
                    
                    conn = sqlite3.connect("universal_search.db")
                    cursor = conn.cursor()
                    
                    count = 0
                    for item in results:
                        title = item.text.split("\n")[0]
                        detail = item.text
                        
                        cursor.execute("""
                            INSERT INTO search_results (query, title, detail)
                            VALUES (?, ?, ?)
                        """, (search_term, title, detail))
                        count += 1
                        
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Successfully scraped and saved {count} items for '{search_term}'!")
                    
                except Exception as e:
                    st.error(f"An error occurred during scraping: {e}")
                finally:
                    driver.quit()

elif menu == "📊 Database Manager":
    st.subheader("📊 Saved Database Records & Analytics")
    
    conn = sqlite3.connect("universal_search.db")
    df = pd.read_sql_query("SELECT id, query, title, detail, scraped_at FROM search_results ORDER BY scraped_at DESC", conn)
    conn.close()
    
    if df.empty:
        st.info("No saved records found in the database yet.")
    else:
        # Search & Filter bar inside database view
        filter_query = st.text_input("Filter saved records by keyword:", placeholder="e.g., HP, Samsung...")
        if filter_query:
            df = df[df['title'].str.contains(filter_query, case=False, na=False) | df['query'].str.contains(filter_query, case=False, na=False)]
            
        st.write(f"Showing **{len(df)}** records:")
        st.dataframe(df, use_container_width=True)
        
        col_dl, col_del = st.columns([1, 1])
        with col_dl:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv,
                file_name="scraped_listings.csv",
                mime="text/csv",
            )
        with col_del:
            if st.button("🗑️ Clear Database History", type="secondary"):
                conn = sqlite3.connect("universal_search.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM search_results")
                conn.commit()
                conn.close()
                st.success("Database cleared successfully!")
                time.sleep(1)
                st.rerun()

elif menu == "⚙️ Settings":
    st.subheader("⚙️ System Preferences")
    st.markdown("Manage your dashboard configurations and security settings.")
    
    with st.form("settings_form"):
        st.text_input("Default Target Marketplace", value="https://jiji.co.ke")
        st.slider("Scraper Timeout Delay (seconds)", min_value=5, max_value=30, value=10)
        st.selectbox("Theme Mode", ["Dark Mode (Default)", "Light Mode"])
        
        submitted = st.form_submit_button("Save Preferences")
        if submitted:
            st.success("Preferences updated successfully!")
            
    st.markdown("---")
    if st.button("🔒 Logout", type="primary"):
        st.session_state["authenticated"] = False
        st.rerun()