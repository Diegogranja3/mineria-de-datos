# Práctica 1 — Limpieza de datos

Carpetas de investigación de la FGJ de la CDMX, 2023. Son 242,392 denuncias.

```
python limpieza.py           # genera carpetas_2023_limpio.parquet
python limpieza.py --demo    # pruebas del pipeline
```

El crudo está en `../data/carpetasFGJ_2023.csv.gz`. Necesita pandas y pyarrow.

Lo guardo en parquet y no en CSV porque en CSV pesa 79 MB contra 10, y porque el CSV no
guarda los tipos: al releerlo se pierden las 9 columnas categóricas y las 4 de fecha, y
hay que reparsear todo otra vez. Se abre con `pd.read_parquet()`.

## Lo que arreglé

`fiscalia` tenía 48 valores distintos pero solo existen 37 fiscalías. Los 11 de más eran
el mismo nombre con basura pegada al final. Pensé que eran espacios, pero al descomprimir
el archivo vi que son retornos de carro, tipo `FISCALÍA ... ELECTORALES\r\r\r...\n`, en
213 registros. Un `strip()` los quita.

Las fechas venían como texto, así que no se podían restar ni ordenar. Las pasé a datetime
y junté fecha con hora en `ts_inicio` y `ts_hecho`. De ahí salió `dias_para_denunciar`,
que no venía en el original (mediana: 2 días).

`alcaldia_hecho` traía `CDMX (indeterminada)` (7,340 casos) y `FUERA DE CDMX` (2,550),
que no son alcaldías. Si los dejas se cuelan al ranking de alcaldías con más delitos.

Había dos columnas para lo mismo: `alcaldia_hecho` y `alcaldia_catalogo`, con unas 110
filas donde se contradicen. Me quedé con `alcaldia_hecho` porque tiene menos huecos (841
contra 4,303). Con colonia fue al revés, ahí `colonia_catalogo` estaba mejor formateada
y solo le rellené los huecos con `colonia_hecho`.

Saqué 8 columnas que no aportaban: `anio_inicio` era 2023 en las 242 mil filas, y los
meses se sacan de la fecha.

No borré ninguna fila.

## Las cinco columnas booleanas

Son avisos, no datos nuevos:

| Columna | Casos | Qué avisa |
|---|---|---|
`sin_coordenadas` | 14,147 | no tiene lat/lon |
`alcaldia_indeterminada` | 7,340 | era `CDMX (indeterminada)` |
`fuera_cdmx` | 2,550 | el hecho fue fuera de la ciudad |
`hora_hecho_estimada` | 23,988 | la hora dice 12:00:00 exacto |
`hecho_posterior_a_inicio` | 1,616 | el delito aparece después de su denuncia |

El `12:00:00` sale en el 9.9% de los registros y no es que haya más delitos a mediodía:
es lo que se captura cuando el denunciante no recuerda la hora. Una gráfica por hora del
día sin filtrar esto tiene un pico enorme al mediodía que no existe.

Las 1,616 del último caso son todas del mismo día, con 23 minutos de diferencia en
promedio. Es error de captura, y no la corregí porque no hay forma de saber cuál de las
dos horas es la mala.

## Por qué quedan nulos

Quedan 69,601 nulos de 5,575,016 valores, el 1.25%. Doce de las 23 columnas no tienen
ninguno y el 93.94% de las filas están completas.

Limpiar no es completar. Si el dato nunca se capturó, lo único que puedes hacer es
inventarlo, y eso ya no es limpiar.

Mi primer impulso fue borrar las 14,147 filas sin coordenada, hasta que revisé qué tenían
en común:

| Categoría | % sin coordenada | % con coordenada |
|---|---|---|
Lesiones por disparo de arma de fuego | 3.10% | 0.16% |
Robo a pasajero en el Metro | 3.23% | 0.40% |
Violación | 5.27% | 0.92% |
Delito de bajo impacto | 74.40% | 88.09% |

Borrarlas me habría quitado una de cada cinco lesiones por arma de fuego del año y casi
ningún delito menor. Y tiene sentido: la coordenada sale de una dirección, y un robo en
el Metro no tiene número de casa, ni una violación se registra con domicilio. La falta de
coordenada dice algo sobre el tipo de hecho, no es azar. En la clasificación de Rubin es
MNAR; lo que sí se puede comprobar con los datos es que no es MCAR.

Rellenarlas tampoco servía. 9,890 de las 14,147 están en grupos donde el 100% no tiene
coordenada, así que no hay de dónde copiar. Y para las otras 3,400, poner el centro de la
colonia metería puntos falsos que el K-Means de la P7 agruparía como si fueran reales. Un
archivo sin nulos se vería más limpio y sería menos cierto, y ya no podría distinguir los
228,245 puntos reales de los inventados.

Los demás huecos son más simples. `colonia` es el mismo hueco que las coordenadas (los
14,144 coinciden exactamente). Los 841 de `alcaldia_hecho` son todos `HECHO NO DELICTIVO`
o `INCOMPETENCIA`: si el asunto no le toca a la fiscalía, no levantan la ubicación. Los
540 de `unidad_investigacion` se concentran en dos fiscalías y las otras 34 no tienen ni
uno, así que depende de quién capturó y no del delito. Esos dos sí se podrían rellenar,
pero son el 0.35% y el 0.22% y ninguna práctica los usa. Los 22 de `fecha_hecho` son tan
pocos que no se puede concluir nada de ellos.

Los 10,731 nulos de `alcaldia` no son dato faltante: son los 841 más los dos centinelas,
y quedan registrados en las banderas.
