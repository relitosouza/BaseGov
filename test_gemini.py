"""Lista os modelos Gemini da sua chave e testa quais respondem agora.
Uso: python test_gemini.py [modelo1 modelo2 ...]
"""
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

BASE = "https://generativelanguage.googleapis.com/v1beta"
HEADERS = {"x-goog-api-key": os.environ["GOOGLE_API_KEY"].strip()}

r = requests.get(f"{BASE}/models?pageSize=200", headers=HEADERS, timeout=30)
if not r.ok:
    raise SystemExit(f"Falha ao listar modelos: HTTP {r.status_code} {r.text[:200]}")
available = [
    m["name"].removeprefix("models/")
    for m in r.json().get("models", [])
    if "generateContent" in m.get("supportedGenerationMethods", [])
    and m["name"].split("/")[-1].startswith("gemini")
]
print("Modelos disponíveis para sua chave:")
print("  " + "\n  ".join(available), "\n")

candidates = sys.argv[1:] or [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]
for model in candidates:
    if model not in available:
        print(f"NÃO EXISTE  {model}")
        continue
    t0 = time.time()
    try:
        r = requests.post(
            f"{BASE}/models/{model}:generateContent",
            headers=HEADERS,
            json={"contents": [{"parts": [{"text": "Diga oi em uma frase."}]}]},
            timeout=45,
        )
        dt = time.time() - t0
        if r.ok:
            parts = r.json()["candidates"][0]["content"]["parts"]
            print(f"OK    {dt:5.1f}s  {model} -> {parts[0].get('text', '')[:50]!r}")
        else:
            err = r.json().get("error", {})
            print(f"ERRO  {dt:5.1f}s  {model} -> {r.status_code} {err.get('status')}")
    except requests.exceptions.RequestException as e:
        print(f"FALHA {time.time() - t0:5.1f}s  {model} -> {type(e).__name__}")
