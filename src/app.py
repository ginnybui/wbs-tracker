import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="WBS Tracker Pro - Alpha Version",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Premium UI container optimization: Completely strip margins, paddings and force full screen
st.markdown(
    """
    <style>
    /* Strip default Streamlit headers, footers and decorators */
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; visibility: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; }
    
    /* Force the iframe rendering component to be a fixed full-screen cover */
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        border: none !important;
        z-index: 999999 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    
    /* Strip any margin, padding or scrolling from parent Streamlit containers */
    .main .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        width: 100% !important;
        height: 100vh !important;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        background-color: #0b0f19 !important; /* Premium dark mode match */
    }
    
    /* Remove any scrolling on parent container to keep it strictly native */
    .stApp {
        overflow: hidden !important;
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