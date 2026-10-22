"""Pruebas de las garantías metodológicas: sin fuga, orden cronológico, métricas, avisos."""
import numpy as np
import pandas as pd
import pytest

from presaia.alertas import Pronostico, evaluar_avisos, nivel_global
from presaia.evaluacion import experimento, metricas, particion_cronologica
from presaia.features import construir_features, matriz_entrenamiento
from presaia.prediccion import pronosticar


def test_features_no_usan_el_futuro(serie_limpia, presa, cfg):
    """Si se altera todo lo posterior a t, las variables en t no deben cambiar."""
    t = pd.Timestamp("2015-06-15")
    X1 = construir_features(serie_limpia, presa, cfg)
    alterada = serie_limpia.copy()
    alterada.loc[alterada.index > t, ["volumen_hm3", "precip_mm", "obra_toma_m3s", "evap_mm"]] *= 3.7
    X2 = construir_features(alterada, presa, cfg)
    pd.testing.assert_series_equal(X1.loc[t], X2.loc[t])


def test_objetivo_es_cambio_futuro(serie_limpia, presa, cfg):
    X, y, vol = matriz_entrenamiento(serie_limpia, presa, cfg, 7)
    t = X.index[100]
    esperado = serie_limpia.loc[t + pd.Timedelta(days=7), "volumen_hm3"] - serie_limpia.loc[t, "volumen_hm3"]
    assert y.loc[t] == pytest.approx(esperado)
    assert X.index.max() <= serie_limpia.index.max() - pd.Timedelta(days=7)


@pytest.mark.parametrize("h", [7, 30])
def test_particion_cronologica_con_embargo(serie_limpia, presa, cfg, h):
    X, _, _ = matriz_entrenamiento(serie_limpia, presa, cfg, h)
    p = particion_cronologica(X.index, cfg, h)
    assert p.entrenamiento.max() + pd.Timedelta(days=h) < p.validacion.min()
    assert p.validacion.max() + pd.Timedelta(days=h) < p.prueba.min()
    assert not set(p.entrenamiento) & set(p.prueba)


def test_particion_proporcional_si_las_fechas_no_alcanzan(serie_limpia, presa, cfg):
    cfg._d["modelo"]["inicio_prueba"] = "2030-01-01"
    X, _, _ = matriz_entrenamiento(serie_limpia, presa, cfg, 7)
    p = particion_cronologica(X.index, cfg, 7)
    assert p.metodo == "proporcional_70_15_15" and len(p.prueba) > 0


def test_metricas_valores_conocidos():
    real = np.array([50.0, 60.0, 70.0])
    pred = np.array([52.0, 58.0, 70.0])
    m = metricas(real, pred, vol_actual=[50, 50, 50], capacidad=100, mae_persistencia=4.0)
    assert m["MAE_hm3"] == pytest.approx(4 / 3, abs=1e-3)
    assert m["RMSE_hm3"] == pytest.approx(np.sqrt(8 / 3), abs=1e-3)
    assert m["mejora_vs_persistencia_pct"] == pytest.approx((1 - (4 / 3) / 4) * 100, abs=0.01)


def test_experimento_y_pronostico_de_punta_a_punta(serie_limpia, presa, cfg):
    X, y, vol = matriz_entrenamiento(serie_limpia, presa, cfg, 7)
    res = experimento(X, y, vol, presa, cfg, 7, ajustar=False)
    assert res.mejor_modelo in ("random_forest", "xgboost")
    mejor = res.metricas_prueba[res.mejor_modelo]
    assert mejor["MAE_hm3"] < res.metricas_prueba["persistencia"]["MAE_hm3"]  # la señal estacional es aprendible
    paquete = {7: {"modelo": res.modelo_final, "columnas": res.columnas, "cuantil_error_hm3": res.cuantil_error_hm3,
                   "nombre_modelo": res.mejor_modelo, "mae_prueba_hm3": mejor["MAE_hm3"]}}
    pron = pronosticar(serie_limpia, presa, cfg, paquete)
    assert len(pron) == 1 and pron[0].inf_hm3 <= pron[0].volumen_hm3 <= pron[0].sup_hm3
    with pytest.raises(ValueError):
        pronosticar(serie_limpia, presa, cfg, paquete, pd.Timestamp("1999-01-01"))


def _pron(vol, h=30):
    return [Pronostico(h, pd.Timestamp("2018-12-31") + pd.Timedelta(days=h), vol, vol - 2, vol + 2, "random_forest", 1.0)]


def test_avisos_por_umbral(serie_limpia, presa, cfg):
    hoy = serie_limpia.index[-1]
    v0 = serie_limpia["volumen_hm3"].iloc[-1]
    sin = evaluar_avisos(serie_limpia, _pron(v0), presa, cfg, hoy)
    assert nivel_global([a for a in sin if a.tipo != "tendencia"]) == "normal"
    critico = evaluar_avisos(serie_limpia, _pron(v0 - 10), presa, cfg, hoy)  # −10 pp
    assert any(a.tipo == "descenso_proyectado" and a.nivel == "critico" for a in critico)
    bajo = evaluar_avisos(serie_limpia, _pron(20.0), presa, cfg, hoy)          # 20 % < 25 %
    assert any(a.tipo == "llenado_bajo" and a.nivel == "critico" for a in bajo)
    assert nivel_global(bajo) == "critico"


def test_aviso_datos_desactualizados(serie_limpia, presa, cfg):
    hoy = serie_limpia.index[-1] + pd.Timedelta(days=40)
    avisos = evaluar_avisos(serie_limpia, [], presa, cfg, hoy)
    assert any(a.tipo == "calidad_datos" and "desactualizados" in a.titulo for a in avisos)
