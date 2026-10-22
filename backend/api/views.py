"""Endpoints JSON de PresaIA. Cada uno corresponde a una parte del tablero:

    Panorama general   → /api/panorama
    1 · Consulta       → /api/presas/<clave>, /serie
    2 · Predicción     → /pronostico, /metricas, /backtest/<h>
    3 · Avisos         → /avisos (+ exportación HTML, CSV y JSON)

Toda la lógica de negocio vive en src/presaia/; aquí solo se adapta a JSON.
"""
from __future__ import annotations

import json

import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from presaia.alertas import evaluar_avisos, nivel_global, tendencia_observada
from presaia.panorama import indicadores_globales
from presaia.pipeline import importar_archivos
from presaia.prediccion import pronosticar
from presaia.reporte import generar_html, tabla_pronosticos

from . import servicios as S

PERIODOS_ANIOS = {"1": 1, "3": 3, "10": 10, "todo": 200}
MAX_PUNTOS = 3000   # series más largas se resumen por semana para no saturar el navegador


def _json(datos, status: int = 200) -> JsonResponse:
    return JsonResponse(S.a_json(datos), status=status, safe=False, json_dumps_params={"ensure_ascii": False})


def _descarga(contenido: str, nombre: str, tipo: str) -> HttpResponse:
    r = HttpResponse(contenido.encode("utf-8"), content_type=f"{tipo}; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return r


def _presa_json(p) -> dict:
    return {"clave": p.clave, "nombre": p.nombre, "estado": p.estado, "sistema": p.sistema,
            "capacidad_namo_hm3": p.capacidad_namo_hm3, "latitud": p.latitud, "longitud": p.longitud,
            "etiqueta": p.etiqueta, "tiene_modelo": bool(S.paquetes(p.clave))}


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
@require_GET
def estado(request):
    cfg = S.cfg()
    ds = S.disponibles()
    m = S.metricas()
    return _json({
        "hay_datos": bool(ds),
        "presas": [_presa_json(p) for p in ds],
        "presas_configuradas": [{"clave": p.clave, "nombre": p.nombre} for p in cfg.presas],
        "horizontes": cfg["modelo"]["horizontes_dias"],
        "umbrales": cfg["alertas"],
        "actualizacion": S.actualizacion(),
        "modelos": {k: S.paquetes(k).get(min(S.paquetes(k), default=0), {}).get("datos_hasta") for k in m},
    })


@require_POST
def recargar(request):
    S.limpiar_cache()
    return _json({"ok": True})


@require_GET
def presas(request):
    q = request.GET.get("q", "").lower()
    lista = [p for p in S.disponibles() if q in f"{p.nombre} {p.estado} {p.clave} {p.sistema}".lower()]
    return _json([_presa_json(p) for p in lista])


# ---------------------------------------------------------------------------
# Panorama general
# ---------------------------------------------------------------------------
@require_GET
def panorama(request):
    tabla = S.panorama()
    if tabla.empty:
        return _json({"indicadores": {}, "presas": [], "comparativo": []})
    # Llenado del último año de cada presa, en una sola tabla por fecha
    series = {}
    for p in S.disponibles():
        ll = S.serie(p.clave)[0]["llenado_pct"].dropna()
        series[p.clave] = ll[ll.index > ll.index.max() - pd.Timedelta(days=365)].round(2)
    comp = pd.DataFrame(series)
    comp.index.name = "fecha"
    return _json({
        "indicadores": indicadores_globales(tabla),
        "umbrales": S.cfg()["alertas"],
        "presas": tabla.to_dict(orient="records"),
        "comparativo": comp.reset_index().to_dict(orient="records"),
    })


@require_GET
def panorama_csv(request):
    tabla = S.panorama().drop(columns=["historia_90d"], errors="ignore")
    return _descarga(tabla.to_csv(index=False), "PresaIA_panorama.csv", "text/csv")


# ---------------------------------------------------------------------------
# Módulo 1 — Consulta
# ---------------------------------------------------------------------------
@require_GET
def consulta(request, clave):
    presa, df, meta = S.presa_o_404(clave)
    cap = presa.capacidad_namo_hm3
    v = df["volumen_hm3"].dropna()
    ultimo = v.index[-1]
    ll = 100 * v / cap
    hace30 = v.asof(ultimo - pd.Timedelta(days=30))
    hace365 = v.asof(ultimo - pd.Timedelta(days=365))

    ficha = {"Clave SIH": presa.clave, "Estado": presa.estado, "Sistema": presa.sistema,
             "Capacidad NAMO (hm³)": f"{cap:,.2f}", "Primer registro": f"{df.index.min():%d/%m/%Y}",
             "Último registro": f"{ultimo:%d/%m/%Y}"}
    cat = S.catalogo()
    fila = cat[cat["clave"] == presa.clave] if cat is not None else None
    if fila is not None and len(fila):
        r = fila.iloc[0]
        ficha.update({"Municipio": r.get("municipio"), "Cuenca": r.get("cuenca"),
                      "Región hidrológica": r.get("region_hidrologica"),
                      "Coordenadas": f"{r.get('latitud'):.4f}, {r.get('longitud'):.4f}"})

    return _json({
        "presa": _presa_json(presa),
        "origen_datos": meta.get("origen_datos", "desconocido"),
        "ultima_obs": ultimo,
        "llenado_pct": ll.iloc[-1],
        "volumen_hm3": v.iloc[-1],
        "cambio_30d_pp": ll.iloc[-1] - 100 * hace30 / cap if pd.notna(hace30) else None,
        "llenado_hace_1a_pct": 100 * hace365 / cap if pd.notna(hace365) else None,
        "promedio_mes_pct": ll[ll.index.month == ultimo.month].mean(),
        "banderas": df["bandera_volumen"].value_counts().to_dict() if "bandera_volumen" in df else {},
        "ficha": {k: (None if pd.isna(x) else str(x)) for k, x in ficha.items()},
        "calidad": {"cobertura_volumen": meta.get("cobertura_volumen"),
                    "dias_por_bandera": meta.get("dias_por_bandera", {})},
    })


@require_GET
def serie(request, clave):
    presa, df, _ = S.presa_o_404(clave)
    anios = PERIODOS_ANIOS.get(request.GET.get("periodo", "10"), 10)
    v = df["volumen_hm3"].dropna()
    vista = df.loc[df.index >= v.index[-1] - pd.DateOffset(years=anios), ["volumen_hm3", "llenado_pct"]]
    resumida = len(vista) > MAX_PUNTOS
    if resumida:
        vista = vista.resample("W").mean()
    vista = vista.round(2)
    vista.index.name = "fecha"
    return _json({"resumida_semanal": resumida, "umbrales": S.cfg()["alertas"],
                  "puntos": vista.reset_index().to_dict(orient="records")})


@require_GET
def serie_csv(request, clave):
    _, df, _ = S.presa_o_404(clave)
    return _descarga(df.to_csv(), f"{clave}_serie_procesada.csv", "text/csv")


# ---------------------------------------------------------------------------
# Módulo 2 — Predicción
# ---------------------------------------------------------------------------
@require_GET
def pronostico(request, clave):
    """Pronóstico vigente, o simulado en una fecha pasada (?fecha=AAAA-MM-DD) con lo que ocurrió después."""
    presa, df, _ = S.presa_o_404(clave)
    paq = S.paquetes(clave)
    if not paq:
        return _json({"error": "Esta presa aún no tiene modelos entrenados. Ejecuta python -m presaia entrenar."}, 404)
    cap = presa.capacidad_namo_hm3
    v = df["volumen_hm3"].dropna()
    ultimo = v.index[-1]

    pedidos = request.GET.get("horizontes")
    sel = sorted(paq) if not pedidos else [h for h in map(int, pedidos.split(",")) if h in paq]

    fecha = ultimo
    simulado = bool(request.GET.get("fecha"))
    if simulado:
        try:
            fecha = pd.Timestamp(request.GET["fecha"])
        except ValueError:
            return _json({"error": "Fecha inválida"}, 400)
        fecha = min(max(fecha, v.index[min(400, len(v) - 1)]), ultimo)
        if fecha not in v.index:
            fecha = v.index[v.index <= fecha][-1]

    pron = pronosticar(df, presa, S.cfg(), {h: paq[h] for h in sel}, fecha) if sel else []
    historia = 100 * v[(v.index <= fecha) & (v.index > fecha - pd.Timedelta(days=365))] / cap
    ocurrido = None
    if simulado:
        hasta = fecha + pd.Timedelta(days=max(sel or [0]))
        ocurrido = (100 * v[(v.index > fecha) & (v.index <= hasta)] / cap).round(2)

    def puntos(s):
        return [{"fecha": t, "llenado_pct": x} for t, x in s.round(2).items()]

    return _json({
        "horizontes_disponibles": sorted(paq),
        "fecha_emision": fecha,
        "fecha_minima": v.index[min(400, len(v) - 1)],
        "fecha_maxima": ultimo,
        "simulado": simulado,
        "pronosticos": [S.pronostico_dict(p, cap) for p in pron],
        "historia": puntos(historia),
        "ocurrido": puntos(ocurrido) if ocurrido is not None else [],
    })


@require_GET
def metricas(request, clave):
    presa, _, meta = S.presa_o_404(clave)
    met = S.metricas().get(clave, {}).get("horizontes", {})
    salida = {}
    for h, r in met.items():
        mejor = r["mejor_modelo"]
        tabla = [{"modelo": k, "nombre": S.NOMBRE_MODELO.get(k, k), **{c: m.get(c) for c in (
                  "MAE_hm3", "RMSE_hm3", "MAE_pp_llenado", "MAPE_pct", "acierto_direccion",
                  "mejora_vs_persistencia_pct")}} for k, m in r["metricas_prueba"].items()]
        salida[h] = {
            "mejor_modelo": mejor,
            "mejor_modelo_nombre": S.NOMBRE_MODELO.get(mejor, mejor),
            "mejor": r["metricas_prueba"][mejor],
            "intervalo": r["intervalo"],
            "particion_prueba": r["particion"]["prueba"],
            "por_temporada": r.get("por_temporada", {}),
            "importancias_top10": r.get("importancias_top10", {}),
            "tabla": sorted(tabla, key=lambda x: x["MAE_hm3"] if x["MAE_hm3"] is not None else 1e18),
        }
    return _json({"horizontes": salida,
                  "calidad": {"cobertura_volumen": meta.get("cobertura_volumen"),
                              "reconstruidos": meta.get("dias_por_bandera", {}).get("reconstruido_nivel", 0)}})


@require_GET
def backtest(request, clave, h):
    presa, _, _ = S.presa_o_404(clave)
    bt = S.backtest(clave, h)
    if bt is None:
        return _json({"error": f"Sin predicciones de prueba para {h} días"}, 404)
    cap = presa.capacidad_namo_hm3
    pct = (100 * bt[["real_hm3", "pred_hm3", "pred_persistencia_hm3", "inf_hm3", "sup_hm3"]] / cap).round(2)
    pct.columns = ["real", "pred", "persistencia", "inf", "sup"]
    if len(pct) > MAX_PUNTOS:
        pct = pct.resample("W").mean().round(2)
    pct.index.name = "fecha"
    return _json(pct.reset_index().to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Módulo 3 — Indicadores y avisos
# ---------------------------------------------------------------------------
def _evaluar(request, clave):
    presa, df, meta = S.presa_o_404(clave)
    cfg_local, u = S.config_con_umbrales(request.GET)
    paq = S.paquetes(clave)
    pron = pronosticar(df, presa, cfg_local, paq) if paq else []
    avisos = evaluar_avisos(df, pron, presa, cfg_local)
    return presa, df, meta, u, pron, avisos


@require_GET
def avisos(request, clave):
    try:
        presa, df, meta, u, pron, lista = _evaluar(request, clave)
    except ValueError as e:
        return _json({"error": str(e)}, 400)
    cap = presa.capacidad_namo_hm3
    v = df["volumen_hm3"].dropna()
    lejano = max(pron, key=lambda p: p.horizonte) if pron else None
    return _json({
        "umbrales": u,
        "estado": nivel_global(lista),
        "tendencia_pp_mes": tendencia_observada(v, cap, int(u["ventana_tendencia_dias"])),
        "ventana_tendencia_dias": u["ventana_tendencia_dias"],
        "proyeccion": ({"horizonte": lejano.horizonte, "llenado_pct": 100 * lejano.volumen_hm3 / cap,
                        "cambio_pp": 100 * (lejano.volumen_hm3 - v.iloc[-1]) / cap} if lejano else None),
        "avisos": [a.a_dict() for a in lista],
    })


@require_GET
def reporte_html(request, clave):
    try:
        presa, df, meta, _, pron, lista = _evaluar(request, clave)
    except ValueError as e:
        return _json({"error": str(e)}, 400)
    met = S.metricas().get(clave, {}).get("horizontes", {})
    html = generar_html(presa, df, pron, lista, nivel_global(lista), meta.get("origen_datos", "desconocido"), met)
    ultimo = df["volumen_hm3"].dropna().index[-1]
    return _descarga(html, f"PresaIA_{clave}_{ultimo:%Y%m%d}.html", "text/html")


@require_GET
def pronostico_csv(request, clave):
    try:
        presa, _, _, _, pron, _ = _evaluar(request, clave)
    except ValueError as e:
        return _json({"error": str(e)}, 400)
    return _descarga(tabla_pronosticos(pron, presa.capacidad_namo_hm3).to_csv(index=False),
                     f"PresaIA_{clave}_pronostico.csv", "text/csv")


@require_GET
def avisos_json(request, clave):
    try:
        *_, lista = _evaluar(request, clave)
    except ValueError as e:
        return _json({"error": str(e)}, 400)
    return _descarga(json.dumps([a.a_dict() for a in lista], ensure_ascii=False, indent=2, default=str),
                     f"PresaIA_{clave}_avisos.json", "application/json")


# ---------------------------------------------------------------------------
# Carga manual de datos del SIH
# ---------------------------------------------------------------------------
MAX_ARCHIVO_MB = 50


def actualizar(request):
    """POST inicia la descarga del SIH con Chromium en segundo plano; GET consulta su avance."""
    if request.method == "POST":
        if not S.lanzar_actualizacion():
            return _json({"error": "Ya hay una actualización o carga en curso.", **S.tarea_actualizar}, status=409)
        return _json(S.tarea_actualizar, status=202)
    return _json(S.tarea_actualizar)


@require_POST
def cargar(request):
    archivos = request.FILES.getlist("archivos")
    if not archivos:
        return _json({"error": "No se recibió ningún archivo."}, status=400)
    grandes = [f.name for f in archivos if f.size > MAX_ARCHIVO_MB * 1024 * 1024]
    if grandes:
        return _json({"error": f"Archivos mayores a {MAX_ARCHIVO_MB} MB: {', '.join(grandes)}"}, status=400)
    with S.bloqueo_carga:
        res = importar_archivos(S.cfg(), {f.name: f.read() for f in archivos})
        S.limpiar_cache()
    return _json(res)
