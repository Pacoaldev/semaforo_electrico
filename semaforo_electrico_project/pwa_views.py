"""
Vistas relacionadas con la PWA (Progressive Web App) y tareas programadas.

El Service Worker se sirve desde la RAÍZ del sitio (/sw.js) para poder
controlar todo el ámbito del dominio (scope '/'). Si se sirviera solo desde
/static/sw.js, por defecto su scope quedaría limitado a /static/.
"""

import io
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET


def health(request):
    """Endpoint simple de salud para plataformas de despliegue."""
    return JsonResponse({"status": "ok"})


@require_GET
def refresh_prices(request):
    """
    Endpoint protegido que ejecuta la captura de precios de OMIE (fetch_prices).

    Se protege con el token CRON_SECRET_TOKEN, que debe enviarse por la
    cabecera "X-Cron-Token" o como parámetro "?token=". Si el token no está
    configurado o no coincide, responde 403 (fail-closed).

    Pensado para ser invocado por un cron externo gratuito
    (GitHub Actions, cron-job.org, etc.).
    """
    expected = settings.CRON_SECRET_TOKEN
    provided = request.headers.get("X-Cron-Token") or request.GET.get("token", "")

    if not expected or provided != expected:
        return JsonResponse({"detail": "No autorizado."}, status=403)

    out = io.StringIO()
    try:
        call_command("fetch_prices", stdout=out)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse(
            {"status": "error", "detail": str(exc)},
            status=500,
        )

    return JsonResponse(
        {"status": "ok", "output": out.getvalue()},
        status=200,
    )


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
