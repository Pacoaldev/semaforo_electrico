"""
Vistas relacionadas con la PWA (Progressive Web App) y tareas programadas.

El Service Worker se sirve desde la RAÍZ del sitio (/sw.js) para poder
controlar todo el ámbito del dominio (scope '/'). Si se sirviera solo desde
/static/sw.js, por defecto su scope quedaría limitado a /static/.
"""

import io
import logging
import secrets
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def health(request):
    """Endpoint simple de salud para plataformas de despliegue."""
    return JsonResponse({"status": "ok"})


@require_GET
def refresh_prices(request):
    """
    Endpoint protegido que ejecuta la captura de precios de OMIE (fetch_prices).

    Se protege con el token CRON_SECRET_TOKEN, que debe enviarse en la
    cabecera "X-Cron-Token". Si el token no está configurado o no coincide,
    responde 403 (fail-closed).

    Notas de seguridad:
    - La comparación se hace en tiempo constante (secrets.compare_digest) para
      no filtrar el token por timing.
    - No se devuelve la salida del comando ni el detalle de excepciones, para
      no exponer información interna. Los errores se registran en el log.

    Pensado para ser invocado por un cron externo gratuito
    (GitHub Actions, cron-job.org, etc.).
    """
    expected = settings.CRON_SECRET_TOKEN
    provided = request.headers.get("X-Cron-Token") or ""

    # Fail-closed: sin token configurado o sin coincidencia exacta -> 403.
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        return JsonResponse({"detail": "No autorizado."}, status=403)

    out = io.StringIO()
    try:
        call_command("fetch_prices", stdout=out)
    except Exception:  # noqa: BLE001
        logger.exception("Error al refrescar precios desde el endpoint protegido.")
        return JsonResponse(
            {"status": "error", "detail": "Error interno al refrescar precios."},
            status=500,
        )

    return JsonResponse({"status": "ok"}, status=200)


def service_worker(request):
    """Sirve el Service Worker desde /sw.js con scope raíz."""
    sw_path: Path = Path(settings.BASE_DIR) / "static" / "sw.js"
    if not sw_path.exists():
        raise Http404("Service worker no encontrado.")

    response = FileResponse(
        open(sw_path, "rb"), content_type="application/javascript"
    )
    # Permite que el SW controle todo el dominio aunque se sirva desde /sw.js.
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
