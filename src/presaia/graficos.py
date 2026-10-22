"""Gráficas estáticas (matplotlib) para los reportes del análisis y la evaluación.

Las gráficas interactivas viven en el frontend (frontend/src/), con datos de la API.

Paleta: categórica en orden fijo (azul = observado, naranja = predicción) y
colores de estado reservados para avisos. Todos los textos van en tinta
neutra; el color solo identifica la serie.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

COLOR = {
    "observado": "#2a78d6",
    "prediccion": "#eb6834",
    "referencia": "#898781",
    "secundario": "#1baf7a",
    "texto": "#0b0b0b",
    "texto2": "#52514e",
    "rejilla": "#e1e0d9",
    "eje": "#c3c2b7",
    "superficie": "#fcfcfb",
}
CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]


def _estilo(ax, titulo: str, ylabel: str = "", xlabel: str = ""):
    ax.set_title(titulo, loc="left", fontsize=12, color=COLOR["texto"], fontweight="bold")
    ax.set_ylabel(ylabel, color=COLOR["texto2"])
    ax.set_xlabel(xlabel, color=COLOR["texto2"])
    ax.grid(axis="y", color=COLOR["rejilla"], linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(COLOR["eje"])
    ax.tick_params(colors=COLOR["texto2"], labelsize=9, length=0)


def _guardar(fig, ruta: Path):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(COLOR["superficie"])
    fig.tight_layout()
    fig.savefig(ruta, dpi=150, facecolor=COLOR["superficie"])
    plt.close(fig)


# ---------------------------------------------------------------------------
# Análisis exploratorio
# ---------------------------------------------------------------------------
def fig_serie_historica(df: pd.DataFrame, nombre: str, cap: float, ruta: Path, demo: bool):
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(df.index, df["llenado_pct"], color=COLOR["observado"], lw=1.2)
    ax.axhline(100, color=COLOR["eje"], lw=1, ls="--")
    ax.text(df.index[0], 101.5, "NAMO (100 %)", fontsize=8, color=COLOR["texto2"])
    _estilo(ax, f"{nombre}: llenado diario{'  [DATOS DEMO]' if demo else ''}", "% de llenado (NAMO)")
    ax.set_ylim(0, max(110, float(df["llenado_pct"].max()) + 5))
    _guardar(fig, ruta)


def fig_estacionalidad(df: pd.DataFrame, nombre: str, cap: float, ruta: Path):
    cambio_mensual = (df["volumen_hm3"].resample("MS").last().diff() / cap * 100).dropna()
    datos = [cambio_mensual[cambio_mensual.index.month == m].to_numpy() for m in range(1, 13)]
    fig, ax = plt.subplots(figsize=(9, 4))
    bp = ax.boxplot(datos, patch_artist=True, widths=0.55, medianprops={"color": COLOR["texto"]},
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": COLOR["referencia"],
                                "markeredgecolor": "none"})
    for caja in bp["boxes"]:
        caja.set(facecolor=COLOR["observado"], alpha=0.35, edgecolor=COLOR["observado"])
    ax.axhline(0, color=COLOR["eje"], lw=1)
    ax.set_xticks(range(1, 13), ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"])
    _estilo(ax, f"{nombre}: cambio de llenado por mes", "pp de llenado en el mes")
    _guardar(fig, ruta)


def fig_cobertura(df: pd.DataFrame, nombre: str, ruta: Path):
    cols = {"volumen_hm3": "Volumen", "nivel_m": "Nivel", "precip_mm": "Precipitación",
            "obra_toma_m3s": "Obra de toma", "evap_mm": "Evaporación"}
    cov = pd.DataFrame({etq: df[c].notna().groupby(df.index.year).mean() for c, etq in cols.items() if c in df})
    fig, ax = plt.subplots(figsize=(11, 2.8))
    im = ax.imshow(cov.T.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(cov.shape[1]), cov.columns)
    paso = max(1, len(cov) // 12)
    ax.set_xticks(range(0, len(cov), paso), cov.index[::paso])
    _estilo(ax, f"{nombre}: fracción de días con dato por año")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    _guardar(fig, ruta)


def fig_precip_vs_cambio(df: pd.DataFrame, nombre: str, cap: float, ruta: Path):
    p30 = df["precip_mm"].rolling(30, min_periods=18).sum()
    c30 = (df["volumen_hm3"].shift(-30) - df["volumen_hm3"]) / cap * 100
    d = pd.DataFrame({"p": p30, "c": c30}).dropna().iloc[::7]
    if len(d) < 30:
        return False
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.scatter(d["p"], d["c"], s=10, color=COLOR["observado"], alpha=0.45, edgecolors="none")
    r = d["p"].corr(d["c"], method="spearman")
    _estilo(ax, f"{nombre}: lluvia vs. cambio siguiente (ρ={r:.2f})",
            "cambio de llenado a 30 días (pp)", "precipitación acumulada 30 días previos (mm)")
    _guardar(fig, ruta)
    return True


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------
def fig_real_vs_pred(tabla: pd.DataFrame, nombre: str, h: int, cap: float, ruta: Path, demo: bool):
    t = tabla / cap * 100
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.fill_between(t.index, t["inf_hm3"], t["sup_hm3"], color=COLOR["prediccion"], alpha=0.15, lw=0,
                    label="Intervalo de incertidumbre")
    ax.plot(t.index, t["real_hm3"], color=COLOR["observado"], lw=1.6, label="Observado")
    ax.plot(t.index, t["pred_hm3"], color=COLOR["prediccion"], lw=1.4, label=f"Predicción a {h} días")
    ax.plot(t.index, t["pred_persistencia_hm3"], color=COLOR["referencia"], lw=1, ls=":", label="Persistencia")
    _estilo(ax, f"{nombre}: periodo de prueba, horizonte {h} días{'  [DATOS DEMO]' if demo else ''}",
            "% de llenado")
    ax.legend(frameon=False, fontsize=9, loc="best", labelcolor=COLOR["texto2"])
    _guardar(fig, ruta)


def fig_comparacion_modelos(met: dict[int, dict], nombre: str, ruta: Path):
    """Barras agrupadas: MAE (pp) por horizonte y modelo, en el periodo de prueba."""
    horizontes = sorted(met)
    modelos = list(met[horizontes[0]].keys())
    ancho = 0.8 / len(modelos)
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, m in enumerate(modelos):
        vals = [met[h][m]["MAE_pp_llenado"] for h in horizontes]
        x = np.arange(len(horizontes)) + i * ancho - 0.4 + ancho / 2
        ax.bar(x, vals, width=ancho * 0.9, color=CATEGORICA[i % len(CATEGORICA)], label=m.replace("_", " "))
    ax.set_xticks(range(len(horizontes)), [f"{h} días" for h in horizontes])
    _estilo(ax, f"{nombre}: error absoluto medio en prueba (menor es mejor)", "MAE (pp de llenado)")
    ax.legend(frameon=False, fontsize=8, ncol=3, labelcolor=COLOR["texto2"])
    _guardar(fig, ruta)


def fig_importancias(imp: pd.Series, nombre: str, h: int, ruta: Path, top: int = 12):
    if imp.empty:
        return
    s = imp.head(top)[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(s.index, s.values, color=COLOR["observado"], height=0.6)
    _estilo(ax, f"{nombre}: variables más importantes (h={h} d)", "", "importancia relativa")
    ax.grid(axis="x", color=COLOR["rejilla"]); ax.grid(axis="y", visible=False)
    _guardar(fig, ruta)


def fig_error_por_mes(tabla: pd.DataFrame, nombre: str, h: int, cap: float, ruta: Path):
    err = (tabla["pred_hm3"] - tabla["real_hm3"]).abs() / cap * 100
    ref = (tabla["pred_persistencia_hm3"] - tabla["real_hm3"]).abs() / cap * 100
    g = pd.DataFrame({"Modelo": err, "Persistencia": ref}).groupby(tabla.index.month).mean()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(g))
    ax.bar(x - 0.2, g["Modelo"], width=0.38, color=COLOR["prediccion"], label="Modelo")
    ax.bar(x + 0.2, g["Persistencia"], width=0.38, color=COLOR["referencia"], label="Persistencia")
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    ax.set_xticks(x, [meses[m - 1] for m in g.index])
    _estilo(ax, f"{nombre}: ¿cuándo falla? error medio por mes (h={h} d)", "MAE (pp)")
    ax.legend(frameon=False, fontsize=9, labelcolor=COLOR["texto2"])
    _guardar(fig, ruta)
