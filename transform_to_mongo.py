"""
Transforma Data__1_.csv (fuente: NASA EONET vía Kaggle) a documentos
MongoDB listos para mongoimport, para la colección `eventos_desastres`
del proyecto final M6-NOSQL.

Decisiones de diseño (documentar en el proyecto):
- Se usa solo Geometry_Coordinates_1 como ubicacion tipo Point.
  ~31 eventos (icebergs y tormentas en movimiento) traen coordenadas
  adicionales que representan una trayectoria, no ubicaciones
  simultáneas; se descartan en este MVP y se documenta como limitación.
- Date + Time se combinan en un solo campo fecha_hora (BSON Date, UTC).
- Los eventos sin Description quedan sin ese campo (no se fuerza a "").
- El ID original de EONET se usa como _id del documento.

Uso:
    python3 transform_to_mongo.py Data__1_.csv eventos_desastres.json

Carga en Mongo (Learner Lab):
    mongoimport --db riesgo_catastrofico --collection eventos_desastres \
        --file eventos_desastres.json --jsonArray
"""

import csv
import json
import sys
from datetime import datetime, timezone


def limpiar_texto(valor):
    """Normaliza espacios dobles/triples que vienen de la fuente y
    recorta espacios sobrantes. Devuelve None si el campo está vacío."""
    if valor is None:
        return None
    texto = " ".join(valor.split())
    return texto if texto else None


def parsear_coordenada(valor):
    """'-117.982361  48.821248' -> [-117.982361, 48.821248] (lon, lat)."""
    if not valor or not valor.strip():
        return None
    partes = valor.split()
    if len(partes) != 2:
        raise ValueError(f"Formato de coordenada inesperado: {valor!r}")
    lon, lat = float(partes[0]), float(partes[1])
    if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
        raise ValueError(f"Coordenada fuera de rango: lon={lon}, lat={lat}")
    return [lon, lat]


def combinar_fecha_hora(fecha, hora):
    """'2025-07-08' + '16:38:00' -> ISODate UTC en formato ISO 8601."""
    dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    return dt


def transformar_fila(fila):
    ubicacion = parsear_coordenada(fila["Geometry_Coordinates_1"])
    if ubicacion is None:
        # No debería pasar (Coordinates_1 nunca está vacío en la fuente),
        # pero se descarta explícitamente si ocurriera.
        return None

    fecha_hora = combinar_fecha_hora(fila["Date"], fila["Time"])

    doc = {
        "_id": fila["ID"],
        "titulo": limpiar_texto(fila["Title"]),
        "categoria": fila["Category_title"].strip(),
        "fecha_hora": fecha_hora.isoformat(),
        "anio": fecha_hora.year,
        "ubicacion": {"type": "Point", "coordinates": ubicacion},
        "fuente": {"origen": "NASA EONET via Kaggle", "id_original": fila["ID"]},
    }

    descripcion = limpiar_texto(fila["Description"])
    if descripcion:
        doc["descripcion"] = descripcion

    return doc


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 transform_to_mongo.py <entrada.csv> <salida.json>")
        sys.exit(1)

    ruta_entrada, ruta_salida = sys.argv[1], sys.argv[2]

    documentos = []
    descartados = []

    with open(ruta_entrada, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        for i, fila in enumerate(lector, start=2):  # 2: contando el header
            try:
                doc = transformar_fila(fila)
                if doc is None:
                    descartados.append((i, fila.get("ID"), "sin coordenada"))
                else:
                    documentos.append(doc)
            except ValueError as e:
                descartados.append((i, fila.get("ID"), str(e)))

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(documentos, f, ensure_ascii=False, indent=2)

    print(f"Documentos transformados: {len(documentos)}")
    print(f"Filas descartadas: {len(descartados)}")
    for fila_num, id_evento, motivo in descartados[:10]:
        print(f"  fila {fila_num} ({id_evento}): {motivo}")
    if len(descartados) > 10:
        print(f"  ... y {len(descartados) - 10} más")


if __name__ == "__main__":
    main()
