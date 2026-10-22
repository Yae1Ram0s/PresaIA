"""Pruebas de lectura del formato SIH y de la limpieza."""
import numpy as np
import pandas as pd
import pytest

from presaia.io_sih import SerieSIH, leer_csv_sih
from presaia.limpieza import limpiar_serie

CSV_SIH = """Comisión Nacional del Agua
Subdirección General Técnica
Estación: Valle de Bravo, Méx.
Clave: VBRMX
Estado: México

Estacion,Fecha,Nivel(m),Precipitacion(mm),VolumenAlm(Mm3),ObraToma(m3/s),Vertedor(m3/s),Derrame(m3/s),Evaporacion(mm)
VBRMX,2020-01-01,1819.24,0.0,300.5,,,,
VBRMX,2020-01-02,1819.20,,300.1,,,,
VBRMX,2020-01-02,1819.20,,300.2,,,,
VBRMX,2020-01-03,1819.18,2.5,299.9,,,,
VBRMX,2020-01-0"""


def test_lee_formato_sih_con_metadatos(tmp_path):
    ruta = tmp_path / "VBRMX.csv"
    ruta.write_text(CSV_SIH, encoding="utf-8")
    s = leer_csv_sih(ruta)
    assert s.clave == "VBRMX"
    assert s.metadatos["estacion"].startswith("Valle de Bravo")
    assert list(s.datos.index.strftime("%Y-%m-%d")) == ["2020-01-01", "2020-01-02", "2020-01-03"]  # fila truncada fuera
    assert s.datos.loc["2020-01-02", "volumen_hm3"] == pytest.approx(300.2)  # duplicado: se queda el último
    assert not s.es_sintetica


def test_orden_de_columnas_distinto_y_latin1(tmp_path):
    texto = ("Clave: CPRNL\n\nEstacion,Fecha,Precipitacion(mm),Nivel(m),VolumenAlm(Mm3),Evaporacion(mm)\n"
             "CPRNL,1990-05-01,35.0,,120.0,6.1\n")
    ruta = tmp_path / "CPRNL.csv"
    ruta.write_bytes(texto.encode("latin-1"))
    s = leer_csv_sih(ruta)
    fila = s.datos.iloc[0]
    assert fila["precip_mm"] == 35.0 and fila["volumen_hm3"] == 120.0 and fila["evap_mm"] == 6.1
    assert np.isnan(fila["obra_toma_m3s"])  # columna ausente se crea vacía


def test_archivo_sin_encabezado_falla(tmp_path):
    ruta = tmp_path / "malo.csv"
    ruta.write_text("esto no es un archivo del SIH\n1,2,3\n")
    with pytest.raises(ValueError, match="encabezado"):
        leer_csv_sih(ruta)


def _sih(df, clave="TEST1"):
    return SerieSIH(clave=clave, datos=df[["volumen_hm3", "nivel_m", "precip_mm", "obra_toma_m3s",
                                           "vertedor_m3s", "derrame_m3s", "evap_mm"]].copy())


def test_limpieza_atipicos_y_huecos(serie_limpia, presa, cfg):
    df = serie_limpia.copy()
    df["nivel_m"] = np.nan                            # sin nivel: no hay reconstrucción
    df.loc["2012-03-10", "volumen_hm3"] = 900.0       # fuera de rango físico
    df.loc["2012-06-15", "volumen_hm3"] = 5.0         # pico aislado
    df.loc["2013-01-01":"2013-01-04", "volumen_hm3"] = np.nan   # hueco corto (4 días)
    df.loc["2014-01-01":"2014-01-20", "volumen_hm3"] = np.nan   # hueco largo (20 días)
    res = limpiar_serie(_sih(df), presa, cfg)
    s = res.serie
    assert s.loc["2012-03-10", "bandera_volumen"] == "atipico_eliminado" or s.loc["2012-03-10", "bandera_volumen"] == "interpolado"
    assert s.loc["2012-06-15", "volumen_hm3"] != 5.0
    assert (s.loc["2013-01-01":"2013-01-04", "bandera_volumen"] == "interpolado").all()
    assert s.loc["2014-01-01":"2014-01-20", "volumen_hm3"].isna().all()
    assert res.resumen["atipicos_eliminados"] >= 2
    assert res.resumen["apta"]


def test_reconstruccion_desde_nivel(serie_limpia, presa, cfg):
    df = serie_limpia.copy()
    df.loc["2011-01-01":"2011-03-31", "volumen_hm3"] = np.nan   # hay nivel, falta volumen
    res = limpiar_serie(_sih(df), presa, cfg)
    tramo = res.serie.loc["2011-01-01":"2011-03-31"]
    assert res.resumen["curva_usada"]
    assert (tramo["bandera_volumen"] == "reconstruido_nivel").all()
    real = serie_limpia.loc["2011-01-01":"2011-03-31", "volumen_hm3"]
    assert (tramo["volumen_hm3"] - real).abs().max() < 1.0
