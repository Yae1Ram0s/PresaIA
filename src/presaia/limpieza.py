"""Limpieza, control de calidad y diagnóstico de las series de almacenamiento.

Cada valor de volumen termina con una *bandera de calidad* para que la
trazabilidad llegue hasta el tablero:

    observado            valor tal como viene del SIH
    reconstruido_nivel   estimado con la curva elevación–volumen (ver abajo)
    interpolado          hueco corto (≤ max_hueco_interpolar días) rellenado
    atipico_eliminado    valor descartado por salto físico imposible
    faltante             sin dato; no se usa para entrenar
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .config import Config, Presa
from .io_sih import SerieSIH


# ---------------------------------------------------------------------------
# Curva elevación–volumen
# ---------------------------------------------------------------------------
@dataclass
class CurvaElevVol:
    coeficientes: list[float]
    r2: float
    n_puntos: int
    nivel_min: float
    nivel_max: float

    def __call__(self, nivel: pd.Series) -> pd.Series:
        dentro = nivel.between(self.nivel_min, self.nivel_max)
        return pd.Series(np.where(dentro, np.polyval(self.coeficientes, nivel), np.nan), index=nivel.index)


def ajustar_curva(df: pd.DataFrame, grado: int = 2) -> CurvaElevVol | None:
    """Ajusta volumen = f(nivel) con días que tienen ambas variables."""
    ambos = df[["nivel_m", "volumen_hm3"]].dropna()
    if len(ambos) < 365:
        return None
    coef = np.polyfit(ambos["nivel_m"], ambos["volumen_hm3"], grado)
    pred = np.polyval(coef, ambos["nivel_m"])
    ss_res = float(((ambos["volumen_hm3"] - pred) ** 2).sum())
    ss_tot = float(((ambos["volumen_hm3"] - ambos["volumen_hm3"].mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return CurvaElevVol(coef.tolist(), r2, len(ambos), float(ambos["nivel_m"].min()), float(ambos["nivel_m"].max()))


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------
@dataclass
class ResultadoLimpieza:
    serie: pd.DataFrame
    resumen: dict


def limpiar_serie(sih: SerieSIH, presa: Presa, cfg: Config) -> ResultadoLimpieza:
    p = cfg["limpieza"]
    cap = presa.capacidad_namo_hm3
    df = sih.datos.copy()
    df = df[df.index >= pd.Timestamp(p["fecha_inicio_minima"])]

    resumen: dict = {"clave": presa.clave, "registros_crudos": int(len(df))}
    bandera = pd.Series("faltante", index=df.index, dtype=object)
    bandera[df["volumen_hm3"].notna()] = "observado"

    # 1) Rango físico: 0 ≤ V ≤ 1.25·NAMO (el NAME suele estar por encima del NAMO)
    fuera = (df["volumen_hm3"] < 0) | (df["volumen_hm3"] > 1.25 * cap)
    df.loc[fuera, "volumen_hm3"] = np.nan
    bandera[fuera] = "atipico_eliminado"

    # 2) Picos aislados: salto grande que se revierte al día siguiente
    umbral = p["max_salto_diario_pct"] / 100 * cap
    v = df["volumen_hm3"]
    pico = ((v - v.shift(1)).abs() > umbral) & ((v - v.shift(-1)).abs() > umbral)
    df.loc[pico, "volumen_hm3"] = np.nan
    bandera[pico] = "atipico_eliminado"
    resumen["atipicos_eliminados"] = int((bandera == "atipico_eliminado").sum())

    # 3) Reconstrucción desde nivel (después de quitar atípicos, y solo si la
    #    curva elevación–volumen es casi perfecta)
    curva = None
    if p.get("reconstruir_desde_nivel", True) and df["nivel_m"].notna().any():
        curva = ajustar_curva(df)
        if curva and curva.r2 >= p["min_r2_curva"]:
            hueco = df["volumen_hm3"].isna() & df["nivel_m"].notna()
            df.loc[hueco, "volumen_hm3"] = curva(df.loc[hueco, "nivel_m"])
            bandera[hueco & df["volumen_hm3"].notna()] = "reconstruido_nivel"
    resumen["curva_elev_vol"] = asdict(curva) if curva else None
    resumen["curva_usada"] = bool(curva and curva.r2 >= p["min_r2_curva"])

    # 4) Calendario diario completo entre el primer y el último volumen válido
    validos = df["volumen_hm3"].dropna()
    if validos.empty:
        resumen.update(apta=False, motivo="sin datos de volumen tras la limpieza")
        return ResultadoLimpieza(df.iloc[0:0], resumen)
    idx = pd.date_range(validos.index.min(), validos.index.max(), freq="D", name="fecha")
    df = df.reindex(idx)
    bandera = bandera.reindex(idx).fillna("faltante")

    # 5) Interpolar solo huecos cortos
    max_h = int(p["max_hueco_interpolar"])
    antes = df["volumen_hm3"].isna()
    df["volumen_hm3"] = df["volumen_hm3"].interpolate(method="time", limit=max_h, limit_area="inside")
    grupos = antes.ne(antes.shift()).cumsum()
    largo_hueco = antes.groupby(grupos).transform("sum")
    relleno = antes & (largo_hueco <= max_h) & df["volumen_hm3"].notna()
    df.loc[~(antes & (largo_hueco <= max_h)) & antes, "volumen_hm3"] = np.nan
    bandera[relleno] = "interpolado"

    df["bandera_volumen"] = bandera
    df["llenado_pct"] = 100 * df["volumen_hm3"] / cap
    resumen.update(_diagnostico(df, cfg))
    return ResultadoLimpieza(df, resumen)


def _diagnostico(df: pd.DataFrame, cfg: Config) -> dict:
    p = cfg["limpieza"]
    v = df["volumen_hm3"]
    cobertura = float(v.notna().mean())
    por_anio = v.notna().groupby(df.index.year).mean()
    anios_validos = int((por_anio >= 0.8).sum())
    faltan = v.isna()
    huecos = faltan.groupby(faltan.ne(faltan.shift()).cumsum()).sum()
    conteo_bandera = df["bandera_volumen"].value_counts().to_dict()
    apta = cobertura >= p["min_cobertura_volumen"] and anios_validos >= p["min_anios_validos"]
    motivo = "cumple criterios" if apta else (
        f"cobertura {cobertura:.0%} (< {p['min_cobertura_volumen']:.0%})"
        if cobertura < p["min_cobertura_volumen"]
        else f"{anios_validos} años válidos (< {p['min_anios_validos']})"
    )
    return {
        "fecha_inicio": str(df.index.min().date()),
        "fecha_fin": str(df.index.max().date()),
        "dias_calendario": int(len(df)),
        "cobertura_volumen": round(cobertura, 4),
        "anios_con_80pct": anios_validos,
        "hueco_max_dias": int(huecos.max()) if len(huecos) else 0,
        "cobertura_precip": round(float(df["precip_mm"].notna().mean()), 4),
        "cobertura_nivel": round(float(df["nivel_m"].notna().mean()), 4),
        "dias_por_bandera": {k: int(v) for k, v in conteo_bandera.items()},
        "volumen_min_hm3": round(float(v.min()), 2),
        "volumen_max_hm3": round(float(v.max()), 2),
        "apta": bool(apta),
        "motivo": motivo,
    }


def diagnosticar_crudo(sih: SerieSIH) -> dict:
    """Diagnóstico rápido de un CSV crudo, útil para elegir presas antes de limpiar."""
    d = sih.datos
    con_vol = d["volumen_hm3"].dropna()
    return {
        "clave": sih.clave,
        "estacion": sih.nombre,
        "registros": int(len(d)),
        "primer_registro": str(d.index.min().date()) if len(d) else None,
        "ultimo_registro": str(d.index.max().date()) if len(d) else None,
        "primer_volumen": str(con_vol.index.min().date()) if len(con_vol) else None,
        "ultimo_volumen": str(con_vol.index.max().date()) if len(con_vol) else None,
        "dias_con_volumen": int(len(con_vol)),
        "dias_con_nivel": int(d["nivel_m"].notna().sum()),
        "dias_con_precip": int(d["precip_mm"].notna().sum()),
        "anios_con_volumen_80pct": int((d["volumen_hm3"].notna().groupby(d.index.year).mean() >= 0.8).sum()),
    }
