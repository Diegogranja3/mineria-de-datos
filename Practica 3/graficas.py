import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # sin ventana: escribe archivos y ya
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

# ---------------------------------------------------------------- que graficar
# Cada entrada es una grafica. `tipo` decide como se dibuja; el resto son los
# datos que ese tipo necesita.
GRAFICAS = [
    {"archivo": "1-histograma", "tipo": "histograma",
     "x": "dias_para_denunciar", "log": False,
     "titulo": "¿Cuántos días tarda la gente en denunciar?",
     "etiqueta_x": "días entre el delito y la denuncia"},

    {"archivo": "2-histograma-log", "tipo": "histograma",
     "x": "dias_para_denunciar", "log": True,
     "titulo": "¿Cuántos días tarda la gente en denunciar? (escala logarítmica)",
     "etiqueta_x": "días entre el delito y la denuncia"},

    {"archivo": "3-barras", "tipo": "barras",
     "x": "categoria_delito",
     "titulo": "¿Cuál es la categoría de denuncia más repetida?",
     "etiqueta_x": "denuncias"},

    {"archivo": "4-dispersion", "tipo": "dispersion",
     "x": "longitud", "y": "latitud",
     "titulo": "¿Qué tan cerca están unos delitos de otros?",
     "etiqueta_x": "longitud", "etiqueta_y": "latitud"},

    {"archivo": "5-linea", "tipo": "linea",
     "x": "hora_inicio",
     "titulo": "¿A qué hora se abren las carpetas?",
     "etiqueta_x": "hora del día", "etiqueta_y": "denuncias"},

    {"archivo": "6-caja", "tipo": "caja",
     "x": "dias_para_denunciar", "y": "categoria_delito",
     "titulo": "Rezago de denuncia por categoría",
     "etiqueta_x": "días entre el delito y la denuncia"},
]


def cargar():
    df = pd.read_parquet(LIMPIO)
    df["hora_inicio"] = df.ts_inicio.dt.hour + df.ts_inicio.dt.minute / 60
    return df


# ------------------------------------------------------------------ como dibujar

def dibujar(ax, df, g):
    """Un solo lugar donde se decide que funcion de matplotlib usar."""
    tipo = g["tipo"]

    if tipo == "histograma":
        s = df[g["x"]].dropna()
        if g.get("log"):
            # log10(1+x) porque hay denuncias con 0 dias y log(0) no existe
            ax.hist(np.log10(1 + s), bins=40, color="#3b6ea5")
            ax.set_xlabel("log10(1 + días)")
        else:
            ax.hist(s, bins=40, color="#3b6ea5")

    elif tipo == "barras":
        conteo = df[g["x"]].value_counts().sort_values()
        etiquetas = [str(k)[:38] for k in conteo.index]
        ax.barh(etiquetas, conteo.values, color="#3b6ea5")
        # doce de las dieciseis barras son tan chicas que no se ven: el numero
        # al final es lo unico que las hace legibles
        for y, n in enumerate(conteo.values):
            ax.annotate(f"{n:,}", (n, y), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=9)
        ax.set_xlim(right=conteo.max() * 1.18)   # espacio para el numero

    elif tipo == "dispersion":
        d = df.dropna(subset=[g["x"], g["y"]])
        # 228 mil puntos en negro solido serian una mancha: con alpha bajo, la
        # densidad se ve como sombreado
        ax.scatter(d[g["x"]], d[g["y"]], s=1, alpha=0.01,
                   color="#3b6ea5", linewidths=0)
        ax.set_aspect("equal")

    elif tipo == "linea":
        por_hora = df[g["x"]].dropna().astype(int).value_counts().sort_index()
        ax.plot(por_hora.index, por_hora.values, color="#3b6ea5", marker="o", ms=3)
        ax.set_xticks(range(0, 24, 2))
        ax.set_ylim(bottom=0)

    elif tipo == "caja":
        d = df.dropna(subset=[g["x"], g["y"]])
        grupos = d.groupby(g["y"], observed=True)[g["x"]]
        # ordenadas por mediana para que se lea de menor a mayor rezago
        orden = grupos.median().sort_values().index
        ax.boxplot([grupos.get_group(k).values for k in orden],
                   tick_labels=[str(k)[:38] for k in orden],
                   orientation="horizontal")
        # sin esto el eje se estira hasta 23,991 dias por los atipicos y las
        # cajas quedan aplastadas en un pixel. En log se ven las cajas Y la cola
        ax.set_xscale("symlog")     # symlog y no log, porque hay valores en 0
        ax.set_xticks([0, 1, 10, 100, 1000, 10000])
        ax.set_xticklabels(["0", "1", "10", "100", "1,000", "10,000"])

    else:
        raise ValueError(f"tipo desconocido: {tipo}")


def generar(df, graficas=GRAFICAS, carpeta=SALIDA):
    """El ciclo. Lo que se repite en todas las graficas se escribe una sola vez."""
    carpeta.mkdir(exist_ok=True)
    hechas = []

    for g in graficas:
        alto = 6 if g["tipo"] not in ("barras", "caja") else 7
        fig, ax = plt.subplots(figsize=(10, alto))

        dibujar(ax, df, g)

        ax.set_title(g["titulo"], fontsize=13, pad=12)
        if "etiqueta_x" in g and not ax.get_xlabel():
            ax.set_xlabel(g["etiqueta_x"])
        if "etiqueta_y" in g:
            ax.set_ylabel(g["etiqueta_y"])
        ax.grid(alpha=.25, linewidth=.5)
        ax.set_axisbelow(True)

        ruta = carpeta / f"{g['archivo']}.png"
        fig.tight_layout()
        fig.savefig(ruta, dpi=120)
        plt.close(fig)

        hechas.append(ruta)
        print(f"  {ruta.name}")

    return hechas


def demo():
    """Comprueba que cada tipo de la lista se dibuja sin reventar."""
    n = 300
    r = np.random.default_rng(0)
    d = pd.DataFrame({
        "dias_para_denunciar": r.integers(0, 400, n).astype(float),
        "hora_inicio": r.uniform(0, 24, n),
        "latitud": r.uniform(19.2, 19.5, n),
        "longitud": r.uniform(-99.3, -99.0, n),
        "categoria_delito": r.choice(["ROBO", "FRAUDE", "OTRO"], n),
    })

    tmp = AQUI / "_demo"
    hechas = generar(d, carpeta=tmp)
    assert len(hechas) == len(GRAFICAS), len(hechas)
    assert all(p.exists() and p.stat().st_size > 0 for p in hechas)

    tipos = {g["tipo"] for g in GRAFICAS}
    assert len(tipos) >= 5, f"solo {len(tipos)} tipos distintos: {tipos}"

    try:
        dibujar(plt.subplots()[1], d, {"tipo": "inventado"})
        raise AssertionError("un tipo desconocido deberia reventar")
    except ValueError:
        pass
    plt.close("all")

    for p in hechas:
        p.unlink()
    tmp.rmdir()
    print(f"demo OK  ({len(hechas)} gráficas, {len(tipos)} tipos distintos)")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(f"escribiendo en {SALIDA.name}/")
        generar(cargar())
