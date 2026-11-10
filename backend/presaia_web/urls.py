from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def frontend(request, ruta=""):
    """Sirve la aplicación React compilada; cualquier ruta desconocida devuelve index.html."""
    indice = settings.FRONTEND_DIST / "index.html"
    if not indice.exists():
        return HttpResponse("Frontend no compilado. Ejecuta: cd frontend && npm install && npm run build "
                            "(o usa npm run dev en http://localhost:5173).", status=503, content_type="text/plain")
    return FileResponse(open(indice, "rb"), content_type="text/html")


urlpatterns = [
    path("api/", include("api.urls")),
    re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIST / "assets"}),
    re_path(r"^mapa/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIST / "mapa"}),
    re_path(
        r"^(?P<path>[^/]+\.(?:png|jpg|jpeg|svg|webp|ico))$",
        serve,
        {"document_root": settings.FRONTEND_DIST},
    ),
    re_path(r"^(?P<ruta>.*)$", frontend),
]
