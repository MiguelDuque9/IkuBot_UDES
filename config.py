import streamlit as st

def get_secrets():
    try:
        # Para Streamlit Cloud
        return {
            'DEEPSEEK_API_KEY': st.secrets["DEEPSEEK"]["API_KEY"],
            'DEEPSEEK_API_URL': st.secrets["DEEPSEEK"]["API_URL"],
            'GOOGLE_SHEET_ID': st.secrets["GOOGLE"]["SHEET_ID"],
            'GOOGLE_CREDENTIALS': dict(st.secrets["GOOGLE_CREDENTIALS"])
        }
    except:
        from decouple import config
        return {
            'DEEPSEEK_API_KEY': config('DEEPSEEK_API_KEY', default=''),
            'DEEPSEEK_API_URL': config('DEEPSEEK_API_URL', default='https://api.deepseek.com/v1/chat/completions'),
            'GOOGLE_SHEET_ID': config('GOOGLE_SHEET_ID', default=''),
            'GOOGLE_CREDENTIALS': {
                'type': config('TYPE', default='service_account'),
                'project_id': config('PROJECT_ID', default=''),
                'private_key_id': config('PRIVATE_KEY_ID', default=''),
                'private_key': config('PRIVATE_KEY', default='').replace('\\n', '\n'),
                'client_email': config('CLIENT_EMAIL', default=''),
                'client_id': config('CLIENT_ID', default=''),
                'auth_uri': config('AUTH_URI', default='https://accounts.google.com/o/oauth2/auth'),
                'token_uri': config('TOKEN_URI', default='https://oauth2.googleapis.com/token'),
                'auth_provider_x509_cert_url': config('AUTH_PROVIDER_X509_CERT_URL', default='https://www.googleapis.com/oauth2/v1/certs'),
                'client_x509_cert_url': config('CLIENT_X509_CERT_URL', default=''),
                'universe_domain': config('UNIVERSE_DOMAIN', default='googleapis.com')
            }
        }

secrets = get_secrets()

DEEPSEEK_API_KEY = secrets['DEEPSEEK_API_KEY']
DEEPSEEK_API_URL = secrets['DEEPSEEK_API_URL']
GOOGLE_SHEET_ID = secrets['GOOGLE_SHEET_ID']
GOOGLE_CREDENTIALS = secrets['GOOGLE_CREDENTIALS']