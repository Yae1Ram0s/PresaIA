"""Pruebas de humo de la API de Django que alimenta el frontend en React.

Requiere haber ejecutado antes `python -m presaia todo` (con o sin --demo);
si no hay datos procesados, la prueba se omite.
"""
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
hay_datos = any((RAIZ / "data" / "processed").glob("*.csv")) and any((RAIZ / "models").glob("*.joblib"))
pytestmark = pytest.mark.skipif(not hay_datos, reason="sin datos procesados ni modelos entrenados")

sys.path.insert(0, str(RAIZ / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "presaia_web.settings")


@pytest.fixture(scope="module")
def cliente():
    django = pytest.importorskip("django")
    django.setup()
    from django.test import Client

    return Client()


@pytest.fixture(scope="module")
def clave(cliente):
    return cliente.get("/api/estado").json()["presas"][0]["clave"]


def test_estado_lista_presas(cliente):
    r = cliente.get("/api/estado").json()
    assert r["hay_datos"] and r["presas"]


def test_panorama_ordenado_por_riesgo(cliente):
    r = cliente.get("/api/panorama").json()
    orden = {"critico": 0, "atencion": 1, "normal": 2}
    estados = [orden[p["estado"]] for p in r["presas"]]
    assert estados == sorted(estados)
    assert r["comparativo"]


def test_busqueda_filtra(cliente, clave):
    r = cliente.get("/api/presas", {"q": "Bravo"}).json()
    assert all("Bravo" in p["nombre"] for p in r)


@pytest.mark.parametrize("ruta", ["", "/serie", "/pronostico", "/metricas", "/backtest/7", "/avisos"])
def test_endpoints_de_presa(cliente, clave, ruta):
    assert cliente.get(f"/api/presas/{clave}{ruta}").status_code == 200


def test_pronostico_simulado_incluye_lo_ocurrido(cliente, clave):
    base = cliente.get(f"/api/presas/{clave}/pronostico").json()
    r = cliente.get(f"/api/presas/{clave}/pronostico", {"fecha": base["fecha_minima"], "horizontes": "30"}).json()
    assert r["simulado"] and r["ocurrido"] and [p["horizonte"] for p in r["pronosticos"]] == [30]


def test_umbral_incoherente_da_error(cliente, clave):
    r = cliente.get(f"/api/presas/{clave}/avisos", {"llenado_critico_pct": 60, "llenado_atencion_pct": 40})
    assert r.status_code == 400 and "más severo" in r.json()["error"]


def test_umbral_bajo_genera_aviso_critico(cliente, clave):
    r = cliente.get(f"/api/presas/{clave}/avisos", {"llenado_atencion_pct": 100, "llenado_critico_pct": 100}).json()
    assert r["estado"] == "critico"


@pytest.mark.parametrize("ruta", ["reporte.html", "pronostico.csv", "avisos.json", "serie.csv"])
def test_exportaciones(cliente, clave, ruta):
    r = cliente.get(f"/api/presas/{clave}/{ruta}")
    assert r.status_code == 200 and "attachment" in r["Content-Disposition"]


def test_presa_inexistente_404(cliente):
    assert cliente.get("/api/presas/NOEXISTE").status_code == 404


def test_cargar_rechaza_archivo_invalido(cliente):
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("VBRMX.csv", b"<html>no es csv</html>", content_type="text/csv")
    r = cliente.post("/api/cargar", {"archivos": [f]}).json()
    assert r["actualizado"] is False and r["archivos"][0]["ok"] is False


def test_cargar_sin_archivos_da_error(cliente):
    assert cliente.post("/api/cargar").status_code == 400


def test_actualizar_estado_inicial(cliente):
    r = cliente.get("/api/actualizar").json()
    assert r["en_curso"] is False
