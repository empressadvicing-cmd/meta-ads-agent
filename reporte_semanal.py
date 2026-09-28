"""Reporte semanal: métricas de 7 días -> Groq redacta -> Brevo envía."""
from collections import defaultdict

from common import enviar_email, modo_demo, obtener_metricas, redactar

PROMPT = (
    "Eres un media buyer senior. Con las métricas de la semana redacta en español un reporte breve para el dueño "
    "de un negocio: 1) resumen en 2 líneas, 2) qué funcionó, 3) qué no, 4) tres recomendaciones concretas. "
    "Sin promesas de resultados garantizados."
)


def main():
    acum = defaultdict(lambda: {"gasto": 0.0, "resultados": 0.0, "ctr": []})
    for f in obtener_metricas(7):
        a = acum[f["nombre"]]
        a["gasto"] += f["gasto"]; a["resultados"] += f["resultados"]; a["ctr"].append(f["ctr"])
    lineas = []
    for nombre, a in acum.items():
        cpa = a["gasto"] / a["resultados"] if a["resultados"] else 0
        ctr = sum(a["ctr"]) / len(a["ctr"])
        lineas.append(f"- {nombre}: gasto {a['gasto']:.2f}, resultados {a['resultados']:.0f}, CPA {cpa:.2f}, CTR {ctr:.2f}%")
    datos = "\n".join(lineas)
    cuerpo = redactar(PROMPT, datos).replace("\n", "<br>")
    aviso = "<p><i>(Datos de demostración)</i></p>" if modo_demo() else ""
    enviar_email("Tu reporte semanal de Meta Ads", f"{aviso}<h2>Reporte semanal</h2>{cuerpo}<hr><pre>{datos}</pre>")


if __name__ == "__main__":
    main()
