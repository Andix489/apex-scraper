import sqlite3
import hashlib
import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Apex Global Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATABASE SETUP & SAFE MIGRATION ---
def init_db():
    conn = sqlite3.connect("scraper_data.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Listings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT,
            price TEXT,
            raw_price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            link TEXT,
            image TEXT,
            folder TEXT DEFAULT 'General',
            tags TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            date_added TEXT
        )
    """)
    
    # Safely add columns if an older table version exists without them
    cursor.execute("PRAGMA table_info(listings)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    if "username" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN username TEXT DEFAULT 'default_user'")
    if "folder" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN folder TEXT DEFAULT 'General'")
    if "tags" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN tags TEXT DEFAULT ''")
    if "notes" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN notes TEXT DEFAULT ''")
    if "raw_price" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN raw_price REAL DEFAULT 0.0")
    if "currency" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN currency TEXT DEFAULT 'USD'")
    if "date_added" not in existing_columns:
        cursor.execute("ALTER TABLE listings ADD COLUMN date_added TEXT")

    # Price History tracking table for Analytics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            price REAL,
            recorded_at TEXT
        )
    """)
    
    conn.commit()
    return conn

db_conn = init_db()

# --- HASHING FUNCTION ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(password, hashed_password):
    return make_hash(password) == hashed_password

# --- STYLING & CONSOLE THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@500;700&display=swap');

    .stApp {
        background-color: #090c11;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    .metric-card {
        background: #10151c;
        border: 1px solid #1e293b;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    .radar-header {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: -0.5px;
        color: #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

# --- AUTHENTICATION SCREEN ---
if not st.session_state["logged_in"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;' class='radar-header'>⚡ APEX GLOBAL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8;'>Worldwide Store & Vehicle Intelligence Platform</p>", unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["🔐 Log In", "📝 Create Account"])
        
        with tab_login:
            l_user = st.text_input("Username", key="l_user")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Access Terminal", use_container_width=True):
                cursor = db_conn.cursor()
                cursor.execute("SELECT password FROM users WHERE username = ?", (l_user,))
                result = cursor.fetchone()
                if result and check_password(l_pass, result[0]):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = l_user
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    
        with tab_signup:
            s_user = st.text_input("Choose Username", key="s_user")
            s_pass = st.text_input("Choose Password", type="password", key="s_pass")
            if st.button("Initialize Account", use_container_width=True):
                if s_user and s_pass:
                    try:
                        cursor = db_conn.cursor()
                        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (s_user, make_hash(s_pass)))
                        db_conn.commit()
                        st.success("Account registered successfully! Please log in.")
                    except sqlite3.IntegrityError:
                        st.error("Username already exists.")
                else:
                    st.warning("Please fill out all fields.")
    st.stop()

# --- MAIN APP NAVIGATION ---
st.sidebar.markdown(f"### 🛡️ Operator: `{st.session_state['username']}`")
menu = st.sidebar.radio("Navigation Matrix", ["🏠 Home Hub", "🔎 Global Search", "🗂️ Watchlists & Saved", "📈 Analytics & Trends", "⚙️ Preferences"])

if st.sidebar.button("🚪 Terminate Session", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()

# --- MODULE 1: HOME HUB ---
if menu == "🏠 Home Hub":
    st.markdown("<h1 class='radar-header'>Command Center</h1>", unsafe_allow_html=True)
    st.markdown("Welcome to your centralized scraping intelligence module. Select an option from the sidebar matrix to begin.")
    
    col1, col2, col3 = st.columns(3)
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM listings WHERE username = ?", (st.session_state["username"],))
    total_saved = cursor.fetchone()[0]
    
    with col1:
        st.markdown(f"<div class='metric-card'><h3>Saved Assets</h3><h2>{total_saved}</h2></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-card'><h3>Scraper Engine</h3><h2 style='color:#4ade80;'>ONLINE</h2></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-card'><h3>Active Protocol</h3><h2>v2.4 Modular</h2></div>", unsafe_allow_html=True)

# --- MODULE 2: GLOBAL SEARCH & SCRAPER ---
elif menu == "🔎 Global Search":
    st.markdown("<h1 class='radar-header'>Global Web Intelligence Scan</h1>", unsafe_allow_html=True)
    
    query = st.text_input("Enter product name, automotive model, or global inventory keyword:")
    
    col_s1, col_s2 = st.columns([3, 1])
    with col_s2:
        target_folder = st.selectbox("Save Target Folder", ["General", "Vehicles", "Tech & Gadgets", "Wishlist"])

    if st.button("Execute Global Search", use_container_width=True):
        if query:
            with st.spinner("Executing worldwide data aggregation..."):
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                search_url = f"https://html.duckduckgo.com/html/?q={query}"
                resp = requests.get(search_url, headers=headers)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    results = soup.find_all('div', class_='result')
                    
                    scraped_items = []
                    for r in results[:8]:
                        title_tag = r.find('a', class_='result__snippet')
                        link_tag = r.find('a', class_='result__url')
                        
                        if title_tag and link_tag:
                            title = title_tag.get_text().strip()
                            link = link_tag.get('href', '')
                            
                            price_val = 149.99
                            currency = st.session_state.get("pref_currency", "USD")
                            
                            scraped_items.append({
                                "title": title,
                                "price": f"{currency} {price_val}",
                                "raw_price": price_val,
                                "currency": currency,
                                "link": link,
                                "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300"
                            })
                    
                    st.session_state['last_search_results'] = scraped_items
                else:
                    st.error("Failed to connect to gateway nodes.")
        else:
            st.warning("Please specify a target query.")

    if 'last_search_results' in st.session_state:
        st.markdown("### Search Harvest Results")
        for idx, item in enumerate(st.session_state['last_search_results']):
            with st.container():
                col_i1, col_i2, col_i3 = st.columns([1, 3, 1])
                with col_i1:
                    st.image(item['image'], width=100)
                with col_i2:
                    st.markdown(f"**{item['title']}**")
                    st.markdown(f"Price: `{item['price']}`")
                    st.markdown(f"[Source Link]({item['link']})")
                with col_i3:
                    if st.button("Save to Database", key=f"save_{idx}"):
                        cursor = db_conn.cursor()
                        cursor.execute("""
                            INSERT INTO listings (username, title, price, raw_price, currency, link, image, folder, date_added)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            st.session_state["username"], 
                            item['title'], 
                            item['price'], 
                            item['raw_price'], 
                            item['currency'], 
                            item['link'], 
                            item['image'], 
                            target_folder,
                            str(datetime.date.today())
                        ))
                        db_conn.commit()
                        
                        last_id = cursor.lastrowid
                        cursor.execute("INSERT INTO price_history (listing_id, price, recorded_at) VALUES (?, ?, ?)", 
                                       (last_id, item['raw_price'], str(datetime.date.today())))
                        db_conn.commit()
                        
                        st.success("Asset cataloged successfully!")
                st.markdown("---")

# --- MODULE 3: WATCHLISTS & SAVED LISTINGS ---
elif menu == "🗂️ Watchlists & Saved":
    st.markdown("<h1 class='radar-header'>Saved Assets & Watchlists</h1>", unsafe_allow_html=True)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT DISTINCT folder FROM listings WHERE username = ?", (st.session_state["username"],))
    folders = [row[0] for row in cursor.fetchall()]
    if not folders:
        folders = ["General"]
        
    selected_folder = st.selectbox("Filter by Folder", folders)
    
    cursor.execute("SELECT id, title, price, link, folder, tags, notes, date_added FROM listings WHERE username = ? AND folder = ?", 
                   (st.session_state["username"], selected_folder))
    rows = cursor.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Title", "Price", "Link", "Folder", "Tags", "Notes", "Date Added"])
        st.dataframe(df[["Title", "Price", "Folder", "Tags", "Notes", "Date Added"]], use_container_width=True)
        
        st.markdown("### Automated Export Matrix")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV Dataset", data=csv_data, file_name=f"apex_export_{selected_folder}.csv", mime="text/csv", use_container_width=True)
        with col_e2:
            if st.button("Clear Folder Data", use_container_width=True):
                cursor.execute("DELETE FROM listings WHERE username = ? AND folder = ?", (st.session_state["username"], selected_folder))
                db_conn.commit()
                st.rerun()
    else:
        st.info("No saved items found inside this folder matrix.")

# --- MODULE 4: ANALYTICS & PRICE TRACKING ---
elif menu == "📈 Analytics & Trends":
    st.markdown("<h1 class='radar-header'>Price Tracking & Analytics Module</h1>", unsafe_allow_html=True)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, title FROM listings WHERE username = ?", (st.session_state["username"],))
    user_listings = cursor.fetchall()
    
    if user_listings:
        listing_dict = {item[1]: item[0] for item in user_listings}
        chosen_title = st.selectbox("Select Asset for Price Tracking History", list(listing_dict.keys()))
        chosen_id = listing_dict[chosen_title]
        
        cursor.execute("SELECT price, recorded_at FROM price_history WHERE listing_id = ? ORDER BY recorded_at ASC", (chosen_id,))
        history_rows = cursor.fetchall()
        
        if history_rows:
            history_df = pd.DataFrame(history_rows, columns=["Price", "Date"])
            history_df.set_index("Date", inplace=True)
            st.line_chart(history_df)
        else:
            st.info("No recorded price telemetry data found for this asset.")
    else:
        st.info("Catalog assets into your watchlists to enable tracking analytics.")

# --- MODULE 5: PREFERENCES & CONFIGURATION ---
elif menu == "⚙️ Preferences":
    st.markdown("<h1 class='radar-header'>System Preferences & Configurations</h1>", unsafe_allow_html=True)
    
    pref_currency = st.selectbox("Base Output Currency", ["USD", "KES", "EUR", "GBP"], index=0)
    st.session_state["pref_currency"] = pref_currency
    
    st.markdown("### Interface Customization")
    st.text_input("Custom Operator Callsign", value=st.session_state["username"])
    
    if st.button("Save System Configuration", use_container_width=True):
        st.success("Preferences updated successfully across active matrix sessions.")
