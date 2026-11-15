"""Root Streamlit entry point for the SWA dashboard."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from common.styles import inject_global_styles
from config import APP_TITLE
from navigation import current_section, render_landing, render_section_header, render_sidebar
from sections import render_selected_section

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")
inject_global_styles()

selected_section = current_section()
if selected_section is None:
    render_landing()
    st.stop()

render_section_header(selected_section)
render_sidebar()
render_selected_section(selected_section)
