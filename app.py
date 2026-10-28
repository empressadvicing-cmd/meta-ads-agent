import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st
from groq import Groq

MODELO = "openai/gpt-oss-20b"

st.set_page_config(page_title="Agente de IA para tu Negocio", page_icon="🤖", layout="wide")
st.title("🤖 Agente de IA para tu Negocio")
st.caption("Meta Ads con IA + servicios de freelance IA (contenido, redes, automatización), todo en un solo lugar.")


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

# ---------------- Acceso por suscripción mensual (Mercado Pago) ----------------
MP_TOKEN = os.getenv("MP_ACCESS_TOKEN") or _secret("MP_ACCESS_TOKEN")
APP_URL = os.getenv("APP_URL") or _secret("APP_URL")
SALT = os.getenv("ACCESS_SALT") or _secret("ACCESS_SALT") or (MP_TOKEN or "sin-token")
PRECIO = float(os.getenv("PRECIO_MXN") or _secret("PRECIO_MXN") or 387)
DIAS_ACCESO = int(os.getenv("DIAS_ACCESO") or _secret("DIAS_ACCESO") or 30)
CANDADO_ACTIVO = bool(MP_TOKEN)  # sin MP_ACCESS_TOKEN la app queda abierta
MP_API = "https://api.mercadopago.com"


def referencia_cliente(correo, pin):
    """Identificador privado del cliente: ligado a su correo + PIN (y a una sal secreta del servidor)."""
    base = f"{correo.strip().lower()}|{pin.strip()}|{SALT}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


def crear_link_de_pago(ref):
    """Crea el link de pago en Mercado Pago. Devuelve (url, error)."""
    cuerpo = {
        "items": [{"title": "Acceso mensual - Agente de IA", "quantity": 1,
                   "unit_price": PRECIO, "currency_id": "MXN"}],
        "external_reference": ref,
    }
    if APP_URL:
        cuerpo["back_urls"] = {"success": APP_URL, "pending": APP_URL, "failure": APP_URL}
        cuerpo["auto_return"] = "approved"
    try:
        r = requests.post(f"{MP_API}/checkout/preferences", json=cuerpo, timeout=20,
                          headers={"Authorization": f"Bearer {MP_TOKEN}"})
        d = r.json()
    except Exception as e:
        return None, f"No se pudo conectar con Mercado Pago ({e})"
    if r.status_code >= 300 or not d.get("init_point"):
        return None, f"Mercado Pago respondió {r.status_code}: {str(d)[:200]}"
    return d["init_point"], None


def consultar_pagos(ref):
    """Pagos aprobados de este cliente. Devuelve (lista, error)."""
    try:
        r = requests.get(f"{MP_API}/v1/payments/search", timeout=20,
                         headers={"Authorization": f"Bearer {MP_TOKEN}"},
                         params={"external_reference": ref, "status": "approved", "limit": 50})
        d = r.json()
    except Exception as e:
        return [], f"No se pudo conectar con Mercado Pago ({e})"
    if r.status_code >= 300:
        return [], f"Mercado Pago respondió {r.status_code}: {str(d)[:200]}"
    return d.get("results", []), None


def calcular_vencimiento(pagos, dias=30):
    """Cada pago aprobado suma `dias` de acceso; si renueva antes de vencer, los días se acumulan."""
    fechas = []
    for p in pagos:
        f = p.get("date_approved") or p.get("date_created")
        if f:
            fechas.append(datetime.fromisoformat(f.replace("Z", "+00:00")))
    vence = None
    for f in sorted(fechas):
        inicio = f if (vence is None or f > vence) else vence
        vence = inicio + timedelta(days=dias)
    return vence


def ahora():
    return datetime.now(timezone.utc)


if CANDADO_ACTIVO:
    st.sidebar.markdown("### 🔑 Acceso completo")
    st.sidebar.caption(f"${PRECIO:,.0f} MXN por {DIAS_ACCESO} días. Usa siempre el mismo correo y PIN: con ellos se identifica tu pago.")
    correo = st.sidebar.text_input("Tu correo")
    pin = st.sidebar.text_input("Crea un PIN (mín. 4 caracteres)", type="password")
    datos_ok = bool(correo.strip()) and len(pin.strip()) >= 4
    ref = referencia_cliente(correo, pin) if datos_ok else None

    c1, c2 = st.sidebar.columns(2)
    if c1.button("Verificar acceso", disabled=not datos_ok):
        pagos, err = consultar_pagos(ref)
        if err:
            st.sidebar.error(err)
        else:
            vence = calcular_vencimiento(pagos, DIAS_ACCESO)
            st.session_state["vence"] = vence
            st.session_state["cliente"] = correo.strip().lower()
            if vence is None:
                st.sidebar.warning("Aún no encuentro un pago con ese correo y PIN.")
    if c2.button("Pagar", disabled=not datos_ok):
        url, err = crear_link_de_pago(ref)
        if err:
            st.sidebar.error(err)
        else:
            st.session_state["link_pago"] = url

    if st.session_state.get("link_pago") and datos_ok:
        st.sidebar.link_button(f"Ir a pagar ${PRECIO:,.0f} MXN", st.session_state["link_pago"], type="primary")
        st.sidebar.caption("Al terminar, vuelve aquí y toca 'Verificar acceso'.")

    vence = st.session_state.get("vence")
    if vence and vence > ahora():
        dias_restantes = (vence - ahora()).days
        st.sidebar.success(f"Acceso activo ✅ ({dias_restantes} días restantes)")
        st.sidebar.caption(f"Cuenta: {st.session_state.get('cliente')}")
    elif vence:
        st.sidebar.error(f"Tu acceso venció el {vence.strftime('%d/%m/%Y')}. Renueva con 'Pagar'.")

_vence = st.session_state.get("vence")
PRO = (not CANDADO_ACTIVO) or bool(_vence and _vence > ahora())


def acceso_denegado(gratis=False):
    """True si hay que bloquear. Con gratis=True se permite 1 uso de prueba por sesión."""
    if PRO:
        return False
    if gratis and st.session_state.get("gratis_usos", 0) < 1:
        return False
    st.warning("🔒 Esta herramienta es parte del acceso completo. Ingresa tu correo y PIN en la barra lateral, paga y toca 'Verificar acceso'.")
    return True


def preguntar(system, user, json_mode=False):
    kwargs = {"model": MODELO, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.6}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Generar campaña", "📊 Analizar métricas", "📝 Reporte semanal",
    "📱 Contenido para redes", "⚙️ Idea de automatización",
])

# ---------------- TAB 1: Generar campaña ----------------
with tab1:
    st.caption("Describe el negocio del cliente y genera la estructura completa de campaña.")
    descripcion = st.text_area(
        "¿Qué vende y cuál es su objetivo?",
        placeholder="Ej: Tienda de café de especialidad en CDMX, vender suscripciones mensuales, presupuesto ~$10 USD/día.",
        height=120, key="desc_campana",
    )
    if st.button("Generar campaña", type="primary", key="btn_campana"):
        if not api_key:
            st.error("Falta la API key de Groq (barra lateral).")
        elif not descripcion.strip():
            st.warning("Describe el negocio primero.")
        elif acceso_denegado(True):
            pass
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
                    st.session_state["gratis_usos"] = st.session_state.get("gratis_usos", 0) + 1
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
                            file_name="campana.json", mime="application/json", key="dl_campana")

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
        elif acceso_denegado(False):
            pass
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
        height=150, key="datos_semana",
    )
    if st.button("Generar reporte", type="primary"):
        if not api_key:
            st.error("Falta la API key de Groq.")
        elif not datos_semana.strip():
            st.warning("Pega las métricas primero.")
        elif acceso_denegado(False):
            pass
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

# ---------------- TAB 4: Contenido para redes ----------------
with tab4:
    st.caption("Describe el negocio y obtén ideas de publicaciones listas para usar en redes sociales.")
    desc_negocio = st.text_area(
        "¿Qué hace el negocio y qué quiere comunicar?",
        placeholder="Ej: Estudio de yoga en Guadalajara, quiere promocionar sus clases de fin de semana y atraer nuevos alumnos.",
        height=120, key="desc_redes",
    )
    plataforma = st.selectbox("Plataforma principal", ["Instagram", "Facebook", "TikTok", "LinkedIn"])
    cantidad = st.slider("¿Cuántas publicaciones quieres?", 1, 5, 3)
    if st.button("Generar contenido", type="primary", key="btn_redes"):
        if not api_key:
            st.error("Falta la API key de Groq.")
        elif not desc_negocio.strip():
            st.warning("Describe el negocio primero.")
        elif acceso_denegado(False):
            pass
        else:
            with st.spinner("Creando publicaciones..."):
                try:
                    contenido = preguntar(
                        f"""Eres un creador de contenido para redes sociales experto en {plataforma}.
Genera {cantidad} publicaciones distintas en español para el negocio descrito, cada una con:
- Gancho inicial (primera línea)
- Cuerpo del texto (breve, natural, no genérico)
- Llamado a la acción
- 5 hashtags relevantes
Separa cada publicación claramente con un número.""",
                        desc_negocio)
                    st.markdown(contenido)
                    st.download_button("Descargar contenido (.txt)", contenido, file_name="contenido_redes.txt", key="dl_redes")
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------- TAB 5: Idea de automatización ----------------
with tab5:
    st.caption("Describe una tarea repetitiva del negocio y recibe una propuesta simple de cómo automatizarla con IA.")
    tarea = st.text_area(
        "¿Qué tarea repetitiva quieres automatizar?",
        placeholder="Ej: Respondo las mismas preguntas de precios y horarios por WhatsApp todos los días.",
        height=120, key="desc_automatizacion",
    )
    if st.button("Proponer automatización", type="primary", key="btn_auto"):
        if not api_key:
            st.error("Falta la API key de Groq.")
        elif not tarea.strip():
            st.warning("Describe la tarea primero.")
        elif acceso_denegado(False):
            pass
        else:
            with st.spinner("Diseñando propuesta..."):
                try:
                    propuesta = preguntar(
                        """Eres un consultor de automatización con IA para pequeños negocios. Con la tarea que te 
                        describan, responde en español con: 1) qué tipo de solución encaja (chatbot, flujo automático, 
                        agente de IA), 2) cómo funcionaría en pasos simples, 3) qué necesitaría el negocio para 
                        implementarlo, 4) una estimación realista de cuánto tiempo ahorraría por semana. 
                        Sé concreto y evita jerga técnica innecesaria.""",
                        tarea)
                    st.markdown(propuesta)
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()
st.markdown("### ¿Quieres que lo hagamos por ti?")
if FORM_URL:
    st.link_button("Contáctame / primer mes gratis", FORM_URL, type="primary")
else:
    st.caption("Configura FORM_URL en los secrets para mostrar aquí tu formulario de contacto.")
