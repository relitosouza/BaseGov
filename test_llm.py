"""Testa quais modelos da NVIDIA respondem rápido com a sua chave.
Uso: python test_llm.py [modelo1 modelo2 ...]
"""
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

MODELS = sys.argv[1:] or [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "minimaxai/minimax-m3.1-flash",
    "meta/llama-3.2-90b-vision-instruct",
]
URL = "https://integrate.api.nvidia.com/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY'].strip()}"}

for model in MODELS:
    t0 = time.time()
    try:
        r = requests.post(
            URL,
            headers=HEADERS,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Diga oi em uma frase."}],
                "max_tokens": 60,
            },
            timeout=40,
        )
        dt = time.time() - t0
        if r.ok:
            txt = (r.json()["choices"][0]["message"].get("content") or "").strip()
            print(f"OK   {dt:5.1f}s  {model}  -> {txt[:60]!r}")
        else:
            print(f"ERRO {dt:5.1f}s  {model}  -> HTTP {r.status_code} {r.text[:80]!r}")
    except requests.exceptions.RequestException as e:
        print(f"FALHA {time.time() - t0:4.1f}s  {model}  -> {type(e).__name__}")
