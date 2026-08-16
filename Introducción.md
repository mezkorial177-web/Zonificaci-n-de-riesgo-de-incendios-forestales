# Zonificación de riesgo de incendios forestales para apoyo a suscripción de seguros de propiedad

---

## 1. Descripción del problema

Las aseguradoras de propiedad necesitan decidir en qué zonas geográficas
aceptar, restringir la suscripción de pólizas contra incendio,
pero esa decisión suele basarse en información histórica dispersa o
desactualizada. Este proyecto construye una base documental que cruza el
historial real de eventos de incendio forestal (NASA EONET, 2023-2025) con
una cartera de pólizas por zona geográfica, para responder qué tan
concentrado está el riesgo de incendio en relación con la exposición
asegurada actual.

La información resultante la utilizaría un **equipo de suscripción/riesgos
catastróficos** dentro de una aseguradora, como insumo para decidir en qué
zonas limitar la emisión de nuevas pólizas, ajustar tarifas, o identificar
zonas de alta actividad de incendios donde la cartera actual está
subexpuesta o sobreexpuesta.
> **Nota sobre cobertura temporal: el dataset completo abarca 2002-2025, pero esas fechas corresponden a la unión de todas las categorías (Volcanes, Hielo Marino y Lacustre, etc.). La categoría Incendio, que es el foco de este proyecto, solo tiene cobertura consistente a partir de 2022 (1 evento en 2022, 19 en 2023, 4,114 en 2024, 1,184 hasta julio 2025). Esta limitación se documenta explícitamente y condiciona qué tipo de preguntas temporales son defendibles con la evidencia disponible.

## 2. Preguntas del proyecto

1. ¿En qué zonas geográficas se concentra históricamente la actividad de
   incendios forestales, y cómo se compara esa concentración con el tamaño
   de la cartera asegurada en cada zona?
2. ¿Qué zonas presentan la mayor **tasa** de eventos por póliza activa
   (frecuencia normalizada por exposición), en lugar de solo el conteo
   bruto de eventos?
3. ¿Existe una tendencia en el número de incendios a lo largo de los años
   (2023-2025) dentro de las zonas de mayor exposición asegurada, que
   sugiera un incremento del riesgo?
4. ¿Hay estacionalidad mensual en la ocurrencia de incendios dentro de las
   zonas con mayor cartera, relevante para renovaciones o vigencias
   estacionales de pólizas?
5. ¿Qué zonas con actividad significativa de incendios quedan **fuera** de
   la cartera actual, y podrían representar riesgo de expansión no
   evaluado?

*(Nota de alcance: el dataset original incluye también las categorías "Tormentas severas", "Volcanes" y "Hielo marino y lacustre", pero con 3, 32 y 40 eventos respectivamente no hay evidencia suficiente para sostener un análisis independiente. Se documentan como limitación y posible línea de trabajo futura, no como parte de las preguntas centrales.)*

## 3. Modelo documental

### Colección principal: `eventos_desastres`

Un documento por evento de incendio forestal reportado por EONET. Es la
colección de mayor volumen (5,393 documentos) y la que cambia con menor
frecuencia una vez cargada (es un histórico, no un dato operativo).

```json
{
  "_id": "EONET_14198",
  "titulo": "HOPE Wildfire Stevens Washington",
  "categoria": "Wildfires",
  "fecha_hora": "2025-07-08T16:38:00+00:00",
  "anio": 2025,
  "ubicacion": { "type": "Point", "coordinates": [-117.982361, 48.821248] },
  "fuente": { "origen": "NASA EONET via Kaggle", "id_original": "EONET_14198" },
  "descripcion": "15 Miles N from KETTLE FALLS WA"
}
```

### Colección relacionada: `carteras`

Un documento por zona geográfica de suscripción, con su polígono y datos
de exposición. Es una colección pequeña (15 documentos) que sí cambiaría
con frecuencia operativa (renovaciones, altas y bajas de pólizas, ajuste
de límites geográficos).

```json
{
  "_id": "zona_01",
  "nombre": "África central (Angola/RDC/Zambia)",
  "poligono": {
    "type": "Polygon",
    "coordinates": [[[15, -15], [30, -15], [30, 0], [15, 0], [15, -15]]]
  },
  "polizas_activas": 1060,
  "suma_asegurada_usd": 190800000,
  "eventos_wildfire_historicos": 619,
  "sintetico": true,
  "nota": "Exposición generada para fines académicos; no representa datos reales de una aseguradora."
}
```

### Justificación: referencia, no anidamiento

Se optó por **dos colecciones independientes relacionadas por ubicación**,
en lugar de embeber la cartera dentro de cada evento o los eventos dentro
de cada zona:

- **Cardinalidad y tasa de cambio distintas.** `eventos_desastres` crece
  por miles y es prácticamente inmutable una vez cargado (es historia).
  `carteras` es pequeña y cambia con la operación normal del negocio
  (pólizas que entran y salen). Embeber datos de cartera en cada evento
  obligaría a reescribir miles de documentos cada vez que cambia una
  póliza — el anti-patrón clásico de embeber un dato de alta frecuencia
  de actualización dentro de un documento de alto volumen.
- **La relación es espacial, no por llave.** No se guarda un campo
  `zona_id` dentro de cada evento. La pertenencia de un evento a una zona
  se calcula dinámicamente con `$geoWithin`/`$lookup` sobre el polígono.
  Esto permite rediseñar los límites de las zonas de suscripción sin tener
  que reprocesar los 5,393 eventos históricos.
- **Ambas colecciones tienen valor por separado.** `eventos_desastres` es
  útil sin cartera (por ejemplo para el componente temporal). `carteras`
  es útil sin eventos (por ejemplo para reportes de exposición). Embeber
  una dentro de otra rompería esa independencia.

## 4. Conjunto de datos

| Colección | Origen | Naturaleza | Documentos |
|---|---|---|---|
| `eventos_desastres` | NASA EONET, vía dataset público de Kaggle ("Global Natural Calamities Dataset") | Real, público, sin información personal | 5,393 (5,318 de categoría Incendio) |
| `carteras` | Generado para este proyecto a partir de las zonas de mayor densidad real de incendios | Sintético, documentado explícitamente como tal en cada documento (`"sintetico": true`) | 15 |

No se utiliza información personal real en ninguna de las dos colecciones:
`eventos_desastres` describe fenómenos naturales geolocalizados (no
personas), y `carteras` es exposición de seguros inventada a nivel de
zona geográfica, sin nombres de asegurados ni domicilios individuales.

Scripts de transformación y carga reproducibles:
- `transform_to_mongo.py` — genera `eventos_desastres.json` desde el CSV
  fuente.
- `generate_carteras.py` — genera `carteras.json` a partir de
  `eventos_desastres.json`.
  (histórico de cambios de polígono) si el alcance del proyecto lo
  justifica — por ahora, fuera de alcance.


 ## 5. Consultas principales

### Consulta 1 — Frecuencia histórica por zona (preguntas 1 y 5)

* **Pregunta que responde:** ¿En qué zonas se concentra la actividad de incendios, y cuáles tienen actividad significativa pero no cartera asignada?
* **Campos usados:** `categoria` (igualdad: `"Wildfires"`), `ubicacion`.
* **Ordenamiento:** Ninguno todavía a este nivel.
* **¿Consulta arreglo?** No.
* **¿Por qué se ejecutaría con frecuencia?** Es la consulta base de todo el análisis — cualquier reporte de exposición parte de "¿cuántos eventos hay por zona?".

### Consulta 2 — Eventos por rango de fechas y categoría (preguntas 3 y 4)

* **Pregunta que responde:** ¿Cómo cambia la frecuencia de incendios año con año, y hay estacionalidad mensual?
* **Campos usados:** `categoria` (igualdad), `fecha_hora` (rango: `$gte`/`$lt` para acotar por año o mes).
* **Ordenamiento:** Por `fecha_hora` ascendente.
* **¿Consulta arreglo?** No.
* **¿Por qué se ejecutaría con frecuencia?** Cualquier corte temporal (por año, por mes, por rango de suscripción) pasa por aquí — es el patrón que se va a repetir más veces al explorar tendencia/estacionalidad.

### Consulta 3 — Tasa de eventos por póliza activa (pregunta 2)

* **Pregunta que responde:** ¿Qué zonas tienen mayor frecuencia de incendios normalizada por su exposición asegurada?
* **Campos usados:** `carteras.polizas_activas` (para el cálculo de tasa), vinculado a `eventos_desastres` vía `$geoWithin`/`$lookup` sobre `ubicacion`/`poligono`.
* **Ordenamiento:** Por la tasa calculada, descendente.
* **¿Consulta arreglo?** No, pero sí es multi-colección (pipeline con `$lookup`).
* **¿Por qué se ejecutaría con frecuencia?** Es la consulta de mayor valor de negocio del proyecto — la que distingue "zona con muchos incendios" de "zona con muchos incendios relativo a su cartera", que es la pregunta real de un suscriptor.



# Medición inicial (antes de indexar)

**Sección:** 3.3 de la guía de avance, semana 2
**Base:** `riesgo_catastrofico`, colección `eventos_desastres` (5,393 documentos, sin índices secundarios)

## Consultas medidas

### Consulta 1 — Frecuencia por zona (representativa: zona África central)
```javascript
db.eventos_desastres.find({
  categoria: "Wildfires",
  ubicacion: {
    $geoWithin: {
      $geometry: {
        type: "Polygon",
        coordinates: [[[15,-15],[30,-15],[30,0],[15,0],[15,-15]]]
      }
    }
  }
}).explain("executionStats")
```

### Consulta 2 — Rango de fechas + categoría (año 2024)
```javascript
db.eventos_desastres.find({
  categoria: "Wildfires",
  fecha_hora: {
    $gte: ISODate("2024-01-01T00:00:00Z"),
    $lt: ISODate("2025-01-01T00:00:00Z")
  }
}).sort({ fecha_hora: 1 }).explain("executionStats")
```

### Consulta 3 — Frecuencia por zona (representativa: zona EUA suroeste)
```javascript
db.eventos_desastres.find({
  categoria: "Wildfires",
  ubicacion: {
    $geoWithin: {
      $geometry: {
        type: "Polygon",
        coordinates: [[[-120,30],[-105,30],[-105,45],[-120,45],[-120,30]]]
      }
    }
  }
}).explain("executionStats")
```

## Resultados

| Consulta | Plan | nReturned | totalKeysExamined | totalDocsExamined | SORT aparte |
|---|---|---|---|---|---|
| 1 — Zona África central | COLLSCAN | 621 | 0 | 5,393 | No |
| 2 — Rango fecha 2024 | COLLSCAN | 4,114 | 0 | 5,393 | Sí |
| 3 — Zona EUA suroeste | COLLSCAN | 377 | 0 | 5,393 | No |

## Interpretación

Las tres consultas ejecutan un `COLLSCAN` completo: examinan los 5,393
documentos de la colección sin importar cuántos resultados regresan
(621, 4,114 o 377). `totalKeysExamined: 0` en las tres confirma que no
hay ningún índice secundario en uso — es la línea base antes de indexar.

La Consulta 2 es la más costosa: además del escaneo completo, agrega una
etapa `SORT` independiente que ordena en memoria los 4,114 documentos
resultantes (`totalDataSizeSorted: 1,208,922` bytes). Esto evidencia que
un índice sobre `fecha_hora` no solo evitaría el `COLLSCAN`, sino también
el ordenamiento en memoria

Las consultas 1 y 3 usan la misma forma (`categoria` + `$geoWithin`
sobre `ubicacion`), solo cambia el polígono de la zona. Esto confirma
que el índice `2dsphere` que se diseñe sirve por igual para las 15 zonas
de `carteras`, no solo para la zona usada en esta medición.


# Estrategia de indexación

**Sección:** 3.4 de la guía de avance, semana 2
**Base:** `riesgo_catastrofico`, colección `eventos_desastres`

Se proponen dos índices — la menor cantidad razonable para cubrir los
tres patrones de consulta definidos en 3.2 (ver `01_punto_partida.md` y
`02_medicion_inicial.md`).

## Índice 1 — Compuesto `categoria` + `fecha_hora`

| Punto | Detalle |
|---|---|
| **Patrón y nombre** | `{ categoria: 1, fecha_hora: 1 }`, nombre `idx_categoria_fecha` |
| **Consulta que apoya** | Consulta 2: igualdad en `categoria` + rango en `fecha_hora` + `sort(fecha_hora)` |
| **Orden de campos** | `categoria` primero (igualdad), `fecha_hora` después (rango + ordenamiento). Patrón ESR (Equality-Sort-Range): como el campo de rango y el de sort coinciden (`fecha_hora`), el índice resuelve ambos sin necesitar una etapa `SORT` aparte. |
| **Reutilización de prefijo** | Sí. Una consulta que solo filtre `{ categoria: "Wildfires" }` sin fecha puede usar el prefijo `{ categoria: 1 }` de este mismo índice. |
| **¿Multikey?** | No. Ni `categoria` ni `fecha_hora` son arreglos. |
| **Costo esperado** | Bajo. Colección de 5,393 documentos; `categoria` tiene solo 4 valores distintos por sí sola, pero combinada con `fecha_hora` discrimina bien. Costo de escritura/almacenamiento marginal frente al beneficio de eliminar `COLLSCAN` + `SORT`. |

## Índice 2 — Geoespacial `2dsphere` sobre `ubicacion`

| Punto | Detalle |
|---|---|
| **Patrón y nombre** | `{ ubicacion: "2dsphere" }`, nombre `idx_ubicacion_2dsphere` |
| **Consulta que apoya** | Consultas 1 y 3: `$geoWithin` sobre las 15 zonas de `carteras`, y futuras `$geoNear`/`$geoIntersects` |
| **Orden de campos** | Un solo campo, no aplica orden compuesto. |
| **Reutilización de prefijo** | No aplica (índice de un solo campo). |
| **¿Multikey?** | No en el sentido de arreglos — `ubicacion` es un único `Point`. Internamente `2dsphere` usa una estructura de geohash, pero es detalle de implementación, no "multikey por arreglo". |
| **Costo esperado** | Más alto que un B-tree simple (construcción y mantenimiento de la estructura de geohash), pero justificado: el componente geoespacial es requisito central del proyecto (semana 3), y sin este índice las 15 consultas por zona seguirían haciendo `COLLSCAN`. |

## Comandos ejecutados

```javascript
use riesgo_catastrofico

db.eventos_desastres.createIndex(
  { categoria: 1, fecha_hora: 1 },
  { name: "idx_categoria_fecha" }
)

db.eventos_desastres.createIndex(
  { ubicacion: "2dsphere" },
  { name: "idx_ubicacion_2dsphere" }
)

db.eventos_desastres.getIndexes()
```

## Evidencia — `getIndexes()`

```javascript
[
        {
                "v" : 2,
                "key" : {
                        "_id" : 1
                },
                "name" : "_id_"
        },
        {
                "v" : 2,
                "key" : {
                        "categoria" : 1,
                        "fecha_hora" : 1
                },
                "name" : "idx_categoria_fecha"
        },
        {
                "v" : 2,
                "key" : {
                        "ubicacion" : "2dsphere"
                },
                "name" : "idx_ubicacion_2dsphere",
                "2dsphereIndexVersion" : 3
        }
]
```

Los dos índices quedaron creados correctamente (`numIndexesAfter: 3`,
contando el índice `_id_` por defecto). Confirmado con `getIndexes()`:
`idx_categoria_fecha` con las claves y orden diseñados, e
`idx_ubicacion_2dsphere` con `2dsphereIndexVersion: 3`.



