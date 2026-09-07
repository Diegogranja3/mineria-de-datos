import sys
from pathlib import Path

import numpy as np
import pandas as pd

LIMPIO = Path(__file__).resolve().parent.parent / "Practica 1" / "carpetas_2023_limpio.parquet"

NUMERICAS = ["dias_para_denunciar", "hora_inicio", "latitud", "longitud"]
CATEGORICAS = ["categoria_delito", "delito", "competencia", "fiscalia",
               "agencia", "unidad_investigacion", "alcaldia", "colonia"]


def cargar():
    df = pd.read_parquet(LIMPIO)
    df["hora_inicio"] = df.ts_inicio.dt.hour + df.ts_inicio.dt.minute / 60
    return df


# (columnas determinantes, columna dependiente) para las pruebas de dependencia
PRUEBAS = [
    (["colonia"], "alcaldia"),
    (["alcaldia"], "municipio_hecho"),
    (["alcaldia", "colonia"], "municipio_hecho"),
    (["delito"], "competencia"),
    (["delito"], "categoria_delito"),
]


# ------------------------------------------------------------ punto 1
def describir_numericas(df, cols=NUMERICAS):
    filas = {}
    for c in cols:
        s = df[c].dropna()
        q1, q2, q3 = s.quantile([.25, .5, .75])
        filas[c] = {
            "n": len(s), "nulos": df[c].isna().sum(),
            "media": s.mean(), "mediana": q2, "moda": s.mode().iloc[0],
            "min": s.min(), "max": s.max(), "rango": s.max() - s.min(),
            "Q1": q1, "Q3": q3, "IQR": q3 - q1,
            "var": s.var(), "std": s.std(), "CV%": s.std() / s.mean() * 100,
            "sesgo": s.skew(), "curtosis": s.kurt(),
            # regla de Tukey: fuera de Q1-1.5*IQR y Q3+1.5*IQR
            "fuera_Tukey%": (~s.between(q1 - 1.5 * (q3 - q1),
                                        q3 + 1.5 * (q3 - q1))).mean() * 100,
        }
    return pd.DataFrame(filas).T


def describir_categoricas(df, cols=CATEGORICAS):
    filas = {}
    for c in cols:
        s = df[c].dropna()
        f = s.value_counts()
        p = f / len(s)
        filas[c] = {
            "n": len(s), "nulos": df[c].isna().sum(), "unicos": len(f),
            "moda": f.index[0], "f_moda": f.iloc[0], "%moda": p.iloc[0] * 100,
            "%top5": p.head(5).sum() * 100,
            # entropia de Shannon dividida entre log2(k): 0 = todo en una
            # categoria, 1 = todas con la misma frecuencia
            "entropia_norm": -(p * np.log2(p)).sum() / np.log2(len(f)),
        }
    return pd.DataFrame(filas).T


# ------------------------------------------------- punto 2: entidades

def probar(df, determinantes, dependiente):
    """Cuenta cuantos valores distintos de `dependiente` tiene cada grupo."""
    sub = df.dropna(subset=determinantes + [dependiente])
    n = sub.groupby(determinantes, observed=True)[dependiente].nunique()
    return {
        "A": " + ".join(determinantes),
        "B": dependiente,
        "grupos": len(n),
        "con_1": int((n == 1).sum()),
        "con_mas_de_1": int((n > 1).sum()),
        "max": int(n.max()),
        "%cumple": round((n == 1).mean() * 100, 2),
    }


def cardinalidad(df, padre, hijo):
    """Cuantos hijos distintos tiene cada padre."""
    n = df.dropna(subset=[padre, hijo]).groupby(padre, observed=True)[hijo].nunique()
    return {"padre": padre, "hijo": hijo, "n_padres": len(n),
            "min": int(n.min()), "mediana": float(n.median()), "max": int(n.max())}

# ------------------------------------------------------------ punto 3: agrupados

def k_sturges(s):
    return int(np.ceil(1 + np.log2(len(s))))


def k_raiz(s):
    return int(np.ceil(np.sqrt(len(s))))


def k_freedman(s):
    iqr = s.quantile(.75) - s.quantile(.25)
    h = 2 * iqr / len(s) ** (1 / 3)
    return int(np.ceil((s.max() - s.min()) / h)) if h else np.nan


REGLAS = {"sturges": k_sturges, "raiz": k_raiz, "freedman": k_freedman}

# cortes a mano para dias_para_denunciar, en dias con sentido operativo
BORDES_DENUNCIA = [0, 1, 3, 7, 15, 30, 90, 365, 23991]


def tabla_frecuencias(s, k=None, bordes=None):
    """Tabla de clases: li, ls, marca de clase (x), amplitud (A), f, F, fr, Fr.

    Con `k`, k clases de igual amplitud sobre el rango. Con `bordes`, las clases
    que se le pasen, que pueden tener amplitudes distintas.
    """
    s = s.dropna().astype(float)
    if bordes is None:
        bordes = np.linspace(s.min(), s.max(), k + 1)
    bordes = np.asarray(bordes, dtype=float)
    s = s[s.between(bordes[0], bordes[-1])]

    t = (pd.cut(s, bins=bordes, include_lowest=True)
         .value_counts().sort_index().rename("f").to_frame().reset_index(drop=True))
    t["li"], t["ls"] = bordes[:-1], bordes[1:]
    t["x"] = (t.li + t.ls) / 2
    t["A"] = t.ls - t.li
    t["F"] = t.f.cumsum()
    t["fr"] = t.f / t.f.sum()
    t["Fr"] = t.fr.cumsum()
    return t[["li", "ls", "x", "A", "f", "F", "fr", "Fr"]]


def cuantil_agrupado(t, p):
    """Li + ((p*n - F_anterior) / f_clase) * A"""
    objetivo = p * t.f.sum()
    i = int((t.F >= objetivo).idxmax())
    f_ant = t.F.iloc[i - 1] if i > 0 else 0
    return t.li.iloc[i] + (objetivo - f_ant) / t.f.iloc[i] * t.A.iloc[i]


def moda_agrupada(t):
    """Czuber: Li + (d1 / (d1 + d2)) * A, con d1 y d2 las diferencias de
    frecuencia contra la clase anterior y la siguiente."""
    i = int(t.f.idxmax())
    d1 = t.f.iloc[i] - (t.f.iloc[i - 1] if i > 0 else 0)
    d2 = t.f.iloc[i] - (t.f.iloc[i + 1] if i < len(t) - 1 else 0)
    return t.li.iloc[i] + d1 / (d1 + d2) * t.A.iloc[i] if d1 + d2 else t.x.iloc[i]


def metricas_agrupadas(t):
    n = t.f.sum()
    media = (t.f * t.x).sum() / n                        # sum(f*x) / n
    var = (t.f * (t.x - media) ** 2).sum() / (n - 1)     # sum(f*(x-media)^2) / (n-1)
    return {"media": media, "mediana": cuantil_agrupado(t, .5),
            "moda": moda_agrupada(t), "var": var, "std": np.sqrt(var),
            "Q1": cuantil_agrupado(t, .25), "Q3": cuantil_agrupado(t, .75)}


def comparar(s, k=None, bordes=None):
    """Metricas calculadas desde la tabla vs. calculadas sobre los datos crudos."""
    s = s.dropna().astype(float)
    g = metricas_agrupadas(tabla_frecuencias(s, k, bordes))
    e = {"media": s.mean(), "mediana": s.median(), "moda": s.mode().iloc[0],
         "var": s.var(), "std": s.std(), "Q1": s.quantile(.25), "Q3": s.quantile(.75)}
    out = pd.DataFrame({"agrupada": {m: g[m] for m in e}, "exacta": e})
    out["error%"] = (out.agrupada - out.exacta).abs() / out.exacta.abs().replace(0, np.nan) * 100
    return out


# ------------------------------------------------------------ reporte

def reporte_entidades(df):
    print("=" * 70)
    print("DEPENDENCIAS FUNCIONALES")
    print("=" * 70)
    print(pd.DataFrame([probar(df, a, b) for a, b in PRUEBAS]).to_string(index=False))

    print("\n" + "=" * 70)
    print("CARDINALIDAD (cuantos hijos por padre)")
    print("=" * 70)
    print(pd.DataFrame([cardinalidad(df, "alcaldia", "colonia"),
                        cardinalidad(df, "categoria_delito", "delito"),
                        cardinalidad(df, "fiscalia", "agencia")]).to_string(index=False))

    print("\n" + "=" * 70)
    print("VALORES DE competencia")
    print("=" * 70)
    print(df.competencia.value_counts().to_string())

    print("\ncuantas competencias distintas tiene un mismo delito (ejemplos):")
    n = df.groupby("delito", observed=True)["competencia"].nunique()
    print(df[df.delito.isin(n[n > 1].index[:3])]
          .groupby(["delito", "competencia"], observed=True).size()
          .loc[lambda s: s > 0].to_string())

    print("\n" + "=" * 70)
    print("LLAVE PRIMARIA DE LA CARPETA")
    print("=" * 70)
    print(f"filas totales           : {len(df):,}")
    print(f"filas duplicadas exactas: {df.duplicated().sum():,}")
    print(f"ts_inicio repetidos     : {df.ts_inicio.duplicated().sum():,}")
    print("columnas que parezcan folio/id:",
          [c for c in df.columns if any(k in c.lower() for k in ("id", "folio", "num"))] or "ninguna")

    print("\n" + "=" * 70)
    print("PARES REALES vs NOMBRES SUELTOS")
    print("=" * 70)
    for cols in (["fiscalia", "agencia"], ["fiscalia", "unidad_investigacion"], ["alcaldia", "colonia"]):
        sueltos = df[cols[1]].nunique()
        pares = df.dropna(subset=cols).groupby(cols, observed=True).ngroups
        print(f"{cols[1]:22} nombres distintos: {sueltos:5,}   pares {tuple(cols)}: {pares:5,}")


def reporte(df):
    pd.set_option("display.width", 200, "display.max_columns", 30,
                  "display.float_format", lambda v: f"{v:,.4f}")

    print("=" * 78, "\n1. DESCRIPTIVOS NUMERICOS\n")
    print(describir_numericas(df).to_string())

    print("\n" + "=" * 78, "\n2. DESCRIPTIVOS CATEGORICOS\n")
    print(describir_categoricas(df).to_string())

    print("\n" + "=" * 78, "\n3. DEPENDENCIAS FUNCIONALES Y ENTIDADES\n")
    reporte_entidades(df)

    print("\n" + "=" * 78, "\n4. NUMERO DE CLASES SEGUN CADA REGLA\n")
    print(pd.DataFrame({c: {r: f(df[c].dropna()) for r, f in REGLAS.items()}
                        for c in NUMERICAS}).T.to_string())

    print("\n" + "=" * 78, "\n5. TABLA DE FRECUENCIAS Y METRICAS AGRUPADAS (k de Sturges)\n")
    for c in NUMERICAS:
        k = k_sturges(df[c].dropna())
        print(f"\n--- {c}   k = {k} ---")
        print(tabla_frecuencias(df[c], k).to_string(index=False))
        print("\nagrupadas vs exactas:")
        print(comparar(df[c], k).to_string())

    print("\n" + "=" * 78, "\n6. SENSIBILIDAD AL NUMERO DE CLASES\n")
    for c in NUMERICAS:
        s = df[c].dropna()
        filas = {k: {m: comparar(s, k).loc[m, "error%"] for m in ["media", "mediana", "std"]}
                 for k in [5, 10, k_sturges(s), 30, 60, 120]}
        print(f"error% en {c}:")
        print(pd.DataFrame(filas).T.rename_axis("k").to_string(), "\n")

    print("=" * 78, "\n7. VARIACION A: CLASES DE AMPLITUD DESIGUAL (dias_para_denunciar)\n")
    print(tabla_frecuencias(df.dias_para_denunciar, bordes=BORDES_DENUNCIA).to_string(index=False))
    print("\nagrupadas vs exactas:")
    print(comparar(df.dias_para_denunciar, bordes=BORDES_DENUNCIA).to_string())

    print("\n" + "=" * 78, "\n8. VARIACION B: ESCALA log10(1 + dias)\n")
    s = np.log10(1 + df.dias_para_denunciar.dropna())
    k = k_sturges(s)
    print(tabla_frecuencias(s, k).to_string(index=False))
    print(f"\nagrupadas vs exactas (k = {k}):")
    print(comparar(s, k).to_string())

    print("\n" + "=" * 78, "\n9. DESCRIPTIVOS POR GRUPO (dias_para_denunciar por categoria)\n")
    print(df.groupby("categoria_delito", observed=True)
          .agg(n=("dias_para_denunciar", "size"),
               media=("dias_para_denunciar", "mean"),
               mediana=("dias_para_denunciar", "median"),
               std=("dias_para_denunciar", "std"),
               p90=("dias_para_denunciar", lambda s: s.quantile(.9)))
          .sort_values("mediana", ascending=False).to_string())


def demo():
    """Verifica formulas y pruebas contra casos resueltos a mano."""
    t = pd.DataFrame({"li": [0., 10, 20, 30], "ls": [10., 20, 30, 40],
                      "x": [5., 15, 25, 35], "A": [10.] * 4,
                      "f": [4, 12, 16, 8], "F": [4, 16, 32, 40]})
    m = metricas_agrupadas(t)
    assert np.isclose(m["media"], 22.0)        # (4*5+12*15+16*25+8*35)/40 = 880/40
    assert np.isclose(m["mediana"], 22.5)      # 20 + ((20-16)/16)*10
    assert np.isclose(m["moda"], 23.3333)      # 20 + (4/(4+8))*10
    assert np.isclose(m["Q1"], 15.0)           # 10 + ((10-4)/12)*10
    assert np.isclose(m["Q3"], 28.75)          # 20 + ((30-16)/16)*10

    t2 = tabla_frecuencias(pd.Series(range(40)), 4)
    assert list(t2.f) == [10, 10, 10, 10] and t2.F.iloc[-1] == 40

    # clases de amplitud desigual
    t3 = tabla_frecuencias(pd.Series([1., 2, 3, 10, 20, 30, 100]), bordes=[0, 5, 50, 100])
    assert list(t3.f) == [3, 3, 1] and list(t3.A) == [5, 45, 50]
    assert np.isclose(cuantil_agrupado(t3, .5), 5 + (3.5 - 3) / 3 * 45)

    d = pd.DataFrame({
        "padre":  ["x", "x", "y", "y"],
        "cumple": [1, 1, 2, 2],      # cada padre con un solo valor
        "falla":  [1, 2, 3, 3],      # el padre x tiene dos
    })
    r = probar(d, ["padre"], "cumple")
    assert r["con_mas_de_1"] == 0 and r["%cumple"] == 100.0, r

    r = probar(d, ["padre"], "falla")
    assert r["con_mas_de_1"] == 1 and r["max"] == 2, r

    # la llave compuesta arregla lo que la simple no: (padre, cumple) -> falla
    r = probar(d, ["padre", "cumple"], "falla")
    assert r["grupos"] == 2, r

    c = cardinalidad(d, "padre", "cumple")
    assert c["n_padres"] == 2 and c["max"] == 1, c
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte(cargar())
