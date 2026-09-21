import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"

X = "dias_para_denunciar"      # la variable numerica
Y = "categoria_delito"         # los grupos
ALFA = 0.05                    # el corte convencional


def cargar():
    df = pd.read_parquet(LIMPIO).dropna(subset=[X, Y])
    return df


def grupos_de(df, x=X, y=Y):
    """Lista de arrays, uno por categoria, ordenados por mediana."""
    g = df.groupby(y, observed=True)[x]
    orden = g.median().sort_values().index
    return {str(k): g.get_group(k).values for k in orden}


# ------------------------------------------------------------ 1. normalidad

def probar_normalidad(grupos):
    """D'Agostino-Pearson: usa sesgo y curtosis, y aguanta muestras grandes.

    Shapiro-Wilk seria la otra opcion pero solo sirve hasta 5,000 datos.
    """
    filas = []
    for nombre, v in grupos.items():
        est, p = stats.normaltest(v)
        filas.append({"grupo": nombre[:38], "n": len(v),
                      "sesgo": stats.skew(v), "curtosis": stats.kurtosis(v),
                      "estadistico": est, "p": p,
                      "¿normal?": "si" if p > ALFA else "no"})
    return pd.DataFrame(filas)


# ------------------------------------------- 2. ANOVA (para mostrar que falla)

def anova(grupos):
    """Se corre a proposito aunque sus supuestos no se cumplan, para comparar.

    ANOVA supone normalidad en cada grupo e igual varianza entre grupos. La
    prueba de Levene revisa el segundo supuesto.
    """
    est, p = stats.f_oneway(*grupos.values())
    lev_est, lev_p = stats.levene(*grupos.values())
    return {"prueba": "ANOVA de una via", "estadistico_F": est, "p": p,
            "Levene (igual varianza)": lev_p,
            "¿varianzas iguales?": "si" if lev_p > ALFA else "no"}


# -------------------------------------------------------- 3. Kruskal-Wallis

def kruskal(grupos):
    est, p = stats.kruskal(*grupos.values())
    return {"prueba": "Kruskal-Wallis", "grupos": len(grupos),
            "n_total": sum(len(v) for v in grupos.values()),
            "estadistico_H": est, "p": p,
            "conclusion": "al menos un grupo difiere" if p < ALFA
                          else "no se puede descartar el azar"}


# ---------------------------------------------------------- 4. Mann-Whitney

def tamano_efecto(a, b):
    """Delta de Cliff: que tan seguido un valor de A supera a uno de B.

    Va de -1 a 1. Cero significa que estan revueltos por igual. Se calcula
    desde el estadistico U, sin comparar los pares uno por uno.
    """
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * u / (len(a) * len(b)) - 1


def por_pares(grupos, minimo=500):
    """Mann-Whitney en cada par. Es el equivalente no parametrico de la t."""
    usables = {k: v for k, v in grupos.items() if len(v) >= minimo}
    filas = []
    for a, b in combinations(usables, 2):
        va, vb = usables[a], usables[b]
        u, p = stats.mannwhitneyu(va, vb, alternative="two-sided")
        filas.append({"grupo A": a[:30], "grupo B": b[:30],
                      "mediana A": np.median(va), "mediana B": np.median(vb),
                      "U": u, "p": p, "delta": tamano_efecto(va, vb)})
    t = pd.DataFrame(filas)
    t["p_ajustada"] = (t.p * len(t)).clip(upper=1)
    t["significativo"] = t.p_ajustada < ALFA
    return t.sort_values("delta", key=abs, ascending=False)


# ------------------------------------------------------------------ reporte

def reporte(df):
    pd.set_option("display.width", 200, "display.max_columns", 20,
                  "display.float_format", lambda v: f"{v:,.4g}")
    grupos = grupos_de(df)

    print("=" * 78, f"\n1. ¿SON NORMALES? (D'Agostino-Pearson, alfa = {ALFA})\n")
    print(probar_normalidad(grupos).to_string(index=False))

    print("\n" + "=" * 78, "\n2. ANOVA, CORRIDA A PROPOSITO PESE A QUE NO APLICA\n")
    for k, v in anova(grupos).items():
        print(f"  {k:26} {v}")

    print("\n" + "=" * 78, "\n3. KRUSKAL-WALLIS SOBRE LAS 16 CATEGORIAS\n")
    for k, v in kruskal(grupos).items():
        print(f"  {k:16} {v}")

    print("\n" + "=" * 78, "\n4. MANN-WHITNEY POR PARES (grupos con n >= 500)\n")
    t = por_pares(grupos)
    print(f"  {len(t)} pares comparados\n")
    print(t.to_string(index=False))

    print("\n" + "=" * 78, "\n5. RESUMEN\n")
    print(f"  pares con p ajustada < {ALFA}:  {t.significativo.sum()} de {len(t)}")
    print(f"  |delta| < 0.10 (diferencia despreciable): {(t.delta.abs() < .10).sum()}")
    print(f"  |delta| > 0.33 (diferencia grande):       {(t.delta.abs() > .33).sum()}")
    print(f"\n  p mas grande de todas: {t.p.max():.3g}")
    print(f"  p mas chica de todas:  {t.p.min():.3g}")


def demo():
    """Casos donde ya se sabe la respuesta."""
    r = np.random.default_rng(0)

    # normalidad: una normal debe pasar, una con cola no
    normal = r.normal(0, 1, 3000)
    sesgada = r.exponential(1, 3000)
    assert stats.normaltest(normal).pvalue > ALFA
    assert stats.normaltest(sesgada).pvalue < ALFA

    # ANOVA sobre grupos identicos tampoco debe dar significativo
    assert anova({f"g{i}": r.normal(0, 1, 200) for i in range(3)})["p"] > ALFA

    # Kruskal-Wallis: tres grupos identicos no deben dar significativo
    iguales = {f"g{i}": r.normal(0, 1, 200) for i in range(3)}
    assert kruskal(iguales)["p"] > ALFA

    # y tres grupos claramente corridos, si
    distintos = {f"g{i}": r.normal(i * 5, 1, 200) for i in range(3)}
    assert kruskal(distintos)["p"] < ALFA

    # delta de Cliff: identicos dan ~0, separados dan ~1
    a = r.normal(0, 1, 500)
    assert abs(tamano_efecto(a, r.normal(0, 1, 500))) < .15
    assert tamano_efecto(r.normal(10, 1, 500), r.normal(0, 1, 500)) > .95

    # la tabla por pares: 3 grupos dan 3 combinaciones
    t = por_pares(distintos, minimo=10)
    assert len(t) == 3 and t.significativo.all()
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte(cargar())
