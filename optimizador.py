"""Pausa conjuntos de anuncios con CPA > CPA_MAX durante N días seguidos. Por defecto DRY_RUN (no toca nada)."""
import os
from collections import defaultdict

from common import enviar_email, modo_demo, obtener_metricas, pausar_adset, redactar

CPA_MAX = float(os.getenv("CPA_MAX", "8"))
DIAS = int(os.getenv("DIAS_CONSECUTIVOS", "3"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"


def main():
    por_adset = defaultdict(list)
    for f in obtener_metricas(DIAS):
        por_adset[(f["adset_id"], f["nombre"])].append(f)

    decisiones = []
    for (adset_id, nombre), filas in por_adset.items():
        filas = sorted(filas, key=lambda f: f["fecha"])[-DIAS:]
        if len(filas) < DIAS:
            continue
        malos = all(f["gasto"] > 0 and (f["resultados"] == 0 or f["gasto"] / f["resultados"] > CPA_MAX) for f in filas)
        gasto = sum(f["gasto"] for f in filas)
        res = sum(f["resultados"] for f in filas)
        cpa = gasto / res if res else float("inf")
        if malos:
            decisiones.append(f"PAUSAR '{nombre}': CPA {cpa:.2f} > {CPA_MAX} por {DIAS} días (gasto {gasto:.2f}, resultados {res:.0f})")
            if not DRY_RUN and not modo_demo():
                pausar_adset(adset_id)
        else:
            decisiones.append(f"MANTENER '{nombre}': CPA {cpa:.2f} (gasto {gasto:.2f}, resultados {res:.0f})")

    texto = "\n".join(decisiones)
    print(("[DRY_RUN] " if DRY_RUN else "") + ("[DEMO] " if modo_demo() else "") + "Decisiones:\n" + texto)
    if any(d.startswith("PAUSAR") for d in decisiones):
        explicacion = redactar(
            "Eres un media buyer. Explica en español, en 3-5 líneas y lenguaje simple para un dueño de negocio, "
            "por qué se toman estas decisiones y qué probar después.", texto)
        enviar_email("Acciones de optimización de tus anuncios", f"<pre>{texto}</pre><p>{explicacion}</p>")


if __name__ == "__main__":
    main()
