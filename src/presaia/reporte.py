"""Exportación de reportes (HTML autocontenido y CSV) desde el tablero o la CLI."""
from __future__ import annotations

import html
from datetime import datetime

import pandas as pd

from .alertas import Aviso, Pronostico
from .config import Presa

_ICONO = {"critico": "▲", "atencion": "●", "informativo": "ℹ", "normal": "✔"}
_COLOR = {"critico": "#d03b3b", "atencion": "#b07a00", "informativo": "#52514e", "normal": "#006300"}
_ETQ = {"critico": "Crítico", "atencion": "Atención", "informativo": "Informativo", "normal": "Normal"}


def tabla_pronosticos(pron: list[Pronostico], cap: float) -> pd.DataFrame:
    return pd.DataFrame([{
        "Horizonte (días)": p.horizonte,
        "Fecha objetivo": p.fecha_objetivo.date(),
        "Volumen estimado (hm³)": round(p.volumen_hm3, 2),
        "Llenado estimado (%)": round(100 * p.volumen_hm3 / cap, 1),
        "Intervalo (hm³)": f"{p.inf_hm3:,.1f} – {p.sup_hm3:,.1f}",
        "Error medio histórico (hm³)": p.mae_prueba_hm3,
        "Modelo": p.modelo,
    } for p in pron])


def generar_html(presa: Presa, df: pd.DataFrame, pron: list[Pronostico], avisos: list[Aviso],
                 estado: str, origen: str, metricas: dict | None = None) -> str:
    e = html.escape
    v = df["volumen_hm3"].dropna()
    t0, v0 = v.index[-1], float(v.iloc[-1])
    cap = presa.capacidad_namo_hm3
    demo = origen == "SINTETICO"
    tabla = tabla_pronosticos(pron, cap).to_html(index=False, border=0, classes="t")
    avisos_html = "".join(
        f'<div class="av" style="border-left-color:{_COLOR[a.nivel]}"><b style="color:{_COLOR[a.nivel]}">'
        f'{_ICONO[a.nivel]} {_ETQ[a.nivel]}</b> — <b>{e(a.titulo)}</b><br>{e(a.motivo)}</div>'
        for a in avisos) or "<p>Sin avisos con los umbrales actuales.</p>"
    met_html = ""
    if metricas:
        filas = "".join(
            f"<tr><td>{h}</td><td>{e(r['mejor_modelo'])}</td><td>{r['metricas_prueba'][r['mejor_modelo']]['MAE_hm3']}</td>"
            f"<td>{r['metricas_prueba'][r['mejor_modelo']]['MAE_pp_llenado']}</td>"
            f"<td>{r['metricas_prueba']['persistencia']['MAE_hm3']}</td>"
            f"<td>{r['metricas_prueba'][r['mejor_modelo']].get('mejora_vs_persistencia_pct', '')}</td>"
            f"<td>{round(100 * r['intervalo']['cobertura_real_prueba'])} %</td></tr>"
            for h, r in sorted(metricas.items(), key=lambda x: int(x[0])))
        met_html = ("<h2>Desempeño histórico (periodo de prueba)</h2><table class='t'><tr><th>Horizonte</th><th>Modelo</th>"
                    "<th>MAE (hm³)</th><th>MAE (pp)</th><th>MAE persistencia (hm³)</th><th>Mejora vs persistencia (%)</th>"
                    f"<th>Cobertura del intervalo</th></tr>{filas}</table>")
    banda = ('<div class="demo">DATOS DE DEMOSTRACIÓN (SINTÉTICOS) — este reporte no describe la situación real '
             'de la presa.</div>') if demo else ""
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PresaIA — {e(presa.nombre)}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#0b0b0b;background:#fcfcfb}}
h1{{font-size:22px;margin-bottom:4px}} h2{{font-size:17px;margin-top:28px}} .sub{{color:#52514e}}
.kpi{{display:flex;gap:12px;flex-wrap:wrap}} .k{{flex:1;min-width:150px;border:1px solid #e1e0d9;border-radius:8px;padding:10px}}
.k b{{font-size:20px;display:block}} table.t{{border-collapse:collapse;width:100%;font-size:13px}}
.t th,.t td{{border-bottom:1px solid #e1e0d9;padding:6px;text-align:left}} .av{{border-left:4px solid;padding:8px 12px;margin:8px 0;background:#fff}}
.demo{{background:#fff3cd;border:1px solid #fab219;padding:10px;border-radius:6px;font-weight:600}}
.nota{{font-size:12px;color:#52514e;margin-top:28px}}
</style></head><body>
{banda}
<h1>PresaIA — {e(presa.etiqueta)}</h1>
<div class="sub">{e(presa.estado)} · Sistema {e(presa.sistema)} · Emitido {datetime.now():%d/%m/%Y %H:%M} · Datos al {t0:%d/%m/%Y} · Fuente: {e(origen)}</div>
<h2>Situación actual</h2>
<div class="kpi">
<div class="k">Llenado<b>{100 * v0 / cap:.1f} %</b></div>
<div class="k">Volumen<b>{v0:,.1f} hm³</b></div>
<div class="k">Capacidad NAMO<b>{cap:,.1f} hm³</b></div>
<div class="k">Estado de avisos<b style="color:{_COLOR[estado]}">{_ICONO[estado]} {_ETQ[estado]}</b></div>
</div>
<h2>Pronóstico</h2>{tabla}
<h2>Avisos</h2>{avisos_html}
{met_html}
<p class="nota">PresaIA es una herramienta de apoyo a la decisión. No sustituye a CONAGUA, a los organismos operadores
ni a un sistema certificado de seguridad de presas. Un descenso proyectado no implica por sí mismo una emergencia.
Los intervalos se calibraron con errores históricos y pueden no cubrir eventos extraordinarios.</p>
</body></html>"""
