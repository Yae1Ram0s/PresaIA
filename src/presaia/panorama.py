"""Panorama general: resumen de todas las presas en una sola tabla.

Es la base del dashboard de inicio. Vive fuera del tablero para poder probarse
y para que la línea de comandos genere el mismo resumen (reports/panorama.csv).
"""
from __future__ import annotations

import pandas as pd

from .alertas import NIVELES, evaluar_avisos, nivel_global, tendencia_observada
from .config import Config, Presa
from .prediccion import pronosticar

ORDEN_ESTADO = {"critico": 0, "atencion": 1, "normal": 2}


def resumir_presa(presa: Presa, df: pd.DataFrame, meta: dict, paquetes: dict, cfg: Config,
                  hoy: pd.Timestamp | None = None) -> dict:
    """Una fila del panorama para una presa."""
    cap = presa.capacidad_namo_hm3
    v = df["volumen_hm3"].dropna()
    t0, v0 = v.index[-1], float(v.iloc[-1])
    hace30 = v.asof(t0 - pd.Timedelta(days=30))
    hace365 = v.asof(t0 - pd.Timedelta(days=365))
    pron = pronosticar(df, presa, cfg, paquetes) if paquetes else []
    avisos = evaluar_avisos(df, pron, presa, cfg, hoy)
    relevantes = [a for a in avisos if a.nivel != "informativo"]
    lejano = max(pron, key=lambda p: p.horizonte) if pron else None
    ultimos_90 = (100 * v[v.index > t0 - pd.Timedelta(days=90)] / cap).round(1)
    return {
        "clave": presa.clave,
        "presa": presa.nombre,
        "estado_rep": presa.estado,
        "sistema": presa.sistema,
        "latitud": presa.latitud,
        "longitud": presa.longitud,
        "capacidad_hm3": cap,
        "ultima_obs": t0,
        "volumen_hm3": v0,
        "llenado_pct": 100 * v0 / cap,
        "cambio_30d_pp": 100 * (v0 - hace30) / cap if pd.notna(hace30) else None,
        "llenado_hace_1a_pct": 100 * hace365 / cap if pd.notna(hace365) else None,
        "tendencia_pp_mes": tendencia_observada(v, cap, int(cfg["alertas"]["ventana_tendencia_dias"])),
        "horizonte_max": lejano.horizonte if lejano else None,
        "llenado_proyectado_pct": 100 * lejano.volumen_hm3 / cap if lejano else None,
        "cambio_proyectado_pp": 100 * (lejano.volumen_hm3 - v0) / cap if lejano else None,
        "volumen_proyectado_hm3": lejano.volumen_hm3 if lejano else None,
        "estado": nivel_global(avisos),
        "n_avisos": len(relevantes),
        "aviso_principal": relevantes[0].titulo if relevantes else "",
        "historia_90d": ultimos_90.tolist(),
        "origen_datos": meta.get("origen_datos", "desconocido"),
        "tiene_modelo": bool(paquetes),
    }


def resumen_presas(cfg: Config, series: dict[str, tuple[pd.DataFrame, dict]],
                   paquetes: dict[str, dict], hoy: pd.Timestamp | None = None) -> pd.DataFrame:
    """Tabla de todas las presas con datos, ordenada de mayor a menor riesgo.

    series:   {clave: (serie_procesada, metadatos)}
    paquetes: {clave: {horizonte: paquete_modelo}}
    """
    filas = [resumir_presa(p, *series[p.clave], paquetes.get(p.clave, {}), cfg, hoy)
             for p in cfg.presas if p.clave in series and series[p.clave][0] is not None]
    if not filas:
        return pd.DataFrame()
    tabla = pd.DataFrame(filas)
    tabla["_orden"] = tabla["estado"].map(ORDEN_ESTADO)
    clave_llenado = tabla["llenado_proyectado_pct"].fillna(tabla["llenado_pct"])
    tabla = tabla.assign(_ll=clave_llenado).sort_values(["_orden", "_ll"]).drop(columns=["_orden", "_ll"])
    return tabla.reset_index(drop=True)


def indicadores_globales(tabla: pd.DataFrame) -> dict:
    """Totales del sistema: llenado conjunto ponderado por capacidad, conteo por estado."""
    if tabla.empty:
        return {}
    cap = tabla["capacidad_hm3"].sum()
    con_pron = tabla.dropna(subset=["volumen_proyectado_hm3"])
    return {
        "presas": int(len(tabla)),
        "capacidad_total_hm3": float(cap),
        "volumen_total_hm3": float(tabla["volumen_hm3"].sum()),
        "llenado_conjunto_pct": float(100 * tabla["volumen_hm3"].sum() / cap),
        "llenado_conjunto_proyectado_pct": (
            float(100 * con_pron["volumen_proyectado_hm3"].sum() / con_pron["capacidad_hm3"].sum())
            if len(con_pron) else None),
        "llenado_conjunto_actual_con_pron_pct": (
            float(100 * con_pron["volumen_hm3"].sum() / con_pron["capacidad_hm3"].sum())
            if len(con_pron) else None),
        "en_critico": int((tabla["estado"] == "critico").sum()),
        "en_atencion": int((tabla["estado"] == "atencion").sum()),
        "normales": int((tabla["estado"] == "normal").sum()),
        "ultima_obs": tabla["ultima_obs"].max(),
        "hay_sinteticos": bool((tabla["origen_datos"] == "SINTETICO").any()),
    }


__all__ = ["resumen_presas", "resumir_presa", "indicadores_globales", "ORDEN_ESTADO", "NIVELES"]
