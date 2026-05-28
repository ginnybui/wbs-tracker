import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="WBS Tracker Pro - Alpha Version",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Premium UI container optimization: Force every single wrapper to be edge-to-edge full-screen
st.markdown(
    """
    <style>
    /* Completely strip and hide all default Streamlit branding & components */
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; visibility: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; }
    
    /* Target all parent containers in Streamlit's tree and force absolute full screen */
    html, body, #root, .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stAppViewBlockContainer"], 
    .main, 
    .main .block-container, 
    .element-container, 
    [data-testid="stHtml"],
    iframe {
        width: 100% !important;
        max-width: 100% !important;
        height: 100vh !important;
        min-height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
        transform: none !important;
        filter: none !important;
        perspective: none !important;
        background-color: #0b0f19 !important; /* Matches our premium dark theme */
    }

    /* Force the inner iframe specifically to take up the full viewport */
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 999999 !important;
    }
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