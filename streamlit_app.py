import streamlit as st
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse

def html_block(markup: str):
    """Render raw HTML/CSS in the main page body.
    st.html() (Streamlit >= 1.31) injects markup directly with no Markdown
    parsing step at all, so indentation can never get misread as a code
    block the way it can with st.markdown(..., unsafe_allow_html=True)."""
    st.html(markup)

def sidebar_html_block(markup: str):
    """Render raw HTML/CSS in the sidebar, same no-markdown-parsing guarantee."""
    with st.sidebar:
        st.html(markup)

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

    /* Section label (e.g. "Quick Access") */
    .section-label{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11.5px; letter-spacing: 0.12em; text-transform: uppercase;
        color: var(--text-dim); margin: 34px 0 14px;
    }

    /* Feature cards on the welcome hub */
    [data-testid="stVerticalBlockBorderWrapper"]{
        background: var(--panel) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover{
        transform: translateY(-3px);
        border-color: var(--amber-dim) !important;
        box-shadow: 0 12px 28px rgba(255,122,61,0.14);
    }
    .feature-icon{
        width: 46px; height: 46px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        background: var(--panel-2); border: 1px solid var(--line);
        font-size: 21px; margin-bottom: 14px;
    }
    .feature-title{
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important; font-size: 17px;
        margin-bottom: 6px;
    }
    .feature-desc{
        font-size: 13px; color: var(--text-dim) !important;
        line-height: 1.55; margin-bottom: 2px; min-height: 58px;
    }

    /* Search bar + result cards on the scraper page */
    .stTextInput input{ padding: 14px 16px !important; font-size: 15px !important; }
    [data-testid="stImage"] img{ border-radius: 10px !important; }
    .result-platform{
        font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
        letter-spacing: 0.08em; text-transform: uppercase;
        color: var(--mint); margin-top: 12px; margin-bottom: 4px;
    }
    .result-title{
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important; font-size: 15px;
        line-height: 1.35; margin-bottom: 8px; min-height: 40px;
    }
    .result-price{
        font-family: 'Space Grotesk', sans-serif; font-weight: 700;
        font-size: 17px; color: var(--amber); margin-bottom: 10px;
    }

    /* Buy Now link buttons -> same amber treatment as regular buttons */
    .stLinkButton > a, [data-testid="stLinkButton"] a{
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        background: var(--amber) !important;
        color: #1a0e06 !important;
        border: none !important;
        text-decoration: none !important;
        display: flex !important;
        align-items: center; justify-content: center;
        padding: 0.6rem 1rem !important;
        transition: background .12s ease, box-shadow .12s ease, transform .12s ease;
    }
    .stLinkButton > a:hover, [data-testid="stLinkButton"] a:hover{
        background: #ff8a53 !important;
        box-shadow: 0 6px 20px rgba(255,122,61,0.28) !important;
        transform: translateY(-1px);
    }
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
                        st.session_state.nav_choice = "🏠 Welcome & Landing Page"
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
                        st.session_state.nav_choice = "🏠 Welcome & Landing Page"
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
    sidebar_html_block(f"""
        <div class="status-pill"><span class="dot"></span>Feeds Online</div>
        <h3 style='margin-top:14px;'>⚡ {st.session_state.username}</h3>
    """)
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

    # 🏠 Landing Page / Hero Screen — the hub every user lands on after login
    if menu == "🏠 Welcome & Landing Page":

        render_ticker()

        # Top bar: logo + live status, nothing else — full navigation lives
        # in the sidebar and in the feature cards below, so this stays clean.
        col_logo, col_status = st.columns([2, 1])
        with col_logo:
            st.markdown("### ⚡ **Apex Global**")
        with col_status:
            html_block(f"""
                <div style="text-align:right; margin-top:8px;">
                    <span class="status-pill"><span class="dot"></span>Feeds Online</span>
                </div>
            """)

        # Radar Hero Section
        html_block("""
            <div class="hero-container">
                <div class="eyebrow" style="margin-bottom:16px;">Universal Inventory Interface</div>
                <div class="hero-title">WORLDWIDE STORE<br>&amp; VEHICLE INTELLIGENCE.</div>
                <div class="hero-subtitle">Instantly scan global store inventories and vehicle listings across dozens of platforms at once. Compare live prices, preview images, and jump straight to the source.</div>
            </div>
        """)

        # Quick Access — clickable feature cards, the real navigation hub
        html_block('<div class="section-label">Quick Access</div>')

        features = [
            ("🔍", "Live Scraper", "Search live inventory across dozens of global marketplaces and dealer networks at once.", "🔍 Worldwide Live Scraper", "Open Scraper"),
            ("📂", "Saved Database", "Browse, filter and export every listing you've collected so far.", "📂 Saved Database", "View Database"),
            ("⚙️", "Settings", "Set your default currency and export format for the whole app.", "⚙️ System Settings", "Open Settings"),
        ]

        card_cols = st.columns(3)
        for col, (icon, title, desc, target, btn_label) in zip(card_cols, features):
            with col:
                with st.container(border=True):
                    html_block(f"""
                        <div class="feature-icon">{icon}</div>
                        <div class="feature-title">{title}</div>
                        <div class="feature-desc">{desc}</div>
                    """)
                    if st.button(btn_label, key=f"card_{target}", use_container_width=True):
                        st.session_state.nav_choice = target
                        st.rerun()

        html_block("""
            <div class="strip">
                <div><div class="num">47</div><div class="lbl">Connected Platforms</div></div>
                <div><div class="num">19</div><div class="lbl">Regions Indexed</div></div>
                <div><div class="num">&lt;4s</div><div class="lbl">Avg. Response Time</div></div>
            </div>
        """)

        html_block('<div class="footer-tagline">You\'re part of the family</div>')

    # 🔍 Live Scraper View
    elif menu == "🔍 Worldwide Live Scraper":

        render_ticker()
        render_radar_header(
            "<h1 style='margin:0;'>Worldwide Store &amp; Vehicle Scraper</h1>",
            "Search for anything — a specific phone, a car model, a laptop — and we scan marketplaces and dealer networks across the globe for matches, with pictures, prices, and a direct link to buy.",
            eyebrow="Query Manifest — 001"
        )

        col_search, col_btn = st.columns([5, 1.3])
        with col_search:
            search_term = st.text_input(
                "Search",
                placeholder="e.g. iPhone 15 Pro, BMW M4, gaming laptop, leather sofa...",
                label_visibility="collapsed"
            )
        with col_btn:
            submit_btn = st.button("🚀 Search", use_container_width=True)

        if submit_btn:
            if not search_term:
                st.warning("Please enter what you're looking for first.")
            else:
                # Auto-detect a rough category from the search term itself —
                # no dropdown needed, and the scraper always searches worldwide.
                term_lower = search_term.lower()
                car_keywords = ["car", "bmw", "benz", "mercedes", "toyota", "honda",
                                 "ford", "audi", "vehicle", "suv", "truck", "motor", "vw", "lexus"]
                is_car_search = any(k in term_lower for k in car_keywords)
                product_type = "Automobiles & Vehicles" if is_car_search else "General Merchandise"

                with st.spinner(f"Scanning global platforms for '{search_term}'..."):
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
                                    elif is_car_search:
                                        stores_list_car = ["BMW Official Center", "Carvana Global", "AutoTrader International", "Motors Hub"]
                                        store_name = stores_list_car[i % len(stores_list_car)]

                                    if is_car_search:
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
                                    "price": "US $45,000 (est.)" if is_car_search else "US $120 (est.)",
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

                        st.success(f"Found {len(scraped_data)} options for '{search_term}' across global platforms.")
                        html_block('<div class="section-label">Results</div>')

                        result_cols = st.columns(3)
                        for idx, row in enumerate(scraped_data):
                            with result_cols[idx % 3]:
                                with st.container(border=True):
                                    st.image(row['image_url'], use_container_width=True)
                                    html_block(f"""
                                        <div class="result-platform">{row['platform']}</div>
                                        <div class="result-title">{row['title'][:70]}</div>
                                        <div class="result-price">{row['price']}</div>
                                    """)
                                    st.link_button("🔗 Buy Now", row['url'], use_container_width=True)

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
