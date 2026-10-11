import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

KS = [2, 3, 4, 5, 6, 7, 8, 10]
SEMILLA = 0
MUESTRA_SILUETA = 20_000      

# los tipos de delito que definen el perfil de una colonia
TIPOS = ["DELITO DE BAJO IMPACTO",
         "ROBO A TRANSEUNTE EN VÍA PÚBLICA CON Y SIN VIOLENCIA",
         "ROBO DE VEHÍCULO CON Y SIN VIOLENCIA",
         "ROBO A NEGOCIO CON VIOLENCIA",
         "VIOLACIÓN",
         "HOMICIDIO DOLOSO"]


def cargar():
    return pd.read_parquet(LIMPIO)


# --------------------------------------------------------------- los dos casos

def caso_denuncias(df):
    """Cada denuncia es un punto, ubicado por sus coordenadas."""
    d = df.dropna(subset=["latitud", "longitud"])
    return StandardScaler().fit_transform(d[["latitud", "longitud"]].values), d


def caso_colonias(df, minimo=30, proporciones=True):
    """Cada colonia es un punto, descrita por su mezcla de delitos.

    Con proporciones el tamano de la colonia se descuenta; con conteos no, y
    los grupos salen por tamano (lo que se vio en la Practica 5).
    """
    d = df.dropna(subset=["colonia", "alcaldia"])
    llave = ["alcaldia", "colonia"]        # el nombre solo no identifica
    m = pd.DataFrame({"total": d.groupby(llave, observed=True).size()})
    for t in TIPOS:
        m[t] = d[d.categoria_delito == t].groupby(llave, observed=True).size()
    m = m.fillna(0).query(f"total >= {minimo}")

    X = m[TIPOS].div(m.total, axis=0) if proporciones else m[TIPOS]
    return StandardScaler().fit_transform(X.values), m


# ------------------------------------------------------------------ evaluacion

def evaluar(X, ks=KS, semilla=SEMILLA, muestra=MUESTRA_SILUETA):
    """Para cada K: que tan apretados quedan los grupos, y que tan separados."""
    rng = np.random.default_rng(semilla)
    idx = (rng.choice(len(X), muestra, replace=False) if len(X) > muestra
           else np.arange(len(X)))
    filas = []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=semilla, n_init=10).fit(X)
        filas.append({"K": k,
                      "inercia": km.inertia_,
                      "silueta": silhouette_score(X[idx], km.labels_[idx]),
                      "grupo_mas_chico": np.bincount(km.labels_).min(),
                      "grupo_mas_grande": np.bincount(km.labels_).max()})
    return pd.DataFrame(filas)


def agrupar(X, k, semilla=SEMILLA):
    return KMeans(n_clusters=k, random_state=semilla, n_init=10).fit(X)


# -------------------------------------------------------------------- graficas

def grafica_codo(tablas):
    """Inercia y silueta contra K, para los dos casos."""
    SALIDA.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for col, (nombre, t) in enumerate(tablas.items()):
        axes[0, col].plot(t.K, t.inercia, marker="o", color="#3b6ea5")
        axes[0, col].set_title(f"{nombre}\nqué tan apretados (método del codo)",
                               fontsize=11)
        axes[0, col].set_ylabel("inercia")

        axes[1, col].plot(t.K, t.silueta, marker="o", color="#c0392b")
        axes[1, col].axhline(0.25, color="gray", linestyle="--", linewidth=1)
        axes[1, col].annotate("0.25: debajo de esto el corte es arbitrario",
                              (t.K.iloc[0], 0.25), xytext=(0, 5),
                              textcoords="offset points", fontsize=8, color="gray")
        axes[1, col].set_title("qué tan separados (silueta)", fontsize=11)
        axes[1, col].set_ylabel("silueta")
        axes[1, col].set_ylim(0, max(.6, t.silueta.max() * 1.2))

        for fila in (0, 1):
            axes[fila, col].set_xlabel("número de grupos (K)")
            axes[fila, col].grid(alpha=.25, linewidth=.5)
            axes[fila, col].set_axisbelow(True)

    ruta = SALIDA / "1-codo-y-silueta.png"
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)
    print(f"  {ruta.name}")


def grafica_mapa(X, d, k):
    """Los grupos del caso A dibujados sobre el mapa."""
    km = agrupar(X, k)
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.scatter(d.longitud, d.latitud, c=km.labels_, s=1, alpha=.05,
               cmap="tab10", linewidths=0)
    centros = StandardScaler().fit(d[["latitud", "longitud"]].values)
    cen = centros.inverse_transform(km.cluster_centers_)
    ax.scatter(cen[:, 1], cen[:, 0], c="black", s=120, marker="X", zorder=5)

    ax.set_title(f"Caso A: denuncias agrupadas por coordenadas (K = {k})\n"
                 "las X negras son los centros de cada grupo", fontsize=12, pad=12)
    ax.set_xlabel("longitud")
    ax.set_ylabel("latitud")
    ax.set_aspect("equal")
    ax.grid(alpha=.25, linewidth=.5)
    ax.set_axisbelow(True)

    ruta = SALIDA / "2-mapa-grupos.png"
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)
    print(f"  {ruta.name}")


def perfil_grupos(X, m, k):
    """Caso B: que distingue a cada grupo de colonias."""
    km = agrupar(X, k)
    t = m.copy()
    t["grupo"] = km.labels_
    props = t[TIPOS].div(t.total, axis=0) * 100
    props["grupo"] = km.labels_
    r = props.groupby("grupo").mean()
    r.insert(0, "colonias", t.groupby("grupo").size())
    r.insert(1, "denuncias_mediana", t.groupby("grupo").total.median())
    return r


# --------------------------------------------------------------------- reporte

def reporte(df):
    pd.set_option("display.width", 200, "display.max_columns", 20,
                  "display.float_format", lambda v: f"{v:,.3f}")

    Xa, da = caso_denuncias(df)
    Xb, mb = caso_colonias(df)
    print("=" * 76, "\n1. LOS DOS CASOS\n")
    print(f"  A) denuncias por coordenadas : {len(Xa):,} puntos, 2 variables")
    print(f"  B) colonias por perfil       : {len(Xb):,} puntos, {len(TIPOS)} variables")

    print("\n" + "=" * 76, "\n2. CUANTOS GRUPOS (codo y silueta)\n")
    tablas = {}
    for nombre, X in [("A) denuncias por coordenadas", Xa),
                      ("B) colonias por perfil", Xb)]:
        print(f"  --- {nombre} ---")
        t = evaluar(X)
        tablas[nombre] = t
        print(t.to_string(index=False).replace("\n", "\n  "))
        print(f"  mejor silueta: K = {t.loc[t.silueta.idxmax(), 'K']:.0f} "
              f"({t.silueta.max():.3f})\n")

    print("=" * 76, "\n3. COMPARACION DIRECTA DE LA SILUETA\n")
    comp = pd.DataFrame({n: t.set_index("K").silueta for n, t in tablas.items()})
    print(comp.to_string())

    print("\n" + "=" * 76, "\n4. CASO B: QUE DISTINGUE A CADA GRUPO\n")
    kb = int(tablas["B) colonias por perfil"].loc[
        tablas["B) colonias por perfil"].silueta.idxmax(), "K"])
    print(f"  con K = {kb} (el de mejor silueta), % promedio de cada tipo por grupo:\n")
    print(perfil_grupos(Xb, mb, kb).to_string())

    print("\n" + "=" * 76, "\n5. CONTROL: LO MISMO CON CONTEOS EN VEZ DE PROPORCIONES\n")
    Xc, mc = caso_colonias(df, proporciones=False)
    tc = evaluar(Xc)
    print(tc.to_string(index=False).replace("\n", "\n  "))
    kc = int(tc.loc[tc.silueta.idxmax(), "K"])
    print(f"\n  con K = {kc}, mediana de denuncias totales por grupo:")
    p = perfil_grupos(Xc, mc, kc)
    print(p[["colonias", "denuncias_mediana"]].to_string())

    print("\n" + "=" * 76, "\n6. GRAFICAS\n")
    grafica_codo(tablas)
    ka = int(tablas["A) denuncias por coordenadas"].loc[
        tablas["A) denuncias por coordenadas"].silueta.idxmax(), "K"])
    grafica_mapa(Xa, da, ka)


def demo():
    """Casos donde ya se sabe la respuesta."""
    r = np.random.default_rng(0)

    # tres nubes bien separadas: la silueta debe ser alta y el mejor K debe ser 3
    nubes = np.vstack([r.normal(c, .3, (200, 2)) for c in [(0, 0), (8, 0), (0, 8)]])
    t = evaluar(nubes, ks=[2, 3, 4, 5])
    mejor = t.loc[t.silueta.idxmax(), "K"]
    assert mejor == 3, f"deberia ser 3, salio {mejor}"
    assert t.silueta.max() > .7, t.silueta.max()

    # ruido uniforme: no hay grupos, la silueta debe quedar baja
    ruido = r.uniform(0, 1, (1500, 2))
    assert evaluar(ruido, ks=[2, 3, 4, 5]).silueta.max() < .45

    # la inercia siempre baja al subir K
    assert t.inercia.is_monotonic_decreasing

    # caso_colonias: proporciones por fila no pasan de 1 antes de escalar
    d = pd.DataFrame({
        "alcaldia": ["A"] * 50 + ["B"] * 50,
        "colonia": ["Centro"] * 100,
        "categoria_delito": ([TIPOS[0]] * 40 + [TIPOS[1]] * 10) * 2,
    })
    X, m = caso_colonias(d, minimo=30)
    assert len(m) == 2, f"la llave compuesta deberia dar 2 colonias, dio {len(m)}"
    assert (m[TIPOS].sum(axis=1) <= m.total).all()
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte(cargar())
