from django.urls import path

from . import views

urlpatterns = [
    path("estado", views.estado),
    path("recargar", views.recargar),
    path("cargar", views.cargar),
    path("actualizar", views.actualizar),
    path("panorama", views.panorama),
    path("panorama.csv", views.panorama_csv),
    path("presas", views.presas),
    path("presas/<str:clave>", views.consulta),
    path("presas/<str:clave>/serie", views.serie),
    path("presas/<str:clave>/serie.csv", views.serie_csv),
    path("presas/<str:clave>/pronostico", views.pronostico),
    path("presas/<str:clave>/metricas", views.metricas),
    path("presas/<str:clave>/backtest/<int:h>", views.backtest),
    path("presas/<str:clave>/avisos", views.avisos),
    path("presas/<str:clave>/reporte.html", views.reporte_html),
    path("presas/<str:clave>/pronostico.csv", views.pronostico_csv),
    path("presas/<str:clave>/avisos.json", views.avisos_json),
]
