"""Local configuration; importing this module never calls an external service."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
if os.environ.get('GEMINI_API_KEY'):
    os.environ['GOOGLE_API_KEY'] = os.environ['GEMINI_API_KEY']
MODEL = os.environ.get('FAITHFULMED_MODEL', 'gemini-3.8-flash')


def model_client():
    from google import genai
    from google.genai import types

    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        raise ValueError('Set GEMINI_API_KEY in the ignored root .env file.')
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60000))


def require_text(response):
    candidates = response.candidates or []
    if not candidates or str(candidates[0].finish_reason).split('.')[-1] != 'STOP':
        raise ValueError('The model did not finish a complete response.')
    if not response.text or not response.text.strip():
        raise ValueError('The model returned no text.')
    return response.text.strip()
