"""Línea de comandos de PresaIA. Cada fase del proyecto es un subcomando.

    python -m presaia descargar            # CSV del SIH + catálogo (requiere internet)
    python -m presaia descargar --todas    # todas las presas, para elegir con 'diagnosticar'
    python -m presaia actualizar           # descargar → preparar → predecir (sin reentrenar)
    python -m presaia actualizar --cada 24 # lo mismo, repetido cada 24 h
    python -m presaia diagnosticar         # ranking de presas por calidad de datos
    python -m presaia preparar             # limpieza + control de calidad
    python -m presaia eda                  # figuras del análisis exploratorio
    python -m presaia entrenar             # referencias, RF, XGBoost, evaluación
    python -m presaia predecir             # pronóstico vigente + avisos
    python -m presaia todo                 # preparar → eda → entrenar → predecir

Agregar --demo a cualquier comando para usar los datos SINTÉTICOS de data/demo.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

from . import graficos as G
from . import navegador
from .alertas import evaluar_avisos, nivel_global
from .config import Config, cargar_config
from .evaluacion import experimento
from .features import matriz_entrenamiento
from .io_sih import leer_catalogo, leer_csv_sih
from .limpieza import diagnosticar_crudo, limpiar_serie
from .modelos import importancias
from .panorama import resumen_presas
from .prediccion import cargar_paquetes, entrenar_produccion, guardar_json, pronosticar

log = logging.getLogger("presaia")


# ---------------------------------------------------------------------------
def _dir_crudos(cfg: Config, demo: bool) -> Path:
    if demo:
        d = cfg.ruta("datos_demo")
        if not any(d.glob("*.csv")):
            from .demo import generar_todos
            log.info("Generando datos DEMO sintéticos en %s", d)
            generar_todos(cfg)
        return d
    return cfg.ruta("datos_crudos")


def _ruta_procesada(cfg: Config, clave: str) -> Path:
    return cfg.ruta("datos_procesados") / f"{clave}.csv"


def cargar_procesada(cfg: Config, clave: str) -> tuple[pd.DataFrame, dict]:
    ruta = _ruta_procesada(cfg, clave)
    df = pd.read_csv(ruta, parse_dates=["fecha"], index_col="fecha")
    meta_ruta = ruta.with_suffix(".json")
    meta = json.loads(meta_ruta.read_text(encoding="utf-8")) if meta_ruta.exists() else {}
    return df, meta


# ---------------------------------------------------------------------------
def cmd_descargar(cfg: Config, args) -> int:
    destino = cfg.ruta("datos_crudos")
    destino.mkdir(parents=True, exist_ok=True)
    cat = "0_Catalogo_de_presas.csv"
    urls = {cat: cfg["fuentes"]["url_catalogo"]}
    registro = []
    if args.todas:
        if not (destino / cat).exists():
            registro += _bajar_lote(urls, destino, args)
        claves = leer_catalogo(destino / cat)["clave"].dropna().tolist()
    else:
        claves = [p.clave for p in cfg.presas]
    urls.update({f"{c}.csv": cfg["fuentes"]["url_base_sih"] + f"{c}.csv" for c in claves})
    registro += _bajar_lote({n: u for n, u in urls.items() if not any(r["archivo"] == n and r["ok"] for r in registro)},
                            destino, args)
    pd.DataFrame(registro).to_csv(cfg.ruta("reportes") / "registro_descargas.csv", index=False)
    return sum(r["ok"] for r in registro)


def _bajar_lote(urls: dict[str, str], destino: Path, args) -> list[dict]:
    """Intenta la descarga directa; lo que falle (p. ej. por la verificación anti-bots del SIH)
    se reintenta con Chromium si Playwright está instalado (ver navegador.py)."""
    metodo = getattr(args, "metodo", "auto")
    res: dict[str, tuple[bool, str]] = {}
    if metodo != "navegador":
        for nombre, url in urls.items():
            res[nombre] = _bajar(url, destino / nombre)
            if "HTML" in res[nombre][1] and metodo == "auto":
                res.update({n: (False, "omitido: el sitio exige navegador") for n in urls if n not in res})
                break
            time.sleep(0.3)  # cortesía con el servidor público
    pendientes = {n: u for n, u in urls.items() if not res.get(n, (False,))[0]}
    if pendientes and metodo != "directo":
        if navegador.disponible():
            log.info("Descargando %d archivo(s) con Chromium…", len(pendientes))
            res.update(navegador.descargar(pendientes, destino, _guardar_validado, getattr(args, "ver_navegador", False)))
        else:
            log.warning("Descarga directa bloqueada. Instala el respaldo con navegador: "
                        "pip install playwright && python -m playwright install chromium")
    registro = []
    for nombre, url in urls.items():
        ok, info = res[nombre]
        registro.append({"archivo": nombre, "url": url, "ok": ok, "detalle": info,
                         "fecha_consulta": time.strftime("%Y-%m-%d %H:%M")})
        log.info("%s %s (%s)", "✔" if ok else "✘", nombre, info)
    return registro


def _guardar_validado(datos: bytes, ruta: Path) -> None:
    """Escribe a un temporal y solo reemplaza el original si el contenido es válido:
    una respuesta de error del servidor (HTML, archivo vacío o truncado) no borra datos buenos."""
    if not datos or datos.lstrip()[:1] == b"<":
        raise ValueError("el servidor respondió HTML (¿página de verificación anti-bots?), no CSV")
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        tmp.write_bytes(datos)
        leer_catalogo(tmp) if ruta.name.startswith("0_") else leer_csv_sih(tmp)
        tmp.replace(ruta)
    finally:
        tmp.unlink(missing_ok=True)


def _bajar(url: str, ruta: Path, intentos: int = 3) -> tuple[bool, str]:
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PresaIA/1.0 (proyecto academico)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            _guardar_validado(datos, ruta)
            return True, f"{len(datos) / 1024:.0f} KB"
        except Exception as e:  # noqa: BLE001
            err = str(e)
            if "302" in err or "HTML" in err:   # bloqueo anti-bots: reintentar no sirve
                return False, "el sitio respondió HTML (verificación anti-bots)"
            time.sleep(2 * (i + 1))
    return False, err


def actualizar_una_vez(cfg: Config, args=None) -> dict:
    """Descarga (directo o con Chromium) → preparar → predecir. Usado por la línea de comandos y
    por el botón «Actualizar» del tablero. Devuelve el pronóstico vigente."""
    args = args or argparse.Namespace(metodo="auto", ver_navegador=False)
    args.todas, args.demo = False, False
    if not cmd_descargar(cfg, args):
        raise RuntimeError("No se descargó ningún archivo del SIH; ver reports/registro_descargas.csv. "
                           "Se conservan los datos y el pronóstico anteriores.")
    cmd_preparar(cfg, args)
    return cmd_predecir(cfg, args)


def cmd_actualizar(cfg: Config, args) -> None:
    """Descarga los datos más recientes del SIH, limpia y emite un pronóstico nuevo con los
    modelos ya entrenados (no reentrena). Con --cada H se repite cada H horas."""
    while True:
        t0 = time.time()
        try:
            actualizar_una_vez(cfg, args)
            _avisar_servidor(args.servidor)
            log.info("Actualización completa en %.0f s", time.time() - t0)
        except Exception:  # noqa: BLE001 — en modo periódico un fallo no debe detener el ciclo
            log.exception("Falló la actualización")
            if not args.cada:
                raise
        if not args.cada:
            return
        log.info("Próxima actualización en %.1f h", args.cada)
        time.sleep(args.cada * 3600)


def importar_archivos(cfg: Config, archivos: dict[str, bytes]) -> dict:
    """Valida CSV del SIH obtenidos a mano (p. ej. subidos desde el tablero), los guarda en
    data/raw y vuelve a preparar y pronosticar. Un archivo inválido no reemplaza al anterior."""
    destino = cfg.ruta("datos_crudos")
    destino.mkdir(parents=True, exist_ok=True)
    claves = {p.clave for p in cfg.presas}
    resultados = []
    for nombre, datos in archivos.items():
        clave = Path(nombre).stem.upper()
        r = {"archivo": nombre, "clave": clave, "ok": False}
        resultados.append(r)
        if clave not in claves:
            r["detalle"] = f"'{clave}' no está entre las presas configuradas ({', '.join(sorted(claves))})"
            continue
        tmp = destino / f"{clave}.csv.tmp"
        try:
            tmp.write_bytes(datos)
            sih = leer_csv_sih(tmp)
            if sih.datos.empty:
                raise ValueError("el archivo no contiene registros")
            tmp.replace(destino / f"{clave}.csv")
            r.update(ok=True, registros=len(sih.datos), desde=str(sih.datos.index.min().date()),
                     hasta=str(sih.datos.index.max().date()))
        except Exception as e:  # noqa: BLE001
            tmp.unlink(missing_ok=True)
            r["detalle"] = f"no es un CSV válido del SIH: {e}"
    calidad, pronostico = {}, {}
    if any(r["ok"] for r in resultados):
        args = argparse.Namespace(demo=False)
        calidad = cmd_preparar(cfg, args)
        pronostico = cmd_predecir(cfg, args)
    for r in resultados:
        if r["ok"]:
            q = calidad.get(r["clave"], {})
            r["apta"], r["motivo"] = q.get("apta"), q.get("motivo")
            r["estado"] = pronostico.get(r["clave"], {}).get("estado")
    return {"archivos": resultados, "actualizado": bool(pronostico)}


def _avisar_servidor(url: str | None) -> None:
    """Pide al tablero (si está corriendo) que limpie su caché para mostrar los datos nuevos."""
    if not url:
        return
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=10)
        log.info("Tablero recargado (%s)", url)
    except Exception as e:  # noqa: BLE001
        log.info("Tablero no disponible en %s (%s); verá los datos al reiniciarse", url, e)


def cmd_diagnosticar(cfg: Config, args) -> pd.DataFrame:
    crudos = _dir_crudos(cfg, args.demo)
    filas = []
    for ruta in sorted(crudos.glob("*.csv")):
        if ruta.name.startswith("0_"):
            continue
        try:
            filas.append(diagnosticar_crudo(leer_csv_sih(ruta)))
        except Exception as e:  # noqa: BLE001
            filas.append({"clave": ruta.stem, "error": str(e)})
    df = pd.DataFrame(filas)
    if "anios_con_volumen_80pct" in df:
        df = df.sort_values(["anios_con_volumen_80pct", "dias_con_volumen"], ascending=False)
    salida = cfg.ruta("reportes") / "diagnostico_presas.csv"
    df.to_csv(salida, index=False)
    log.info("Diagnóstico de %d archivos → %s", len(df), salida)
    print(df.head(25).to_string(index=False))
    return df


def cmd_preparar(cfg: Config, args) -> dict:
    crudos = _dir_crudos(cfg, args.demo)
    calidad = {}
    for presa in cfg.presas:
        ruta = crudos / f"{presa.clave}.csv"
        if not ruta.exists():
            log.warning("Falta %s — ejecuta 'descargar' o usa --demo", ruta)
            continue
        sih = leer_csv_sih(ruta)
        res = limpiar_serie(sih, presa, cfg)
        res.resumen["origen_datos"] = "SINTETICO" if sih.es_sintetica else "SIH-CONAGUA"
        res.resumen["archivo_origen"] = ruta.name
        calidad[presa.clave] = res.resumen
        if len(res.serie):
            res.serie.to_csv(_ruta_procesada(cfg, presa.clave))
            guardar_json(res.resumen, _ruta_procesada(cfg, presa.clave).with_suffix(".json"))
        log.info("%s: %s — %s", presa.clave, "APTA" if res.resumen.get("apta") else "NO APTA",
                 res.resumen.get("motivo"))
    guardar_json(calidad, cfg.ruta("reportes") / "calidad_datos.json")
    return calidad


def cmd_eda(cfg: Config, args) -> None:
    fig_dir = cfg.ruta("reportes") / "figuras"
    resumen = {}
    for presa in cfg.presas:
        if not _ruta_procesada(cfg, presa.clave).exists():
            continue
        df, meta = cargar_procesada(cfg, presa.clave)
        demo = meta.get("origen_datos") == "SINTETICO"
        cap, n = presa.capacidad_namo_hm3, presa.nombre
        G.fig_serie_historica(df, n, cap, fig_dir / f"{presa.clave}_01_serie.png", demo)
        G.fig_estacionalidad(df, n, cap, fig_dir / f"{presa.clave}_02_estacionalidad.png")
        G.fig_cobertura(df, n, fig_dir / f"{presa.clave}_03_cobertura.png")
        G.fig_precip_vs_cambio(df, n, cap, fig_dir / f"{presa.clave}_04_lluvia_vs_cambio.png")
        ll = df["llenado_pct"]
        mensual = ll.groupby(df.index.month).mean()
        resumen[presa.clave] = {
            "llenado_medio_pct": round(float(ll.mean()), 2),
            "llenado_min_pct": round(float(ll.min()), 2),
            "fecha_min": str(ll.idxmin().date()),
            "llenado_max_pct": round(float(ll.max()), 2),
            "mes_mas_bajo": int(mensual.idxmin()), "mes_mas_alto": int(mensual.idxmax()),
            "cambio_diario_std_pp": round(float((df["volumen_hm3"].diff() / cap * 100).std()), 4),
            "origen_datos": meta.get("origen_datos"),
        }
    guardar_json(resumen, cfg.ruta("reportes") / "eda_resumen.json")
    log.info("Figuras de EDA en %s", fig_dir)


def cmd_entrenar(cfg: Config, args) -> dict:
    fig_dir = cfg.ruta("reportes") / "figuras"
    pred_dir = cfg.ruta("reportes") / "predicciones_prueba"
    pred_dir.mkdir(exist_ok=True)
    todo = {}
    for presa in cfg.presas:
        if not _ruta_procesada(cfg, presa.clave).exists():
            continue
        df, meta = cargar_procesada(cfg, presa.clave)
        if not meta.get("apta", False) and not args.forzar:
            log.warning("%s no es apta (%s). Usa --forzar para entrenar de todos modos.", presa.clave, meta.get("motivo"))
            continue
        demo = meta.get("origen_datos") == "SINTETICO"
        cap = presa.capacidad_namo_hm3
        por_h, met_prueba = {}, {}
        for h in cfg["modelo"]["horizontes_dias"]:
            t0 = time.time()
            X, y, vol = matriz_entrenamiento(df, presa, cfg, h)
            res = experimento(X, y, vol, presa, cfg, h, ajustar=not args.rapido)
            ruta_mdl = entrenar_produccion(df, presa, cfg, res, meta.get("origen_datos", "?"))
            res.predicciones_prueba.to_csv(pred_dir / f"{presa.clave}_h{h}.csv")
            G.fig_real_vs_pred(res.predicciones_prueba, presa.nombre, h, cap,
                               fig_dir / f"{presa.clave}_10_prueba_h{h}.png", demo)
            G.fig_error_por_mes(res.predicciones_prueba, presa.nombre, h, cap,
                                fig_dir / f"{presa.clave}_12_error_mes_h{h}.png")
            imp = importancias(res.modelo_final, res.columnas)
            G.fig_importancias(imp, presa.nombre, h, fig_dir / f"{presa.clave}_13_importancias_h{h}.png")
            met_prueba[h] = res.metricas_prueba
            por_h[h] = {
                "mejor_modelo": res.mejor_modelo,
                "particion": res.particion,
                "metricas_validacion": res.metricas_validacion,
                "metricas_prueba": res.metricas_prueba,
                "por_temporada": res.por_temporada,
                "avisos_descenso": res.avisos_descenso,
                "hiperparametros": res.hiperparametros,
                "busqueda_hiperparametros": res.busqueda,
                "intervalo": {"nivel": cfg["incertidumbre"]["nivel_confianza"],
                              "cuantil_error_hm3": res.cuantil_error_hm3,
                              "cobertura_real_prueba": res.cobertura_intervalo_prueba},
                "importancias_top10": imp.head(10).round(4).to_dict(),
                "modelo_guardado": str(ruta_mdl.relative_to(cfg.raiz)),
                "segundos": round(time.time() - t0, 1),
            }
            m = res.metricas_prueba[res.mejor_modelo]
            log.info("%s h=%2d  %-14s MAE=%.2f hm³ (%.2f pp)  mejora vs persistencia=%s%%  cobertura=%.0f%%",
                     presa.clave, h, res.mejor_modelo, m["MAE_hm3"], m["MAE_pp_llenado"],
                     m.get("mejora_vs_persistencia_pct"), 100 * res.cobertura_intervalo_prueba)
        G.fig_comparacion_modelos(met_prueba, presa.nombre, fig_dir / f"{presa.clave}_11_comparacion_modelos.png")
        todo[presa.clave] = {"origen_datos": meta.get("origen_datos"), "horizontes": por_h}
    guardar_json(todo, cfg.ruta("reportes") / "metricas.json")
    _tabla_resumen(todo, cfg)
    return todo


def _tabla_resumen(todo: dict, cfg: Config) -> None:
    filas = []
    for clave, d in todo.items():
        for h, r in d["horizontes"].items():
            for modelo, m in r["metricas_prueba"].items():
                filas.append({"presa": clave, "horizonte_dias": h, "modelo": modelo,
                              "seleccionado": modelo == r["mejor_modelo"], **m})
    if filas:
        pd.DataFrame(filas).to_csv(cfg.ruta("reportes") / "metricas_prueba.csv", index=False)


def cmd_predecir(cfg: Config, args) -> dict:
    salida = {}
    for presa in cfg.presas:
        paquetes = cargar_paquetes(cfg, presa.clave)
        if not paquetes or not _ruta_procesada(cfg, presa.clave).exists():
            continue
        df, meta = cargar_procesada(cfg, presa.clave)
        pron = pronosticar(df, presa, cfg, paquetes)
        avisos = evaluar_avisos(df, pron, presa, cfg)
        salida[presa.clave] = {
            "presa": presa.etiqueta, "origen_datos": meta.get("origen_datos"),
            "fecha_emision": str(df["volumen_hm3"].dropna().index.max().date()),
            "llenado_actual_pct": round(float(df["llenado_pct"].dropna().iloc[-1]), 2),
            "pronosticos": [{"horizonte": p.horizonte, "fecha": str(p.fecha_objetivo.date()),
                             "volumen_hm3": round(p.volumen_hm3, 2),
                             "llenado_pct": round(100 * p.volumen_hm3 / presa.capacidad_namo_hm3, 2),
                             "intervalo_hm3": [round(p.inf_hm3, 2), round(p.sup_hm3, 2)], "modelo": p.modelo}
                            for p in pron],
            "estado": nivel_global(avisos),
            "avisos": [a.a_dict() for a in avisos],
        }
        log.info("%s: estado %s, %d aviso(s)", presa.clave, salida[presa.clave]["estado"], len(avisos))
    guardar_json(salida, cfg.ruta("reportes") / "pronostico_vigente.json")
    series = {p.clave: cargar_procesada(cfg, p.clave) for p in cfg.presas if _ruta_procesada(cfg, p.clave).exists()}
    panorama = resumen_presas(cfg, series, {c: cargar_paquetes(cfg, c) for c in series})
    if not panorama.empty:
        panorama.drop(columns=["historia_90d"]).to_csv(cfg.ruta("reportes") / "panorama.csv", index=False)
    return salida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="presaia", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["descargar", "actualizar", "diagnosticar", "preparar", "eda", "entrenar",
                                        "predecir", "todo"])
    ap.add_argument("--demo", action="store_true", help="usar datos SINTÉTICOS de data/demo")
    ap.add_argument("--todas", action="store_true", help="descargar todas las presas del catálogo")
    ap.add_argument("--rapido", action="store_true", help="omitir búsqueda de hiperparámetros")
    ap.add_argument("--forzar", action="store_true", help="entrenar aunque la presa no cumpla criterios")
    ap.add_argument("--config", default=None, help="ruta alternativa a config.toml")
    ap.add_argument("--metodo", choices=["auto", "directo", "navegador"], default="auto",
                    help="descargar/actualizar: 'auto' intenta directo y recurre a Chromium si el sitio lo bloquea")
    ap.add_argument("--ver-navegador", action="store_true", help="mostrar la ventana de Chromium (depuración)")
    ap.add_argument("--cada", type=float, default=None, metavar="HORAS",
                    help="actualizar: repetir cada HORAS horas (el proceso queda corriendo)")
    ap.add_argument("--servidor", default="http://127.0.0.1:8010/api/recargar",
                    help="actualizar: URL de recarga del tablero ('' para no avisar)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    cfg = cargar_config(args.config)
    pasos = {"descargar": [cmd_descargar], "actualizar": [cmd_actualizar], "diagnosticar": [cmd_diagnosticar], "preparar": [cmd_preparar],
             "eda": [cmd_eda], "entrenar": [cmd_entrenar], "predecir": [cmd_predecir],
             "todo": [cmd_preparar, cmd_eda, cmd_entrenar, cmd_predecir]}[args.comando]
    for paso in pasos:
        paso(cfg, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
