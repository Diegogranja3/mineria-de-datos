import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

MINIMO = 30        # denuncias minimas para que una colonia entre al analisis

TIPOS = {
    "bajo_impacto": "DELITO DE BAJO IMPACTO",
    "transeunte": "ROBO A TRANSEUNTE EN VÍA PÚBLICA CON Y SIN VIOLENCIA",
    "vehiculo": "ROBO DE VEHÍCULO CON Y SIN VIOLENCIA",
}

# el modelo principal: una variable explica a la otra
X, Y = "vehiculo", "transeunte"


def por_colonia(df=None, minimo=MINIMO):
    """Una fila por colonia: total y conteo de cada tipo de delito."""
    if df is None:
        df = pd.read_parquet(LIMPIO)
    df = df.dropna(subset=["colonia", "alcaldia"])
    llave = ["alcaldia", "colonia"]      # el nombre solo no identifica (Practica 2)

    m = pd.DataFrame({"total": df.groupby(llave, observed=True).size()})
    for col, cat in TIPOS.items():
        m[col] = df[df.categoria_delito == cat].groupby(llave, observed=True).size()
    return m.fillna(0).query(f"total >= {minimo}")


def a_proporciones(m):
    """Cada conteo dividido entre el total de su colonia."""
    p = m[list(TIPOS)].div(m.total, axis=0)
    p["total"] = m.total
    return p


def ajustar(x, y):
    """Recta de minimos cuadrados. R2 es r al cuadrado en regresion simple."""
    r = stats.linregress(x, y)
    pred = r.intercept + r.slope * x
    residuos = y - pred
    return {"pendiente": r.slope, "interseccion": r.intercept,
            "r": r.rvalue, "R2": r.rvalue ** 2, "p": r.pvalue,
            "error_pendiente": r.stderr, "n": len(x),
            "residuo_medio": residuos.mean(), "residuo_std": residuos.std()}


def correlaciones(m):
    return m[list(TIPOS)].corr()


def sensibilidad(m, x=None, y=None):
    """Vuelve a ajustar quitando los puntos extremos, para ver de cuanto depende
    el R2 de un punado de colonias."""
    x, y = x or X, y or Y
    casos = [
        ("todas las colonias", m),
        (f"sin el top 1 de {x}", m.drop(m.nlargest(1, x).index)),
        (f"sin el top 3 de {x}", m.drop(m.nlargest(3, x).index)),
        (f"sin el top 1 de {y}", m.drop(m.nlargest(1, y).index)),
        ("sin el top 3 de ambos ejes",
         m.drop(m.nlargest(3, x).index.union(m.nlargest(3, y).index))),
    ]
    filas = []
    for etiqueta, d in casos:
        a = ajustar(d[x].values, d[y].values)
        filas.append({"caso": etiqueta, "n": a["n"], "R2": a["R2"],
                      "pendiente": a["pendiente"]})
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ graficas

def dibujar(m, p):
    SALIDA.mkdir(exist_ok=True)
    hechas = []
    for datos, etiqueta, archivo in [(m, "conteos", "1-conteos"),
                                     (p, "proporciones", "2-proporciones")]:
        x, y = datos[X].values, datos[Y].values
        a = ajustar(x, y)

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(x, y, s=10, alpha=.25, color="#3b6ea5", linewidths=0)
        linea = np.array([x.min(), x.max()])
        ax.plot(linea, a["interseccion"] + a["pendiente"] * linea,
                color="#c0392b", linewidth=2)

        ax.set_title(f"Robo a transeúnte contra robo de vehículo, por colonia "
                     f"({etiqueta})\nR² = {a['R2']:.3f}", fontsize=12, pad=12)
        ax.set_xlabel(f"robo de vehículo ({etiqueta})")
        ax.set_ylabel(f"robo a transeúnte ({etiqueta})")
        ax.grid(alpha=.25, linewidth=.5)
        ax.set_axisbelow(True)

        ruta = SALIDA / f"{archivo}.png"
        fig.tight_layout()
        fig.savefig(ruta, dpi=120)
        plt.close(fig)
        hechas.append(ruta)
        print(f"  {ruta.name}")
    return hechas


# ------------------------------------------------------------------- reporte

def reporte():
    pd.set_option("display.width", 160, "display.float_format", lambda v: f"{v:,.4f}")
    m = por_colonia()
    p = a_proporciones(m)

    print("=" * 74, f"\n1. LA UNIDAD DE ANALISIS: LA COLONIA (minimo {MINIMO} denuncias)\n")
    print(f"  colonias que entran: {len(m):,}")
    print(f"  denuncias cubiertas: {m.total.sum():,}")
    print(f"\n  reparto de cada tipo sobre el total general:")
    for c in TIPOS:
        print(f"    {c:14} {m[c].sum():>8,.0f}  ({m[c].sum()/m.total.sum()*100:5.2f}%)")

    print("\n" + "=" * 74, "\n2. CORRELACION ENTRE TIPOS\n")
    print("  conteos:")
    print(correlaciones(m).to_string().replace("\n", "\n  "))
    print("\n  proporciones:")
    print(correlaciones(p).to_string().replace("\n", "\n  "))

    print("\n" + "=" * 74, f"\n3. MODELO LINEAL: {Y} ~ {X}\n")
    for datos, etiqueta in [(m, "CONTEOS"), (p, "PROPORCIONES")]:
        print(f"  --- {etiqueta} ---")
        for k, v in ajustar(datos[X].values, datos[Y].values).items():
            print(f"    {k:16} {v:,.6g}")
        print()

    print("=" * 74, "\n4. SENSIBILIDAD A LOS PUNTOS EXTREMOS (conteos)\n")
    print(sensibilidad(m).to_string(index=False))
    print("\n  las colonias mas extremas de cada eje:")
    print(m.nlargest(3, X)[["total", X, Y]].to_string().replace("\n", "\n    "))
    print(m.nlargest(3, Y)[["total", X, Y]].to_string().replace("\n", "\n    "))

    print("\n" + "=" * 74, "\n5. GRAFICAS\n")
    dibujar(m, p)


def demo():
    x = np.arange(20, dtype=float)
    a = ajustar(x, 3 * x + 2)
    assert np.isclose(a["pendiente"], 3) and np.isclose(a["interseccion"], 2)
    assert np.isclose(a["R2"], 1)

    r = np.random.default_rng(0)
    assert ajustar(r.normal(size=2000), r.normal(size=2000))["R2"] < .01

    assert ajustar(x, -2 * x + 5)["pendiente"] < 0

    d = pd.DataFrame({
        "alcaldia": ["A"] * 40 + ["B"] * 40,
        "colonia": ["Centro"] * 80,
        "categoria_delito": ([TIPOS["transeunte"]] * 10 + [TIPOS["vehiculo"]] * 30) * 2,
    })
    m = por_colonia(d, minimo=30)
    assert len(m) == 2, f"deberian ser 2 colonias distintas, salieron {len(m)}"
    assert (m.transeunte == 10).all() and (m.vehiculo == 30).all()

    n = 60
    tabla = pd.DataFrame({"vehiculo": np.arange(n, dtype=float),
                          "transeunte": np.arange(n, dtype=float)})
    tabla.loc[n - 1, "transeunte"] = 500          
    s = sensibilidad(tabla)
    assert len(s) == 5
    r2_todas = s.loc[s.caso == "todas las colonias", "R2"].iloc[0]
    r2_sin = s.loc[s.caso == "sin el top 1 de transeunte", "R2"].iloc[0]
    assert r2_sin > r2_todas, (r2_todas, r2_sin)
    assert np.isclose(r2_sin, 1)

    p = a_proporciones(m)
    assert (p[list(TIPOS)].sum(axis=1) <= 1 + 1e-9).all()
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte()
