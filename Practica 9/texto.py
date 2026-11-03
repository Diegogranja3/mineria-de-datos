"""Practica 9 - Analisis de texto sobre la columna `delito`.

Dos formas de contar, a proposito:
  A) cada uno de los 286 delitos cuenta UNA vez   -> el vocabulario del catalogo
  B) las 242,392 denuncias, cada una con su texto -> lo que de verdad pasa

Es la misma tension de las practicas 5, 6 y 7: la frecuencia contra la
composicion.

La lista de palabras vacias es propia y no la generica de la libreria: en este
corpus CON y SIN distinguen delitos distintos ("ROBO A TRANSEUNTE EN VIA PUBLICA
CON VIOLENCIA" contra "... SIN VIOLENCIA"), asi que quitarlas borraria el
significado.

Uso:  python texto.py
      python texto.py --demo    comprueba las funciones con casos conocidos
"""
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

COLUMNA = "delito"

# conectores puros: aparecen en casi todas las etiquetas y no distinguen nada
VACIAS = {"de", "del", "la", "el", "los", "las", "en", "y", "o", "a", "al",
          "por", "para", "que", "su", "sus", "un", "una", "lo", "se"}

# se conservan a proposito, aunque una lista generica las quitaria:
#   con / sin   -> "con violencia" y "sin violencia" son delitos distintos
#   no          -> "hecho no delictivo"
#   contra      -> "delitos contra la salud"


def cargar():
    return pd.read_parquet(LIMPIO, columns=[COLUMNA]).dropna()


def normalizar(texto):
    """Minusculas y sin acentos, para que ROBO, Robo y róbo sean la misma palabra."""
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def palabras(texto, quitar_vacias=True):
    ws = re.findall(r"[a-zñ]+", normalizar(texto))
    return [w for w in ws if not (quitar_vacias and w in VACIAS)]


def contar(serie, por_denuncia, quitar_vacias=True):
    """A) por_denuncia=False: cada etiqueta distinta cuenta una vez.
       B) por_denuncia=True:  cada etiqueta cuenta tantas veces como aparece."""
    c = Counter()
    if por_denuncia:
        for etiqueta, n in serie.value_counts().items():
            for w in palabras(etiqueta, quitar_vacias):
                c[w] += n
    else:
        for etiqueta in serie.unique():
            c.update(palabras(etiqueta, quitar_vacias))
    return c


def bigramas(serie, por_denuncia, quitar_vacias=False):
    """Pares de palabras seguidas. Sin quitar vacias por defecto: 'con violencia'
    y 'arma de fuego' se rompen si se quitan los conectores."""
    c = Counter()
    fuente = (serie.value_counts().items() if por_denuncia
              else ((e, 1) for e in serie.unique()))
    for etiqueta, n in fuente:
        ws = palabras(etiqueta, quitar_vacias)
        for a, b in zip(ws, ws[1:]):
            c[f"{a} {b}"] += n
    return c


def cobertura(contador, objetivo=.80):
    """Cuantas palabras distintas hacen falta para cubrir el `objetivo` del texto."""
    total = sum(contador.values())
    acumulado = 0
    for i, (_, n) in enumerate(contador.most_common(), start=1):
        acumulado += n
        if acumulado >= total * objetivo:
            return i, len(contador), acumulado / total
    return len(contador), len(contador), 1.0


def longitudes(serie):
    distintas = pd.Series([len(palabras(e, False)) for e in serie.unique()])
    return {"etiquetas": len(distintas), "media": distintas.mean(),
            "mediana": distintas.median(), "min": distintas.min(),
            "max": distintas.max(),
            "de 1 palabra": int((distintas == 1).sum()),
            "de mas de 10": int((distintas > 10).sum())}


# -------------------------------------------------------------------- graficas

def nube(contador, titulo, archivo):
    SALIDA.mkdir(exist_ok=True)
    wc = WordCloud(width=1400, height=800, background_color="white",
                   colormap="tab10", random_state=0,
                   max_words=120, relative_scaling=.5
                   ).generate_from_frequencies(contador)
    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(titulo, fontsize=14, pad=14)
    fig.tight_layout()
    fig.savefig(SALIDA / archivo, dpi=110)
    plt.close(fig)
    print(f"  {archivo}")


def barras_comparadas(ca, cb, n=18):
    """Las mismas palabras, ordenadas por su peso en cada version."""
    SALIDA.mkdir(exist_ok=True)
    ta = sum(ca.values())
    tb = sum(cb.values())
    # un solo orden para los dos paneles: con el eje compartido cada panel no
    # puede tener el suyo, y ademas asi se comparan renglon a renglon
    top = [w for w, _ in cb.most_common(n)]
    orden = sorted(top, key=lambda w: ca[w] / ta)
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), sharey=True)
    for ax, c, total, titulo in [
            (axes[0], ca, ta, "A) el catálogo\ncada delito cuenta una vez"),
            (axes[1], cb, tb, "B) las denuncias\ncada delito cuenta lo que pesa")]:
        ax.barh(orden, [c[w] / total * 100 for w in orden], color="#3b6ea5")
        ax.set_title(titulo, fontsize=11)
        ax.set_xlabel("% de las palabras del corpus")
        ax.grid(alpha=.25, linewidth=.5, axis="x")
        ax.set_axisbelow(True)
    fig.suptitle("Las mismas palabras, pesadas de dos maneras", fontsize=13)
    fig.tight_layout()
    fig.savefig(SALIDA / "3-comparacion.png", dpi=120)
    plt.close(fig)
    print("  3-comparacion.png")


# --------------------------------------------------------------------- reporte

def reporte():
    pd.set_option("display.width", 150)
    df = cargar()
    s = df[COLUMNA].astype(str)

    print("=" * 74, "\n1. EL CORPUS\n")
    for k, v in longitudes(s).items():
        print(f"  {k:16} {v:,.2f}" if isinstance(v, float) else f"  {k:16} {v:,}")
    print(f"  denuncias        {len(s):,}")
    print("\n  las tres etiquetas mas largas:")
    for e in sorted(s.unique(), key=lambda x: -len(palabras(x, False)))[:3]:
        print(f"    ({len(palabras(e, False))} palabras) {e[:92]}...")

    ca = contar(s, por_denuncia=False)
    cb = contar(s, por_denuncia=True)

    print("\n" + "=" * 74, "\n2. PALABRAS MAS FRECUENTES, EN LAS DOS VERSIONES\n")
    t = pd.DataFrame({
        "A) catalogo": pd.Series(dict(ca.most_common(15))),
        "A) %": pd.Series({w: n / sum(ca.values()) * 100 for w, n in ca.most_common(15)}),
    }).join(pd.DataFrame({
        "B) denuncias": pd.Series(dict(cb.most_common(15))),
        "B) %": pd.Series({w: n / sum(cb.values()) * 100 for w, n in cb.most_common(15)}),
    }), how="outer").sort_values("B) denuncias", ascending=False)
    print(t.head(20).to_string(float_format=lambda v: f"{v:,.2f}"))

    print("\n  palabras que mandan en una version y no en la otra:")
    ra = {w: i for i, (w, _) in enumerate(ca.most_common(40), 1)}
    rb = {w: i for i, (w, _) in enumerate(cb.most_common(40), 1)}
    for w in sorted(set(ra) | set(rb)):
        a, b = ra.get(w), rb.get(w)
        if a and b and abs(a - b) >= 12:
            print(f"    {w:16} lugar {a:>2} en el catalogo, lugar {b:>2} en las denuncias")
        elif bool(a) != bool(b):
            donde = "solo en el catalogo" if a else "solo en las denuncias"
            print(f"    {w:16} {donde} (lugar {a or b})")

    print("\n" + "=" * 74, "\n3. BIGRAMAS (pares de palabras seguidas)\n")
    ba, bb = bigramas(s, False), bigramas(s, True)
    print("  en el catalogo:          en las denuncias:")
    for (pa, na), (pb, nb) in zip(ba.most_common(12), bb.most_common(12)):
        print(f"    {pa:26} {na:>4}    {pb:26} {nb:>9,}")

    print("\n" + "=" * 74, "\n4. COBERTURA DEL VOCABULARIO\n")
    for nombre, c in [("A) catalogo", ca), ("B) denuncias", cb)]:
        for obj in (.50, .80, .90):
            k, total, real = cobertura(c, obj)
            print(f"  {nombre:14} {k:>4} de {total} palabras cubren el {real * 100:.1f}% del texto")
        print()

    print("=" * 74, "\n5. GRAFICAS\n")
    nube(ca, "A) El vocabulario del catálogo: cada delito cuenta una vez",
         "1-nube-catalogo.png")
    nube(cb, "B) Lo que de verdad pasa: cada delito pesa según sus denuncias",
         "2-nube-denuncias.png")
    barras_comparadas(ca, cb)


def demo():
    """Casos donde ya se sabe la respuesta."""
    s = pd.Series(["ROBO A TRANSEUNTE CON VIOLENCIA"] * 100 +
                  ["ROBO A TRANSEUNTE SIN VIOLENCIA"] * 10 +
                  ["SECUESTRO"] * 1)

    # normalizar quita acentos y baja a minusculas
    assert normalizar("VÍA PÚBLICA Ñ") == "via publica n", normalizar("VÍA PÚBLICA Ñ")

    # las vacias se van, con y sin se quedan
    assert palabras("ROBO A TRANSEUNTE CON VIOLENCIA") == ["robo", "transeunte", "con", "violencia"]
    assert "a" not in palabras("ROBO A NEGOCIO")

    # A) el catalogo: 3 etiquetas distintas, cada una cuenta una vez
    ca = contar(s, por_denuncia=False)
    assert ca["secuestro"] == 1 and ca["con"] == 1 and ca["sin"] == 1
    assert ca["robo"] == 2, ca["robo"]        # aparece en dos etiquetas distintas

    # B) las denuncias: cada etiqueta pesa lo que aparece
    cb = contar(s, por_denuncia=True)
    assert cb["secuestro"] == 1 and cb["con"] == 100 and cb["sin"] == 10
    assert cb["robo"] == 110, cb["robo"]

    # la diferencia entre las dos versiones es justo lo que se quiere mostrar
    assert ca["con"] == ca["sin"] and cb["con"] != cb["sin"]

    # bigramas: conservan los conectores
    bb = bigramas(s, por_denuncia=True)
    assert bb["con violencia"] == 100 and bb["sin violencia"] == 10

    # cobertura: con una sola palabra dominante, pocas cubren mucho
    k, total, real = cobertura(cb, .50)
    assert k <= 3 and real >= .50, (k, real)

    # longitudes
    L = longitudes(s)
    assert L["etiquetas"] == 3 and L["min"] == 1 and L["max"] == 5
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte()
