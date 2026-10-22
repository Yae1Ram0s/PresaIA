"""Descarga del SIH con un Chromium real (Playwright).

El sitio de CONAGUA pide una verificación en JavaScript que urllib no puede ejecutar. Chromium la
resuelve como cualquier navegador al abrir la página de presas; después las descargas comparten sus
cookies. El modo headless es rechazado por el servidor, así que se abre una ventana normal colocada
fuera de la pantalla.

Requiere:  pip install playwright  &&  python -m playwright install chromium
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

log = logging.getLogger("presaia")

PAGINA_INICIAL = "https://sih.conagua.gob.mx/presas.html"


def disponible() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def descargar(urls: dict[str, str], destino: Path, guardar: Callable[[bytes, Path], None],
              visible: bool = False) -> dict[str, tuple[bool, str]]:
    """Descarga cada {nombre: url} a destino/nombre. `guardar(datos, ruta)` valida y escribe
    (lanza excepción si el contenido no sirve). Devuelve {nombre: (ok, detalle)}."""
    from playwright.sync_api import sync_playwright

    args = [] if visible else ["--window-position=-32000,-32000", "--window-size=800,600"]
    res = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=False, args=args)
        try:
            ctx = nav.new_context()
            ctx.new_page().goto(PAGINA_INICIAL, wait_until="networkidle", timeout=90_000)
            for nombre, url in urls.items():
                try:
                    r = ctx.request.get(url, timeout=90_000)
                    if not r.ok:
                        raise RuntimeError(f"HTTP {r.status}")
                    datos = r.body()
                    guardar(datos, destino / nombre)
                    res[nombre] = (True, f"{len(datos) / 1024:.0f} KB (navegador)")
                except Exception as e:  # noqa: BLE001
                    res[nombre] = (False, f"navegador: {e}")
        finally:
            nav.close()
    return res
