"""Partición cronológica, métricas, ajuste de hiperparámetros e incertidumbre.

Esquema de validación (sin mezclar el orden temporal):

    |------------ entrenamiento ------------|emb|---- validación ----|emb|---- prueba ----|
                                             ^                          ^
    "emb" = embargo de h días: se eliminan las últimas h filas de cada bloque
    porque su objetivo V(t+h) cae dentro del bloque siguiente (fuga sutil).

1. Se ajustan hiperparámetros con entrenamiento → validación.
2. Con los residuos en validación se calibra el intervalo de incertidumbre
   (método conformal por partición: cuantil del error absoluto).
3. Se reentrena con entrenamiento+validación y se evalúa UNA vez en prueba.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import Config, Presa
from .modelos import MODELOS_ML, MODELOS_REFERENCIA, crear_modelo


# ---------------------------------------------------------------------------
# Partición
# ---------------------------------------------------------------------------
@dataclass
class Particion:
    entrenamiento: pd.DatetimeIndex
    validacion: pd.DatetimeIndex
    prueba: pd.DatetimeIndex
    metodo: str

    def resumen(self) -> dict:
        def r(ix):
            return {"inicio": str(ix.min().date()), "fin": str(ix.max().date()), "filas": len(ix)} if len(ix) else None
        return {"metodo": self.metodo, "entrenamiento": r(self.entrenamiento),
                "validacion": r(self.validacion), "prueba": r(self.prueba)}


def particion_cronologica(indice: pd.DatetimeIndex, cfg: Config, horizonte: int) -> Particion:
    m = cfg["modelo"]
    iv, ip = pd.Timestamp(m["inicio_validacion"]), pd.Timestamp(m["inicio_prueba"])
    tr, va, te = indice[indice < iv], indice[(indice >= iv) & (indice < ip)], indice[indice >= ip]
    metodo = "fechas_config"
    # Si las fechas configuradas no dejan bloques útiles (series que terminan antes),
    # se usa 70/15/15 cronológico.
    if min(len(tr), len(va), len(te)) < 180:
        n = len(indice)
        a, b = int(n * 0.70), int(n * 0.85)
        tr, va, te = indice[:a], indice[a:b], indice[b:]
        metodo = "proporcional_70_15_15"
    emb = pd.Timedelta(days=horizonte)
    if len(va):
        tr = tr[tr < va.min() - emb]
    if len(te):
        va = va[va < te.min() - emb]
    return Particion(tr, va, te, metodo)


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def metricas(y_real_vol, y_pred_vol, vol_actual, capacidad, mae_persistencia=None) -> dict:
    y_real_vol, y_pred_vol = np.asarray(y_real_vol), np.asarray(y_pred_vol)
    err = y_pred_vol - y_real_vol
    mae = mean_absolute_error(y_real_vol, y_pred_vol)
    rmse = float(np.sqrt(mean_squared_error(y_real_vol, y_pred_vol)))
    # MAPE solo donde el volumen es suficientemente grande (evita dividir entre ~0)
    m = y_real_vol > 0.05 * capacidad
    mape = float(np.mean(np.abs(err[m]) / y_real_vol[m]) * 100) if m.any() else np.nan
    # Acierto en la dirección del cambio (sube/baja), ignorando cambios mínimos
    d_real = y_real_vol - np.asarray(vol_actual)
    d_pred = y_pred_vol - np.asarray(vol_actual)
    relevante = np.abs(d_real) > 0.002 * capacidad
    direccion = float(np.mean(np.sign(d_real[relevante]) == np.sign(d_pred[relevante]))) if relevante.any() else np.nan
    out = {
        "MAE_hm3": round(float(mae), 3),
        "RMSE_hm3": round(rmse, 3),
        "MAE_pp_llenado": round(float(mae / capacidad * 100), 3),
        "MAPE_pct": round(mape, 3),
        "sesgo_hm3": round(float(err.mean()), 3),
        "acierto_direccion": round(direccion, 3),
        "n": int(len(y_real_vol)),
    }
    if mae_persistencia:
        out["mejora_vs_persistencia_pct"] = round(float((1 - mae / mae_persistencia) * 100), 2)
    return out


def metricas_por_temporada(fechas, y_real, y_pred, vol_act, cap) -> dict:
    lluvias = pd.DatetimeIndex(fechas).month.isin([6, 7, 8, 9, 10])
    res = {}
    for nombre, mask in (("lluvias_jun_oct", lluvias), ("estiaje_nov_may", ~lluvias)):
        if mask.sum() > 30:
            res[nombre] = metricas(np.asarray(y_real)[mask], np.asarray(y_pred)[mask], np.asarray(vol_act)[mask], cap)
    return res


def evaluar_avisos_descenso(y_real, y_pred, vol_act, cap, umbral_pp: float) -> dict:
    """¿Qué tan bien anticipa el modelo descensos ≥ umbral_pp puntos de llenado?"""
    real = (np.asarray(vol_act) - np.asarray(y_real)) / cap * 100 >= umbral_pp
    pred = (np.asarray(vol_act) - np.asarray(y_pred)) / cap * 100 >= umbral_pp
    vp, fp, fn = int((real & pred).sum()), int((~real & pred).sum()), int((real & ~pred).sum())
    precision = vp / (vp + fp) if vp + fp else np.nan
    sensibilidad = vp / (vp + fn) if vp + fn else np.nan
    return {"umbral_pp": umbral_pp, "eventos_reales": int(real.sum()), "avisos_emitidos": int(pred.sum()),
            "verdaderos_positivos": vp, "falsos_positivos": fp, "falsos_negativos": fn,
            "precision": None if np.isnan(precision) else round(precision, 3),
            "sensibilidad": None if np.isnan(sensibilidad) else round(sensibilidad, 3)}


# ---------------------------------------------------------------------------
# Ajuste de hiperparámetros (solo con validación)
# ---------------------------------------------------------------------------
REJILLA_RF = {"max_depth": [8, 14, None], "min_samples_leaf": [3, 10]}
REJILLA_XGB = {"max_depth": [3, 5], "learning_rate": [0.03, 0.08]}


def ajustar_hiperparametros(nombre, X_tr, y_tr, X_va, y_va, cfg, horizonte, capacidad):
    rejilla = REJILLA_RF if nombre == "random_forest" else REJILLA_XGB
    resultados = []
    for valores in product(*rejilla.values()):
        params = dict(zip(rejilla.keys(), valores))
        extra = {"n_estimators": 100} if nombre == "random_forest" else {}
        mdl = crear_modelo(nombre, cfg, horizonte, capacidad, **params, **extra)
        mdl.fit(X_tr, y_tr)
        mae = mean_absolute_error(y_va, mdl.predict(X_va))
        resultados.append({**params, "MAE_validacion_hm3": round(float(mae), 4)})
    mejor = min(resultados, key=lambda r: r["MAE_validacion_hm3"])
    params = {k: v for k, v in mejor.items() if k != "MAE_validacion_hm3"}
    return params, resultados


# ---------------------------------------------------------------------------
# Experimento completo para una presa y un horizonte
# ---------------------------------------------------------------------------
@dataclass
class ResultadoHorizonte:
    horizonte: int
    particion: dict
    metricas_validacion: dict
    metricas_prueba: dict
    por_temporada: dict
    avisos_descenso: dict
    hiperparametros: dict
    busqueda: dict
    mejor_modelo: str
    cuantil_error_hm3: float
    cobertura_intervalo_prueba: float
    predicciones_prueba: pd.DataFrame
    modelo_final: object = field(repr=False)
    columnas: list[str] = field(default_factory=list)


def experimento(X: pd.DataFrame, y: pd.Series, vol: pd.Series, presa: Presa, cfg: Config,
                horizonte: int, ajustar: bool = True) -> ResultadoHorizonte:
    cap = presa.capacidad_namo_hm3
    part = particion_cronologica(X.index, cfg, horizonte)
    tr, va, te = part.entrenamiento, part.validacion, part.prueba
    conf = cfg["incertidumbre"]["nivel_confianza"]

    # --- 1) Validación: todos los modelos entrenados solo con 'entrenamiento'
    met_val, preds_val, hiper, busqueda = {}, {}, {}, {}
    for nombre in MODELOS_REFERENCIA + MODELOS_ML:
        params = {}
        if ajustar and nombre in MODELOS_ML:
            params, busqueda[nombre] = ajustar_hiperparametros(
                nombre, X.loc[tr], y.loc[tr], X.loc[va], y.loc[va], cfg, horizonte, cap)
            hiper[nombre] = params
        mdl = crear_modelo(nombre, cfg, horizonte, cap, **params).fit(X.loc[tr], y.loc[tr])
        preds_val[nombre] = mdl.predict(X.loc[va])
    mae_p = mean_absolute_error(y.loc[va], preds_val["persistencia"])
    for nombre, p in preds_val.items():
        met_val[nombre] = metricas(vol.loc[va] + y.loc[va], vol.loc[va] + p, vol.loc[va], cap, mae_p)

    # El modelo de ML con menor MAE en validación pasa a producción
    mejor = min(MODELOS_ML, key=lambda n: met_val[n]["MAE_hm3"])
    residuos_val = np.abs(y.loc[va].to_numpy() - preds_val[mejor])
    q = float(np.quantile(residuos_val, conf))

    # --- 2) Prueba: reentrenar con entrenamiento+validación (respetando embargo)
    trva = X.index[X.index < te.min() - pd.Timedelta(days=horizonte)]
    met_te, preds_te = {}, {}
    finales = {}
    for nombre in MODELOS_REFERENCIA + MODELOS_ML:
        mdl = crear_modelo(nombre, cfg, horizonte, cap, **hiper.get(nombre, {})).fit(X.loc[trva], y.loc[trva])
        preds_te[nombre] = mdl.predict(X.loc[te])
        finales[nombre] = mdl
    real_te = vol.loc[te] + y.loc[te]
    mae_p_te = mean_absolute_error(y.loc[te], preds_te["persistencia"])
    for nombre, p in preds_te.items():
        met_te[nombre] = metricas(real_te, vol.loc[te] + p, vol.loc[te], cap, mae_p_te)

    pred_mejor = vol.loc[te] + preds_te[mejor]
    cobertura = float(np.mean(np.abs(real_te - pred_mejor) <= q))
    tabla = pd.DataFrame({
        "volumen_actual_hm3": vol.loc[te],
        "real_hm3": real_te,
        "pred_hm3": pred_mejor,
        "pred_persistencia_hm3": vol.loc[te],
        "inf_hm3": (pred_mejor - q).clip(lower=0),
        "sup_hm3": pred_mejor + q,
    })
    # La fecha de la tabla es la fecha OBJETIVO (t+h), útil para graficar contra lo observado
    tabla.index = tabla.index + pd.Timedelta(days=horizonte)
    tabla.index.name = "fecha_objetivo"

    al = cfg["alertas"]
    return ResultadoHorizonte(
        horizonte=horizonte,
        particion=part.resumen(),
        metricas_validacion=met_val,
        metricas_prueba=met_te,
        por_temporada=metricas_por_temporada(te, real_te, pred_mejor, vol.loc[te], cap),
        avisos_descenso={
            "atencion": evaluar_avisos_descenso(real_te, pred_mejor, vol.loc[te], cap, al["descenso_atencion_pp"]),
            "critico": evaluar_avisos_descenso(real_te, pred_mejor, vol.loc[te], cap, al["descenso_critico_pp"]),
        },
        hiperparametros=hiper,
        busqueda=busqueda,
        mejor_modelo=mejor,
        cuantil_error_hm3=round(q, 4),
        cobertura_intervalo_prueba=round(cobertura, 4),
        predicciones_prueba=tabla,
        modelo_final=finales[mejor],
        columnas=list(X.columns),
    )
