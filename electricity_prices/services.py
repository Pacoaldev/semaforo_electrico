# electricity_prices/services.py

"""
Servicio de auto-refresco de precios.

Motivación: dependíamos de que un cron externo (GitHub Actions) llamase al
endpoint `/tasks/refresh-prices/` cada día. En la práctica, el `schedule` de
GitHub Actions no es fiable (se retrasa, se pierde o no arranca), así que la
app podía quedarse sin datos del día.

Este módulo hace que la propia app se auto-refresque: si no hay precios para
HOY, lanza `fetch_prices` automáticamente. Un lock en caché evita ráfagas de
refrescos; si OMIE aún no ha publicado los precios del día, se libera el lock
para reintentar en la siguiente visita. Así la app se actualiza sola cuando
alguien la abre, sin depender de ningún cron.
"""

import logging
import threading

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone

from .models import ElectricityPrice

logger = logging.getLogger(__name__)

# Clave del lock: evita lanzar más de un refresco por día.
_REFRESH_LOCK_KEY = "prices_auto_refresh_lock"
# El lock dura 1 hora: si OMIE aún no ha publicado los precios de hoy (p. ej. a
# primera hora de la madrugada), no reintentamos en bucle, pero sí damos margen
# a que una hora después se vuelva a intentar automáticamente.
_REFRESH_LOCK_TTL = 60 * 60


def has_prices_for_today(today=None) -> bool:
    """¿Hay ya precios guardados para el día indicado (por defecto, hoy)?"""
    today = today or timezone.localdate()
    return ElectricityPrice.objects.filter(date=today).exists()


def _run_fetch_prices(today) -> None:
    """Ejecuta fetch_prices capturando su salida (se registra en el log)."""
    try:
        call_command("fetch_prices")
        if has_prices_for_today(today):
            logger.info("Auto-refresco: precios de %s obtenidos correctamente.", today)
        else:
            # OMIE aún no publica los precios del día. NO liberamos el lock: así
            # se reintenta como máximo una vez por hora (evita que un usuario
            # refrescando en bucle dispare descargas de OMIE sin parar).
            logger.info(
                "Auto-refresco: OMIE todavía no publica precios para %s. "
                "Se reintentará automáticamente en la próxima hora.",
                today,
            )
    except Exception:  # noqa: BLE001 - nunca debe romper la vista del usuario
        # En caso de error sí liberamos el lock, para no dejar la app "atascada"
        # una hora entera sin posibilidad de reintento.
        cache.delete(_REFRESH_LOCK_KEY)
        logger.exception("Error durante el auto-refresco de precios.")


def ensure_prices_for_today(today=None) -> None:
    """
    Si no hay precios para hoy, lanza fetch_prices en segundo plano.

    - Como máximo un lanzamiento por día (lock en caché).
    - No bloquea: se ejecuta en un hilo aparte, así la vista responde ya con
      lo que haya (la siguiente carga mostrará los datos recién traídos).
    - No lanza excepción: cualquier fallo se registra en el log.

    Si quieres el refresco de forma SÍNCRONA (útil en tests), pasa
    `background=False` a `refresh_if_needed`.
    """
    refresh_if_needed(today=today, background=True)


def refresh_if_needed(today=None, background: bool = True) -> bool:
    """
    Lanza el refresco si hace falta. Devuelve True si se disparó.

    `background=False` ejecuta fetch_prices de forma síncrona (tests/CLI).
    """
    today = today or timezone.localdate()

    # Si ya hay datos de hoy, nada que hacer.
    if has_prices_for_today(today):
        return False

    # Lock: evita avalanchas de peticiones simultáneas sin datos.
    # cache.add() solo devuelve True si la clave NO existía (atómico en la
    # mayoría de backends). Si ya existe, otro proceso lo está refrescando.
    if not cache.add(_REFRESH_LOCK_KEY, "1", _REFRESH_LOCK_TTL):
        return False

    if background:
        threading.Thread(target=_run_fetch_prices, args=(today,), daemon=True).start()
    else:
        _run_fetch_prices(today)
    return True
