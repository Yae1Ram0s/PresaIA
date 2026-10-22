"""Entrenamiento del modelo de producción, persistencia en disco y pronóstico operativo."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from . import __version__
from .alertas import Pronostico
from .config import Config, Presa
from .evaluacion import ResultadoHorizonte
from .features import construir_features, matriz_entrenamiento
from .modelos import crear_modelo


def ruta_modelo(cfg: Config, clave: str, h: int) -> Path:
    return cfg.ruta("modelos") / f"{clave}_h{h}.joblib"


def entrenar_produccion(df: pd.DataFrame, presa: Presa, cfg: Config, res: ResultadoHorizonte,
                        origen_datos: str) -> Path:
    """Reentrena el mejor modelo con TODOS los datos y lo guarda con sus metadatos."""
    X, y, _ = matriz_entrenamiento(df, presa, cfg, res.horizonte)
    mdl = crear_modelo(res.mejor_modelo, cfg, res.horizonte, presa.capacidad_namo_hm3,
                       **res.hiperparametros.get(res.mejor_modelo, {}))
    mdl.fit(X[res.columnas], y)
    paquete = {
        "modelo": mdl,
        "nombre_modelo": res.mejor_modelo,
        "columnas": res.columnas,
        "horizonte": res.horizonte,
        "clave": presa.clave,
        "capacidad_namo_hm3": presa.capacidad_namo_hm3,
        "cuantil_error_hm3": res.cuantil_error_hm3,
        "nivel_confianza": cfg["incertidumbre"]["nivel_confianza"],
        "mae_prueba_hm3": res.metricas_prueba[res.mejor_modelo]["MAE_hm3"],
        "hiperparametros": res.hiperparametros.get(res.mejor_modelo, {}),
        "datos_hasta": str(df["volumen_hm3"].dropna().index.max().date()),
        "origen_datos": origen_datos,
        "entrenado": datetime.now().isoformat(timespec="seconds"),
        "versiones": {"presaia": __version__, "scikit-learn": sklearn.__version__, "pandas": pd.__version__},
    }
    ruta = ruta_modelo(cfg, presa.clave, res.horizonte)
    joblib.dump(paquete, ruta, compress=3)
    return ruta


def cargar_paquetes(cfg: Config, clave: str) -> dict[int, dict]:
    paquetes = {}
    for h in cfg["modelo"]["horizontes_dias"]:
        r = ruta_modelo(cfg, clave, h)
        if r.exists():
            paquetes[h] = joblib.load(r)
    return paquetes


def pronosticar(df: pd.DataFrame, presa: Presa, cfg: Config, paquetes: dict[int, dict],
                fecha_emision: pd.Timestamp | None = None) -> list[Pronostico]:
    """Pronóstico emitido en `fecha_emision` (por defecto, el último día con volumen)."""
    X = construir_features(df, presa, cfg)
    validas = df["volumen_hm3"].dropna().index
    t = fecha_emision if fecha_emision is not None else validas.max()
    if t not in validas:
        raise ValueError(f"No hay volumen registrado el {t.date()} para emitir el pronóstico")
    v0 = float(df.loc[t, "volumen_hm3"])
    salida = []
    for h, p in sorted(paquetes.items()):
        fila = X.loc[[t]].reindex(columns=p["columnas"])
        delta = float(p["modelo"].predict(fila)[0])
        vol = v0 + delta
        q = p["cuantil_error_hm3"]
        salida.append(Pronostico(h, t + pd.Timedelta(days=h), vol, max(vol - q, 0.0), vol + q,
                                 p["nombre_modelo"], p.get("mae_prueba_hm3")))
    return salida


def guardar_json(obj, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
