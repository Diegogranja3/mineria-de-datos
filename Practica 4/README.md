# Práctica 4 — Pruebas estadísticas

La práctica pide ANOVA con prueba t, **o** Kruskal-Wallis. Es una elección, y
justificarla es parte del trabajo.

Se usan las mismas denuncias limpias de la Práctica 1
(`../Practica 1/carpetas_2023_limpio.parquet`).

```
python pruebas.py          # el reporte completo (queda en salida.txt)
python pruebas.py --demo   # comprueba las funciones con casos de respuesta conocida
```

Necesita `scipy`.

## La pregunta

> ¿`dias_para_denunciar` cambia según `categoria_delito`?

Es la misma tabla de la sección 4 de la Práctica 2, donde las medianas iban de 0 a 7
días. Ahí se describió la diferencia; aquí se comprueba si aguanta.

## Qué contestan estas pruebas

Cuando dos grupos dan números distintos hay dos explicaciones posibles:

```
1. De verdad son distintos.
2. Fue suerte: tocaron esos casos y salió esa diferencia.
```

Una prueba estadística sirve para descartar la segunda. El **p-value** es la
respuesta a: *si todo fuera casualidad, ¿cada cuánto saldría una diferencia así de
grande?* Si la respuesta es "casi nunca", la casualidad no lo explica.

El corte convencional es 0.05. No sale de ninguna teoría: alguien lo propuso hace un
siglo y se quedó, igual que el 1.5 de la regla de Tukey.

Ojo con cómo se lee, porque es el error más común:

```
NO es:  "hay 1% de probabilidad de que la diferencia sea casualidad"
SÍ es:  "SI fuera casualidad, habría 1% de ver algo así de grande"
```

---

## 1. Por qué Kruskal-Wallis y no ANOVA

Las tres pruebas contestan lo mismo por caminos distintos:

| | compara | supone normalidad | le afectan los extremos |
|---|---|---|---|
| prueba t | 2 grupos, promedios | sí | sí |
| ANOVA | muchos grupos, promedios | sí | sí |
| Kruskal-Wallis | muchos grupos, posiciones | no | no |

Kruskal-Wallis primero convierte todo a posiciones: ordena las 242,370 denuncias de
menor a mayor y a cada una le pone su lugar en la fila.

```
valor real:     0    0    1    2    5    100    23,991
posición:       1    2    3    4    5      6          7
```

Con eso, el caso de 23,991 días pesa lo mismo que si fuera de 100. En ANOVA pesaría
23,991 veces más que el de 1 día.

Se escogió Kruskal-Wallis por dos razones.

La primera es que ANOVA supone que los datos siguen una curva normal, y aquí no se
cumple en ninguna de las 16 categorías. Eso se comprueba en la sección siguiente,
pero ya se veía desde la Práctica 2 con el sesgo de 20.45 y desde el histograma de la
Práctica 3.

La segunda importa más. ANOVA compara promedios, y en la Práctica 2 quedó establecido
que la media de `dias_para_denunciar` no describe nada: da 66.85 días contra una
mediana de 2, porque la jalan unos pocos casos de años de rezago. Aunque ANOVA diera
la respuesta correcta, estaría comparando un número que ya se había descartado.
Kruskal-Wallis compara posiciones, que es lo más cercano a comparar medianas.

## 2. ¿Son normales los datos?

Se usó **D'Agostino-Pearson** y no Shapiro-Wilk, porque Shapiro solo sirve hasta
5,000 datos y aquí hay 242,370. D'Agostino está construida con el sesgo y la
curtosis, o sea los mismos dos números que se calcularon en la Práctica 2.

Resultado sobre las 16 categorías:

```
"no normal" en las 16, sin excepción
el p más grande de los 16 grupos fue 0.0000000000089
sesgos entre 4.1 y 56.2        (una curva normal tiene 0)
curtosis entre 14.7 y 3,847.6  (una curva normal tiene 0)
```

Las 16 categorías salen "no normal", sin una sola excepción, y el p más grande de
todas fue 0.0000000000089. No es un resultado apretado: es un rechazo rotundo.

No es una sorpresa. El sesgo de 20.45 de la Práctica 2 y el histograma de la Práctica
3 ya lo decían. Lo que agrega esta prueba es que ahora la decisión de usar
Kruskal-Wallis se apoya en algo formal y no en "se ve torcido".

## 3. ANOVA, corrida a propósito aunque no aplique

Se corrió de todos modos, para ver qué pasa cuando se usa una prueba cuyos supuestos
están rotos.

```
ANOVA de una vía           F = 323.6     p = 0.0
Levene (igual varianza)                  p = 0.0   ->  las varianzas tampoco son iguales
```

ANOVA supone dos cosas: que cada grupo sigue una curva normal y que todos tienen la
misma varianza. **Incumple las dos.**

ANOVA rompe sus dos supuestos: los datos no son normales (sección 2) y las varianzas
tampoco son iguales, según Levene con p = 0.0. Y aun así llega a la misma conclusión
que Kruskal-Wallis.

Eso no vuelve válido usarla, por dos razones.

La primera es que aquí la diferencia entre grupos es enorme, con medianas de 0 a 7
días, y con una diferencia así de grande casi cualquier prueba la detecta. Si la
diferencia fuera chica, ANOVA con sus supuestos rotos sí podría equivocarse, y no
habría forma de saberlo desde el resultado.

La segunda es la de siempre: ANOVA compara promedios. Aunque el sí o no sea correcto,
el número que está comparando no describe esta variable.

Coincidir en la respuesta no es lo mismo que ser la herramienta correcta.

## 4. Kruskal-Wallis sobre las 16 categorías

```
H = 8,804     p = 0.0     n = 242,370     16 grupos
```

Con p = 0.0 se descarta que las diferencias entre las 16 categorías sean casualidad.
Al menos una se sale del resto.

Pero eso es todo lo que dice. No dice cuál, ni cuántas, ni de qué tamaño es la
diferencia. Es el mismo hueco que deja ANOVA, y es la razón de la sección siguiente.

## 5. Comparación por pares

Kruskal-Wallis deja el mismo hueco que ANOVA: dice que alguien difiere, no quién.
Ese hueco lo llena la prueba t en el camino paramétrico. Del lado no paramétrico, la
equivalente se llama **Mann-Whitney**.

```
ANOVA            + prueba t        <- camino paramétrico
Kruskal-Wallis   + Mann-Whitney    <- el que se usó
```

Se compararon los 11 grupos con al menos 500 casos, o sea 55 pares. A cada p se le
aplicó **corrección de Bonferroni**: al hacer 55 pruebas a la vez el riesgo de un
falso positivo se acumula, así que se exige un corte más estricto.

Y se agregó una columna que la consigna no pedía: el **tamaño del efecto**, medido
con la delta de Cliff. Va de −1 a 1 y dice qué tan seguido un valor de un grupo
supera a uno del otro. Cero significa que están revueltos.

```
55 pares comparados
49 significativos
24 con efecto grande (|delta| > 0.33)
 9 significativos pero con efecto despreciable (|delta| < 0.10)
 6 no significativos
```

Los 24 con efecto grande, en palabras:

| diferencia | se denuncia antes | se denuncia después |
|---|---|---|
| 0.70 | HOMICIDIO DOLOSO (mediana 0) | VIOLACIÓN (mediana 7) |
| 0.64 | HOMICIDIO DOLOSO (0) | ROBO EN EL METRO (2) |
| 0.63 | LESIONES POR DISPARO (0) | VIOLACIÓN (7) |
| 0.61 | HECHO NO DELICTIVO (0) | VIOLACIÓN (7) |
| 0.59 | HOMICIDIO DOLOSO (0) | DELITO DE BAJO IMPACTO (2) |
| ... | | |
| 0.33 | HOMICIDIO DOLOSO (0) | ROBO A TRANSEÚNTE (1) |

Los 6 que **no** son distinguibles del azar:

| par | medianas | delta | p ajustada |
|---|---|---|---|
| ROBO EN MICROBÚS vs ROBO EN METRO | 1 y 2 | −0.086 | 0.090 |
| ROBO A NEGOCIO vs ROBO EN MICROBÚS | 1 y 1 | −0.072 | 0.251 |
| ROBO A NEGOCIO vs ROBO A REPARTIDOR | 1 y 1 | −0.068 | 0.126 |
| DELITO DE BAJO IMPACTO vs ROBO EN METRO | 2 y 2 | +0.047 | 0.138 |
| ROBO A NEGOCIO vs ROBO DE VEHÍCULO | 1 y 1 | +0.037 | 0.466 |
| ROBO EN MICROBÚS vs ROBO A REPARTIDOR | 1 y 1 | +0.011 | 1.000 |

Los 24 pares con efecto grande no están repartidos al azar. Casi todos tienen del
lado rápido a `HOMICIDIO DOLOSO`, `LESIONES POR DISPARO` o `HECHO NO DELICTIVO`, y
`VIOLACIÓN` aparece del lado lento en 9 de los 24.

Es la misma división que ya se había explicado en la Práctica 2, y ahora con
respaldo: los delitos que se denuncian el mismo día son los que llegan por reporte de
emergencia, donde la carpeta la abre la autoridad. La violación está en el otro
extremo porque la carpeta solo se abre si la víctima decide denunciar.

La diferencia más grande de las 55 es justo entre esos dos extremos: homicidio contra
violación, con delta de 0.70.

## 6. El p-value con 242 mil filas

Este par salió significativo:

```
HECHO NO DELICTIVO  vs  LESIONES POR DISPARO DE ARMA DE FUEGO

    mediana A      0
    mediana B      0          <- idénticas
    delta       -0.084        <- despreciable
    p ajustada   0.00008      <- "significativo"
```

Dos grupos con la misma mediana exacta, y la prueba dice que son distintos. `HECHO
NO DELICTIVO` tiene 5,101 casos y `LESIONES` 811.

Dos grupos con la misma mediana exacta salen "significativos". Pasa porque el p-value
contesta *"¿puede ser casualidad?"*, y entre más datos haya, menos cosas puede
explicar la casualidad. Con 5,101 y 811 casos, una diferencia minúscula pero real ya
se vuelve detectable.

La consecuencia es que con 242,370 filas el p-value deja de servir para decidir qué
importa:

```
p-value  ->  mide si la diferencia se puede DETECTAR
delta    ->  mide si la diferencia IMPORTA
```

Por eso se agregó la delta de Cliff, que la consigna no pedía. Reportar los 49 pares
significativos sería decir que hay 49 diferencias reales entre categorías, cuando 9
de ellas tienen efecto despreciable. El criterio que se usó para reportar fue
`|delta| > 0.33`, que deja 24.

## 7. Qué se ganó sobre la Práctica 2

En la Práctica 2 ya estaba la tabla de medianas por categoría y ya estaba la
explicación de por qué unas tardan más que otras. Aquí no salió ningún grupo nuevo.

La Práctica 2 ya tenía la tabla de medianas y ya tenía la explicación. Aquí no
apareció ningún grupo nuevo. Lo que agrega son dos cosas.

La primera es que las 24 diferencias grandes ya no son una lectura de la tabla: se
descartó que sean casualidad.

La segunda se olvida y vale igual. En la Práctica 2, las 16 medianas se veían como 16
valores distintos y todos parecían decir algo. Ahora se sabe que 6 pares no son
distinguibles del azar y que otros 9 tienen efecto despreciable. `ROBO A NEGOCIO` y
`ROBO A REPARTIDOR` eran dos renglones separados de la tabla; resultaron
indistinguibles.

O sea que la práctica confirmó lo que sí y descartó lo que no.
