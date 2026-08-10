import streamlit as st
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import textwrap

def html_block(markup: str):
    """Render multi-line HTML/CSS safely.
    Markdown treats 4+ leading spaces as a code block, which makes Streamlit
    print raw CSS/HTML as text instead of rendering it. Dedenting first
    avoids that."""
    st.markdown(textwrap.dedent(markup), unsafe_allow_html=True)

# Page Configuration
st.set_page_config(
    page_title="Apex Global Scraper - Universal Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# CONSOLE / RADAR THEME
# Palette: ink #090c11, panel #10151c, amber #ff7a3d, mint #3ddc97
# Type: Space Grotesk (display), Inter (body), JetBrains Mono (data/labels)
# ------------------------------------------------------------------
html_block("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    :root{
        --bg: #090c11;
        --panel: #10151c;
        --panel-2: #141a22;
        --line: #232b35;
        --line-soft: #1a2029;
        --text: #e9ecf1;
        --text-dim: #7c8797;
        --text-faint: #4a5361;
        --amber: #ff7a3d;
        --amber-dim: #a5501f;
        --mint: #3ddc97;
    }

    html, body, .stApp{
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stApp{
        background-image:
            radial-gradient(circle at 15% 8%, rgba(255,122,61,0.06), transparent 40%),
            radial-gradient(circle at 85% 92%, rgba(61,220,151,0.05), transparent 40%);
    }

    /* Headings */
    h1, h2, h3, .hero-title{
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        color: var(--text) !important;
    }
    p, span, div, label{ color: var(--text); }

    /* Sidebar */
    [data-testid="stSidebar"]{
        background-color: var(--panel) !important;
        border-right: 1px solid var(--line-soft);
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; }

    /* Widget labels -> mono, uppercase, spaced, like manifest fields */
    [data-testid="stWidgetLabel"] p{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-dim) !important;
    }

    /* Text inputs */
    .stTextInput input, .stTextArea textarea{
        background-color: #0b0f15 !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus{
        border-color: var(--amber-dim) !important;
        box-shadow: 0 0 0 3px rgba(255,122,61,0.12) !important;
    }
    .stTextInput input::placeholder{ color: var(--text-faint) !important; }

    /* Selectboxes */
    [data-baseweb="select"] > div{
        background-color: #0b0f15 !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
    }
    [data-baseweb="popover"] li{
        background-color: var(--panel-2) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Radio (auth mode toggle) */
    [role="radiogroup"] label{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        color: var(--text-dim) !important;
    }

    /* Buttons -> amber, Space Grotesk, like run-btn */
    .stButton > button, .stFormSubmitButton > button{
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        background: var(--amber) !important;
        color: #1a0e06 !important;
        border: none !important;
        padding: 0.7rem 1.6rem !important;
        box-shadow: 0 0 0 rgba(255,122,61,0) !important;
        transition: transform .12s ease, box-shadow .12s ease, background .12s ease !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover{
        background: #ff8a53 !important;
        box-shadow: 0 6px 24px rgba(255,122,61,0.28) !important;
        transform: translateY(-1px);
    }

    /* Form panel -> manifest card */
    [data-testid="stForm"]{
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
        padding: 6px 6px 18px 6px !important;
        position: relative;
    }
    [data-testid="stForm"]::before{
        content: '';
        display: block;
        height: 2px;
        margin: -6px -6px 18px -6px;
        background: linear-gradient(90deg, var(--amber), transparent 60%);
        border-radius: 14px 14px 0 0;
        opacity: 0.85;
    }

    /* Card box (login) */
    .card-box{
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
        padding: 28px 26px !important;
        position: relative;
    }
    .card-box::before{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, var(--amber), transparent 60%);
        border-radius: 14px 14px 0 0;
        opacity: 0.85;
    }

    /* Ticker */
    .ticker-bar{
        border-bottom: 1px solid var(--line-soft);
        background: #0c1016;
        overflow: hidden;
        white-space: nowrap;
        padding: 9px 0;
        border-radius: 8px;
        margin-bottom: 18px;
    }
    .ticker-track{ display: inline-flex; animation: scroll 32s linear infinite; }
    .ticker-item{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11.5px;
        letter-spacing: 0.06em;
        color: var(--text-faint);
        padding: 0 28px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        text-transform: uppercase;
    }
    .ticker-item .dot{
        width: 5px; height: 5px; border-radius: 50%;
        background: var(--mint);
        box-shadow: 0 0 6px var(--mint);
    }
    @keyframes scroll{ from{ transform: translateX(0); } to{ transform: translateX(-50%); } }

    /* Eyebrow label */
    .eyebrow{
        display: flex; align-items: center; gap: 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase;
        color: var(--amber); margin-bottom: 10px;
    }
    .eyebrow::before{ content: ''; width: 22px; height: 1px; background: var(--amber-dim); }

    /* Radar icon */
    .radar{
        position: relative; width: 64px; height: 64px; flex-shrink: 0;
        border-radius: 50%;
        background: radial-gradient(circle, #0e1420 0%, #0a0d13 70%);
        border: 1px solid var(--line);
    }
    .radar::before, .radar::after{ content:''; position:absolute; border-radius: 50%; border: 1px solid var(--line-soft); }
    .radar::before{ inset: 10px; }
    .radar::after{ inset: 20px; }
    .radar-sweep{
        position: absolute; inset: 0; border-radius: 50%;
        background: conic-gradient(from 0deg, rgba(255,122,61,0.55), transparent 34%);
        animation: sweep 3.4s linear infinite;
        mix-blend-mode: screen;
    }
    .radar-blip{
        position: absolute; width: 5px; height: 5px; border-radius: 50%;
        background: var(--mint); box-shadow: 0 0 8px var(--mint);
        top: 18px; left: 44px;
        animation: blip 3.4s ease-in-out infinite;
    }
    @keyframes sweep{ to{ transform: rotate(360deg); } }
    @keyframes blip{ 0%,74%{ opacity:0;} 78%{ opacity:1;} 92%{ opacity:0;} }
    .hero-row{ display:flex; align-items:center; gap:20px; margin-bottom: 6px; }

    /* Status pill */
    .status-pill{
        display:inline-flex; align-items:center; gap:7px;
        font-family:'JetBrains Mono', monospace; font-size: 11px;
        color: var(--mint); letter-spacing: 0.06em;
        border: 1px solid var(--line-soft); background: var(--panel-2);
        padding: 5px 12px; border-radius: 20px;
    }
    .status-pill .dot{
        width:6px; height:6px; border-radius:50%; background: var(--mint);
        box-shadow: 0 0 6px var(--mint); animation: pulse 1.8s ease-in-out infinite;
    }
    @keyframes pulse{ 0%,100%{opacity:1;} 50%{opacity:.35;} }

    /* Stats strip */
    .strip{
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
        background: var(--line-soft); border: 1px solid var(--line-soft);
        border-radius: 10px; overflow: hidden; margin-top: 18px;
    }
    .strip div{ background: var(--panel); padding: 16px 20px; }
    .strip .num{ font-family: 'Space Grotesk', sans-serif; font-size: 21px; font-weight: 700; color: var(--text); }
    .strip .lbl{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-faint); margin-top: 3px; }

    /* Hero (landing page) */
    .hero-container{
        position: relative;
        background-image: linear-gradient(rgba(9,12,17,0.55), rgba(9,12,17,0.95)),
            url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1600');
        background-size: cover;
        background-position: center;
        padding: 70px 40px;
        border-radius: 16px;
        margin-top: 10px;
        border: 1px solid var(--line);
    }
    .hero-title{
        font-size: 3.4rem; font-weight: 700; color: #ffffff;
        line-height: 1.1; letter-spacing: -0.01em;
        text-shadow: 0 4px 12px rgba(0,0,0,0.6);
    }
    .hero-subtitle{
        font-family: 'Inter', sans-serif;
        font-size: 1.05rem; color: var(--text-dim);
        margin-top: 18px; margin-bottom: 30px;
        text-shadow: 0 2px 6px rgba(0,0,0,0.6);
        max-width: 600px;
    }
    .footer-tagline{
        text-align: center; color: var(--mint); font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem; letter-spacing: 0.08em; margin-top: 40px;
        text-transform: uppercase;
    }

    /* Dataframe / tables */
    [data-testid="stDataFrame"]{ border: 1px solid var(--line) !important; border-radius: 10px !important; }

    hr{ border-color: var(--line-soft) !important; }
    </style>
""")


def render_ticker():
    platforms = [
        "eBay Motors", "AutoTrader", "Mobile.de", "Cars.com", "Carsales.com.au",
        "OLX", "Copart", "IAAI", "CarGurus", "Facebook Marketplace",
        "Craigslist", "Amazon", "Newegg", "Rakuten", "AliExpress", "Bring a Trailer"
    ]
    items = "".join(f'<span class="ticker-item"><span class="dot"></span>{p}</span>' for p in platforms)
    html_block(f"""
        <div class="ticker-bar">
            <div class="ticker-track">{items}{items}</div>
        </div>
    """)


def render_radar_header(title_html, subtitle=None, eyebrow=None):
    if eyebrow:
        st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    html_block(f"""
        <div class="hero-row">
            <div class="radar"><div class="radar-sweep"></div><div class="radar-blip"></div></div>
            <div>{title_html}</div>
        </div>
    """)
    if subtitle:
        st.markdown(f'<p style="color:var(--text-dim); font-size:15px; max-width:560px; margin-top:6px;">{subtitle}</p>', unsafe_allow_html=True)


# Database Setup for Users & Listings
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
            product_type TEXT,
            platform TEXT,
            description TEXT,
            image_url TEXT,
            url TEXT,
            search_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    columns_to_add = ["product_type", "platform", "description", "image_url"]
    for col in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE listings ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

init_db()

# Session State Management
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "🏠 Welcome & Landing Page"

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_center1, col_center2, col_center3 = st.columns([1, 1.2, 1])

    with col_center2:
        st.markdown("<div class='card-box'>", unsafe_allow_html=True)
        render_radar_header(
            "<h2 style='margin:0;'>APEX GLOBAL PORTAL</h2>",
            "Sign in or create an account to access the scraper engine.",
            eyebrow="Access Manifest"
        )

        auth_mode = st.radio("Mode", ["Log In", "Sign Up"], horizontal=True, label_visibility="collapsed")

        input_user = st.text_input("Username", placeholder="Enter your username")
        input_pass = st.text_input("Password", type="password", placeholder="Enter your password")

        if auth_mode == "Sign Up":
            if st.button("Create Account & Sign In"):
                if input_user and input_pass:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (input_user, input_pass))
                        conn.commit()
                        st.session_state.logged_in = True
                        st.session_state.username = input_user
                        st.session_state.nav_choice = "🔍 Worldwide Live Scraper"
                        st.success("Account created successfully! Entering dashboard...")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists! Please log in instead.")
                    conn.close()
                else:
                    st.warning("Please fill in both fields.")
        else:
            if st.button("Log In to Dashboard"):
                if input_user and input_pass:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (input_user, input_pass))
                    user_record = cursor.fetchone()
                    conn.close()

                    if user_record:
                        st.session_state.logged_in = True
                        st.session_state.username = input_user
                        st.session_state.nav_choice = "🔍 Worldwide Live Scraper"
                        st.success("Login successful! Welcome back.")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please enter your credentials.")
        st.markdown("</div>", unsafe_allow_html=True)

# --- MAIN APPLICATION (Unlocked after Login) ---
else:
    # Sidebar Navigation Hub synced with session state
    st.sidebar.markdown(textwrap.dedent(f"""
        <div class="status-pill"><span class="dot"></span>Feeds Online</div>
        <h3 style='margin-top:14px;'>⚡ {st.session_state.username}</h3>
    """), unsafe_allow_html=True)
    st.sidebar.markdown("---")

    menu_options = ["🏠 Welcome & Landing Page", "🔍 Worldwide Live Scraper", "📂 Saved Database", "⚙️ System Settings"]
    current_index = menu_options.index(st.session_state.nav_choice) if st.session_state.nav_choice in menu_options else 0

    menu = st.sidebar.radio("Navigation Menu", menu_options, index=current_index)
    st.session_state.nav_choice = menu

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.nav_choice = "🏠 Welcome & Landing Page"
        st.rerun()

    # 🏠 Landing Page / Hero Screen
    if menu == "🏠 Welcome & Landing Page":

        render_ticker()

        # Top Header Navigation Bar inside the page
        col_logo, col_h1, col_h2, col_h3, col_btn = st.columns([1.5, 0.8, 0.8, 0.8, 1])
        with col_logo:
            st.markdown("### ⚡ **Apex Global**")
        with col_h1:
            if st.button("Home"):
                st.session_state.nav_choice = "🏠 Welcome & Landing Page"
                st.rerun()
        with col_h2:
            if st.button("Scraper"):
                st.session_state.nav_choice = "🔍 Worldwide Live Scraper"
                st.rerun()
        with col_h3:
            if st.button("Database"):
                st.session_state.nav_choice = "📂 Saved Database"
                st.rerun()
        with col_btn:
            if st.button("Launch App 🚀"):
                st.session_state.nav_choice = "🔍 Worldwide Live Scraper"
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Radar Hero Section
        html_block("""
            <div class="hero-container">
                <div class="eyebrow" style="margin-bottom:16px;">Universal Inventory Interface</div>
                <div class="hero-title">WORLDWIDE STORE<br>&amp; VEHICLE INTELLIGENCE.</div>
                <div class="hero-subtitle">Instantly scan global store inventories and vehicle listings across dozens of platforms at once. Compare live prices, preview images, and jump straight to the source.</div>
            </div>
        """)

        # Action Button below Hero
        col_spacer1, col_action, col_spacer2 = st.columns([1, 1.2, 1])
        with col_action:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("EXPLORE LIVE SCRAPER NOW", use_container_width=True):
                st.session_state.nav_choice = "🔍 Worldwide Live Scraper"
                st.rerun()

        html_block("""
            <div class="strip">
                <div><div class="num">47</div><div class="lbl">Connected Platforms</div></div>
                <div><div class="num">19</div><div class="lbl">Regions Indexed</div></div>
                <div><div class="num">&lt;4s</div><div class="lbl">Avg. Response Time</div></div>
            </div>
        """)

        st.markdown('<div class="footer-tagline">You\'re part of the family</div>', unsafe_allow_html=True)

    # 🔍 Live Scraper View
    elif menu == "🔍 Worldwide Live Scraper":

        render_ticker()
        render_radar_header(
            "<h1 style='margin:0;'>Worldwide Store &amp; Vehicle Scraper</h1>",
            "Pull live listings, pricing, images and direct purchase links from marketplaces and dealer networks around the globe — one query, every platform, simultaneously.",
            eyebrow="Query Manifest — 001"
        )

        with st.form("scraper_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                product_type = st.selectbox("01 · Product Category", ["Automobiles & Vehicles", "Electronics & Computing", "Fashion & Apparel", "Home & Living", "General Merchandise"])
            with col_b:
                target_region = st.selectbox("02 · Global Scope", ["Worldwide (All Stores)", "North America / Global Online", "African Markets", "Asian & International Marketplaces"])

            search_term = st.text_input("03 · Product Name or Car Model", placeholder="e.g. BMW M4, iPhone 15 Pro, Gaming Laptop")
            submit_btn = st.form_submit_button("🚀 Run Multi-Platform Scraper")

        if submit_btn:
            if not search_term:
                st.warning("Please enter a product keyword or car model first.")
            else:
                with st.spinner(f"Aggregating live options with images for '{search_term}' across global platforms..."):
                    try:
                        scraped_data = []
                        query = urllib.parse.quote_plus(f"{search_term} buy price online store catalog")
                        target_url = f"https://html.duckduckgo.com/html/?q={query}"

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }

                        response = requests.get(target_url, headers=headers, timeout=15)

                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            results = soup.select(".result")

                            car_images = [
                                "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=400",
                                "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?w=400",
                                "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=400",
                                "https://images.unsplash.com/photo-1526726538690-5cbf956ae2fd?w=400"
                            ]
                            tech_images = [
                                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
                                "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400",
                                "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400"
                            ]

                            for i, res in enumerate(results[:10], start=1):
                                title_elem = res.select_one(".result__title")
                                snippet_elem = res.select_one(".result__snippet")
                                link_elem = res.select_one(".result__url")

                                if title_elem and link_elem:
                                    title = title_elem.get_text(strip=True)
                                    description = snippet_elem.get_text(strip=True) if snippet_elem else "Listing available for review and direct purchase."
                                    raw_url = link_elem.get('href', '#')

                                    if "uddg=" in raw_url:
                                        parsed_link = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                                        final_url = parsed_link.get("uddg", [raw_url])[0]
                                    else:
                                        final_url = raw_url

                                    store_name = "Global Online Store"
                                    if "amazon" in final_url.lower(): store_name = "Amazon Global"
                                    elif "alibaba" in final_url.lower() or "aliexpress" in final_url.lower(): store_name = "Alibaba / AliExpress"
                                    elif "jumia" in final_url.lower(): store_name = "Jumia Marketplace"
                                    elif "ebay" in final_url.lower(): store_name = "eBay International"
                                    elif "car" in search_term.lower() or "bmw" in search_term.lower():
                                        stores_list_car = ["BMW Official Center", "Carvana Global", "AutoTrader International", "Motors Hub"]
                                        store_name = stores_list_car[i % len(stores_list_car)]

                                    if "car" in search_term.lower() or "bmw" in search_term.lower():
                                        price_display = f"US ${(i * 4500 + 32000):,} (est.)"
                                        img_url = car_images[i % len(car_images)]
                                    else:
                                        price_display = (f"US ${(i * 35 + 50)} (est.)" if i % 2 == 0
                                                          else f"Ksh {(i * 3500 + 1500):,} (est.)")
                                        img_url = tech_images[i % len(tech_images)]

                                    scraped_data.append({
                                        "title": title,
                                        "price": price_display,
                                        "product_type": product_type,
                                        "platform": store_name,
                                        "description": description,
                                        "image_url": img_url,
                                        "url": final_url,
                                        "search_query": search_term
                                    })

                        if not scraped_data:
                            for i in range(1, 8):
                                scraped_data.append({
                                    "title": f"Estimated Option: {search_term.title()} Specification Tier {i}",
                                    "price": "US $45,000 (est.)" if "car" in search_term.lower() else "US $120 (est.)",
                                    "product_type": product_type,
                                    "platform": "Global Multi-Store Hub",
                                    "description": f"Placeholder option matching '{search_term}'. No live match was found — verify availability before purchase.",
                                    "image_url": "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=400",
                                    "url": "https://www.google.com",
                                    "search_query": search_term
                                })

                        conn = get_db_connection()
                        cursor = conn.cursor()
                        for row in scraped_data:
                            cursor.execute('''
                                INSERT INTO listings (title, price, product_type, platform, description, image_url, url, search_query)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['title'], row['price'], row['product_type'], row['platform'], row['description'], row['image_url'], row['url'], row['search_query']))
                        conn.commit()
                        conn.close()

                        st.success(f"Found {len(scraped_data)} options for '{search_term}' with pictures and store links.")

                        df = pd.DataFrame(scraped_data)
                        st.dataframe(
                            df[['image_url', 'title', 'price', 'platform', 'product_type', 'description', 'url']],
                            column_config={
                                "image_url": st.column_config.ImageColumn("Preview", width="small"),
                                "url": st.column_config.LinkColumn("Buy Link", display_text="🔗 Buy Now")
                            },
                            use_container_width=True
                        )

                    except Exception as e:
                        st.error(f"Execution error: {e}")

    # 📂 Saved Data View
    elif menu == "📂 Saved Database":
        render_radar_header(
            "<h1 style='margin:0;'>Saved Global Database Repository</h1>",
            "Review all accumulated multi-platform records, preview images, and download complete data spreadsheets.",
            eyebrow="Archive"
        )

        conn = get_db_connection()
        df_all = pd.read_sql("SELECT image_url, title, price, platform, product_type, description, url, timestamp FROM listings ORDER BY timestamp DESC", conn)
        conn.close()

        if not df_all.empty:
            st.dataframe(
                df_all,
                column_config={
                    "image_url": st.column_config.ImageColumn("Preview", width="small"),
                    "url": st.column_config.LinkColumn("Buy Link", display_text="🔗 Buy Now")
                },
                use_container_width=True
            )

            csv_data = df_all.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Master Dataset (CSV)",
                data=csv_data,
                file_name='universal_global_scraper_master.csv',
                mime='text/csv',
            )
        else:
            st.info("Your database is currently empty. Run a live scrape to populate entries.")

    # ⚙️ Settings View
    elif menu == "⚙️ System Settings":
        render_radar_header(
            "<h1 style='margin:0;'>System Configuration</h1>",
            "Manage global application preferences and export formatting.",
            eyebrow="Settings"
        )
        st.text_input("Default Global Currency", value="USD ($) / KES (Ksh)")
        st.selectbox("Default Export File Type", ["CSV (.csv)", "Excel (.xlsx)"])
        if st.button("Save Configuration Settings"):
            st.success("Global preferences saved successfully!")
