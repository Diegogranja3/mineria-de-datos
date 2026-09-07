# Cómo uso la IA en este repo

Registro de cómo se usa Claude Code en la materia de Minería de Datos, y las reglas
con las que opera. Este archivo se carga solo al inicio de cada sesión, así que
sirve de instrucción y de bitácora al mismo tiempo.

## Reglas de la materia

Del README del repo, sección "Reglas que cuestan la materia":

> IA solo como pair programmer (sintaxis, debug, librerías). Prohibido delegarle el
> análisis o la interpretación de hallazgos.
>
> En cada práctica se evalúa el **por qué** de las decisiones, y que se probaron
> variaciones.

## Prompt que le doy a Claude

Textual, tal como se lo pasé:

> Actúa como mi compañero de programación (Pair Programmer) experto en Python,
> Pandas y Ciencia de Datos. Estoy cursando una materia de Minería de Datos y
> quiero que me asistas con mi código, pero NO quiero que hagas el trabajo por mí.
>
> Tus instrucciones son:
>
> **Rol:** Tú eres el 'Navegante' y yo el 'Conductor'. Yo escribo la lógica y el
> código; tú me ayudas a revisar sintaxis, sugerir librerías vectorizadas o señalar
> errores de lógica.
>
> **Depuración formativa:** Si te comparto un error o traceback, no me des la
> solución directa inmediatamente. Explícame el origen conceptual del fallo (ej.
> tipos de datos, índices, indentación) y dame una pista para corregirlo.
>
> **Prohibido interpretar hallazgos:** Si te muestro métricas (R², p-value, matriz
> de confusión) o una gráfica, NO me des las conclusiones de negocio ni interpretes
> qué significan los datos por mí; hazme preguntas para que yo aprenda a
> interpretar.
>
> **No generes código completo de la nada:** Espera a que yo te comparta mi
> pseudocódigo o mi primer intento antes de hacer sugerencias.

### Lo que sí le pido

- Explicar conceptos que no conozco (qué es la curtosis, qué es una carpeta de
  investigación, qué significa el CV). Eso es conocimiento, no interpretación de
  mis datos.
- Correr código y devolverme la salida cruda, sin conclusiones.
- Escribir el andamio mecánico (el `groupby`, la fórmula) cuando el tiempo aprieta,
  siempre que las conclusiones las escriba yo.
- Revisar si un argumento mío se sostiene contra los datos.

### Lo que no

- Escribir las interpretaciones ni las conclusiones.
- Dar la solución de un error antes de explicarme por qué falló.
- Elegir por mí entre dos decisiones de modelado defendibles.

## Estado de las prácticas

| # | Práctica | Estado |
|---|---|---|
| 1 | Limpieza de datos | entregada (commit `a4b517c`) |
| 2 | Estadística descriptiva, entidades/relaciones, diagrama, métricas agrupadas | entregada |
| 3-10 | — | pendientes |

## Bitácora

### Práctica 1 — limpieza

Hecha antes de establecer estas reglas.

### Práctica 2 — estadística descriptiva

**Aviso importante para el registro:** al principio de la sesión, antes de que yo le
diera el prompt de Pair Programmer, Claude escribió la Práctica 2 completa por su
cuenta — código e interpretaciones. **No es mío y no cuenta.** Ese trabajo quedó en
un commit local que nunca se subió, y el commit se borró del historial con
`git reset` el 31 de agosto de 2026. Los archivos también se sacaron del repo.

Lo que sigue es la versión trabajada con las reglas puestas.

**Método del punto 2 (entidades).** No se asumió la estructura por los nombres de
las columnas. Cada relación se planteó como hipótesis falsable y se probó con
`groupby(A)[B].nunique()`: si algún valor de A tiene más de un valor de B, la
dependencia funcional no se cumple y B no es atributo de A.

Decisiones que tomé yo, con la evidencia que las respalda:

- `categoria_delito` es atributo de `delito`, no de la carpeta (0 excepciones en 286).
- `competencia` no depende del delito (falla en 124 de 286) ni de la fiscalía (está
  repartida en 36 de 37): es atributo de la carpeta.
- Las llaves de `agencia`, `unidad_investigacion` y `colonia` son compuestas con su
  padre, porque el nombre solo se repite entre padres distintos.
- La jerarquía `fiscalía → agencia → unidad` **se cayó**: agencia y unidad son ramas
  paralelas de la fiscalía, N:M entre sí, y lo que las cruza es la carpeta.
- `CARPETA` no tiene llave primaria en el origen. Se agrega `id_carpeta` sustituta.
- Se agregó la relación directa `FISCALIA ||--|{ CARPETA` aunque sea parcialmente
  redundante con la llave de AGENCIA.

Hipótesis mías que los datos corrigieron, y quedan documentadas como parte del
trabajo:

- Pensé que `delito` era la entidad central. Es un catálogo; la entidad es la carpeta.
- Pensé que `anio_inicio` era catálogo. Es una columna derivada de `fecha_inicio`.
- Pensé que los nombres de colonia repetidos eran una colonia partida entre
  alcaldías. Salieron las dos cosas: 153 de 226 están a menos de 2 km (frontera) y
  67 a más de 5 km (nombres repetidos en rumbos distintos).

**Punto 1.** Los hallazgos que escribí: la media (66.85) y la mediana (2) de
`dias_para_denunciar` están separadas por la cola de valores extremos; el 17.18%
que marca la regla de Tukey no son errores sino la forma de la distribución; el CV
no aplica a coordenadas porque el cero de la escala es una convención.

**Punto 4.** Decidí reportar las tres variaciones (subir k, clases de amplitud
desigual, escala logarítmica) en lugar de una sola, para mostrar que cada una
arregla una métrica y rompe otra. La conclusión que saqué: el número de clases
importa menos que si la variable está en la escala correcta.

**Sección 4 del reporte.** Agregué los descriptivos agrupados por categoría de
delito, que es donde el punto 1 y el punto 2 se juntan. El hallazgo: las medianas van
de 0 a 7 días y el orden depende de quién abre la carpeta. Homicidio y lesiones por
arma de fuego dan mediana 0 porque los reporta la autoridad; violación da mediana 7
con un 10% arriba de cuatro años porque depende de que la víctima decida denunciar.

### Quién hizo qué en la Práctica 2

Lo pongo explícito para que no se malinterprete.

**Mío:**

- Las hipótesis de cómo estaba estructurado el dataset, incluidas las que se cayeron.
- Cada decisión de modelado: qué es entidad y qué es atributo, dónde va la llave
  compuesta, qué cardinalidad lleva cada relación del diagrama, agregar `id_carpeta`.
- La interpretación de todos los números y las conclusiones de los cuatro puntos.
- La decisión de reportar las tres variaciones del punto 4 en lugar de una.

**De Claude:**

- `estadistica_desc.py`: el código que calcula. Es el andamio mecánico (los
  `groupby`, las fórmulas de datos agrupados), no el análisis.
- Correr el script y devolverme la salida cruda.
- Explicarme los conceptos que no conocía: curtosis, sesgo, entropía, coeficiente de
  variación, qué es una carpeta de investigación, la sintaxis de Mermaid.
- Redactar los párrafos del README a partir de lo que yo le dictaba, y reescribirlos
  cuando le pedía simplificar.

**Cómo se trabajó el texto.** Hueco por hueco. Claude ponía los números y una
pregunta; yo contestaba con mi lectura; él la redactaba y yo la aprobaba o le pedía
acortarla. Cuando un argumento mío no aguantaba los datos me lo dijo en lugar de
escribirlo: pasó con `municipio_hecho`, donde yo dije que la columna no servía de
nada y resultó que sí tiene 231 valores, solo que toda su información está en las
filas sin alcaldía.

Al final pedí simplificar el README completo: sin siglas, con glosario de cada
término y sin jerga, para que se entienda sin saber estadística.

## Archivos

```
data/                     dataset crudo (csv.gz)
Practica 1/limpieza.py    pipeline de limpieza -> parquet
Practica 2/
  estadistica_desc.py     los tres puntos: descriptivos, entidades, agrupados
  salida.txt              salida completa del script
  README.md               el reporte
```

Los scripts traen `--demo` con asserts que verifican las fórmulas contra casos
resueltos a mano antes de correrlas sobre las 242,392 filas.
