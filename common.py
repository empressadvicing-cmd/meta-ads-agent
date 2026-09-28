"""Utilidades compartidas: Meta Graph API, Groq y Brevo. Sin token de Meta funciona en MODO DEMO."""
import os

import requests

API_VERSION = os.getenv("META_API_VERSION", "v23.0")  # revisa la versión vigente en developers.facebook.com
BASE = f"https://graph.facebook.com/{API_VERSION}"
MODELO = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
RESULT_ACTIONS = [a.strip() for a in os.getenv("RESULT_ACTIONS", "purchase,lead").split(",")]

DEMO_DATA = [
    {"adset_id": "1", "nombre": "Público café CDMX", "fecha": f"d{d}", "gasto": g, "resultados": r, "ctr": c}
    for d, (g, r, c) in enumerate([(10, 1, 1.1), (10, 1, 1.0), (10, 1, 0.9)])
] + [
    {"adset_id": "2", "nombre": "Lookalike compradores", "fecha": f"d{d}", "gasto": g, "resultados": r, "ctr": c}
    for d, (g, r, c) in enumerate([(10, 5, 2.4), (10, 6, 2.6), (10, 5, 2.5)])
]


def modo_demo():
    return not (os.getenv("META_ACCESS_TOKEN") and os.getenv("META_AD_ACCOUNT_ID"))


def obtener_metricas(dias=3):
    """Devuelve filas diarias por conjunto de anuncios: adset_id, nombre, fecha, gasto, resultados, ctr."""
    if modo_demo():
        return DEMO_DATA
    cuenta = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")
    params = {
        "level": "adset",
        "fields": "adset_id,adset_name,spend,ctr,actions",
        "time_increment": 1,
        "date_preset": "last_3d" if dias <= 3 else "last_7d",
        "limit": 500,
        "access_token": os.environ["META_ACCESS_TOKEN"],
    }
    r = requests.get(f"{BASE}/act_{cuenta}/insights", params=params, timeout=60)
    r.raise_for_status()
    filas = []
    for x in r.json().get("data", []):
        resultados = sum(
            float(a["value"]) for a in x.get("actions", []) if a["action_type"] in RESULT_ACTIONS
        )
        filas.append({
            "adset_id": x["adset_id"], "nombre": x["adset_name"], "fecha": x["date_start"],
            "gasto": float(x.get("spend", 0)), "resultados": resultados, "ctr": float(x.get("ctr", 0)),
        })
    return filas


def pausar_adset(adset_id):
    r = requests.post(
        f"{BASE}/{adset_id}",
        data={"status": "PAUSED", "access_token": os.environ["META_ACCESS_TOKEN"]},
        timeout=60,
    )
    r.raise_for_status()


def redactar(prompt_sistema, datos_texto):
    """Pide a Groq que redacte. Si no hay key, devuelve el texto plano."""
    if not os.getenv("GROQ_API_KEY"):
        return datos_texto
    from groq import Groq
    resp = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
        model=MODELO,
        messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": datos_texto}],
        temperature=0.4,
    )
    return resp.choices[0].message.content


def enviar_email(asunto, html):
    """Envía con Brevo. Si faltan credenciales, solo imprime."""
    key, dest, remitente = os.getenv("BREVO_API_KEY"), os.getenv("CLIENT_EMAIL"), os.getenv("SENDER_EMAIL")
    if not (key and dest and remitente):
        print("[sin Brevo configurado] Asunto:", asunto, "\n", html)
        return
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": key, "content-type": "application/json"},
        json={
            "sender": {"name": os.getenv("SENDER_NAME", "Tu Agente de Ads"), "email": remitente},
            "to": [{"email": e.strip()} for e in dest.split(",")],
            "subject": asunto,
            "htmlContent": html,
        },
        timeout=60,
    )
    r.raise_for_status()
    print("Email enviado a", dest)
