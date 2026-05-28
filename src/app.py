import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="WBS Tracker Pro - Alpha Version",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Premium UI container optimization: Force every single wrapper in the hierarchy to be edge-to-edge
# Using st.markdown with unsafe_allow_html=True to bypass sanitization and guarantee CSS injection
st.markdown(
    """
    <style>
    /* Reset everything globally to prevent default margins/paddings */
    * {
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }
    
    /* Force HTML, body, and React root to take up full viewport and match premium dark background */
    html, body, #root {
        width: 100vw !important;
        height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        background-color: #0b0f19 !important;
    }
    
    /* Style every descendant div, section, and main inside .stApp to be full width/height with no padding/margins */
    .stApp,
    .stApp div, 
    .stApp section,
    .stApp main {
        width: 100% !important;
        max-width: 100% !important;
        height: 100% !important;
        min-height: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        background-color: transparent !important;
        transform: none !important;
        filter: none !important;
        perspective: none !important;
    }

    /* Force the iframe to be fixed full-screen, filling the exact viewport */
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        max-width: 100vw !important;
        max-height: 100vh !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 999999 !important;
    }
    
    /* Hide streamlit specific UI elements completely */
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; visibility: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# Resolve file path dynamically
base_path = os.path.dirname(os.path.abspath(__file__))
html_file_path = os.path.join(os.path.dirname(base_path), "dashboard_preview.html")

try:
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Render the interactive mockup iframe full screen
    components.html(html_content, height=1400, scrolling=True)
except Exception as e:
    st.error(f"Failed to load Alpha Mockup layout: {e}")