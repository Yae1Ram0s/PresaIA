"""Acceso en caché a los archivos que genera `python -m presaia todo`.

Equivale a las funciones @st.cache_* del tablero anterior. Tras volver a
entrenar se llama a `limpiar_cache()` (POST /api/recargar) o se reinicia el
servidor.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime
import threading
from functools import lru_cache

import numpy as np
import pandas as pd
from django.conf import settings
from django.http import Http404

from presaia.alertas import Pronostico
from presaia.config import Config, Presa, cargar_config
from presaia.io_sih import leer_catalogo
from presaia.panorama import resumen_presas
from presaia.pipeline import actualizar_una_vez
from presaia.prediccion import cargar_paquetes

NOMBRE_MODELO = {"random_forest": "Random Forest", "xgboost": "XGBoost", "persistencia": "Persistencia",
                 "tendencia_30d": "Tendencia 30 días", "regresion_lineal": "Regresión lineal (Ridge)"}
bloqueo_carga = threading.Lock()  # una sola importación a la vez
CLAVES_UMBRAL = ["llenado_atencion_pct", "llenado_critico_pct", "descenso_atencion_pp", "descenso_critico_pp"]


@lru_cache(maxsize=1)
def cfg() -> Config:
    return cargar_config(settings.PRESAIA_CONFIG)


@lru_cache(maxsize=None)
def serie(clave: str) -> tuple[pd.DataFrame | None, dict]:
    ruta = cfg().raiz / cfg()["rutas"]["datos_procesados"] / f"{clave}.csv"
    if not ruta.exists():
        return None, {}
    df = pd.read_csv(ruta, parse_dates=["fecha"], index_col="fecha")
    meta_r = ruta.with_suffix(".json")
    return df, (json.loads(meta_r.read_text(encoding="utf-8")) if meta_r.exists() else {})


@lru_cache(maxsize=None)
def paquetes(clave: str) -> dict[int, dict]:
    return cargar_paquetes(cfg(), clave)


@lru_cache(maxsize=1)
def metricas() -> dict:
    r = cfg().raiz / cfg()["rutas"]["reportes"] / "metricas.json"
    return json.loads(r.read_text(encoding="utf-8")) if r.exists() else {}


@lru_cache(maxsize=1)
def catalogo() -> pd.DataFrame | None:
    r = cfg().raiz / cfg()["rutas"]["catalogo"]
    try:
        return leer_catalogo(r) if r.exists() else None
    except Exception:  # noqa: BLE001
        return None


def backtest(clave: str, h: int) -> pd.DataFrame | None:
    r = cfg().raiz / cfg()["rutas"]["reportes"] / "predicciones_prueba" / f"{clave}_h{h}.csv"
    return pd.read_csv(r, parse_dates=["fecha_objetivo"], index_col="fecha_objetivo") if r.exists() else None


def disponibles() -> list[Presa]:
    return [p for p in cfg().presas if serie(p.clave)[0] is not None]


def presa_o_404(clave: str) -> tuple[Presa, pd.DataFrame, dict]:
    try:
        presa = cfg().presa(clave)
    except KeyError as e:
        raise Http404(str(e)) from e
    df, meta = serie(clave)
    if df is None:
        raise Http404(f"No hay datos procesados de {clave}. Ejecuta python -m presaia todo")
    return presa, df, meta


@lru_cache(maxsize=1)
def panorama() -> pd.DataFrame:
    ds = disponibles()
    return resumen_presas(cfg(), {p.clave: serie(p.clave) for p in ds}, {p.clave: paquetes(p.clave) for p in ds})


def actualizacion() -> dict:
    """Cuándo se generó el pronóstico vigente (tras `actualizar`, `predecir` o una carga desde el
    tablero) y fecha del dato más reciente entre las presas disponibles."""
    ruta = cfg().ruta("reportes") / "pronostico_vigente.json"
    fechas = [df.index.max() for p in disponibles() if (df := serie(p.clave)[0]) is not None and len(df)]
    return {
        "fecha": datetime.fromtimestamp(ruta.stat().st_mtime).isoformat(timespec="minutes") if ruta.exists() else None,
        "ultimo_dato": str(max(fechas).date()) if fechas else None,
    }


# Actualización desde el SIH lanzada con el botón del tablero. Corre en un hilo porque la
# descarga con Chromium y el pronóstico tardan alrededor de un minuto.
tarea_actualizar = {"en_curso": False, "inicio": None, "fin": None, "ok": None, "mensaje": None}


def lanzar_actualizacion() -> bool:
    """Inicia la actualización en segundo plano; False si ya hay una en curso."""
    if not bloqueo_carga.acquire(blocking=False):
        return False
    tarea_actualizar.update(en_curso=True, inicio=datetime.now().isoformat(timespec="seconds"),
                            fin=None, ok=None, mensaje="Descargando datos del SIH…")

    def trabajo():
        try:
            pron = actualizar_una_vez(cfg())
            tarea_actualizar.update(ok=True, mensaje=f"Pronóstico actualizado para {len(pron)} presa(s).")
        except Exception as e:  # noqa: BLE001
            tarea_actualizar.update(ok=False, mensaje=str(e))
        finally:
            limpiar_cache()
            tarea_actualizar.update(en_curso=False, fin=datetime.now().isoformat(timespec="seconds"))
            bloqueo_carga.release()

    threading.Thread(target=trabajo, daemon=True, name="presaia-actualizar").start()
    return True


def limpiar_cache() -> None:
    for f in (cfg, serie, paquetes, metricas, catalogo, panorama):
        f.cache_clear()


def config_con_umbrales(params) -> tuple[Config, dict]:
    """Copia de la configuración con los umbrales de la petición (equivale a los de la sesión).

    Lanza ValueError si los umbrales son incoherentes.
    """
    base = cfg()
    u = dict(base["alertas"])
    for k in CLAVES_UMBRAL:
        if params.get(k) not in (None, ""):
            try:
                u[k] = float(params[k])
            except ValueError as e:
                raise ValueError(f"Valor no numérico en {k}") from e
    if u["llenado_critico_pct"] > u["llenado_atencion_pct"] or u["descenso_critico_pp"] < u["descenso_atencion_pp"]:
        raise ValueError("El umbral crítico debe ser más severo que el de atención.")
    return Config({**base._d, "alertas": u}, base.raiz), u


def pronostico_dict(p: Pronostico, cap: float) -> dict:
    return {
        "horizonte": p.horizonte,
        "fecha_objetivo": p.fecha_objetivo,
        "volumen_hm3": p.volumen_hm3,
        "inf_hm3": p.inf_hm3,
        "sup_hm3": p.sup_hm3,
        "llenado_pct": 100 * p.volumen_hm3 / cap,
        "inf_pct": 100 * p.inf_hm3 / cap,
        "sup_pct": 100 * p.sup_hm3 / cap,
        "modelo": p.modelo,
        "modelo_nombre": NOMBRE_MODELO.get(p.modelo, p.modelo),
        "mae_prueba_hm3": p.mae_prueba_hm3,
    }


def a_json(x):
    """Convierte recursivamente tipos de pandas/numpy a JSON; NaN → null."""
    if isinstance(x, dict):
        return {str(k): a_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray, pd.Series)):
        return [a_json(v) for v in list(x)]
    if isinstance(x, pd.Timestamp):
        return None if pd.isna(x) else x.date().isoformat() if x == x.normalize() else x.isoformat()
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if math.isnan(x) or math.isinf(x) else float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if x is pd.NaT:
        return None
    return x
