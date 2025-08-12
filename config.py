import os
from dotenv import load_dotenv

load_dotenv()

def get_secret(name, default=None):
    val = os.getenv(name)
    if val:
        return val
    try:
        import streamlit as st
        val = st.secrets.get(name)
        if val:
            return val
    except Exception:
        pass
    return default

DEEPSEEK_API_KEY = get_secret("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = get_secret("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
GOOGLE_SHEET_ID = get_secret("GOOGLE_SHEET_ID")
