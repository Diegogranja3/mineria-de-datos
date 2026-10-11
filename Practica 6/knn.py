"""Practica 6 - Clasificacion con KNN.

Objetivo: predecir si una denuncia es de bajo impacto o del resto (dos clases,
88% contra 12%).

Variables de entrada: latitud, longitud, hora_inicio, dias_para_denunciar.
Se excluyen fiscalia, agencia y unidad_investigacion a proposito: sus nombres
contienen el tipo de delito ("FISCALIA DEL DELITO DE SECUESTRO"), asi que
usarlas seria fuga de informacion.

Uso:  python knn.py
      python knn.py --demo    comprueba las funciones con casos conocidos
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

AQUI = Path(__file__).resolve().parent
LIMPIO = AQUI.parent / "Practica 1" / "carpetas_2023_limpio.parquet"
SALIDA = AQUI / "graficas"

BASE = ["latitud", "longitud", "hora_inicio", "dias_para_denunciar"]
MAYORITARIA = "DELITO DE BAJO IMPACTO"
SEMILLA = 0


def cargar():
    df = pd.read_parquet(LIMPIO)
    df["hora_inicio"] = df.ts_inicio.dt.hour + df.ts_inicio.dt.minute / 60
    df["mes"] = df.ts_inicio.dt.month
    df["dia_semana"] = df.ts_inicio.dt.dayofweek
    return df


def preparar(df, columnas=BASE, con_alcaldia=False):
    """Devuelve X escalada e y binaria, partidas en entrenamiento y prueba.

    Escalar es obligatorio en KNN: sin eso, dias_para_denunciar (rango 23,991)
    aplastaria a latitud (rango 0.45) al calcular distancias.
    """
    necesarias = list(columnas) + (["alcaldia"] if con_alcaldia else [])
    d = df.dropna(subset=necesarias)

    partes = [d[list(columnas)].values]
    if con_alcaldia:
        partes.append(pd.get_dummies(d.alcaldia, dtype=float).values)

    X = StandardScaler().fit_transform(np.hstack(partes))
    y = (d.categoria_delito != MAYORITARIA).astype(int).values
    return train_test_split(X, y, test_size=.2, random_state=SEMILLA, stratify=y)


def balancear(Xtr, ytr, semilla=SEMILLA):
    """Recorta la clase mayoritaria al tamano de la minoritaria."""
    rng = np.random.default_rng(semilla)
    i0, i1 = np.where(ytr == 0)[0], np.where(ytr == 1)[0]
    chica, grande = (i1, i0) if len(i1) < len(i0) else (i0, i1)
    sel = np.concatenate([chica, rng.choice(grande, len(chica), replace=False)])
    return Xtr[sel], ytr[sel]


def medir(yte, pred):
    """Metricas de la clase minoritaria (1 = delito que no es de bajo impacto)."""
    p, r, f, _ = precision_recall_fscore_support(yte, pred, labels=[1], zero_division=0)
    cm = confusion_matrix(yte, pred, labels=[0, 1])
    return {"accuracy": (pred == yte).mean(), "precision": p[0], "recall": r[0],
            "F1": f[0], "graves_marcados": int(cm[1, 1]), "graves_reales": int(cm[1].sum()),
            "falsas_alarmas": int(cm[0, 1])}


def matriz(yte, pred):
    cm = confusion_matrix(yte, pred, labels=[0, 1])
    return pd.DataFrame(cm, index=["real: bajo impacto", "real: resto"],
                        columns=["predijo: bajo impacto", "predijo: resto"])


# ------------------------------------------------------------------ graficas

def curva_precision_recall(Xtr, ytr, Xte, yte, k=15):
    """Como se mueven precision y recall al bajar el umbral de decision."""
    m = KNeighborsClassifier(n_neighbors=k).fit(Xtr, ytr)
    prob = m.predict_proba(Xte)[:, 1]

    filas = []
    for votos in range(k, 0, -1):
        pred = (prob >= votos / k - 1e-9).astype(int)
        filas.append({"votos": votos, **medir(yte, pred)})
    t = pd.DataFrame(filas)

    SALIDA.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(t.recall, t.precision, marker="o", ms=5, color="#3b6ea5")
    for _, r in t.iterrows():
        if r.votos in (1, 2, 4, 8, k):
            ax.annotate(f"{int(r.votos)}/{k}", (r.recall, r.precision),
                        xytext=(6, 6), textcoords="offset points", fontsize=9)

    base = yte.mean()
    ax.axhline(base, color="#c0392b", linestyle="--", linewidth=1.5)
    ax.annotate(f"azar: {base:.3f}", (0.02, base), xytext=(0, 6),
                textcoords="offset points", color="#c0392b", fontsize=10)

    ax.set_title(f"Precisión contra recall al bajar el umbral (K = {k})\n"
                 "cada punto es «marcar como grave si al menos N de K vecinos lo son»",
                 fontsize=12, pad=12)
    ax.set_xlabel("recall: qué proporción de los delitos graves se alcanza a marcar")
    ax.set_ylabel("precisión: de los marcados, cuántos lo eran")
    ax.set_ylim(0, max(.35, t.precision.max() * 1.15))
    ax.grid(alpha=.25, linewidth=.5)
    ax.set_axisbelow(True)

    ruta = SALIDA / "1-precision-recall.png"
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)
    print(f"  {ruta.name}")
    return t


# ------------------------------------------------------------------- reporte

def reporte(df):
    pd.set_option("display.width", 170, "display.float_format", lambda v: f"{v:,.4f}")
    Xtr, Xte, ytr, yte = preparar(df)

    print("=" * 76, "\n1. LOS DATOS\n")
    print(f"  filas usables: {len(Xtr) + len(Xte):,}  "
          f"(se pierden {len(df) - len(Xtr) - len(Xte):,} por nulos en lat/lon)")
    print(f"  variables: {', '.join(BASE)}")
    print(f"  reparto:  bajo impacto {(1 - yte.mean()) * 100:.2f}%   "
          f"resto {yte.mean() * 100:.2f}%")

    print("\n" + "=" * 76, "\n2. EL MODELO TONTO (siempre contesta la clase mayoritaria)\n")
    tonto = medir(yte, np.zeros_like(yte))
    for k, v in tonto.items():
        print(f"  {k:18} {v:,.4f}" if isinstance(v, float) else f"  {k:18} {v:,}")

    print("\n" + "=" * 76, "\n3. KNN TAL CUAL (K = 15, sin balancear)\n")
    m = KNeighborsClassifier(n_neighbors=15).fit(Xtr, ytr)
    pred = m.predict(Xte)
    print(matriz(yte, pred).to_string().replace("\n", "\n  "))
    print()
    for k, v in medir(yte, pred).items():
        print(f"  {k:18} {v:,.4f}" if isinstance(v, float) else f"  {k:18} {v:,}")

    print("\n" + "=" * 76, "\n4. VARIACION B: ENTRENAR BALANCEADO\n")
    Xb, yb = balancear(Xtr, ytr)
    print(f"  entrenamiento recortado de {len(ytr):,} a {len(yb):,} filas "
          f"({(yb == 1).sum():,} de cada clase)\n")
    filas = []
    for k in [5, 15, 51, 101]:
        p = KNeighborsClassifier(n_neighbors=k).fit(Xb, yb).predict(Xte)
        filas.append({"K": k, **medir(yte, p)})
    print(pd.DataFrame(filas).to_string(index=False))

    print("\n" + "=" * 76, "\n5. VARIACION C: BAJAR EL UMBRAL DE DECISION\n")
    print("  (sin balancear; marcar grave si al menos N de 15 vecinos lo son)\n")
    t = curva_precision_recall(Xtr, ytr, Xte, yte)
    print()
    print(t[t.votos.isin([15, 8, 4, 2, 1])].to_string(index=False))

    print("\n" + "=" * 76, "\n6. VARIACION D: ¿AYUDAN MAS VARIABLES?\n")
    print("  (todas entrenadas balanceadas con K = 51)\n")
    conjuntos = [
        ("4 numericas (original)", BASE, False),
        ("+ mes y dia de semana", BASE + ["mes", "dia_semana"], False),
        ("+ alcaldia", BASE, True),
        ("todo junto", BASE + ["mes", "dia_semana"], True),
        ("solo dias_para_denunciar", ["dias_para_denunciar"], False),
        ("solo latitud y longitud", ["latitud", "longitud"], False),
    ]
    filas = []
    for nombre, cols, alc in conjuntos:
        a, b, c, d2 = preparar(df, cols, alc)
        Xb2, yb2 = balancear(a, c)
        p = KNeighborsClassifier(n_neighbors=51).fit(Xb2, yb2).predict(b)
        filas.append({"variables": nombre, **medir(d2, p)})
    print(pd.DataFrame(filas).to_string(index=False))


def demo():
    """Casos donde ya se sabe la respuesta."""
    # medir: una prediccion perfecta da 1 en todo
    y = np.array([0, 0, 1, 1])
    m = medir(y, y.copy())
    assert m["precision"] == 1 and m["recall"] == 1 and m["F1"] == 1

    # contestar siempre la mayoritaria: recall 0, accuracy = proporcion de ceros
    m = medir(y, np.zeros_like(y))
    assert m["recall"] == 0 and m["precision"] == 0 and m["accuracy"] == .5

    # la matriz de confusion cuadra con los conteos
    cm = matriz(np.array([0, 0, 0, 1]), np.array([0, 1, 0, 1])).values
    assert cm.tolist() == [[2, 1], [0, 1]], cm

    # balancear deja la misma cantidad de cada clase
    r = np.random.default_rng(0)
    X = r.normal(size=(1000, 3))
    ytr = np.array([0] * 900 + [1] * 100)
    Xb, yb = balancear(X, ytr)
    assert (yb == 0).sum() == (yb == 1).sum() == 100, np.bincount(yb)

    # KNN sobre dos nubes bien separadas tiene que acertar casi todo
    X = np.vstack([r.normal(0, .3, (300, 2)), r.normal(5, .3, (300, 2))])
    y = np.array([0] * 300 + [1] * 300)
    k = KNeighborsClassifier(n_neighbors=5).fit(X, y)
    assert medir(y, k.predict(X))["F1"] > .98
    print("demo OK")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else reporte(cargar())
