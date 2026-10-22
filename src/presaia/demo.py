"""Generador de DATOS DEMO (sintéticos) en el formato exacto del SIH.

⚠  Estos datos NO son reales. Solo sirven para probar el sistema de punta a
   punta mientras se descargan los CSV oficiales. Cada archivo lleva la línea
   "Fuente: SINTETICO" y el tablero muestra una franja de advertencia.

Modelo físico simplificado (balance hídrico diario):
    V(t+1) = V(t) + Entradas(t) − ObraToma(t) − Evaporación(t) − Derrame(t)
  * Lluvia: proceso estacional (temporada de lluvias jun–oct) con años secos y
    húmedos encadenados (AR(1)) para generar sequías plurianuales.
  * Entradas: escurrimiento de la cuenca con respuesta retardada (embalse lineal).
  * Extracción: regla de operación que reduce la entrega cuando el llenado baja.
  * Evaporación: lámina diaria estacional × área del espejo (∝ V^(2/3)).
  * Derrame: excedente sobre el NAMO.
Se agregan huecos, datos faltantes de lluvia y algunos valores atípicos para
que la etapa de limpieza tenga algo real que resolver.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config, Presa
from .io_sih import escribir_csv_sih

# Parámetros por presa (escala relativa a la capacidad)
PARAMS = {
    "VBRMX": dict(lluvia_media=7.5, aporte_rel=0.95, extraccion_rel=0.62, nivel_base=1790.0, nivel_escala=4.6),
    "VVCMX": dict(lluvia_media=6.5, aporte_rel=0.85, extraccion_rel=0.55, nivel_base=2580.0, nivel_escala=3.4),
    "LBQCH": dict(lluvia_media=4.2, aporte_rel=0.55, extraccion_rel=0.42, nivel_base=1260.0, nivel_escala=2.1),
}
DEFECTO = dict(lluvia_media=6.0, aporte_rel=0.8, extraccion_rel=0.55, nivel_base=1000.0, nivel_escala=3.0)


def simular_presa(presa: Presa, inicio="1990-01-01", fin="2026-09-30", semilla=42) -> pd.DataFrame:
    p = PARAMS.get(presa.clave, DEFECTO)
    rng = np.random.default_rng(semilla + sum(map(ord, presa.clave)))
    idx = pd.date_range(inicio, fin, freq="D")
    n, cap = len(idx), presa.capacidad_namo_hm3
    doy = idx.dayofyear.to_numpy()
    anios = idx.year.to_numpy()

    # --- Humedad interanual: AR(1) con una sequía marcada 2020–2023
    u_anios = np.unique(anios)
    factor = np.empty(len(u_anios))
    f = 0.0
    for i, a in enumerate(u_anios):
        f = 0.55 * f + rng.normal(0, 0.28)
        factor[i] = f
    factor = np.exp(factor)
    factor[(u_anios >= 2020) & (u_anios <= 2023)] *= 0.72
    fa = factor[np.searchsorted(u_anios, anios)]

    # --- Lluvia diaria
    estacion = np.exp(-0.5 * ((doy - 210) / 42) ** 2)          # máximo a fines de julio
    prob = 0.04 + 0.62 * estacion
    llueve = rng.random(n) < np.clip(prob * np.sqrt(fa), 0, 0.95)
    lluvia = np.where(llueve, rng.gamma(0.75, p["lluvia_media"] * (0.6 + 1.4 * estacion) * fa / 0.75), 0.0)

    # --- Entradas: embalse lineal sobre la lluvia efectiva (k = 25 días)
    efectiva = np.maximum(lluvia - 4.0, 0.0)
    escala = p["aporte_rel"] * cap / max(efectiva.sum() / (n / 365.25), 1e-6)
    entradas = np.zeros(n)
    s = 0.0
    for t in range(n):
        s = s * np.exp(-1 / 25) + efectiva[t] * escala
        entradas[t] = s * (1 - np.exp(-1 / 25))

    # --- Evaporación (mm/día), máxima en abril–mayo
    evap = 4.2 + 2.0 * np.sin(2 * np.pi * (doy - 30) / 365.25) + rng.normal(0, 0.4, n)
    evap = np.clip(evap, 1.0, None)

    # --- Simulación
    v = np.empty(n)
    vol = 0.7 * cap
    obra = np.empty(n)
    derrame = np.zeros(n)
    area_namo_km2 = 0.035 * cap ** 0.9           # aproximación de escala
    demanda_base = p["extraccion_rel"] * cap / 365.25
    for t in range(n):
        llen = vol / cap
        regla = np.clip(0.35 + 0.9 * llen, 0.4, 1.1)          # recorta entregas si baja el llenado
        demanda = demanda_base * regla * (1.15 if doy[t] < 150 or doy[t] > 320 else 0.9)
        demanda *= rng.normal(1.0, 0.06)
        area = area_namo_km2 * max(llen, 0.02) ** (2 / 3)
        perdida_evap = evap[t] / 1000 * area                  # km²·m = hm³ (×1e6 m²·m ÷1e6)
        vol = vol + entradas[t] - demanda - perdida_evap
        if vol > cap:
            derrame[t] = vol - cap
            vol = cap - rng.uniform(0, 0.002) * cap
        vol = max(vol, 0.03 * cap)
        v[t], obra[t] = vol, demanda / 0.0864                  # hm³/día -> m³/s

    nivel = p["nivel_base"] + p["nivel_escala"] * (v ** 0.42)
    df = pd.DataFrame({
        "nivel_m": nivel + rng.normal(0, 0.01, n),
        "precip_mm": np.round(lluvia, 1),
        "volumen_hm3": v + rng.normal(0, 0.0008 * cap, n),
        "obra_toma_m3s": obra,
        "vertedor_m3s": derrame / 0.0864,
        "derrame_m3s": 0.0,
        "evap_mm": np.round(evap, 2),
    }, index=pd.DatetimeIndex(idx, name="fecha"))

    # --- Imperfecciones realistas
    faltan_cortos = rng.random(n) < 0.02
    df.loc[faltan_cortos, "volumen_hm3"] = np.nan
    for _ in range(4):                                         # huecos largos
        i0 = rng.integers(0, n - 60)
        df.iloc[i0:i0 + rng.integers(15, 50), df.columns.get_loc("volumen_hm3")] = np.nan
    df.loc[rng.random(n) < 0.10, "precip_mm"] = np.nan
    df.loc[rng.random(n) < 0.30, "evap_mm"] = np.nan
    atip = rng.choice(n, 6, replace=False)                     # errores de captura
    df.iloc[atip, df.columns.get_loc("volumen_hm3")] *= rng.choice([0.1, 10.0], 6)
    # Primeros años: solo nivel (como en muchos archivos reales del SIH)
    df.loc[df.index < "1994-01-01", "volumen_hm3"] = np.nan
    return df


def generar_todos(cfg: Config) -> list[str]:
    rutas = []
    for presa in cfg.presas:
        df = simular_presa(presa, semilla=cfg.semilla)
        meta = {
            "Fuente": "SINTETICO — datos de demostración generados por PresaIA, NO usar como datos reales",
            "Estación": f"{presa.nombre} (demo)",
            "Clave": presa.clave,
            "Estado": presa.estado,
        }
        ruta = cfg.ruta("datos_demo") / f"{presa.clave}.csv"
        escribir_csv_sih(df, ruta, meta, presa.clave)
        rutas.append(str(ruta))
    return rutas
