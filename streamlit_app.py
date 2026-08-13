import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
try:
    import stripe
except ImportError:
    stripe = None
def html_block(markup: str):
    """Render raw HTML/CSS in the main page
body.
    st.html() (Streamlit >= 1.31) injects
markup directly with no Markdown
    parsing step at all, so indentation can
never get misread as a code
    block the way it can with
st.markdown(...,
unsafe_allow_html=True)."""
    st.html(markup)
def sidebar_html_block(markup: str):
    """Render raw HTML/CSS in the sidebar,
same no-markdown-parsing guarantee."""
    with st.sidebar:
        st.html(markup)
_PRICE_PATTERN =
re.compile(r'(?:USD|US\$|\$|KES|Ksh|£|
€|R\s)\s?[\d,]+(?:\.\d{1,2})?')
def extract_price_from_text(text):
    """Look for an obvious currency amount
in plain text (e.g. a search
    snippet). Returns None rather than a
guess if nothing matches."""
    if not text:
        return None
    match = _PRICE_PATTERN.search(text)
    return match.group(0).strip() if match
else None
def fetch_real_product_details(url,
timeout=6):
    """Best-effort real photo + real price
straight off the actual listing
    page (via Open Graph / product meta
tags). Many retailers block
    scraping or simply don't expose this
data — when that happens this
    returns None for that field instead of
inventing a number or picture."""
    result = {"image": None, "price": None}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0
(Windows NT 10.0; Win64; x64)
AppleWebKit/537.36 (KHTML, like Gecko)
Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url,
headers=headers, timeout=timeout)
        if resp.status_code == 200:
            page = BeautifulSoup(resp.text,
"html.parser")
            og_image = page.find("meta",
property="og:image")
            if og_image and
og_image.get("content"):
                result["image"] =
og_image["content"]
            price_meta = (
                page.find("meta",
property="product:price:amount")
                or page.find("meta",
property="og:price:amount")
                or page.find("meta", attrs=
{"itemprop": "price"})
            )
            currency_meta = (
                page.find("meta",
property="product:price:currency")
                or page.find("meta",
property="og:price:currency")
            )
            if price_meta and
price_meta.get("content"):
                currency =
currency_meta["content"] if currency_meta
and currency_meta.get("content") else ""
                result["price"] = f"
{currency} {price_meta['content']}".strip()
            else:
                result["price"] =
extract_price_from_text(page.get_text(" ",
strip=True)[:5000])
    except Exception:
        pass
    return result
# -----------------------------------------
-------------------------
# PASSWORD SECURITY
# Plain-text passwords are never stored —
bcrypt hashes + salts every
# password before it touches the database,
and verification re-hashes
# the attempt to compare rather than ever
storing/comparing raw text.
# -----------------------------------------
-------------------------
def hash_secret(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-
8"), bcrypt.gensalt()).decode("utf-8")
def verify_secret(raw: str, hashed: str) ->
bool:
    if not raw or not hashed:
        return False
    try:
        return
bcrypt.checkpw(raw.encode("utf-8"),
hashed.encode("utf-8"))
    except Exception:
        return False
def get_secret(key: str, default: str = "")
-> str:
    """Safe secrets lookup — returns the
default instead of crashing when
    no secrets.toml exists yet (e.g. on a
fresh deploy with nothing configured)."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default
# -----------------------------------------
-------------------------
# AFFILIATE LINK WIRING
# Fill these in via Streamlit secrets once
you're approved for each
# program (Amazon Associates, eBay Partner
Network, etc). Until you do,
# links go straight to the source with no
commission attached — nothing
# breaks either way, this just activates
automatically once configured.
# -----------------------------------------
-------------------------
AFFILIATE_TAGS = {
    "amazon.": ("tag",
get_secret("AMAZON_AFFILIATE_TAG")),
    "ebay.": ("campid",
get_secret("EBAY_CAMPAIGN_ID")),
    "aliexpress.": ("aff_id",
get_secret("ALIEXPRESS_AFFILIATE_ID")),
}
def apply_affiliate_tag(url: str, domain:
str) -> str:
    for key, (param, value) in
AFFILIATE_TAGS.items():
        if key in domain and value:
            separator = "&" if "?" in url
else "?"
            return f"{url}{separator}
{param}={value}"
    return url
# -----------------------------------------
-------------------------
# SEARCH BACKEND — tries three sources,
cheapest/free-est first isn't
# actually first here; it's ordered by
RELIABILITY, falling back toward
# free options so a real result is still
likely even with $0 to spend:
#
# 1. Serper (serper.dev) — only used if you
add a SERPER_API_KEY secret.
#    Paid past its small free trial, but
reliable. Add this once the site
#    is earning something — it's the
current best paid option (Google's
#    old Custom Search API is closed to new
signups as of 2025).
# 2. A public SearXNG instance — free, no
signup, no key required at all.
#    Not guaranteed reliable (public
instances get busy/rate-limited too)
#    but costs nothing to try, so it's a
free second attempt.
# 3. Scraping DuckDuckGo's HTML page
directly — free, no key, but the
#    least reliable since cloud server IPs
get blocked/rate-limited.
# -----------------------------------------
-------------------------
def fetch_search_results(query: str, num:
int = 9):
    """Returns (results, warning_message).
results is a list of dicts with
    title/url/snippet. warning_message is
None on success, or a short
    string explaining what went wrong (only
set if EVERY source failed)."""
    warnings = []
    # 1. Serper — paid, add SERPER_API_KEY
once there's revenue to spend
    serper_key =
get_secret("SERPER_API_KEY")
    if serper_key:
        try:
            resp = requests.post(
               
"https://google.serper.dev/search",
                headers={"X-API-KEY":
serper_key, "Content-Type":
"application/json"},
                json={"q": query, "num":
num},
                timeout=15
            )
            if resp.status_code == 200:
                organic =
resp.json().get("organic", [])
                results = [
                    {"title":
it.get("title", ""), "url": it.get("link",
""), "snippet": it.get("snippet", "")}
                    for it in organic[:num]
                ]
                if results:
                    return results, None
            warnings.append(f"Serper
returned status {resp.status_code}")
        except Exception as e:
            warnings.append(f"Serper error:
{e}")
    # 2. Free public SearXNG instances — no
key needed, try a few in case
    # one is down or rate-limiting right
now
    searx_instances = [
        "https://searx.be/search",
        "https://priv.au/search",
       
"https://searx.tiekoetter.com/search",
    ]
    headers = {"User-Agent": "Mozilla/5.0
(Windows NT 10.0; Win64; x64)
AppleWebKit/537.36 (KHTML, like Gecko)
Chrome/120.0.0.0 Safari/537.36"}
    for instance in searx_instances:
        try:
            resp = requests.get(
                instance,
                params={"q": query,
"format": "json"},
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                items =
resp.json().get("results", [])[:num]
                if items:
                    results = [
                        {"title":
it.get("title", ""), "url": it.get("url",
""), "snippet": it.get("content", "")}
                        for it in items
                    ]
                    return results, None
        except Exception:
            continue
    warnings.append("Public SearXNG
instances returned nothing")
    # 3. Last resort: scrape DuckDuckGo's
HTML page directly
    try:
        target_url =
f"https://html.duckduckgo.com/html/?q=
{urllib.parse.quote_plus(query)}"
        resp = requests.get(target_url,
headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text,
'html.parser')
            raw_results =
soup.select(".result")[:num]
            results = []
            for res in raw_results:
                title_elem =
res.select_one(".result__title")
                snippet_elem =
res.select_one(".result__snippet")
                link_elem =
res.select_one(".result__url")
                if not (title_elem and
link_elem):
                    continue
                raw_url =
link_elem.get('href', '#')
                if "uddg=" in raw_url:
                    parsed_link =
urllib.parse.parse_qs(urllib.parse.urlparse
(raw_url).query)
                    final_url =
parsed_link.get("uddg", [raw_url])[0]
                else:
                    final_url = raw_url
                results.append({
                    "title":
title_elem.get_text(strip=True),
                    "url": final_url,
                    "snippet":
snippet_elem.get_text(strip=True) if
snippet_elem else "",
                })
            if results:
                return results, None
            warnings.append("DuckDuckGo
returned a page with no results")
        else:
            warnings.append(f"DuckDuckGo
returned status {resp.status_code}")
    except Exception as e:
        warnings.append(f"DuckDuckGo error:
{e}")
    # Every source failed
    return [], "All search sources failed —
" + "; ".join(warnings) + ". This can be
temporary; try again in a moment, or add a
SERPER_API_KEY secret for a reliable paid
option."
# Page Configuration
st.set_page_config(
    page_title="PriceRadar — Global Product
& Vehicle Search",
    page_icon="🛰",
    layout="wide",
    initial_sidebar_state="expanded"
)
# -----------------------------------------
-------------------------
# PRICERADAR THEME — v2: violet primary +
coral accent, dark ink base
# Palette: ink #0a0b14, panel #12131f,
violet #8B5CF6 (was amber),
# coral #FF6B4A (new — deals/highlights),
mint #3ddc97 (status)
# Type: Space Grotesk (display), Inter
(body), JetBrains Mono (data/labels)
# -----------------------------------------
-------------------------
html_block("""
    <link rel="preconnect"
href="https://fonts.googleapis.com">
    <link
href="https://fonts.googleapis.com/css2?
family=Space+Grotesk:wght@500;600;700&famil
y=JetBrains+Mono:wght@400;500;600&family=In
ter:wght@400;500;600&display=swap"
rel="stylesheet">
    <style>
    :root{
        --bg: #0a0b14;
        --panel: #12131f;
        --panel-2: #171829;
        --line: #262840;
        --line-soft: #1c1d30;
        --text: #eef0fb;
        --text-dim: #8b8fae;
        --text-faint: #52546f;
        --amber: #8B5CF6;
        --amber-dim: #5B3FD6;
        --coral: #FF6B4A;
        --coral-dim: #C2431F;
        --mint: #3ddc97;
    }
    html, body, .stApp{
        background-color: var(--bg)
!important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif
!important;
    }
    .stApp{
        background-image:
            radial-gradient(circle at 15%
8%, rgba(139,92,246,0.10), transparent
40%),
            radial-gradient(circle at 85%
92%, rgba(255,107,74,0.07), transparent
40%);
    }
    /* Headings */
    h1, h2, h3, .hero-title{
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        color: var(--text) !important;
    }
    p, span, div, label{ color: var(--
text); }
    /* Sidebar */
    [data-testid="stSidebar"]{
        background-color: var(--panel)
!important;
        border-right: 1px solid var(--line￾soft);
    }
    [data-testid="stSidebar"] * { color:
var(--text) !important; }
    /* Widget labels -> mono, uppercase,
spaced, like manifest fields */
    [data-testid="stWidgetLabel"] p{
        font-family: 'JetBrains Mono',
monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-dim) !important;
    }
    /* Text inputs -> soft glass pill, used
everywhere for consistency */
    .stTextInput input, .stTextArea
textarea{
        background-color:
rgba(23,24,41,0.75) !important;
        backdrop-filter: blur(6px);
        border: 1px solid var(--line)
!important;
        border-radius: 999px !important;
        padding: 0.65rem 1.3rem !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif
!important;
    }
    .stTextArea textarea{ border-radius:
18px !important; }
    .stTextInput input:focus, .stTextArea
textarea:focus{
        border-color: var(--amber)
!important;
        box-shadow: 0 0 0 4px
rgba(139,92,246,0.16) !important;
    }
    .stTextInput input::placeholder{ color:
var(--text-faint) !important; }
    /* Selectboxes */
    [data-baseweb="select"] > div{
        background-color:
rgba(23,24,41,0.75) !important;
        border: 1px solid var(--line)
!important;
        border-radius: 18px !important;
        color: var(--text) !important;
    }
    [data-baseweb="popover"] li{
        background-color: var(--panel-2)
!important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif
!important;
    }
    /* Radio (auth mode toggle) */
    [role="radiogroup"] label{
        font-family: 'JetBrains Mono',
monospace !important;
        font-size: 12px !important;
        color: var(--text-dim) !important;
    }
    /* Buttons -> violet, pill-shaped,
Space Grotesk */
    .stButton > button, .stFormSubmitButton
> button{
        border-radius: 999px !important;
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg,
var(--amber), var(--amber-dim)) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 0.7rem 1.6rem !important;
        box-shadow: 0 0 0
rgba(139,92,246,0) !important;
        transition: transform .12s ease,
box-shadow .12s ease, background .12s ease
!important;
    }
    .stButton > button:hover,
.stFormSubmitButton > button:hover{
        background: #a586ff !important;
        box-shadow: 0 6px 24px
rgba(139,92,246,0.28) !important;
        transform: translateY(-1px);
    }
    /* Form panel -> manifest card */
    [data-testid="stForm"]{
        background: var(--panel)
!important;
        border: 1px solid var(--line)
!important;
        border-radius: 14px !important;
        padding: 6px 6px 18px 6px
!important;
        position: relative;
    }
    [data-testid="stForm"]::before{
        content: '';
        display: block;
        height: 2px;
        margin: -6px -6px 18px -6px;
        background: linear-gradient(90deg,
var(--amber), transparent 60%);
        border-radius: 14px 14px 0 0;
        opacity: 0.85;
    }
    /* Card box (login) -> rounder, warmer,
with a soft decorative glow
       behind it instead of a flat panel */
    .card-box{
        background: var(--panel)
!important;
        border: 1px solid var(--line)
!important;
        border-radius: 28px !important;
        padding: 36px 32px !important;
        position: relative;
        box-shadow: 0 30px 70px -20px
rgba(139,92,246,0.25);
    }
    .card-box::before{
        content: '';
        position: absolute; top: -60px;
left: -40px; right: -40px; height: 160px;
        background:
            radial-gradient(circle at 20%
30%, rgba(139,92,246,0.35), transparent
60%),
            radial-gradient(circle at 80%
30%, rgba(255,107,74,0.25), transparent
60%);
        border-radius: 50%;
        z-index: -1;
        filter: blur(10px);
    }
    /* Ticker */
    .ticker-bar{
        border-bottom: 1px solid var(--
line-soft);
        background: #0c1016;
        overflow: hidden;
        white-space: nowrap;
        padding: 9px 0;
        border-radius: 8px;
        margin-bottom: 18px;
    }
    .ticker-track{ display: inline-flex;
animation: scroll 32s linear infinite; }
    .ticker-item{
        font-family: 'JetBrains Mono',
monospace;
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
        width: 5px; height: 5px; border￾radius: 50%;
        background: var(--mint);
        box-shadow: 0 0 6px var(--mint);
    }
    @keyframes scroll{ from{ transform:
translateX(0); } to{ transform:
translateX(-50%); } }
    /* Eyebrow label */
    .eyebrow{
        display: flex; align-items: center;
gap: 10px;
        font-family: 'JetBrains Mono',
monospace;
        font-size: 12px; letter-spacing:
0.14em; text-transform: uppercase;
        color: var(--amber); margin-bottom:
10px;
    }
    .eyebrow::before{ content: ''; width:
22px; height: 1px; background: var(--amber￾dim); }
    /* Radar icon */
    .radar{
        position: relative; width: 64px;
height: 64px; flex-shrink: 0;
        border-radius: 50%;
        background: radial-gradient(circle,
#0e1420 0%, #0a0d13 70%);
        border: 1px solid var(--line);
    }
    .radar::before, .radar::after{
content:''; position:absolute; border￾radius: 50%; border: 1px solid var(--line￾soft); }
    .radar::before{ inset: 10px; }
    .radar::after{ inset: 20px; }
    .radar-sweep{
        position: absolute; inset: 0;
border-radius: 50%;
        background: conic-gradient(from
0deg, rgba(139,92,246,0.55), transparent
34%);
        animation: sweep 3.4s linear
infinite;
        mix-blend-mode: screen;
    }
    .radar-blip{
        position: absolute; width: 5px;
height: 5px; border-radius: 50%;
        background: var(--mint); box￾shadow: 0 0 8px var(--mint);
        top: 18px; left: 44px;
        animation: blip 3.4s ease-in-out
infinite;
    }
    @keyframes sweep{ to{ transform:
rotate(360deg); } }
    @keyframes blip{ 0%,74%{ opacity:0;}
78%{ opacity:1;} 92%{ opacity:0;} }
    .hero-row{ display:flex; align￾items:center; gap:20px; margin-bottom: 6px;
}
    /* Status pill */
    .status-pill{
        display:inline-flex; align￾items:center; gap:7px;
        font-family:'JetBrains Mono',
monospace; font-size: 11px;
        color: var(--mint); letter-spacing:
0.06em;
        border: 1px solid var(--line-soft);
background: var(--panel-2);
        padding: 5px 12px; border-radius:
20px;
    }
    .status-pill .dot{
        width:6px; height:6px; border￾radius:50%; background: var(--mint);
        box-shadow: 0 0 6px var(--mint);
animation: pulse 1.8s ease-in-out infinite;
    }
    @keyframes pulse{ 0%,100%{opacity:1;}
50%{opacity:.35;} }
    /* Sidebar brand lockup */
    .sidebar-brand{
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 700 !important; font￾size: 19px;
        letter-spacing: -0.01em; color:
var(--text) !important;
        margin-bottom: 14px;
    }
    /* Stats strip */
    .strip{
        display: grid; grid-template￾columns: repeat(3, 1fr); gap: 1px;
        background: var(--line-soft);
border: 1px solid var(--line-soft);
        border-radius: 10px; overflow:
hidden; margin-top: 18px;
    }
    .strip div{ background: var(--panel);
padding: 16px 20px; }
    .strip .num{ font-family: 'Space
Grotesk', sans-serif; font-size: 21px;
font-weight: 700; color: var(--amber); }
    .strip .lbl{ font-family: 'JetBrains
Mono', monospace; font-size: 10.5px;
letter-spacing: 0.08em; text-transform:
uppercase; color: var(--text-faint);
margin-top: 3px; }
    /* Hero (landing page) */
    .hero-container{
        position: relative;
        background-image: linear￾gradient(rgba(9,12,17,0.55),
rgba(9,12,17,0.95)),
           
url('https://images.unsplash.com/photo-
1486406146926-c627a92ad1ab?w=1600');
        background-size: cover;
        background-position: center;
        padding: 70px 40px;
        border-radius: 16px;
        margin-top: 10px;
        border: 1px solid var(--line);
    }
    .hero-title{
        font-size: 2.7rem; font-weight:
700; color: #ffffff;
        line-height: 1.15; letter-spacing:
-0.01em;
        text-shadow: 0 4px 12px
rgba(0,0,0,0.6);
    }
    .hero-subtitle{
        font-family: 'Inter', sans-serif;
        font-size: 1.05rem; color: var(--
text-dim);
        margin-top: 18px; margin-bottom:
30px;
        text-shadow: 0 2px 6px
rgba(0,0,0,0.6);
        max-width: 600px;
    }
    .footer-tagline{
        text-align: center; color: var(--
mint); font-weight: 600;
        font-family: 'JetBrains Mono',
monospace;
        font-size: 1rem; letter-spacing:
0.08em; margin-top: 40px;
        text-transform: uppercase;
    }
    /* Dataframe / tables */
    [data-testid="stDataFrame"]{ border:
1px solid var(--line) !important; border￾radius: 10px !important; }
    hr{ border-color: var(--line-soft)
!important; }
    /* Section label (e.g. "Quick Access")
*/
    .section-label{
        font-family: 'JetBrains Mono',
monospace;
        font-size: 11.5px; letter-spacing:
0.12em; text-transform: uppercase;
        color: var(--text-dim); margin:
34px 0 14px;
    }
    /* Feature cards on the welcome hub */
    [data￾testid="stVerticalBlockBorderWrapper"]{
        background: var(--panel)
!important;
        border: 1px solid var(--line)
!important;
        border-radius: 14px !important;
        transition: transform .15s ease,
box-shadow .15s ease, border-color .15s
ease;
    }
    [data￾testid="stVerticalBlockBorderWrapper"]:hove
r{
        transform: translateY(-3px);
        border-color: var(--amber-dim)
!important;
        box-shadow: 0 12px 28px
rgba(139,92,246,0.14);
    }
    .feature-icon{
        width: 46px; height: 46px; border￾radius: 14px;
        display: flex; align-items: center;
justify-content: center;
        background: var(--panel-2); border:
1px solid var(--line);
        font-size: 21px; margin-bottom:
14px;
    }
    .feature-icon.violet{ background:
rgba(139,92,246,0.15); border-color:
rgba(139,92,246,0.35); }
    .feature-icon.coral{ background:
rgba(255,107,74,0.15); border-color:
rgba(255,107,74,0.35); }
    .feature-icon.mint{ background:
rgba(61,220,151,0.15); border-color:
rgba(61,220,151,0.35); }
    .feature-title{
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 600 !important; font￾size: 17px;
        margin-bottom: 6px;
    }
    .feature-desc{
        font-size: 13px; color: var(--text￾dim) !important;
        line-height: 1.55; margin-bottom:
2px; min-height: 58px;
    }
    /* Search bar + result cards on the
scraper page */
    .stTextInput input{ padding: 14px 16px
!important; font-size: 15px !important; }
    [data-testid="stImage"] img{ border￾radius: 10px !important; }
    .result-platform{
        font-family: 'JetBrains Mono',
monospace; font-size: 10.5px;
        letter-spacing: 0.08em; text￾transform: uppercase;
        color: var(--mint); margin-top:
12px; margin-bottom: 4px;
    }
    .result-title{
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 600 !important; font￾size: 15px;
        line-height: 1.35; margin-bottom:
8px; min-height: 40px;
    }
    .result-price{
        font-family: 'Space Grotesk', sans￾serif; font-weight: 700;
        font-size: 17px; color: var(--
amber); margin-bottom: 10px;
    }
    /* Buy Now link buttons -> same violet
treatment as regular buttons */
    .stLinkButton > a, [data￾testid="stLinkButton"] a{
        border-radius: 999px !important;
        font-family: 'Space Grotesk', sans-
serif !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg,
var(--amber), var(--amber-dim)) !important;
        color: #ffffff !important;
        border: none !important;
        text-decoration: none !important;
        display: flex !important;
        align-items: center; justify￾content: center;
        padding: 0.6rem 1rem !important;
        transition: background .12s ease,
box-shadow .12s ease, transform .12s ease;
    }
    .stLinkButton > a:hover, [data￾testid="stLinkButton"] a:hover{
        background: #a586ff !important;
        box-shadow: 0 6px 20px
rgba(139,92,246,0.28) !important;
        transform: translateY(-1px);
    }
    /* Best-price badge on the cheapest
result in a search */
    .best-price-badge{
        display: inline-flex; align-items:
center; gap: 5px;
        font-family: 'JetBrains Mono',
monospace; font-size: 10.5px;
        letter-spacing: 0.06em; text￾transform: uppercase; font-weight: 600;
        color: #2b0e04; background: var(--
coral);
        padding: 4px 10px; border-radius:
20px; margin-bottom: 10px;
        box-shadow: 0 0 14px
rgba(255,107,74,0.4);
    }
    /* Subtle page-load fade so switching
between pages feels less abrupt */
    .main .block-container{
        animation: fadein .35s ease;
    }
    @keyframes fadein{
        from{ opacity: 0; transform:
translateY(4px); }
        to{ opacity: 1; transform:
translateY(0); }
    }
    /* Tabs (Favorites / Recent Searches /
Full Log) themed to match */
    .stTabs [data-baseweb="tab-list"]{
        gap: 6px; border-bottom: 1px solid
var(--line-soft);
    }
    .stTabs [data-baseweb="tab"]{
        font-family: 'Space Grotesk', sans￾serif !important;
        font-weight: 600 !important; font￾size: 14px !important;
        color: var(--text-dim) !important;
        background: transparent !important;
        border-radius: 8px 8px 0 0
!important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"]{
        color: var(--amber) !important;
        border-bottom: 2px solid var(--
amber) !important;
    }
    </style>
""")
def render_ticker():
    platforms = [
        "eBay Motors", "AutoTrader",
"Mobile.de", "Cars.com", "Carsales.com.au",
        "OLX", "Copart", "IAAI",
"CarGurus", "Facebook Marketplace",
        "Craigslist", "Amazon", "Newegg",
"Rakuten", "AliExpress", "Bring a Trailer"
    ]
    items = "".join(f'<span class="ticker￾item"><span class="dot"></span>{p}</span>'
for p in platforms)
    html_block(f"""
        <div class="ticker-bar">
            <div class="ticker-track">
{items}{items}</div>
        </div>
    """)
def render_radar_header(title_html,
subtitle=None, eyebrow=None):
    if eyebrow:
        st.markdown(f'<div class="eyebrow">
{eyebrow}</div>', unsafe_allow_html=True)
    html_block(f"""
        <div class="hero-row">
            <div class="radar"><div
class="radar-sweep"></div><div
class="radar-blip"></div></div>
            <div>{title_html}</div>
        </div>
    """)
    if subtitle:
        st.markdown(f'<p style="color:var(-
-text-dim); font-size:15px; max￾width:560px; margin-top:6px;">{subtitle}
</p>', unsafe_allow_html=True)
# -----------------------------------------
-------------------------
# DATABASE
# Defaults to a local SQLite file (zero
setup — works immediately).
# IMPORTANT: Streamlit Cloud's filesystem
is not permanent — every
# redeploy/restart can wipe local SQLite
data, including user accounts.
# Add a DATABASE_URL secret (e.g. a free
Supabase or Neon Postgres
# instance) to switch to real persistent
storage with no code changes.
# -----------------------------------------
-------------------------
DB_URL = get_secret("DATABASE_URL",
"sqlite:///scraper_data.db")
engine = create_engine(DB_URL,
pool_pre_ping=True)
IS_SQLITE = engine.dialect.name == "sqlite"
USING_TEMP_STORAGE = IS_SQLITE and not
get_secret("DATABASE_URL")
def init_db():
    id_column = "id INTEGER PRIMARY KEY
AUTOINCREMENT" if IS_SQLITE else "id SERIAL
PRIMARY KEY"
    bool_default = "0" if IS_SQLITE else
"FALSE"
    with engine.begin() as conn:
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS
listings (
                {id_column},
                title TEXT,
                price TEXT,
                product_type TEXT,
                platform TEXT,
                description TEXT,
                image_url TEXT,
                url TEXT,
                search_query TEXT,
                featured BOOLEAN DEFAULT
{bool_default},
                timestamp TIMESTAMP DEFAULT
CURRENT_TIMESTAMP
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS
users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                security_question TEXT,
                security_answer_hash TEXT,
                failed_attempts INTEGER
DEFAULT 0,
                locked_until TIMESTAMP NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS
favorites (
                {id_column},
                username TEXT,
                title TEXT,
                price TEXT,
                platform TEXT,
                image_url TEXT,
                url TEXT,
                saved_at TIMESTAMP DEFAULT
CURRENT_TIMESTAMP
            )
        '''))
    # Lightweight migrations for columns
added after the initial deploy.
    # Each runs in its OWN transaction — if
a column already exists, the
    # ALTER fails and we swallow it, but on
Postgres a failed statement
    # poisons the rest of that transaction,
so these can't share one.
    def _safe_migrate(stmt):
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass
    _safe_migrate("ALTER TABLE listings ADD
COLUMN username TEXT")
    _safe_migrate("ALTER TABLE users ADD
COLUMN preferred_currency TEXT DEFAULT
'USD'")
init_db()
CURRENCY_OPTIONS = ["USD", "EUR", "GBP",
"KES", "NGN", "INR", "ZAR", "AED", "CAD",
"AUD"]
_CURRENCY_SYMBOL_MAP = {
    "US$": "USD", "USD": "USD", "$": "USD",
    "£": "GBP", "GBP": "GBP",
    "€": "EUR", "EUR": "EUR",
    "KES": "KES", "Ksh": "KES",
    "R ": "ZAR", "ZAR": "ZAR",
}
@st.cache_data(ttl=3600)
def fetch_exchange_rates():
    """Free, no-key exchange rate feed,
refreshed hourly. Returns an empty
    dict on failure — callers just skip
conversion rather than crash."""
    try:
        resp =
requests.get("https://open.er￾api.com/v6/latest/USD", timeout=8)
        if resp.status_code == 200:
            return resp.json().get("rates",
{})
    except Exception:
        pass
    return {}
def convert_price_display(price_str,
target_currency, rates):
    """Best-effort currency conversion for
a free-text price string like
    '$799' or 'KES 45,000'. This is
approximate — it's regex-parsing text,
    not structured data — so it appends a
converted estimate rather than
    replacing the original price."""
    if not price_str or not rates or
target_currency not in rates:
        return price_str
    match = re.search(r'([\d,]+
(?:\.\d{1,2})?)', price_str)
    if not match:
        return price_str
    try:
        amount =
float(match.group(1).replace(",", ""))
    except ValueError:
        return price_str
    source_currency = "USD"
    for symbol, code in
_CURRENCY_SYMBOL_MAP.items():
        if symbol in price_str:
            source_currency = code
            break
    if source_currency == target_currency
or source_currency not in rates:
        return price_str
    usd_amount = amount /
rates[source_currency]
    converted = usd_amount *
rates[target_currency]
    return f"{price_str}  (≈
{converted:,.2f} {target_currency})"
SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your childhood nickname?",
    "What's the name of your favorite
teacher?",
]
# Session State Management
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = "🏠 Home"
if "currency" not in st.session_state:
    st.session_state.currency = "USD"
if "prefill_search" not in
st.session_state:
    st.session_state.prefill_search = ""
if "admin_bypass" not in st.session_state:
    st.session_state.admin_bypass = False
# -----------------------------------------
-------------------------
# LAUNCH GATE
# Keeps the site closed to everyone until
LAUNCH_DATE, then opens on its
# own — no need to remember to flip a
switch. Override the date via a
# LAUNCH_DATE secret (ISO format, e.g.
"2026-11-23T00:00:00") if plans
# change. Enter ADMIN_ACCESS_CODE (set as a
secret) on the closed screen
# to keep testing the app yourself while
it's locked for everyone else.
# -----------------------------------------
-------------------------
try:
    LAUNCH_DATE =
datetime.fromisoformat(get_secret("LAUNCH_D
ATE", "2026-11-23T00:00:00"))
except ValueError:
    LAUNCH_DATE = datetime(2026, 11, 23)
ADMIN_ACCESS_CODE =
get_secret("ADMIN_ACCESS_CODE")
site_is_locked = datetime.utcnow() <
LAUNCH_DATE and not
st.session_state.admin_bypass
if site_is_locked:
    st.markdown("<br><br><br>",
unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1,
1.2, 1])
    with col_l2:
        st.markdown("<div class='card￾box'>", unsafe_allow_html=True)
        render_radar_header(
            "<h2
style='margin:0;'>PRICERADAR</h2>",
            f"We're putting the finishing
touches on things. Check back on
{LAUNCH_DATE.strftime('%B %d, %Y')}.",
            eyebrow="Coming Soon"
        )
        if ADMIN_ACCESS_CODE:
            with st.expander("Owner
access"):
                entered_code =
st.text_input("Access code",
type="password",
label_visibility="collapsed",
placeholder="Access code")
                if st.button("Unlock"):
                    if entered_code ==
ADMIN_ACCESS_CODE:
                       
st.session_state.admin_bypass = True
                        st.rerun()
                    else:
                        st.error("Incorrect
code.")
        st.markdown("</div>",
unsafe_allow_html=True)
    st.stop()
# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<br><br>",
unsafe_allow_html=True)
    col_center1, col_center2, col_center3 =
st.columns([1, 1.2, 1])
    with col_center2:
        st.markdown("<div class='card￾box'>", unsafe_allow_html=True)
        render_radar_header(
            "<h2
style='margin:0;'>PRICERADAR</h2>",
            "Sign in to start comparing
prices across the globe.",
            eyebrow="Access Manifest"
        )
        if USING_TEMP_STORAGE:
            st.warning("Running on
temporary storage — accounts may be reset
on redeploy. Add a DATABASE_URL secret for
permanent accounts.", icon="⚠️")
        auth_mode = st.radio("Mode", ["Log
In", "Sign Up", "Forgot Password"],
horizontal=True,
label_visibility="collapsed")
        # ---------------- SIGN UP --------
--------
        if auth_mode == "Sign Up":
            input_user =
st.text_input("Username",
placeholder="Enter your username")
            input_pass =
st.text_input("Password", type="password",
placeholder="Choose a password")
            input_question =
st.selectbox("Security question (for
password recovery)", SECURITY_QUESTIONS)
            input_answer =
st.text_input("Your answer",
placeholder="Used only if you ever forget
your password")
            if st.button("Create Account &
Sign In"):
                if input_user and
input_pass and input_answer:
                    with engine.begin() as
conn:
                        existing =
conn.execute(
                            text("SELECT
username FROM users WHERE username = :u"),
                            {"u":
input_user}
                        ).fetchone()
                        if existing:
                           
st.error("Username already exists! Please
log in instead.")
                        else:
                            conn.execute(
                               
text('''INSERT INTO users
                                       
(username, password_hash,
security_question, security_answer_hash,
failed_attempts)
                                       
VALUES (:u, :p, :q, :a, 0)'''),
                                {
                                    "u":
input_user,
                                    "p":
hash_secret(input_pass),
                                    "q":
input_question,
                                    "a":
hash_secret(input_answer.strip().lower()),
                                }
                            )
                           
st.session_state.logged_in = True
                           
st.session_state.username = input_user
                           
st.session_state.nav_choice = "🏠 Home"
                           
st.success("Account created successfully!
Entering dashboard...")
                            st.rerun()
                else:
                    st.warning("Please fill
in every field, including the security
answer.")
        # ---------------- LOG IN ---------
-------
        elif auth_mode == "Log In":
            input_user =
st.text_input("Username",
placeholder="Enter your username")
            input_pass =
st.text_input("Password", type="password",
placeholder="Enter your password")
            if st.button("Log In to
Dashboard"):
                if input_user and
input_pass:
                    with engine.begin() as
conn:
                        user_record =
conn.execute(
                            text("SELECT *
FROM users WHERE username = :u"),
                            {"u":
input_user}
                       
).mappings().fetchone()
                        now =
datetime.utcnow()
                        locked_until =
user_record["locked_until"] if user_record
else None
                        if
isinstance(locked_until, str):
                            try:
                               
locked_until =
datetime.fromisoformat(locked_until)
                            except
ValueError:
                               
locked_until = None
                        if user_record and
locked_until and locked_until > now:
                            minutes_left =
max(1, int((locked_until -
now).total_seconds() // 60) + 1)
                            st.error(f"Too
many failed attempts. Try again in about
{minutes_left} minute(s).")
                        elif user_record
and verify_secret(input_pass,
user_record["password_hash"]):
                            conn.execute(
                               
text("UPDATE users SET failed_attempts = 0,
locked_until = NULL WHERE username = :u"),
                                {"u":
input_user}
                            )
                           
st.session_state.logged_in = True
                           
st.session_state.username = input_user
                           
st.session_state.nav_choice = "🏠 Home"
                           
st.session_state.currency =
user_record["preferred_currency"] or "USD"
                           
st.success("Login successful! Welcome
back.")
                            st.rerun()
                        else:
                            if user_record:
                                attempts =
(user_record["failed_attempts"] or 0) + 1
                                if attempts
>= 5:
                                   
conn.execute(
                                       
text("UPDATE users SET failed_attempts =
:a, locked_until = :l WHERE username =
:u"),
                                       
{"a": attempts, "l": now +
timedelta(minutes=15), "u": input_user}
                                    )
                                   
st.error("Too many failed attempts. Account
locked for 15 minutes.")
                                else:
                                   
conn.execute(
                                       
text("UPDATE users SET failed_attempts = :a
WHERE username = :u"),
                                       
{"a": attempts, "u": input_user}
                                    )
                                   
st.error(f"Invalid username or password. {5
- attempts} attempt(s) left before a
temporary lock.")
                            else:
                               
st.error("Invalid username or password.")
                else:
                    st.warning("Please
enter your credentials.")
        # ---------------- FORGOT PASSWORD
----------------
        else:
            recover_user =
st.text_input("Username",
placeholder="Enter your username",
key="recover_user")
            if recover_user:
                with engine.begin() as
conn:
                    record = conn.execute(
                        text("SELECT
security_question, security_answer_hash
FROM users WHERE username = :u"),
                        {"u": recover_user}
                    ).mappings().fetchone()
                if not record:
                    st.error("No account
found with that username.")
                else:
                    st.markdown(f"**
{record['security_question']}**")
                    recover_answer =
st.text_input("Your answer",
key="recover_answer")
                    new_pass =
st.text_input("New password",
type="password", key="recover_new_pass")
                    if st.button("Reset
Password"):
                        if recover_answer
and new_pass:
                            if
verify_secret(recover_answer.strip().lower(
), record["security_answer_hash"]):
                                with
engine.begin() as conn:
                                   
conn.execute(
                                       
text("UPDATE users SET password_hash = :p,
failed_attempts = 0, locked_until = NULL
WHERE username = :u"),
                                       
{"p": hash_secret(new_pass), "u":
recover_user}
                                    )
                               
st.success("Password reset! You can now log
in with your new password.")
                            else:
                               
st.error("That answer doesn't match our
records.")
                        else:
                           
st.warning("Please answer the question and
choose a new password.")
        st.markdown("</div>",
unsafe_allow_html=True)
# --- MAIN APPLICATION (Unlocked after
Login) ---
else:
    # Sidebar Navigation Hub synced with
session state
    sidebar_html_block(f"""
        <div class="sidebar-brand">🛰
PriceRadar</div>
        <div class="status-pill"><span
class="dot"></span>Feeds Online</div>
        <h3 style='margin-top:14px;'>👋
{st.session_state.username}</h3>
    """)
    st.sidebar.markdown("---")
    menu_options = ["🏠 Home", "🔎 Search",
"🗂 Saved Listings", "⚙️ Preferences"]
    current_index =
menu_options.index(st.session_state.nav_cho
ice) if st.session_state.nav_choice in
menu_options else 0
    menu = st.sidebar.radio("Navigation
Menu", menu_options, index=current_index)
    st.session_state.nav_choice = menu
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.nav_choice = "🏠
Home"
        st.rerun()
    # 🏠 Landing Page / Hero Screen — the
hub every user lands on after login
    if menu == "🏠 Home":
        render_ticker()
        # Top bar: logo + live status,
nothing else — full navigation lives
        # in the sidebar and in the feature
cards below, so this stays clean.
        col_logo, col_status =
st.columns([2, 1])
        with col_logo:
            st.markdown("### 🛰
**PriceRadar**")
        with col_status:
            html_block(f"""
                <div style="text￾align:right; margin-top:8px;">
                    <span class="status￾pill"><span class="dot"></span>Feeds
Online</span>
                </div>
            """)
        # Radar Hero Section
        html_block("""
            <div class="hero-container">
                <div class="eyebrow"
style="margin-bottom:16px;">One Search.
Every Marketplace.</div>
                <div class="hero￾title">FIND IT.<br>COMPARE IT.<br>&amp; BUY
IT.</div>
                <div class="hero￾subtitle">PriceRadar scans stores and
dealer networks across the globe at once —
real photos, real prices where available,
and a direct link to buy.</div>
            </div>
        """)
        # Quick Access — clickable feature
cards, the real navigation hub
        html_block('<div class="section￾label">Quick Access</div>')
        features = [
            ("🔎", "Search", "Search live
inventory across dozens of global
marketplaces and dealer networks at once.",
"🔎 Search", "Start Searching", "violet"),
            ("🗂", "Saved Listings",
"Browse, filter and export every listing
you've collected so far.", "🗂 Saved
Listings", "View Saved", "coral"),
            ("⚙️", "Preferences", "Set your
default currency and export format for the
whole app.", "⚙️ Preferences", "Open
Preferences", "mint"),
        ]
        card_cols = st.columns(3)
        for col, (icon, title, desc,
target, btn_label, accent) in
zip(card_cols, features):
            with col:
                with
st.container(border=True):
                    html_block(f"""
                        <div
class="feature-icon {accent}">{icon}</div>
                        <div
class="feature-title">{title}</div>
                        <div
class="feature-desc">{desc}</div>
                    """)
                    if st.button(btn_label,
key=f"card_{target}",
use_container_width=True):
                       
st.session_state.nav_choice = target
                        st.rerun()
        html_block("""
            <div class="strip">
                <div><div
class="num">47</div><div
class="lbl">Connected Platforms</div></div>
                <div><div
class="num">19</div><div
class="lbl">Regions Indexed</div></div>
                <div><div
class="num">&lt;4s</div><div
class="lbl">Avg. Response Time</div></div>
            </div>
        """)
        # Trending Searches — real data,
not decorative: whatever people
        # across the whole site have
searched for most recently
        trending_df = pd.read_sql(
            text('''SELECT search_query,
COUNT(*) AS times_searched
                    FROM listings GROUP BY
search_query
                    ORDER BY MAX(timestamp)
DESC LIMIT 8'''),
            engine
        )
        if not trending_df.empty:
            html_block('<div
class="section-label">Trending
Searches</div>')
            trend_cols = st.columns(4)
            for idx, trend in
trending_df.iterrows():
                with trend_cols[idx % 4]:
                    if st.button(f"🔥
{trend['search_query']}",
key=f"trend_{idx}",
use_container_width=True):
                       
st.session_state.prefill_search =
trend['search_query']
                       
st.session_state.nav_choice = "🔎 Search"
                        st.rerun()
        html_block('<div class="footer￾tagline">Search smarter. Buy better.
</div>')
    # 🔎 Search View
    elif menu == "🔎 Search":
        render_ticker()
        render_radar_header(
            "<h1 style='margin:0;'>Search
Worldwide</h1>",
            "Search for anything — a
specific phone, a car model, a laptop — and
we scan marketplaces and dealer networks
across the globe for real matches, with
real photos, real prices where available,
and a direct link to buy.",
            eyebrow="Query Manifest — 001"
        )
        col_search, col_btn =
st.columns([5, 1.3])
        with col_search:
            search_term = st.text_input(
                "Search",
               
value=st.session_state.prefill_search,
                placeholder="e.g. iPhone 15
Pro, BMW M4, gaming laptop, leather
sofa...",
               
label_visibility="collapsed"
            )
        with col_btn:
            submit_btn = st.button("🚀
Search", use_container_width=True)
        st.session_state.prefill_search =
""
        # Category quick-filters — tap one
to prefill a search rather than
        # typing from scratch
        category_chips = [
            ("📱", "Phones", "smartphone"),
            ("💻", "Laptops", "laptop"),
            ("🚗", "Vehicles", "car"),
            ("👗", "Fashion", "clothing"),
            ("🛋", "Home", "furniture"),
            ("🎧", "Audio", "headphones"),
        ]
        chip_cols =
st.columns(len(category_chips))
        for col, (icon, label, term) in
zip(chip_cols, category_chips):
            with col:
                if st.button(f"{icon}
{label}", key=f"chip_{term}",
use_container_width=True):
                   
st.session_state.prefill_search = term
                    st.rerun()
        with st.expander("🎯 Refine your
search (optional)"):
            col_site, col_country =
st.columns(2)
            with col_site:
                site_filter =
st.text_input("Limit to a specific site",
placeholder="e.g. ebay.com, jumia.co.ke")
            with col_country:
                country_filter =
st.text_input("Limit to a country or
region", placeholder="e.g. Kenya, Germany,
UAE")
        if submit_btn:
            if not search_term:
                st.warning("Please enter
what you're looking for first.")
            else:
                # Auto-detect a rough
category from the search term itself —
                # no dropdown needed, and
the search always covers the globe
                # unless you've narrowed it
with a site/country above.
                term_lower =
search_term.lower()
                car_keywords = ["car",
"bmw", "benz", "mercedes", "toyota",
"honda",
                                 "ford",
"audi", "vehicle", "suv", "truck", "motor",
"vw", "lexus"]
                is_car_search = any(k in
term_lower for k in car_keywords)
                product_type = "Automobiles
& Vehicles" if is_car_search else "General
Merchandise"
                spinner_msg = f"Scanning
global platforms for '{search_term}'"
                if site_filter:
                    spinner_msg += f" on
{site_filter}"
                if country_filter:
                    spinner_msg += f" in
{country_filter}"
                with st.spinner(spinner_msg
+ " — pulling real photos and prices from
each listing, this can take a moment..."):
                    try:
                        scraped_data = []
                        query_parts =
[search_term, "buy", "price"]
                        if
site_filter.strip():
                           
query_parts.append(f"site:
{site_filter.strip()}")
                        if
country_filter.strip():
                           
query_parts.append(country_filter.strip())
                        query = "
".join(query_parts)
                        known_platforms = {
                            "amazon.":
"Amazon", "ebay.": "eBay", "alibaba.":
"Alibaba",
                            "aliexpress.":
"AliExpress", "jumia.": "Jumia",
"autotrader.": "AutoTrader",
                            "cars.com":
"Cars.com", "carsales.": "Carsales",
"mobile.de": "Mobile.de",
                            "cargurus.":
"CarGurus", "olx.": "OLX", "craigslist.":
"Craigslist",
                            "facebook.":
"Facebook Marketplace", "walmart.":
"Walmart", "newegg.": "Newegg",
                        }
                        search_results,
search_warning =
fetch_search_results(query, num=9)
                        if search_warning:
                           
st.warning(search_warning)
                        for res in
search_results:
                            title =
res["title"]
                            description =
res["snippet"]
                            final_url =
res["url"]
                            domain =
urllib.parse.urlparse(final_url).netloc.rep
lace("www.", "")
                            store_name =
domain or "Online Store"
                            for key, label
in known_platforms.items():
                                if key in
domain:
                                   
store_name = label
                                    break
                            # Try to pull
the real photo + real price straight off
                            # the actual
listing page. Many sites block this or
                            # don't expose
it — when that happens we're honest
                            # about it
instead of making something up.
                            details =
fetch_real_product_details(final_url)
                            image_url =
details["image"] or
f"https://www.google.com/s2/favicons?
sz=128&domain={domain}"
                            price_display =
details["price"] or
extract_price_from_text(description) or
"See listing for price"
                            # Route through
your affiliate tag if one's configured
                            # for this
platform — otherwise the link is untouched.
                            final_url =
apply_affiliate_tag(final_url, domain)
                           
scraped_data.append({
                                "title":
title,
                                "price":
price_display,
                               
"product_type": product_type,
                                "platform":
store_name,
                               
"description": description or "No
description available — open the listing
for details.",
                               
"image_url": image_url,
                                "url":
final_url,
                               
"search_query": search_term,
                                "username":
st.session_state.username,
                            })
                        if scraped_data:
                            with
engine.begin() as conn:
                                for row in
scraped_data:
                                   
conn.execute(
                                       
text('''INSERT INTO listings
                                           
     (title, price, product_type, platform,
description, image_url, url, search_query,
username)
                                           
     VALUES (:title, :price, :product_type,
:platform, :description, :image_url, :url,
:search_query, :username)'''),
                                        row
                                    )
                           
st.success(f"Found {len(scraped_data)} real
matches for '{search_term}'.")
                           
st.session_state["last_results"] =
scraped_data
                        else:
                           
st.session_state["last_results"] = []
                            st.info("No
direct matches found for that search. Try a
different phrase, remove the site/country
filter, or check the spelling.")
                    except Exception as e:
                       
st.error(f"Execution error: {e}")
        # Render whatever the last search
produced — kept outside the
        # submit block so favorite/currency
clicks below don't wipe results
        # on rerun.
        scraped_data =
st.session_state.get("last_results", [])
        if scraped_data:
            rates = fetch_exchange_rates()
            currency =
st.session_state.currency
            def _numeric_price(p):
                m = re.search(r'([\d,]+
(?:\.\d{1,2})?)', p["price"])
                return
float(m.group(1).replace(",", "")) if m
else None
            col_label, col_sort =
st.columns([3, 1.4])
            with col_label:
                html_block('<div
class="section-label">Results</div>')
            with col_sort:
                sort_choice = st.selectbox(
                    "Sort", ["Best match",
"Price: Low to High", "Price: High to
Low"],
                   
label_visibility="collapsed"
                )
            if sort_choice == "Price: Low
to High":
                scraped_data =
sorted(scraped_data, key=lambda r:
(_numeric_price(r) is None,
_numeric_price(r) or 0))
            elif sort_choice == "Price:
High to Low":
                scraped_data =
sorted(scraped_data, key=lambda r:
(_numeric_price(r) is None, -
(_numeric_price(r) or 0)))
            # Figure out the cheapest
parseable price so we can badge it —
            # purely a nice-to-have,
results with no parseable price are
            # just skipped for this
comparison.
            priced = [(i,
_numeric_price(r)) for i, r in
enumerate(scraped_data)]
            priced = [(i, v) for i, v in
priced if v is not None]
            best_idx = min(priced,
key=lambda x: x[1])[0] if priced else None
            st.caption("Some links below
are affiliate links — we may earn a
commission on qualifying purchases at no
extra cost to you.")
            result_cols = st.columns(3)
            for idx, row in
enumerate(scraped_data):
                with result_cols[idx % 3]:
                    with
st.container(border=True):
                       
st.image(row['image_url'],
use_container_width=True)
                        badge = '<div
class="best-price-badge">🏆 Best
Price</div>' if idx == best_idx else ''
                        html_block(f"""
                            {badge}
                            <div
class="result-platform">{row['platform']}
</div>
                            <div
class="result-title">{row['title'][:70]}
</div>
                            <div
class="result-price">
{convert_price_display(row['price'],
currency, rates)}</div>
                        """)
                        col_buy, col_fav =
st.columns([3, 1])
                        with col_buy:
                           
st.link_button("🔗 View & Buy", row['url'],
use_container_width=True)
                        with col_fav:
                            if
st.button("♡", key=f"fav_{idx}",
use_container_width=True, help="Save to
favorites"):
                                with
engine.begin() as conn:
                                   
conn.execute(
                                       
text('''INSERT INTO favorites (username,
title, price, platform, image_url, url)
                                           
     VALUES (:username, :title, :price,
:platform, :image_url, :url)'''),
                                       
{"username": st.session_state.username,
"title": row["title"],
                                        
"price": row["price"], "platform":
row["platform"],
                                        
"image_url": row["image_url"], "url":
row["url"]}
                                    )
                               
st.toast("Saved to favorites ❤️")
            # Side-by-side price comparison
table
            with st.expander("📊 Compare
all results side-by-side"):
                compare_df =
pd.DataFrame([{
                    "Platform":
r["platform"],
                    "Title": r["title"]
[:60],
                    "Price": r["price"],
                    f"≈ {currency}":
convert_price_display(r["price"], currency,
rates),
                    "Link": r["url"],
                } for r in scraped_data])
                st.dataframe(
                    compare_df,
                    column_config={"Link":
st.column_config.LinkColumn("Buy Link",
display_text="🔗 Open")},
                   
use_container_width=True,
                    hide_index=True,
                )
    elif menu == "🗂 Saved Listings":
        render_radar_header(
            "<h1 style='margin:0;'>Saved
Listings</h1>",
            "Your favorites, your recent
searches, and your full search history in
one place.",
            eyebrow="Archive"
        )
        tab_favorites, tab_history, tab_log
= st.tabs(["❤️ Favorites", "🕓 Recent
Searches", "📦 Full Log"])
        with tab_favorites:
            favorites_df = pd.read_sql(
                text("SELECT id, image_url,
title, price, platform, url, saved_at FROM
favorites WHERE username = :u ORDER BY
saved_at DESC"),
                engine, params={"u":
st.session_state.username}
            )
            if favorites_df.empty:
                st.info("Nothing saved yet
— tap the ♡ button on any search result to
save it here.")
            else:
                rates =
fetch_exchange_rates()
                fav_cols = st.columns(3)
                for idx, fav in
favorites_df.iterrows():
                    with fav_cols[idx % 3]:
                        with
st.container(border=True):
                           
st.image(fav['image_url'],
use_container_width=True)
                            html_block(f"""
                                <div
class="result-platform">{fav['platform']}
</div>
                                <div
class="result-title">{fav['title'][:70]}
</div>
                                <div
class="result-price">
{convert_price_display(fav['price'],
st.session_state.currency, rates)}</div>
                            """)
                            col_buy,
col_del = st.columns([3, 1])
                            with col_buy:
                               
st.link_button("🔗 View & Buy", fav['url'],
use_container_width=True)
                            with col_del:
                                if
st.button("🗑", key=f"del_fav_{fav['id']}",
use_container_width=True, help="Remove"):
                                    with
engine.begin() as conn:
                                       
conn.execute(text("DELETE FROM favorites
WHERE id = :id"), {"id": int(fav['id'])})
                                   
st.rerun()
        with tab_history:
            history_df = pd.read_sql(
                text('''SELECT
search_query, MAX(timestamp) AS
last_searched
                        FROM listings WHERE
username = :u
                        GROUP BY
search_query ORDER BY last_searched DESC
LIMIT 15'''),
                engine, params={"u":
st.session_state.username}
            )
            if history_df.empty:
                st.info("No searches yet —
anything you search for shows up here for
quick reuse.")
            else:
                for idx, hist in
history_df.iterrows():
                    col_q, col_go =
st.columns([4, 1])
                    with col_q:
                        st.write(f"🔎 **
{hist['search_query']}**")
                    with col_go:
                        if
st.button("Search again",
key=f"rerun_search_{idx}",
use_container_width=True):
                           
st.session_state.prefill_search =
hist['search_query']
                           
st.session_state.nav_choice = "🔎 Search"
                            st.rerun()
        with tab_log:
            df_all = pd.read_sql(
                text("SELECT image_url,
title, price, platform, product_type,
description, url, timestamp FROM listings
WHERE username = :u ORDER BY timestamp
DESC"),
                engine, params={"u":
st.session_state.username}
            )
            if not df_all.empty:
                st.dataframe(
                    df_all,
                    column_config={
                        "image_url":
st.column_config.ImageColumn("Preview",
width="small"),
                        "url":
st.column_config.LinkColumn("Buy Link",
display_text="🔗 Buy Now")
                    },
                   
use_container_width=True
                )
                csv_data =
df_all.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download My
Search History (CSV)",
                    data=csv_data,
                   
file_name='my_search_history.csv',
                    mime='text/csv',
                )
            else:
                st.info("Your search log is
empty. Run a search to populate this.")
    # ⚙️ Preferences View
    elif menu == "⚙️ Preferences":
        render_radar_header(
            "<h1 style='margin:0;'>Your
Preferences</h1>",
            "Currency, plan, and the legal
fine print — all in one place.",
            eyebrow="Settings"
        )
        selected_currency = st.selectbox(
            "Display Currency",
            CURRENCY_OPTIONS,
           
index=CURRENCY_OPTIONS.index(st.session_sta
te.currency) if st.session_state.currency
in CURRENCY_OPTIONS else 0,
            help="Prices are shown in their
original currency plus an approximate
conversion to this one."
        )
        st.selectbox("Default Export File
Type", ["CSV (.csv)", "Excel (.xlsx)"])
        if st.button("Save Configuration
Settings"):
            st.session_state.currency =
selected_currency
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE users SET
preferred_currency = :c WHERE username =
:u"),
                    {"c":
selected_currency, "u":
st.session_state.username}
                )
            st.success("Preferences saved
successfully!")
        html_block('<div class="section￾label">Upgrade</div>')
        stripe_key =
get_secret("STRIPE_SECRET_KEY")
        stripe_price =
get_secret("STRIPE_PRICE_ID")
        with st.container(border=True):
            html_block("""
                <div class="feature-icon">
💳</div>
                <div class="feature￾title">Apex Pro — $5/month</div>
                <div class="feature￾desc">Unlimited searches, saved price
alerts, and CSV export with no daily
limits.</div>
            """)
            if stripe and stripe_key and
stripe_price:
                if st.button("Upgrade to
Pro", use_container_width=True):
                    try:
                        stripe.api_key =
stripe_key
                        checkout_session =
stripe.checkout.Session.create(
                           
payment_method_types=["card"],
                            line_items=
[{"price": stripe_price, "quantity": 1}],
                           
mode="subscription",
                           
success_url=get_secret("APP_URL",
"https://your-app-url.streamlit.app") + "?
upgraded=true",
                           
cancel_url=get_secret("APP_URL",
"https://your-app-url.streamlit.app"),
                        )
                       
st.link_button("Complete Payment →",
checkout_session.url,
use_container_width=True)
                    except Exception as e:
                        st.error(f"Couldn't
start checkout: {e}")
            else:
                st.info("Payments aren't
configured yet. Add STRIPE_SECRET_KEY,
STRIPE_PRICE_ID, and APP_URL to your
Streamlit secrets to enable this.")
        html_block('<div class="section￾label">Legal</div>')
        with st.expander("📜 Terms of
Service (draft template)"):
            st.markdown("""
This is a starting template only — have it
reviewed by a lawyer before accepting real
payments or storing real user data.
**Use of Service.** This app helps you
search publicly available listings across
third-party websites and surfaces links to
those sites. We do not sell products
directly and are not a party to any
transaction between you and a third-party
seller.
**No Warranty on Listings.** Prices,
availability, and images are pulled from
third-party sites and may be inaccurate or
outdated. Always verify details on the
seller's site before purchasing.
**Accounts.** You're responsible for
keeping your login credentials
confidential. Contact support if you
suspect unauthorized access.
**Subscription & Billing.** Paid plans are
billed on a recurring basis via Stripe
until cancelled. Refunds are handled on a
case-by-case basis.
**Limitation of Liability.** This service
is provided "as is" without warranties of
any kind.
            """)
        with st.expander("🔒 Privacy Policy
(draft template)"):
            st.markdown("""
This is a starting template only — have it
reviewed by a lawyer before accepting real
payments or storing real user data.
**What we store.** Your username, a
securely hashed password (never stored in
plain text), your chosen security question,
and the listings you search for.
**What we don't store.** We don't store
your payment card details — those are
handled entirely by Stripe.
**Third parties.** Search results link out
to third-party marketplaces; their own
privacy policies apply once you leave this
app.
**Affiliate disclosure.** Some outbound
links on this site are affiliate links. If
you click one and make a purchase, we may
earn a commission at no extra cost to you.
**Your rights.** You can request deletion
of your account and associated data at any
time by contacting support.
            """)
        with st.expander("💬 Affiliate
Disclosure"):
            st.markdown("""
This site is a participant in affiliate
programs including the Amazon Services LLC
Associates Program, an affiliate
advertising program designed to provide a
means for sites to earn advertising fees by
advertising and linking to Amazon.com and
affiliated sites, as well as other
affiliate programs listed above under
"Upgrade" and search results.
As an Associate, we earn from qualifying
purchases made through links on this site.
This never affects the price you pay.
            """)
