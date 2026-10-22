"""Configuración de Django para PresaIA.

La API no usa base de datos: lee los mismos archivos que genera la línea de
comandos (data/processed, models, reports), de modo que el núcleo de
aprendizaje automático en src/presaia/ no se duplica.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent      # backend/
RAIZ_PROYECTO = BASE_DIR.parent                         # presaia/ (config.toml, data, models, reports)
sys.path.insert(0, str(RAIZ_PROYECTO / "src"))          # funciona aunque no se haya hecho `pip install -e .`

SECRET_KEY = os.environ.get("PRESAIA_SECRET_KEY", "solo-desarrollo-cambiar-en-produccion")
DEBUG = os.environ.get("PRESAIA_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("PRESAIA_HOSTS", "localhost,127.0.0.1,testserver").split(",")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "presaia_web.urls"
WSGI_APPLICATION = "presaia_web.wsgi.application"
DATABASES = {}

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = False
USE_TZ = True

# Frontend compilado (cd frontend && npm run build). En desarrollo se usa el
# servidor de Vite, que redirige /api a este backend.
FRONTEND_DIST = RAIZ_PROYECTO / "frontend" / "dist"
STATIC_URL = "static/"

PRESAIA_CONFIG = Path(os.environ.get("PRESAIA_CONFIG", RAIZ_PROYECTO / "config.toml"))
