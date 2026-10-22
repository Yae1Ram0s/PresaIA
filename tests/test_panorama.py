"""Pruebas del resumen de todas las presas (base del dashboard de inicio)."""
import pandas as pd
import pytest

from presaia.config import Config, Presa
from presaia.evaluacion import experimento
from presaia.features import matriz_entrenamiento
from presaia.panorama import indicadores_globales, resumen_presas


@pytest.fixture
def escenario(cfg, serie_limpia, presa):
    """Tres presas: una sana, una con descenso fuerte reciente y una sin modelo."""
    X, y, vol = matriz_entrenamiento(serie_limpia, presa, cfg, 7)
    res = experimento(X, y, vol, presa, cfg, 7, ajustar=False)
    paquete = {7: {"modelo": res.modelo_final, "columnas": res.columnas, "nombre_modelo": res.mejor_modelo,
                   "cuantil_error_hm3": res.cuantil_error_hm3, "mae_prueba_hm3": 1.0}}

    seca = serie_limpia.copy()
    seca["volumen_hm3"] = seca["volumen_hm3"] * 0.3          # ~18 % de llenado: crítico
    seca["llenado_pct"] = seca["volumen_hm3"]

    d = dict(cfg._d)
    d["presas"] = [
        {"clave": "SANA1", "nombre": "Sana", "estado": "México", "sistema": "A", "capacidad_namo_hm3": 100.0,
         "latitud": 19.0, "longitud": -99.0},
        {"clave": "SECA1", "nombre": "Seca", "estado": "Sonora", "sistema": "B", "capacidad_namo_hm3": 100.0,
         "latitud": 29.0, "longitud": -110.0},
        {"clave": "SINM1", "nombre": "Sin modelo", "estado": "Jalisco", "sistema": "C", "capacidad_namo_hm3": 100.0},
    ]
    cfg3 = Config(d, cfg.raiz)
    series = {"SANA1": (serie_limpia, {"origen_datos": "SIH-CONAGUA"}),
              "SECA1": (seca, {"origen_datos": "SIH-CONAGUA"}),
              "SINM1": (serie_limpia, {"origen_datos": "SINTETICO"})}
    paquetes = {"SANA1": paquete, "SECA1": paquete}
    return cfg3, series, paquetes


def test_resumen_ordena_por_riesgo(escenario):
    cfg3, series, paquetes = escenario
    tabla = resumen_presas(cfg3, series, paquetes, hoy=pd.Timestamp("2019-01-01"))
    assert list(tabla.columns[:3]) == ["clave", "presa", "estado_rep"]
    assert tabla.iloc[0]["clave"] == "SECA1" and tabla.iloc[0]["estado"] == "critico"
    assert len(tabla.iloc[0]["historia_90d"]) == 90
    sin_modelo = tabla.set_index("clave").loc["SINM1"]
    assert not sin_modelo["tiene_modelo"] and pd.isna(sin_modelo["llenado_proyectado_pct"])


def test_indicadores_globales_ponderados(escenario):
    cfg3, series, paquetes = escenario
    tabla = resumen_presas(cfg3, series, paquetes, hoy=pd.Timestamp("2019-01-01"))
    g = indicadores_globales(tabla)
    assert g["presas"] == 3 and g["en_critico"] >= 1
    assert g["llenado_conjunto_pct"] == pytest.approx(100 * tabla["volumen_hm3"].sum() / 300)
    assert g["hay_sinteticos"]
    assert g["llenado_conjunto_proyectado_pct"] is not None  # solo con las presas que tienen modelo


def test_resumen_vacio(cfg):
    assert resumen_presas(cfg, {}, {}).empty
    assert indicadores_globales(pd.DataFrame()) == {}
