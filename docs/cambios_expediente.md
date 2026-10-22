# Cambios al expediente técnico: migración del tablero a Django + React

Texto listo para sustituir en *PresaIA — Expediente técnico del proyecto*. Solo cambian las secciones
que mencionan Streamlit, Plotly o el número de pruebas; las Fases 2 a 5 (datos, limpieza, modelos y
validación) no cambian, porque el núcleo `src/presaia/` no se modificó.

---

## Resumen ejecutivo (primer párrafo)

> PresaIA estima el almacenamiento de una presa a 7, 15 y 30 días y emite avisos explicables cuando lo
> proyectado cruza umbrales configurables. Usa registros diarios públicos del SIH de CONAGUA, modelos
> Random Forest y XGBoost, una API en Django y una aplicación web en React.

## Fase 1 — Requisitos de aceptación (filas que cambian)

| # | Requisito | Cómo se verifica |
|---|---|---|
| RA5 | La aplicación web muestra los 3 módulos y exporta un reporte | `tests/test_api.py` (endpoints de cada módulo y exportaciones) + pruebas funcionales de la Fase 7 |
| RA6 | Cada aviso muestra motivo, datos e incertidumbre | Revisión del Módulo 3; `GET /api/presas/<clave>/avisos` devuelve `motivo` y `datos` |

## Fase 6 — Aplicación funcional y manual de usuario

**Párrafo de apertura**

> La aplicación tiene dos capas: una API en Django que expone como JSON los archivos que genera la línea
> de comandos, y una interfaz en React que los presenta. Ninguna capa duplica la lógica del núcleo de
> aprendizaje automático.

**Diagrama de arquitectura**: sustituir la caja «Tablero · Streamlit + reportes» por dos cajas:

```
… → Pronóstico (intervalo + avisos) → API Django (JSON, sin base de datos) → Interfaz React (Vite + Recharts)
```

Pie del diagrama: *config.toml define presas, horizontes, fechas de corte y umbrales para todas las etapas.*

**Título de la tabla de módulos**: «Módulos de la aplicación (`frontend/src/paginas/`)». Agregar la fila:

| Módulo | Funciones | Requisito de la propuesta cubierto |
|---|---|---|
| Panorama general | Indicadores conjuntos ponderados por capacidad; mapa de ubicación y estado; llenado del último año de todas las presas; tabla ordenada por riesgo con acceso al detalle; descarga CSV | Vista general y priorización entre presas |

Las filas 1 · Consulta, 2 · Predicción y 3 · Indicadores y avisos se conservan igual.

**Endpoints de la API** (tabla nueva, después de la de módulos):

| Endpoint | Módulo |
|---|---|
| `GET /api/estado`, `/api/presas?q=` | Presas disponibles, búsqueda y umbrales base |
| `GET /api/panorama`, `/api/panorama.csv` | Panorama general |
| `GET /api/presas/<clave>`, `/serie`, `/serie.csv` | 1 · Consulta |
| `GET /api/presas/<clave>/pronostico`, `/metricas`, `/backtest/<h>` | 2 · Predicción |
| `GET /api/presas/<clave>/avisos`, `/reporte.html`, `/pronostico.csv`, `/avisos.json` | 3 · Indicadores y avisos |

**Manual de usuario — Instalación (una sola vez)**

1. Instalar Python 3.11 o superior y Node.js 18 o superior.
2. En la carpeta del proyecto: `python -m venv .venv`, activar el entorno y ejecutar
   `pip install -r requirements.txt` y `pip install -e .`
3. Compilar la interfaz: `cd frontend`, `npm install` y `npm run build`.

**Manual de usuario — Usar la aplicación**

1. `python backend/manage.py runserver` abre la aplicación en `http://localhost:8010`.
2. En la barra lateral, escribir parte del nombre o el estado y elegir la presa.
3. **Panorama general**: revisar el estado conjunto; hacer clic en una presa del mapa o de la tabla para
   abrir su detalle.
4. **Consulta**: revisar el llenado actual y la serie; cambiar unidad y periodo con los botones sobre la
   gráfica.
5. **Predicción**: elegir horizontes; activar «Simular un pronóstico en una fecha pasada» para ver cómo se
   habría comportado el modelo en una fecha concreta.
6. **Indicadores y avisos**: ajustar umbrales; leer cada aviso y abrir «Datos utilizados»; descargar el
   reporte.

Tras volver a entrenar, reiniciar el servidor (o enviar `POST /api/recargar`) para que la aplicación lea
los modelos nuevos.

**Mensajes frecuentes** (filas que cambian; las demás se conservan):

| Mensaje | Significado | Qué hacer |
|---|---|---|
| No se pudo conectar con la API | El servidor de Django no está en ejecución | `python backend/manage.py runserver` |
| Frontend no compilado | Falta la carpeta `frontend/dist` | `cd frontend && npm install && npm run build` |
| Datos de demostración (franja amarilla) | Se están usando datos sintéticos | No usar las cifras; ejecutar con datos del SIH |

## Fase 7 — Pruebas y preparación comercial

**Párrafo de apertura**

> Las 34 pruebas automatizadas pasan (17 del núcleo y 17 de la API web); las pruebas funcionales de la
> interfaz y la de aceptación con datos reales quedan como lista a ejecutar por el equipo, con evidencia
> en capturas.

**Sustituir el párrafo sobre `test_app.py` por:**

> Las 17 pruebas de la API (`tests/test_api.py`) usan el cliente de pruebas de Django y verifican que cada
> endpoint responda, que el panorama salga ordenado por riesgo, que la simulación en fecha pasada incluya
> lo ocurrido, que un umbral incoherente devuelva error 400, que umbrales severos generen un aviso
> crítico, que las cuatro exportaciones se descarguen y que una presa inexistente devuelva 404.

**Pruebas funcionales**: F1 a F6 se conservan; ahora además las cubre la API de forma automática.
Cambian:

- F7 · Descargar el reporte HTML desde el Módulo 3 y abrirlo en otro equipo
- F8 · Borrar `models/` y reiniciar el servidor: Predicción muestra el mensaje de modelos faltantes sin
  romper la aplicación
- F11 (nueva) · Hacer clic en una presa del mapa del panorama abre su módulo de Consulta
- F12 (nueva) · Con el sistema en modo oscuro, la aplicación cambia de tema y el mapa y las gráficas se
  leen bien

**Tabla de costos — fila de licencias**: «Python, scikit-learn, XGBoost, Django, React — 0».

## Fase 8 — Entrega final (filas que cambian)

| # | Bloque | Entregable | Evidencia en el proyecto | Estado |
|---|---|---|---|---|
| 11 | Software | Código fuente completo y README | `src/presaia/`, `backend/`, `frontend/`, README | Listo |
| 12 | Software | Aplicación ejecutable o instrucciones | `backend/manage.py runserver` + `frontend/`, README §1–2 | Listo |
| 13 | Software | Pruebas funcionales y de manejo de errores | `tests/` (34 automatizadas) + lista F1–F12 de la Fase 7 | En proceso |
| 14 | Software | Manual de usuario y capturas | Fase 6 (faltan capturas de la aplicación web) | En proceso |

## Licencias (sustituir la tabla)

| Componente | Licencia |
|---|---|
| Python | PSF License |
| pandas, NumPy, scikit-learn, Django | BSD-3-Clause |
| XGBoost | Apache 2.0 |
| Matplotlib | Licencia de Matplotlib (basada en PSF) |
| React, React Router, Recharts, Vite | MIT |
| d3-geo, topojson-client | ISC |
| Contorno del mapa (Natural Earth, empaquetado por sane-topojson) | Dominio público / MIT |
| Datos del SIH e Inventario de Presas | Información pública de CONAGUA; citar la fuente y verificar los términos del portal antes de redistribuir los archivos |

## Limitaciones (agregar una viñeta)

- **Aplicación local**: el servidor de desarrollo de Django no está pensado para uso público. Para
  publicarla se necesita un servidor de aplicaciones (por ejemplo, gunicorn o waitress), una
  `PRESAIA_SECRET_KEY` propia, `PRESAIA_DEBUG=0` y una autenticación que restrinja el acceso.

## Fuentes y referencias (sustituir la última línea)

- Documentación de scikit-learn — RandomForestRegressor.
- Documentación de Django y de React.
