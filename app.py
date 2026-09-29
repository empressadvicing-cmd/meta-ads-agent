import json
import os

import streamlit as st
from groq import Groq

MODELO = "llama-3.1-8b-instant"

st.set_page_config(page_title="Agente Meta Ads", page_icon="📈", layout="wide")
st.title("📈 Agente de IA para Meta Ads")

# ---- API key ----
def _secret(nombre):
    try:
        return st.secrets.get(nombre)
    except Exception:
        return None


api_key = os.getenv("GROQ_API_KEY") or _secret("GROQ_API_KEY")
FORM_URL = os.getenv("FORM_URL") or _secret("FORM_URL")
if not api_key:
    api_key = st.sidebar.text_input("Groq API Key", type="password")
    st.sidebar.markdown("Consíguela gratis en [console.groq.com](https://console.groq.com)")

client = Groq(api_key=api_key) if api_key else None


def preguntar(system, user, json_mode=False):
    kwargs = {"model": MODELO, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.5}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


tab1, tab2, tab3 = st.tabs(["🎯 Generar campaña", "📊 Analizar métricas", "📝 Reporte semanal"])

# ---------------- TAB 1: Generar campaña ----------------
with tab1:
    st.caption("Describe el negocio del cliente y genera la estructura completa de campaña.")
    descripcion = st.text_area(
        "¿Qué vende y cuál es su objetivo?",
        placeholder="Ej: Tienda de café de especialidad en CDMX, vender suscripciones mensuales, presupuesto ~$10 USD/día.",
        height=120,
    )
    if st.button("Generar campaña", type="primary"):
        if not api_key:
            st.error("Falta la API key de Groq (barra lateral).")
        elif not descripcion.strip():
            st.warning("Describe el negocio primero.")
        else:
            with st.spinner("Diseñando campaña..."):
                try:
                    campana = json.loads(preguntar(
                        """Eres experto en Meta Ads. Devuelve SOLO un JSON:
{"nombre_campana":"","objetivo":"OUTCOME_SALES | OUTCOME_LEADS | OUTCOME_TRAFFIC",
"presupuesto_diario_usd":0,"publicos":[{"nombre":"","intereses":[],"edad":[18,65],"paises":[]}],
"anuncios":[{"titulo":"","copy_principal":"","copy_secundario":"","cta":""}]}
Genera 2 públicos y 3 anuncios en español.""",
                        descripcion, json_mode=True))
                    st.session_state["campana"] = campana
                except Exception as e:
                    st.error(f"Error: {e}")

    campana = st.session_state.get("campana")
    if campana:
        st.subheader(campana.get("nombre_campana", "Campaña"))
        c1, c2 = st.columns(2)
        c1.metric("Objetivo", campana.get("objetivo", "-"))
        c2.metric("Presupuesto diario (USD)", campana.get("presupuesto_diario_usd", "-"))
        for p in campana.get("publicos", []):
            with st.expander(p.get("nombre", "Público")):
                st.write("**Intereses:**", ", ".join(p.get("intereses", [])))
                st.write("**Edad:**", p.get("edad"))
                st.write("**Países:**", ", ".join(p.get("paises", [])))
        for i, a in enumerate(campana.get("anuncios", []), 1):
            with st.container(border=True):
                st.markdown(f"**Anuncio {i}: {a.get('titulo', '')}**")
                st.write(a.get("copy_principal", ""))
                st.caption(a.get("copy_secundario", ""))
        st.download_button("Descargar JSON", json.dumps(campana, ensure_ascii=False, indent=2),
                            file_name="campana.json", mime="application/json")

# ---------------- TAB 2: Analizar métricas ----------------
with tab2:
    st.caption(
        "Copia y pega aquí las métricas de tus conjuntos de anuncios (desde el Administrador de Anuncios de Meta: "
        "nombre, gasto, resultados, CPA, CTR de los últimos días). El agente te dice qué pausar o escalar."
    )
    cpa_max = st.number_input("¿Cuál es tu CPA máximo aceptable (USD)?", min_value=0.0, value=8.0, step=0.5)
    datos = st.text_area(
        "Pega tus métricas aquí (una línea por conjunto de anuncios)",
        placeholder="Público café CDMX: gasto $30, 3 resultados, CTR 1.0%\nLookalike compradores: gasto $30, 16 resultados, CTR 2.5%",
        height=150,
    )
    if st.button("Analizar y recomendar", type="primary"):
        if not api_key:
            st.error("Falta la API key de Groq.")
        elif not datos.strip():
            st.warning("Pega tus métricas primero.")
        else:
            with st.spinner("Analizando..."):
                try:
                    analisis = preguntar(
                        f"""Eres un media buyer experto. El CPA máximo aceptable es ${cpa_max}.
Para cada conjunto de anuncios que te den, calcula el CPA (gasto/resultados) y di PAUSAR o MANTENER,
con una explicación breve en español y una recomendación concreta. No prometas resultados garantizados.""",
                        datos)
                    st.markdown(analisis)
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------- TAB 3: Reporte semanal ----------------
with tab3:
    st.caption("Pega las métricas de la semana y genera un reporte listo para copiar y enviar a tu cliente por WhatsApp o email.")
    nombre_cliente = st.text_input("Nombre del cliente/negocio", placeholder="Ej: Café Aroma")
    datos_semana = st.text_area(
        "Métricas de la semana",
        placeholder="Gasto total: $210\nResultados: 42\nCTR promedio: 1.8%\nMejor conjunto: Lookalike compradores\nPeor conjunto: Público café CDMX",
        height=150,
        key="datos_semana",
    )
    if st.button("Generar reporte", type="primary"):
        if not api_key:
            st.error("Falta la API key de Groq.")
        elif not datos_semana.strip():
            st.warning("Pega las métricas primero.")
        else:
            with st.spinner("Redactando reporte..."):
                try:
                    reporte = preguntar(
                        "Eres media buyer senior. Redacta en español un reporte semanal breve para el dueño de un "
                        "negocio: 1) resumen en 2 líneas, 2) qué funcionó, 3) qué no, 4) 3 recomendaciones concretas. "
                        "Sin promesas de resultados garantizados. Usa un tono cercano y profesional.",
                        f"Cliente: {nombre_cliente}\n{datos_semana}")
                    st.markdown(reporte)
                    st.download_button("Descargar reporte (.txt)", reporte, file_name=f"reporte_{nombre_cliente or 'cliente'}.txt")
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()
st.markdown("### ¿Quieres que manejemos tus anuncios por ti?")
if FORM_URL:
    st.link_button("Quiero mi primer mes gratis", FORM_URL, type="primary")
else:
    st.caption("Configura FORM_URL en los secrets de Streamlit para mostrar aquí tu formulario de clientes.")
