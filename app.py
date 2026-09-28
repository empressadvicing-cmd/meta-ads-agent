import json
import os

import streamlit as st
from groq import Groq

# ---- Configuración ----
MODELO = "llama-3.3-70b-versatile"  # si Groq lo retira, revisa https://console.groq.com/docs/models

SYSTEM_PROMPT = """Eres un experto en Meta Ads. Cuando el usuario describa su negocio,
producto y objetivo, devuelve ÚNICAMENTE un JSON válido con esta estructura:
{
  "nombre_campana": "",
  "objetivo": "OUTCOME_SALES | OUTCOME_LEADS | OUTCOME_TRAFFIC",
  "presupuesto_diario_usd": 0,
  "publicos": [{"nombre": "", "intereses": [], "edad": [18, 65], "paises": []}],
  "anuncios": [{"titulo": "", "copy_principal": "", "copy_secundario": "", "cta": ""}]
}
Genera 2 públicos y 3 anuncios. Escribe los textos en español, orientados a conversión."""

st.set_page_config(page_title="Agente Meta Ads", page_icon="📈", layout="wide")
st.title("📈 Agente de IA para Meta Ads")
st.caption("Describe tu negocio y genera la estructura completa de tu campaña.")

def _secret(nombre):
    try:
        return st.secrets.get(nombre)
    except Exception:
        return None


api_key = os.getenv("GROQ_API_KEY") or _secret("GROQ_API_KEY")
FORM_URL = os.getenv("FORM_URL") or _secret("FORM_URL")  # link de tu Google Form de clientes
if not api_key:
    api_key = st.sidebar.text_input("Groq API Key", type="password")

descripcion = st.text_area(
    "¿Qué vendes y cuál es tu objetivo?",
    placeholder="Ej: Tengo una tienda de café de especialidad en CDMX, quiero vender suscripciones mensuales, presupuesto ~$10 USD al día.",
    height=140,
)

if st.button("Generar campaña", type="primary"):
    if not api_key:
        st.error("Falta la API key de Groq.")
    elif not descripcion.strip():
        st.warning("Describe tu negocio primero.")
    else:
        with st.spinner("Diseñando tu campaña..."):
            try:
                client = Groq(api_key=api_key)
                resp = client.chat.completions.create(
                    model=MODELO,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": descripcion},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                campana = json.loads(resp.choices[0].message.content)
                st.session_state["campana"] = campana
            except Exception as e:
                st.error(f"Error: {e}")

campana = st.session_state.get("campana")
if campana:
    st.subheader(campana.get("nombre_campana", "Campaña"))
    c1, c2 = st.columns(2)
    c1.metric("Objetivo", campana.get("objetivo", "-"))
    c2.metric("Presupuesto diario (USD)", campana.get("presupuesto_diario_usd", "-"))

    st.markdown("### 🎯 Públicos")
    for p in campana.get("publicos", []):
        with st.expander(p.get("nombre", "Público")):
            st.write("**Intereses:**", ", ".join(p.get("intereses", [])))
            st.write("**Edad:**", p.get("edad"))
            st.write("**Países:**", ", ".join(p.get("paises", [])))

    st.markdown("### 📝 Anuncios")
    for i, a in enumerate(campana.get("anuncios", []), 1):
        with st.container(border=True):
            st.markdown(f"**Anuncio {i}: {a.get('titulo', '')}**")
            st.write(a.get("copy_principal", ""))
            st.caption(a.get("copy_secundario", ""))
            st.button(a.get("cta", "Más info"), key=f"cta{i}", disabled=True)

    st.download_button(
        "Descargar JSON",
        json.dumps(campana, ensure_ascii=False, indent=2),
        file_name="campana.json",
        mime="application/json",
    )


st.divider()
st.markdown("### ¿Quieres que manejemos tus anuncios por ti?")
if FORM_URL:
    st.link_button("Quiero mi primer mes gratis", FORM_URL, type="primary")
else:
    st.caption("Configura FORM_URL en los secrets para mostrar aquí tu formulario de clientes.")
