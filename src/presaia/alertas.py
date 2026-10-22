"""Reglas de avisos basadas en umbrales configurables.

Los avisos son una herramienta de APOYO A LA DECISIÓN. No sustituyen la
evaluación de CONAGUA ni de los organismos operadores, y un descenso no
implica por sí mismo una emergencia. Cada aviso explica su motivo, los datos
utilizados y la incertidumbre, para que una persona pueda revisarlo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from .config import Config, Presa

NIVELES = {"informativo": 0, "atencion": 1, "critico": 2}


@dataclass
class Aviso:
    nivel: str                 # informativo | atencion | critico
    tipo: str                  # llenado_bajo | descenso_proyectado | tendencia | calidad_datos
    titulo: str
    motivo: str
    datos: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Pronostico:
    horizonte: int
    fecha_objetivo: pd.Timestamp
    volumen_hm3: float
    inf_hm3: float
    sup_hm3: float
    modelo: str
    mae_prueba_hm3: float | None = None


def tendencia_observada(serie: pd.Series, capacidad: float, dias: int) -> float | None:
    """Pendiente (pp de llenado por 30 días) de una regresión lineal sobre los últimos `dias`."""
    s = serie.dropna().iloc[-dias:]
    if len(s) < dias * 0.6:
        return None
    t = (s.index - s.index[0]).days.to_numpy(dtype=float)
    pendiente = np.polyfit(t, s.to_numpy() / capacidad * 100, 1)[0]
    return float(pendiente * 30)


def evaluar_avisos(serie: pd.DataFrame, pronosticos: list[Pronostico], presa: Presa,
                   cfg: Config, hoy: pd.Timestamp | None = None) -> list[Aviso]:
    a = cfg["alertas"]
    cap = presa.capacidad_namo_hm3
    v = serie["volumen_hm3"].dropna()
    ultimo_dia, v0 = v.index[-1], float(v.iloc[-1])
    ll0 = 100 * v0 / cap
    avisos: list[Aviso] = []

    # 1) Calidad y vigencia de los datos
    hoy = hoy or pd.Timestamp.today().normalize()
    antiguedad = (hoy - ultimo_dia).days
    if antiguedad > 7:
        avisos.append(Aviso("informativo", "calidad_datos", "Datos desactualizados",
                            f"La última observación es del {ultimo_dia:%d/%m/%Y} ({antiguedad} días). "
                            "Los pronósticos se calculan a partir de esa fecha, no de hoy.",
                            {"ultima_observacion": str(ultimo_dia.date()), "dias": antiguedad}))
    if "bandera_volumen" in serie:
        b = serie.loc[ultimo_dia, "bandera_volumen"]
        if b != "observado":
            avisos.append(Aviso("informativo", "calidad_datos", "Último valor no observado directamente",
                                f"El volumen más reciente tiene bandera '{b}'.", {"bandera": b}))

    # 2) Llenado actual y proyectado
    for p in pronosticos:
        ll_p, ll_inf = 100 * p.volumen_hm3 / cap, 100 * p.inf_hm3 / cap
        nivel = None
        if ll_p < a["llenado_critico_pct"]:
            nivel = "critico"
        elif ll_p < a["llenado_atencion_pct"] or ll_inf < a["llenado_critico_pct"]:
            nivel = "atencion"
        if nivel:
            avisos.append(Aviso(
                nivel, "llenado_bajo", f"Llenado proyectado bajo a {p.horizonte} días",
                f"Se estima {ll_p:.1f} % de llenado para el {p.fecha_objetivo:%d/%m/%Y} "
                f"(intervalo {ll_inf:.1f}–{100 * p.sup_hm3 / cap:.1f} %). Umbrales: atención "
                f"< {a['llenado_atencion_pct']} %, crítico < {a['llenado_critico_pct']} %.",
                {"horizonte": p.horizonte, "llenado_actual_pct": round(ll0, 2), "llenado_proyectado_pct": round(ll_p, 2),
                 "intervalo_pct": [round(ll_inf, 2), round(100 * p.sup_hm3 / cap, 2)], "modelo": p.modelo}))

    # 3) Descenso proyectado
    for p in pronosticos:
        descenso = 100 * (v0 - p.volumen_hm3) / cap
        nivel = ("critico" if descenso >= a["descenso_critico_pp"]
                 else "atencion" if descenso >= a["descenso_atencion_pp"] else None)
        if nivel:
            avisos.append(Aviso(
                nivel, "descenso_proyectado", f"Descenso proyectado de {descenso:.1f} pp en {p.horizonte} días",
                f"El modelo estima que el almacenamiento pasará de {v0:,.1f} a {p.volumen_hm3:,.1f} hm³. "
                f"El error medio histórico de este horizonte es ±{p.mae_prueba_hm3 or 0:,.1f} hm³.",
                {"horizonte": p.horizonte, "descenso_pp": round(descenso, 2), "volumen_actual_hm3": round(v0, 2),
                 "volumen_proyectado_hm3": round(p.volumen_hm3, 2), "modelo": p.modelo}))

    # 4) Tendencia observada (no depende del modelo)
    dias = int(a["ventana_tendencia_dias"])
    pend = tendencia_observada(v, cap, dias)
    if pend is not None and pend <= -a["descenso_atencion_pp"]:
        avisos.append(Aviso("atencion", "tendencia", "Tendencia observada de descenso",
                            f"En los últimos {dias} días el llenado bajó a un ritmo de {abs(pend):.1f} pp por mes.",
                            {"pendiente_pp_por_30d": round(pend, 2)}))
    elif pend is not None and pend >= a["descenso_atencion_pp"]:
        avisos.append(Aviso("informativo", "tendencia", "Tendencia observada de recuperación",
                            f"En los últimos {dias} días el llenado subió {pend:.1f} pp por mes.",
                            {"pendiente_pp_por_30d": round(pend, 2)}))

    return sorted(avisos, key=lambda x: -NIVELES[x.nivel])


def nivel_global(avisos: list[Aviso]) -> str:
    if not avisos:
        return "normal"
    peor = max(avisos, key=lambda x: NIVELES[x.nivel]).nivel
    return "normal" if peor == "informativo" else peor
