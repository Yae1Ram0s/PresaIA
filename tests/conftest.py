import copy

import numpy as np
import pandas as pd
import pytest

from presaia.config import Config, Presa, cargar_config


@pytest.fixture(scope="session")
def cfg_base() -> Config:
    return cargar_config()


@pytest.fixture
def cfg(cfg_base) -> Config:
    """Configuración rápida para pruebas (modelos pequeños)."""
    d = copy.deepcopy(cfg_base._d)
    d["modelo"]["random_forest"].update(n_estimators=20, max_depth=6)
    d["modelo"]["xgboost"].update(n_estimators=40)
    d["modelo"]["inicio_validacion"] = "2015-01-01"
    d["modelo"]["inicio_prueba"] = "2017-01-01"
    return Config(d, cfg_base.raiz)


@pytest.fixture
def presa() -> Presa:
    return Presa("TEST1", "Presa de Prueba", "México", "Prueba", 100.0)


@pytest.fixture
def serie_limpia(presa) -> pd.DataFrame:
    """Serie diaria 2010–2018 con estacionalidad simple, ya en formato procesado."""
    idx = pd.date_range("2010-01-01", "2018-12-31", freq="D", name="fecha")
    rng = np.random.default_rng(0)
    doy = idx.dayofyear.to_numpy()
    vol = 60 + 25 * np.sin(2 * np.pi * (doy - 200) / 365.25) + rng.normal(0, 0.3, len(idx))
    df = pd.DataFrame({
        "volumen_hm3": vol,
        "nivel_m": 1000 + vol / 10,
        "precip_mm": np.where(rng.random(len(idx)) < 0.3, rng.gamma(1, 8, len(idx)), 0.0),
        "obra_toma_m3s": 5.0, "vertedor_m3s": 0.0, "derrame_m3s": 0.0, "evap_mm": 5.0,
    }, index=idx)
    df["bandera_volumen"] = "observado"
    df["llenado_pct"] = df["volumen_hm3"] / presa.capacidad_namo_hm3 * 100
    return df
