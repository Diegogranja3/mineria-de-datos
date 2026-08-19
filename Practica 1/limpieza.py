import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
CRUDO = DATA / "carpetasFGJ_2023.csv.gz"
LIMPIO = Path(__file__).resolve().parent / "carpetas_2023_limpio.parquet"

ALCALDIAS = {
    "ALVARO OBREGON": "Alvaro Obregon",
    "AZCAPOTZALCO": "Azcapotzalco",
    "BENITO JUAREZ": "Benito Juarez",
    "COYOACAN": "Coyoacan",
    "CUAJIMALPA DE MORELOS": "Cuajimalpa de Morelos",
    "CUAUHTEMOC": "Cuauhtemoc",
    "GUSTAVO A. MADERO": "Gustavo A. Madero",
    "IZTACALCO": "Iztacalco",
    "IZTAPALAPA": "Iztapalapa",
    "LA MAGDALENA CONTRERAS": "La Magdalena Contreras",
    "MIGUEL HIDALGO": "Miguel Hidalgo",
    "MILPA ALTA": "Milpa Alta",
    "TLAHUAC": "Tlahuac",
    "TLALPAN": "Tlalpan",
    "VENUSTIANO CARRANZA": "Venustiano Carranza",
    "XOCHIMILCO": "Xochimilco",
    "CDMX (indeterminada)": None,
    "FUERA DE CDMX": None,
}

CATEGORICAS = ["delito", "categoria_delito", "competencia", "fiscalia", "agencia",
               "unidad_investigacion", "alcaldia", "colonia", "municipio_hecho"]

BANDERAS = ["sin_coordenadas", "alcaldia_indeterminada", "fuera_cdmx",
            "hora_hecho_estimada", "hecho_posterior_a_inicio"]

SALIDA = ["ts_inicio", "fecha_inicio", "ts_hecho", "fecha_hecho",
          "dias_para_denunciar", "delito", "categoria_delito", "competencia",
          "fiscalia", "agencia", "unidad_investigacion", "alcaldia", "colonia",
          "municipio_hecho", "latitud", "longitud", "alcaldia_hecho",
          "colonia_hecho"] + BANDERAS


def limpiar(df):
    df = df.drop_duplicates()

    for c in df.select_dtypes(include=["object", "str"]).columns:
        df[c] = (df[c].astype("string").str.strip()
                 .str.replace(r"\s+", " ", regex=True).replace("", None))

    for c in ["fecha_inicio", "fecha_hecho"]:
        df[c] = pd.to_datetime(df[c], format="%Y-%m-%d", errors="coerce")
    for c in ["hora_inicio", "hora_hecho"]:
        df[c] = pd.to_timedelta(df[c], errors="coerce")

    df["ts_inicio"] = df.fecha_inicio + df.hora_inicio
    df["ts_hecho"] = df.fecha_hecho + df.hora_hecho
    df["dias_para_denunciar"] = (df.fecha_inicio - df.fecha_hecho).dt.days

    df["alcaldia"] = df.alcaldia_hecho.map(ALCALDIAS).astype("string")
    df["colonia"] = df.colonia_catalogo.fillna(df.colonia_hecho.str.title())

    fuera = ~(df.latitud.between(19.0, 19.7) & df.longitud.between(-99.4, -98.9))
    df.loc[fuera, ["latitud", "longitud"]] = pd.NA

    df["sin_coordenadas"] = df.latitud.isna()
    df["alcaldia_indeterminada"] = df.alcaldia_hecho.eq("CDMX (indeterminada)").fillna(False)
    df["fuera_cdmx"] = df.municipio_hecho.notna() & df.municipio_hecho.ne("CDMX")
    # el 12:00 en punto no es un pico de delitos, es lo que se captura cuando nadie recuerda la ora
    df["hora_hecho_estimada"] = df.hora_hecho.eq(pd.Timedelta(hours=12))
    df["hecho_posterior_a_inicio"] = (df.ts_hecho > df.ts_inicio).fillna(False)

    for c in CATEGORICAS:
        df[c] = df[c].astype("category")

    return df[SALIDA]


def reporte(crudo, df):
    print(f"filas {len(crudo):,} -> {len(df):,}"
          f"   columnas {crudo.shape[1]} -> {df.shape[1]}")
    print(f"duplicados exactos {crudo.duplicated().sum()}")

    print("\ncategorias que se fusionaron al quitar espacios:")
    for c in ["fiscalia", "unidad_investigacion", "colonia_hecho", "delito"]:
        antes, ahora = crudo[c].nunique(), df[c].nunique()
        if antes != ahora:
            print(f"  {c}: {antes} -> {ahora}")

    print("\nbanderas de calidad:")
    for c in BANDERAS:
        print(f"  {c}: {df[c].sum():,} ({df[c].mean() * 100:.2f}%)")

    print(f"\ndenuncias el mismo dia del hecho: "
          f"{(df.dias_para_denunciar == 0).mean() * 100:.2f}%")
    print(f"con mas de un anio de rezago: {(df.dias_para_denunciar > 365).sum():,}")

    print("\nnulos que quedan:")
    print(df.isna().sum().loc[lambda s: s > 0].to_string())


def demo():
    d = pd.DataFrame({
        "anio_inicio": [2023] * 3, "mes_inicio": ["Enero"] * 3,
        "fecha_inicio": ["2023-01-05"] * 3, "hora_inicio": ["10:00:00"] * 3,
        "anio_hecho": [2023.0, 2020.0, None], "mes_hecho": ["Enero", "Mayo", None],
        "fecha_hecho": ["2023-01-05", "2020-05-01", None],
        "hora_hecho": ["12:00:00", "08:30:00", None],
        "delito": ["ROBO  SIMPLE", "ROBO SIMPLE", "OTRO"],
        "categoria_delito": ["DELITO DE BAJO IMPACTO"] * 3,
        "competencia": ["FUERO COMUN"] * 3,
        "fiscalia": [" FISCALIA A ", "FISCALIA A", "FISCALIA B"],
        "agencia": ["A-1"] * 3, "unidad_investigacion": ["UI-1"] * 3,
        "colonia_hecho": ["CENTRO", "DEL VALLE", None],
        "colonia_catalogo": [None, "Del Valle", None],
        "alcaldia_hecho": ["CUAUHTEMOC", "BENITO JUAREZ", "FUERA DE CDMX"],
        "alcaldia_catalogo": [None, "Benito Juarez", None],
        "municipio_hecho": ["CDMX", "CDMX", "TOLUCA"],
        "latitud": [19.43, 0.0, None], "longitud": [-99.13, 0.0, None],
    })
    out = limpiar(d)
    assert out.delito.nunique() == 2 and out.fiscalia.nunique() == 2
    assert out.alcaldia.tolist()[:2] == ["Cuauhtemoc", "Benito Juarez"]
    assert pd.isna(out.alcaldia.iloc[2])
    assert out.colonia.tolist()[:2] == ["Centro", "Del Valle"]
    assert out.sin_coordenadas.tolist() == [False, True, True]
    assert out.hora_hecho_estimada.tolist() == [True, False, False]
    assert out.hecho_posterior_a_inicio.tolist() == [True, False, False]
    assert out.alcaldia_indeterminada.tolist() == [False, False, False]
    assert out.fuera_cdmx.tolist() == [False, False, True]
    assert out.dias_para_denunciar.tolist()[:2] == [0, 979]
    assert list(out.columns) == SALIDA
    print("demo OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        crudo = pd.read_csv(CRUDO, low_memory=False, encoding="utf-8")
        df = limpiar(crudo.copy())
        reporte(crudo, df)
        # parquet y no csv: pesa 8 veces menos y conserva los tipos (category,
        # datetime) que el csv tira en cada lectura
        df.to_parquet(LIMPIO, index=False)
        print(f"\nescrito: {LIMPIO.name} ({LIMPIO.stat().st_size / 1e6:.1f} MB)")
