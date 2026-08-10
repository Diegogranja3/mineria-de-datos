# Minería de Datos — 031 A2026 (Asíncrono)

Prof. José Anastacio Hernández Saldaña · FCFM UANL · Ago–Dic 2026

- Grabaciones: https://drive.google.com/drive/folders/1dTXg19oMu2nYAC5l5oabkP6hzuGWJbsu
- Código de clases: https://github.com/ppGodel/data_mining
- Registro del repo: https://forms.cloud.microsoft/r/DUYX1cSwMb

## Dataset

**Carpetas de investigación FGJ CDMX, año 2023** — `data/carpetasFGJ_2023.csv.gz`

- Fuente: Portal de Datos Abiertos de la CDMX, Fiscalía General de Justicia
- Origen: https://archivo.datos.cdmx.gob.mx/FGJ/carpetas/carpetasFGJ_2023.csv
- Catálogo: https://datos.cdmx.gob.mx/dataset/carpetas-de-investigacion-fgj-de-la-ciudad-de-mexico
- Descargado: 10 ago 2026 · 242,392 filas × 21 columnas · 69 MB crudo, 12 MB en gzip

`pandas.read_csv()` lee el `.gz` directo, no hace falta descomprimir.

Requisitos verificados:

- [x] ≥ 4 variables distintas — **21**
- [x] ≥ 2 numéricas — `latitud`, `longitud`, `anio_hecho`
- [x] ≥ 1 alfanumérica — `delito` (286 valores únicos, 422 palabras distintas)
- [x] ≥ 1 fecha con continuidad temporal — `fecha_inicio`, **365 de 365 días de 2023**
- [x] ≥ 5,000 filas — **242,392**
- [x] 1 solo archivo
- [x] No es de Kaggle ni trae análisis resuelto

### Trampas conocidas del dataset

Detectadas al explorarlo. Sirven de material para la Práctica 1 y evitan sorpresas después:

1. **Usar `fecha_inicio` para la serie de tiempo, no `fecha_hecho`.** `fecha_inicio` es la apertura de la carpeta (365 días continuos de 2023). `fecha_hecho` es cuándo ocurrió el delito y llega hasta 1957 — son denuncias de hechos viejos. Como serie temporal tiene huecos enormes.
2. **`categoria_delito` está desbalanceado ~87%** hacia "DELITO DE BAJO IMPACTO". Para el KNN de la Práctica 6, un clasificador que siempre predice esa clase acierta 87% sin aprender nada. Usar `delito` (286 clases), agrupar en clases balanceadas, o reportar métricas por clase y no solo accuracy.
3. **`latitud`/`longitud` tienen ~6.5% de nulos** y coordenadas en 0 o fuera de CDMX. Filtrar antes del clustering de la Práctica 7.
4. **Columnas duplicadas a propósito**: `colonia_hecho` vs `colonia_catalogo`, `alcaldia_hecho` vs `alcaldia_catalogo`. Las `_catalogo` están normalizadas (Title Case, nombres oficiales); las `_hecho` vienen crudas del expediente. Decidir cuál usar y justificarlo — el profe evalúa el por qué.
5. **Encoding**: el CSV viene en UTF-8 pero con acentos inconsistentes en algunos campos.

## Entregas

Fechas estimadas asumiendo Semana 1 = 3 ago 2026. Confirmar con el profesor.

| # | Práctica | Semana | Estimado | Estado |
|---|---|---|---|---|
| 1 | Limpieza de datos (+ subir dataset) | 4 | 24 ago | |
| 2 | Estadística descriptiva, entidades/relaciones, diagrama, métricas agrupadas | 5 | 31 ago | |
| 3 | Visualización — ≥5 tipos de gráfica, generadas con ciclos/automatización | 6 | 7 sep | |
| 4 | Pruebas estadísticas — ANOVA + t, o Kruskal-Wallis | 7 | 14 sep | |
| 5 | Modelo lineal + correlación + R² | 9 | 28 sep | |
| 6 | Clasificación — KNN | 10 | 5 oct | |
| 7 | Clustering — K-Means | 12 | 19 oct | |
| 8 | Pronóstico — regresión / serie de tiempo | 13 | 26 oct | |
| 9 | Análisis de texto — nube de palabras + EDA | 14 | 2 nov | |
| 10 | **PIA** — video ≤8 min | 15 | 9 nov | |

**Límite absoluto de todo el semestre: 17 de noviembre.**

## Reglas que cuestan la materia

- Sin PIA repruebas automáticamente, aunque entregues las 9 prácticas.
- El PIA es un reporte de inteligencia de negocios, no un resumen de tareas. Prohibido grabar scroll de código, prohibido video tipo podcast. Integrar ≥2 técnicas avanzadas. Soporte visual obligatorio.
- Sin commit dentro de 2 semanas de la fecha programada → práctica penalizada.
- Todo en rama `main`, una carpeta por práctica.
- IA solo como pair programmer (sintaxis, debug, librerías). Prohibido delegarle el análisis o la interpretación de hallazgos.
- En cada práctica se evalúa el **por qué** de las decisiones, y que se probaron variaciones.

## Supervisiones

Cada 4 semanas, horario por acordar. Asistencia no obligatoria, pero las entregas sí.
