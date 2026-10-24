"""Practica 8 - Pronostico sobre la serie diaria de denuncias.

La serie son las denuncias por dia de 2023: 365 puntos sin huecos, gracias a que
en la Practica 1 se escogio fecha_inicio y no fecha_hecho.

El corte entrenamiento/prueba es CRONOLOGICO, no al azar como en la Practica 6:
partir al azar dejaria que el modelo vea el futuro para predecir el pasado.

  ene ---------------- sep | oct --- dic
  |---- 275 dias entrenar -|-- 90 probar --|

Uso:  python pronostico.py
      python pronostico.py --demo    comprueba las funciones con casos conocidos
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

DIAS_PRUEBA = 90
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def serie_diaria(df=None):
    """Denuncias por dia, con el indice como fecha."""
    if df is None:
        df = pd.read_parquet(LIMPIO)
    s = df.groupby(df.fecha_inicio.dt.date).size()
    s.index = pd.to_datetime(s.index)
    return s.sort_index().rename("denuncias")


def partir(s, dias_prueba=DIAS_PRUEBA):
    return s.iloc[:-dias_prueba], s.iloc[-dias_prueba:]


# ------------------------------------------------------------------ los modelos

def matriz_diseno(fechas, con_tendencia=True, con_dia=True, con_mes=False, origen=None):
    """Arma las columnas de la regresion a partir de las fechas.

    La tendencia se mide en dias desde `origen` para que entrenamiento y prueba
    usen la misma escala; si cada uno empezara en 0, la prueba estaria mal.
    """
    origen = origen if origen is not None else fechas.min()
    partes = [np.ones((len(fechas), 1))]                      # la constante
    if con_tendencia:
        partes.append(((fechas - origen).days.values).reshape(-1, 1).astype(float))
    if con_dia:
        # seis columnas, no siete: la septima seria redundante con la constante
        d = pd.get_dummies(fechas.dayofweek, dtype=float).reindex(
            columns=range(7), fill_value=0.0).values[:, 1:]
        partes.append(d)
    if con_mes:
        m = pd.get_dummies(fechas.month, dtype=float).reindex(
            columns=range(1, 13), fill_value=0.0).values[:, 1:]
        partes.append(m)
    return np.hstack(partes)


def regresion(entrena, prueba, **opciones):
    """Minimos cuadrados con numpy: no hace falta sklearn para esto."""
    origen = entrena.index.min()
    Xtr = matriz_diseno(entrena.index, origen=origen, **opciones)
    Xte = matriz_diseno(prueba.index, origen=origen, **opciones)
    coef, *_ = np.linalg.lstsq(Xtr, entrena.values, rcond=None)
    return pd.Series(Xte @ coef, index=prueba.index), coef


def naive_estacional(entrena, prueba, periodo=7):
    """Cada dia se predice con el mismo dia de la semana anterior.

    Para los dias de prueba mas alla del primer periodo se usa el ultimo valor
    observado de ese dia de la semana en el entrenamiento: en un pronostico real
    no se conocen los valores reales de la prueba.
    """
    ultimos = {}
    for fecha, v in entrena.items():
        ultimos[fecha.dayofweek] = v
    return pd.Series([ultimos[f.dayofweek] for f in prueba.index], index=prueba.index)


def media_simple(entrena, prueba):
    return pd.Series(entrena.mean(), index=prueba.index)


# ------------------------------------------------------------------- evaluacion

def errores(real, pred):
    e = real.values - pred.values
    return {"MAE": np.abs(e).mean(),
            "MAPE%": (np.abs(e) / real.values).mean() * 100,
            "sesgo": e.mean(),          # positivo = el modelo se queda corto
            "peor_dia": np.abs(e).max()}


def comparar(entrena, prueba):
    modelos = {
        "0. la media de siempre": media_simple(entrena, prueba),
        "1. mismo dia semana pasada": naive_estacional(entrena, prueba),
        "2. tendencia": regresion(entrena, prueba, con_dia=False)[0],
        "3. tendencia + dia de semana": regresion(entrena, prueba)[0],
        "4. tendencia + dia + mes": regresion(entrena, prueba, con_mes=True)[0],
        "5. solo dia de semana": regresion(entrena, prueba, con_tendencia=False)[0],
    }
    t = pd.DataFrame({n: errores(prueba, p) for n, p in modelos.items()}).T
    return t.sort_values("MAE"), modelos


# -------------------------------------------------------------------- graficas

def graficar(s, entrena, prueba, modelos):
    SALIDA.mkdir(exist_ok=True)

    # 1) la serie completa con el corte y los dos mejores pronosticos
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(s.index, s.values, color="#999", linewidth=.8, label="real")
    ax.axvline(prueba.index[0], color="black", linestyle="--", linewidth=1.2)
    ax.annotate("aquí empieza la prueba", (prueba.index[0], s.max()),
                xytext=(6, -12), textcoords="offset points", fontsize=9)
    for nombre, color in [("3. tendencia + dia de semana", "#c0392b"),
                          ("1. mismo dia semana pasada", "#2980b9")]:
        ax.plot(modelos[nombre].index, modelos[nombre].values, color=color,
                linewidth=1.4, label=nombre)
    ax.set_title("Denuncias por día en 2023, y el pronóstico de los últimos 90 días",
                 fontsize=13, pad=12)
    ax.set_ylabel("denuncias")
    ax.legend(fontsize=9)
    ax.grid(alpha=.25, linewidth=.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(SALIDA / "1-serie-y-pronostico.png", dpi=120)
    plt.close(fig)
    print("  1-serie-y-pronostico.png")

    # 2) el patron semanal, que es lo que domina
    fig, ax = plt.subplots(figsize=(9, 5))
    por_dia = s.groupby(s.index.dayofweek).mean()
    ax.bar([DIAS[i] for i in por_dia.index], por_dia.values, color="#3b6ea5")
    ax.axhline(s.mean(), color="#c0392b", linestyle="--", linewidth=1.5)
    ax.annotate(f"promedio general: {s.mean():.0f}", (6, s.mean()), xytext=(0, -16),
                textcoords="offset points", color="#c0392b", fontsize=9, ha="right")
    for i, v in enumerate(por_dia.values):
        ax.annotate(f"{v:.0f}", (i, v), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9)
    ax.set_title("Promedio de denuncias por día de la semana", fontsize=13, pad=12)
    ax.set_ylabel("denuncias")
    ax.grid(alpha=.25, linewidth=.5, axis="y")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(SALIDA / "2-patron-semanal.png", dpi=120)
    plt.close(fig)
    print("  2-patron-semanal.png")


# --------------------------------------------------------------------- reporte

def reporte():
    pd.set_option("display.width", 160, "display.float_format", lambda v: f"{v:,.2f}")
    s = serie_diaria()
    entrena, prueba = partir(s)

    print("=" * 74, "\n1. LA SERIE\n")
    print(f"  {len(s)} dias, del {s.index.min().date()} al {s.index.max().date()}, sin huecos")
    print(f"  media {s.mean():.1f}   mediana {s.median():.0f}   "
          f"min {s.min()} ({s.idxmin().date()})   max {s.max()} ({s.idxmax().date()})")
    print(f"\n  entrenamiento: {len(entrena)} dias "
          f"({entrena.index.min().date()} a {entrena.index.max().date()})")
    print(f"  prueba:        {len(prueba)} dias "
          f"({prueba.index.min().date()} a {prueba.index.max().date()})")
    print(f"\n  media del entrenamiento: {entrena.mean():.1f}")
    print(f"  media de la prueba:      {prueba.mean():.1f}  "
          f"({(prueba.mean() / entrena.mean() - 1) * 100:+.1f}%)")

    print("\n" + "=" * 74, "\n2. LA ESTRUCTURA DE LA SERIE\n")
    print("  promedio por dia de la semana:")
    for i, v in s.groupby(s.index.dayofweek).mean().items():
        print(f"    {DIAS[i]:10} {v:7.1f}")
    print(f"\n  diferencia entre el mas alto y el mas bajo: "
          f"{s.groupby(s.index.dayofweek).mean().max() - s.groupby(s.index.dayofweek).mean().min():.0f}")
    print("\n  promedio por mes:")
    pm = s.groupby(s.index.month).mean()
    print("   ", "  ".join(f"{m}:{v:.0f}" for m, v in pm.items()))
    print(f"  diferencia entre el mes mas alto y el mas bajo: {pm.max() - pm.min():.0f}")

    print("\n" + "=" * 74, f"\n3. LOS MODELOS, EVALUADOS EN LOS {DIAS_PRUEBA} DIAS APARTADOS\n")
    t, modelos = comparar(entrena, prueba)
    print(t.to_string())
    print(f"\n  MAE del modelo 0 (la media): {t.loc['0. la media de siempre', 'MAE']:.1f} denuncias")
    print(f"  mejor modelo: {t.index[0]} con MAE {t.MAE.iloc[0]:.1f}")
    print(f"  mejora sobre la media: "
          f"{(1 - t.MAE.iloc[0] / t.loc['0. la media de siempre', 'MAE']) * 100:.1f}%")

    print("\n" + "=" * 74, "\n4. QUE DICE LA REGRESION COMPLETA\n")
    _, coef = regresion(entrena, prueba, con_mes=True)
    print(f"  constante (lunes de enero):      {coef[0]:8.1f}")
    print(f"  tendencia (cambio por dia):      {coef[1]:8.3f}  "
          f"-> {coef[1] * 365:+.0f} denuncias en un ano")
    print("\n  ajuste por dia de la semana (contra lunes):")
    for i, c in enumerate(coef[2:8], start=1):
        print(f"    {DIAS[i]:10} {c:+8.1f}")

    print("\n" + "=" * 74, "\n5. GRAFICAS\n")
    graficar(s, entrena, prueba, modelos)


def demo():
    """Casos donde ya se sabe la respuesta."""
    fechas = pd.date_range("2023-01-01", periods=120)

    # una recta perfecta: la regresion con tendencia debe clavarla
    recta = pd.Series(100 + 2 * np.arange(120, dtype=float), index=fechas)
    e, p = partir(recta, dias_prueba=30)
    pred, coef = regresion(e, p, con_dia=False)
    assert np.allclose(pred.values, p.values), pred.values[:3]
    assert np.isclose(coef[1], 2), coef[1]

    # patron semanal puro: el naive estacional debe acertar exacto
    semanal = pd.Series([500 + 100 * (f.dayofweek < 5) for f in fechas],
                        index=fechas, dtype=float)
    e, p = partir(semanal, dias_prueba=30)
    assert errores(p, naive_estacional(e, p))["MAE"] == 0

    # y la regresion con dia de semana tambien
    assert errores(p, regresion(e, p)[0])["MAE"] < 1e-6

    # la media sola NO debe acertar en una serie con patron
    assert errores(p, media_simple(e, p))["MAE"] > 10

    # el corte es cronologico: la prueba va despues del entrenamiento
    e, p = partir(recta, dias_prueba=30)
    assert e.index.max() < p.index.min()
    assert len(e) == 90 and len(p) == 30

    # el sesgo detecta quedarse corto
    real = pd.Series([100.0] * 10, index=fechas[:10])
    assert errores(real, pd.Series([90.0] * 10, index=fechas[:10]))["sesgo"] == 10
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte()
