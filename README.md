# PresaIA — Predicción y alerta temprana del almacenamiento de presas de México

Sistema de aprendizaje automático que estima el volumen almacenado de una presa a **7, 15 y 30 días**,
detecta tendencias de descenso o recuperación y emite avisos configurables. Usa datos públicos del
Sistema de Información Hidrológica (SIH) de CONAGUA y herramientas de software libre.

> Herramienta de **apoyo a la decisión**. No sustituye a CONAGUA, a los organismos operadores ni a un
> sistema certificado de seguridad de presas.

---

## 1. Instalación

Requisitos: Python 3.11 o superior y Node.js 18 o superior (solo para la interfaz web).

Abre PowerShell en la carpeta raíz del proyecto y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium
Set-Location frontend
npm install
npm run build
Set-Location ..
```

## 2. Ejecución rápida con datos de demostración

Con el entorno virtual activo:

```powershell
python -m presaia todo --demo
python backend\manage.py runserver
```

El segundo comando abre el tablero completo, incluido el diseño React compilado, en
`http://localhost:8010`. Si modificaste archivos del frontend, vuelve a ejecutar
`npm run build` antes de reiniciar Django.

> Si `python -m presaia` no encuentra el paquete, ejecuta antes `pip install -e .`
> o antepone `PYTHONPATH=src` (Windows PowerShell: `$env:PYTHONPATH="src"`).

Los datos demo llevan la marca **SINTETICO** en el archivo, en los reportes y en una franja del tablero.
**No deben presentarse como resultados reales.**

### Desarrollo de la interfaz

Con recarga en caliente, en dos terminales:

Terminal 1 (backend):

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver
```

Terminal 2 (frontend):

```powershell
Set-Location frontend
npm run dev
```

Abre `http://localhost:5173`. Vite muestra el diseño con recarga automática y redirige
las peticiones `/api` a Django en `http://127.0.0.1:8010`.

Tras volver a entrenar, reinicia Django o envía `POST /api/recargar` para limpiar la caché.

| Endpoint | Módulo |
|---|---|
| `GET /api/estado`, `/api/presas?q=` | presas disponibles, búsqueda, umbrales base |
| `GET /api/panorama`, `/api/panorama.csv` | panorama general |
| `GET /api/presas/<clave>`, `/serie?periodo=1\|3\|10\|todo`, `/serie.csv` | 1 · Consulta |
| `GET /api/presas/<clave>/pronostico?horizontes=7,30&fecha=AAAA-MM-DD`, `/metricas`, `/backtest/<h>` | 2 · Predicción |
| `GET /api/presas/<clave>/avisos?llenado_atencion_pct=…`, `/reporte.html`, `/pronostico.csv`, `/avisos.json` | 3 · Indicadores y avisos |

## 3. Ejecución con datos reales del SIH

```bash
python -m presaia descargar --todas    # catálogo + ~210 presas (≈5 min, requiere internet)
python -m presaia diagnosticar         # ranking de presas por años con volumen → reports/diagnostico_presas.csv
#   → elegir 3 a 10 presas con buena cobertura y anotarlas en config.toml ([[presas]])
#   → verificar su capacidad NAMO en https://presas.conagua.gob.mx/inventario/
python -m presaia todo                 # preparar → eda → entrenar → predecir
python backend/manage.py runserver
```

Para descargar solo las presas configuradas: `python -m presaia descargar`.

**Descarga automática con Chromium.** El sitio de CONAGUA exige una verificación en JavaScript que
bloquea la descarga directa. Si Playwright está instalado, `descargar` y `actualizar` abren un Chromium
(ventana fuera de la pantalla) que la resuelve y descarga los CSV:

```bash
pip install playwright && python -m playwright install chromium
python -m presaia actualizar             # descargar → preparar → predecir (sin reentrenar)
python -m presaia actualizar --cada 24   # repetir cada 24 h
```

`--metodo directo|navegador` fuerza un método; `--ver-navegador` muestra la ventana. También se pueden
subir los CSV a mano en la sección **Cargar datos** del tablero.

### Opciones útiles

| Opción | Efecto |
|---|---|
| `--demo` | usa los CSV sintéticos de `data/demo/` |
| `--rapido` | omite la búsqueda de hiperparámetros (≈3× más rápido) |
| `--forzar` | entrena aunque la presa no cumpla los criterios de calidad |
| `--config otra.toml` | usa otra configuración |

## 4. Estructura

```
presaia/
├── config.toml               # presas, horizontes, fechas de corte, umbrales — TODO lo configurable
├── src/presaia/
│   ├── io_sih.py             # lectura del formato SIH (metadatos, columnas en distinto orden)
│   ├── limpieza.py           # control de calidad, curva elevación–volumen, banderas, diagnóstico
│   ├── features.py           # variables predictoras sin fuga de información
│   ├── modelos.py            # persistencia, tendencia, regresión lineal, Random Forest, XGBoost
│   ├── evaluacion.py         # partición cronológica con embargo, métricas, ajuste, intervalos
│   ├── prediccion.py         # modelo de producción, guardado y pronóstico operativo
│   ├── alertas.py            # reglas de avisos explicables
│   ├── reporte.py            # reporte HTML/CSV exportable
│   ├── graficos.py           # figuras estáticas (matplotlib) para reportes
│   ├── demo.py               # generador de datos sintéticos en formato SIH
│   └── pipeline.py           # línea de comandos (python -m presaia ...)
├── backend/                  # API en Django: expone el núcleo como JSON (sin base de datos)
│   ├── presaia_web/          #   configuración, rutas; sirve también el frontend compilado
│   └── api/                  #   servicios.py (caché de archivos) y views.py (endpoints)
├── frontend/                 # interfaz en React (Vite + Recharts)
│   ├── src/paginas/          #   Panorama, Consulta, Predicción, Avisos, Acerca de
│   ├── src/MapaPresas.jsx    #   mapa SVG (d3-geo) del panorama
│   └── public/mapa/          #   contorno Natural Earth local: el mapa funciona sin internet
├── tests/                    # pruebas automatizadas (pytest)
├── data/raw/                 # CSV originales del SIH (no se modifican)
├── data/processed/           # series limpias + resumen de calidad (.json)
├── models/                   # modelos entrenados (.joblib) con metadatos
└── reports/                  # métricas, diagnósticos, figuras, predicciones de prueba
```

## 5. Metodología en una página

1. **Objetivo de predicción**: el *cambio* de volumen Δh = V(t+h) − V(t). El pronóstico es V(t) + Δ̂h.
   Los árboles no extrapolan; el cambio es más estable entre años secos y húmedos que el nivel absoluto.
2. **Variables** (solo información disponible el día *t*): volumen y llenado actual, cambios de 1–30 días,
   media y desviación del cambio diario (7/30/90 d), extremos del último año, lluvia acumulada (7/30/90 d)
   y su anomalía, extracciones, evaporación, calendario cíclico.
3. **Partición cronológica** entrenamiento → validación → prueba, con **embargo de h días** entre bloques
   para que ningún objetivo de entrenamiento caiga en el periodo evaluado.
4. **Referencias obligatorias**: persistencia (Δ = 0), tendencia de 30 días y regresión lineal.
5. **Modelos**: Random Forest (principal) y XGBoost (opcional). Hiperparámetros elegidos con validación;
   el de menor MAE en validación pasa a producción.
6. **Evaluación final** una sola vez en prueba: MAE, RMSE, MAE en puntos de llenado, MAPE, sesgo,
   acierto de dirección, mejora vs. persistencia, error por temporada y por mes, precisión/sensibilidad
   de los avisos de descenso.
7. **Incertidumbre**: intervalo conformal por partición (cuantil 90 % del error absoluto en validación);
   se reporta su **cobertura real** en prueba.
8. **Producción**: el modelo elegido se reentrena con todos los datos y se guarda con versión,
   fecha de corte de datos, hiperparámetros y error esperado.

## 6. Pruebas

```bash
pytest -q
```

Incluye: lectura del formato SIH (encabezado, orden de columnas, latin-1, fila truncada), limpieza
(atípicos, huecos cortos/largos, reconstrucción desde nivel), **prueba de no-fuga** (alterar el futuro no
cambia las variables de hoy), embargo de la partición, métricas con valores conocidos, flujo completo de
entrenamiento y pronóstico, reglas de avisos y manejo de errores, y la **API web** (`tests/test_api.py`:
endpoints de cada módulo, simulación en fecha pasada, umbrales incoherentes y exportaciones).

## 7. Reproducibilidad

* Semilla fija en `config.toml` (`[proyecto] semilla`).
* `reports/registro_descargas.csv` guarda URL y fecha de consulta de cada archivo.
* Cada modelo `.joblib` guarda versiones de scikit-learn/pandas; para cargarlo se recomienda la misma
  versión de scikit-learn. Si cambia, reentrenar con `python -m presaia entrenar`.

## 8. Fuentes de datos

* SIH CONAGUA, estaciones en presas: https://sih.conagua.gob.mx/presas.html
* Inventario de Presas: https://presas.conagua.gob.mx/inventario/
* Datos Abiertos CONAGUA: https://datos.conagua.gob.mx/views/index_datos_abiertos.html
