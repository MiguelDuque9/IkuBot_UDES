"""Carga y validación de configuración sensible para IkúBot.

Prioriza `st.secrets` (deploy Streamlit). Fallback: variables de entorno (python-decouple).
No se exponen valores reales en el repositorio. Añade soporte a KNOWLEDGE_DOC_ID.
"""

from __future__ import annotations

import streamlit as st
from typing import Dict, Any


def _load_from_st_secrets() -> Dict[str, Any]:
    return {
        'DEEPSEEK_API_KEY': st.secrets['DEEPSEEK']['API_KEY'],
        'DEEPSEEK_API_URL': st.secrets['DEEPSEEK'].get('API_URL', 'https://api.deepseek.com/v1/chat/completions'),
        'GOOGLE_SHEET_ID': st.secrets['GOOGLE']['SHEET_ID'],
        'GOOGLE_CREDENTIALS': dict(st.secrets['GOOGLE_CREDENTIALS']),
        'KNOWLEDGE_DOC_ID': st.secrets.get('KNOWLEDGE', {}).get('DOC_ID', ''),
    }


def _load_from_env() -> Dict[str, Any]:
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
        },
        'KNOWLEDGE_DOC_ID': config('KNOWLEDGE_DOC_ID', default=''),
    }


def _validate(cfg: Dict[str, Any]) -> None:
    missing = []
    for key in ['DEEPSEEK_API_KEY', 'GOOGLE_SHEET_ID']:
        if not cfg.get(key):
            missing.append(key)
    if missing:
        print(f"[WARN] Faltan configuraciones requeridas: {', '.join(missing)}")
    gc = cfg.get('GOOGLE_CREDENTIALS', {})
    for k in ['private_key', 'client_email']:
        if not gc.get(k):
            print(f"[WARN] GOOGLE_CREDENTIALS incompleto: falta '{k}'")


def load_config() -> Dict[str, Any]:
    try:
        cfg = _load_from_st_secrets()
    except Exception:
        cfg = _load_from_env()
    _validate(cfg)
    return cfg


_CFG = load_config()

DEEPSEEK_API_KEY: str = _CFG['DEEPSEEK_API_KEY']
DEEPSEEK_API_URL: str = _CFG['DEEPSEEK_API_URL']
GOOGLE_SHEET_ID: str = _CFG['GOOGLE_SHEET_ID']
GOOGLE_CREDENTIALS: Dict[str, Any] = _CFG['GOOGLE_CREDENTIALS']
KNOWLEDGE_DOC_ID: str = _CFG.get('KNOWLEDGE_DOC_ID', '')

__all__ = [
    'DEEPSEEK_API_KEY',
    'DEEPSEEK_API_URL',
    'GOOGLE_SHEET_ID',
    'GOOGLE_CREDENTIALS',
    'KNOWLEDGE_DOC_ID',
    'load_config'
]