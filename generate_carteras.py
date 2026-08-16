"""
Genera la colección `carteras` (SINTÉTICA) del proyecto final M6-NOSQL.

Esta colección NO proviene de EONET/Kaggle. Se construyó a partir de las
zonas de mayor concentración real de eventos Wildfire en eventos_desastres
(celdas de rejilla 15x15 grados con más eventos), y se le asignaron datos
de exposición de seguros (pólizas activas, suma asegurada) GENERADOS de
forma sintética y determinista solo para efectos del proyecto académico.
No representan una aseguradora real ni datos de clientes reales.

Uso:
    python3 generate_carteras.py eventos_desastres.json carteras.json
"""

import hashlib
import json
import sys

CELL = 15  # grados, debe coincidir con el análisis de densidad


def celda_de(lon, lat):
    return (int(lon // CELL) * CELL, int(lat // CELL) * CELL)


def nombre_legible(lon0, lat0):
    # Nombres asignados manualmente a partir de la ubicación real de las
    # top-15 celdas por densidad de wildfires (ver exploración previa).
    nombres = {
        (15, -15): "África central (Angola/RDC/Zambia)",
        (-105, 30): "EUA centro-sur (Texas/Oklahoma)",
        (-120, 30): "EUA suroeste (California/Nevada/Arizona)",
        (-60, -15): "Amazonía norte (Brasil)",
        (-60, -30): "Amazonía sur (Brasil/Paraguay)",
        (135, -30): "Australia este",
        (15, 0): "Sahel (Chad/RCA)",
        (120, -30): "Australia oeste",
        (15, -30): "África austral (Zimbabue/Botsuana)",
        (-90, 30): "EUA sureste",
        (30, -15): "África oriental (Tanzania/Kenia)",
        (-120, 45): "EUA/Canadá noroeste Pacífico",
        (-75, -15): "Perú/Brasil (Amazonía oeste)",
        (105, 45): "Siberia/Mongolia",
        (-135, 30): "EUA costa oeste (Pacífico)",
    }
    return nombres.get((lon0, lat0), f"Zona sin nombre ({lon0},{lat0})")


def poligono_rectangular(lon0, lat0):
    """Rectángulo GeoJSON simple para la celda. Simplificación: no sigue
    fronteras reales ni corrige distorsión por proyección; documentado
    como limitación del modelo (igual que semana 3, sección 3.4)."""
    lon1, lat1 = lon0 + CELL, lat0 + CELL
    anillo = [
        [lon0, lat0],
        [lon1, lat0],
        [lon1, lat1],
        [lon0, lat1],
        [lon0, lat0],  # cierre del anillo
    ]
    return {"type": "Polygon", "coordinates": [anillo]}


def valores_sinteticos(zona_id, count_eventos):
    """Genera polizas_activas y suma_asegurada de forma determinista
    (hash del id de zona) para que sea reproducible entre corridas,
    con una variación proporcional inversa al conteo de eventos: zonas
    de mayor actividad histórica tienden a tener suscripción más
    restringida (menos pólizas) -- supuesto de negocio documentado,
    no un dato observado."""
    h = int(hashlib.sha256(zona_id.encode()).hexdigest(), 16)
    variacion = 0.7 + (h % 600) / 1000  # 0.70 - 1.30

    base_polizas = 2500
    factor_riesgo = 1 / (1 + count_eventos / 300)
    polizas = int(base_polizas * factor_riesgo * variacion)

    valor_promedio_por_poliza = 180_000  # USD, supuesto fijo simplificado
    suma_asegurada = polizas * valor_promedio_por_poliza

    return polizas, suma_asegurada


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 generate_carteras.py <eventos.json> <carteras.json>")
        sys.exit(1)

    ruta_eventos, ruta_salida = sys.argv[1], sys.argv[2]

    with open(ruta_eventos, encoding="utf-8") as f:
        eventos = json.load(f)

    wildfires = [e for e in eventos if e["categoria"] == "Wildfires"]

    conteo = {}
    for e in wildfires:
        lon, lat = e["ubicacion"]["coordinates"]
        celda = celda_de(lon, lat)
        conteo[celda] = conteo.get(celda, 0) + 1

    top15 = sorted(conteo.items(), key=lambda x: -x[1])[:15]

    carteras = []
    for i, ((lon0, lat0), count) in enumerate(top15, start=1):
        zona_id = f"zona_{i:02d}"
        polizas, suma_asegurada = valores_sinteticos(zona_id, count)
        carteras.append({
            "_id": zona_id,
            "nombre": nombre_legible(lon0, lat0),
            "poligono": poligono_rectangular(lon0, lat0),
            "polizas_activas": polizas,
            "suma_asegurada_usd": suma_asegurada,
            "eventos_wildfire_historicos": count,
            "sintetico": True,
            "nota": "Exposición generada para fines académicos; no representa datos reales de una aseguradora.",
        })

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(carteras, f, ensure_ascii=False, indent=2)

    print(f"Zonas generadas: {len(carteras)}")
    for c in carteras:
        print(f"  {c['_id']}: {c['nombre']} — {c['polizas_activas']} pólizas, "
              f"${c['suma_asegurada_usd']:,} USD asegurados")


if __name__ == "__main__":
    main()
