"""Definición de modelos: referencias (persistencia, regresión lineal) y modelos de árboles."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import Config

try:  # XGBoost es opcional
    from xgboost import XGBRegressor
    HAY_XGBOOST = True
except ImportError:  # pragma: no cover
    HAY_XGBOOST = False


class Persistencia(BaseEstimator, RegressorMixin):
    """Referencia obligatoria: el almacenamiento futuro es igual al actual (Δ = 0)."""

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        return np.zeros(len(X))


class TendenciaReciente(BaseEstimator, RegressorMixin):
    """Referencia adicional: extrapola el cambio medio de los últimos 30 días.

    Δ̂h = h · (cambio diario medio de 30 días), convertido de % a hm³.
    Sirve para mostrar si el ML aporta algo más que "seguir la tendencia".
    """

    def __init__(self, horizonte: int = 7, capacidad: float = 1.0):
        self.horizonte = horizonte
        self.capacidad = capacidad

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        media = X["cambio_diario_media_30d_pct"].fillna(0).to_numpy()
        return self.horizonte * media * self.capacidad / 100


def crear_modelo(nombre: str, cfg: Config, horizonte: int = 7, capacidad: float = 1.0, **sobrescribir):
    semilla = cfg.semilla
    if nombre == "persistencia":
        return Persistencia()
    if nombre == "tendencia_30d":
        return TendenciaReciente(horizonte=horizonte, capacidad=capacidad)
    if nombre == "regresion_lineal":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=1.0))
    if nombre == "random_forest":
        params = {**cfg["modelo"]["random_forest"], **sobrescribir}
        return RandomForestRegressor(random_state=semilla, **params)
    if nombre == "xgboost":
        if not HAY_XGBOOST:
            raise ImportError("Instala xgboost para usar este modelo: pip install xgboost")
        params = {**cfg["modelo"]["xgboost"], **sobrescribir}
        return XGBRegressor(random_state=semilla, n_jobs=-1, objective="reg:squarederror", **params)
    raise ValueError(f"Modelo desconocido: {nombre}")


MODELOS_REFERENCIA = ["persistencia", "tendencia_30d", "regresion_lineal"]
MODELOS_ML = ["random_forest"] + (["xgboost"] if HAY_XGBOOST else [])


def importancias(modelo, columnas: list[str]) -> pd.Series:
    """Importancia de variables (impureza) para modelos de árboles."""
    imp = getattr(modelo, "feature_importances_", None)
    if imp is None:
        return pd.Series(dtype=float)
    return pd.Series(imp, index=columnas).sort_values(ascending=False)
