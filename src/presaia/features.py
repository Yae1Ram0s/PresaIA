"""Construcción de variables predictoras SIN fuga de información.

Regla de oro: toda variable en la fila con fecha *t* usa exclusivamente datos
observados en fechas ≤ *t* (el día en que se emitiría el pronóstico).

Objetivo: en lugar de predecir el volumen absoluto V(t+h) se predice el CAMBIO
    Δh(t) = V(t+h) − V(t)
y después se reconstruye  V̂(t+h) = V(t) + Δ̂h(t).
Motivo: los modelos de árboles no extrapolan fuera del rango visto en
entrenamiento; el cambio es mucho más estable entre años secos y húmedos
que el nivel absoluto, y la persistencia queda como caso particular Δ̂ = 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config, Presa


def construir_features(df: pd.DataFrame, presa: Presa, cfg: Config) -> pd.DataFrame:
    """Devuelve un DataFrame indexado por fecha con todas las variables predictoras."""
    m = cfg["modelo"]
    cap = presa.capacidad_namo_hm3
    v = df["volumen_hm3"]
    dv = v.diff()  # cambio diario observado (hm³/día)
    X = pd.DataFrame(index=df.index)

    # Estado actual
    X["volumen_hm3"] = v
    X["llenado_pct"] = 100 * v / cap

    # Cambios respecto al pasado (equivalentes a lags, pero escalados)
    for k in m["lags_dias"]:
        X[f"cambio_{k}d_pct"] = 100 * (v - v.shift(k)) / cap

    # Dinámica reciente: media y variabilidad del cambio diario
    for w in m["ventanas_dias"]:
        X[f"cambio_diario_media_{w}d_pct"] = 100 * dv.rolling(w, min_periods=int(w * 0.6)).mean() / cap
        X[f"cambio_diario_std_{w}d_pct"] = 100 * dv.rolling(w, min_periods=int(w * 0.6)).std() / cap

    # Posición respecto a los extremos del último año
    X["llenado_max_365d"] = X["llenado_pct"].rolling(365, min_periods=200).max()
    X["llenado_min_365d"] = X["llenado_pct"].rolling(365, min_periods=200).min()

    # Calendario (codificación cíclica para que dic y ene queden cerca)
    doy = df.index.dayofyear
    X["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    X["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    X["mes"] = df.index.month
    X["temporada_lluvias"] = df.index.month.isin([6, 7, 8, 9, 10]).astype(int)

    # Precipitación observada en el sitio (si existe). Los NaN se conservan:
    # RandomForest (scikit-learn ≥ 1.4) y XGBoost los manejan de forma nativa.
    if m.get("usar_precipitacion", True) and df["precip_mm"].notna().mean() > 0.3:
        p = df["precip_mm"]
        for w in (7, 30, 90):
            X[f"precip_{w}d_mm"] = p.rolling(w, min_periods=int(w * 0.6)).sum()
        X["precip_anomalia_30d"] = X["precip_30d_mm"] - X["precip_30d_mm"].rolling(365 * 3, min_periods=365).mean()

    # Extracciones por obra de toma (si existen mediciones)
    if "obra_toma_m3s" in df and df["obra_toma_m3s"].notna().mean() > 0.3:
        q = df["obra_toma_m3s"]
        X["obra_toma_media_7d_m3s"] = q.rolling(7, min_periods=4).mean()
        X["obra_toma_media_30d_m3s"] = q.rolling(30, min_periods=18).mean()

    if "evap_mm" in df and df["evap_mm"].notna().mean() > 0.3:
        X["evap_30d_mm"] = df["evap_mm"].rolling(30, min_periods=18).sum()

    return X


def construir_objetivo(df: pd.DataFrame, horizonte: int) -> pd.Series:
    """Δh(t) = V(t+h) − V(t). NaN si alguno de los dos extremos falta."""
    v = df["volumen_hm3"]
    return (v.shift(-horizonte) - v).rename(f"delta_{horizonte}d")


def matriz_entrenamiento(df: pd.DataFrame, presa: Presa, cfg: Config, horizonte: int):
    """Une X, y, y el volumen actual; descarta filas sin estado u objetivo."""
    X = construir_features(df, presa, cfg)
    y = construir_objetivo(df, horizonte)
    # El estado actual debe ser un dato real o un hueco corto interpolado
    estado_valido = df["volumen_hm3"].notna() & df.get("bandera_volumen", "observado").ne("faltante")
    ok = estado_valido & y.notna()
    return X[ok], y[ok], df.loc[ok, "volumen_hm3"]
