# Agente de IA para Meta Ads

- `app.py` – demo pública (Streamlit) que genera campañas con Groq y captura clientes.
- `optimizador.py` – pausa adsets con CPA alto (DRY_RUN por defecto).
- `reporte_semanal.py` – reporte semanal redactado por IA y enviado por Brevo.
- `.github/workflows/automatizacion.yml` – lo corre todo solo, gratis.

Sin token de Meta todo corre en MODO DEMO con datos de ejemplo.

## Secrets (GitHub → Settings → Secrets and variables → Actions)
GROQ_API_KEY, BREVO_API_KEY, SENDER_EMAIL, CLIENT_EMAIL, META_ACCESS_TOKEN, META_AD_ACCOUNT_ID
Variables: CPA_MAX (ej. 8), DRY_RUN (`true` hasta que confíes; `false` para pausar de verdad)

## Correr local
    pip install -r requirements.txt
    streamlit run app.py
    python reporte_semanal.py
    python optimizador.py
