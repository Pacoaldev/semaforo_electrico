# electricity_prices/tests.py

"""
Tests del auto-refresco de precios (electricity_prices.services y la vista).

Motivación: el cron de GitHub Actions no era fiable y la app se quedaba sin
precios del día. Estos tests garantizan que el auto-refresco:
  - dispara fetch_prices cuando NO hay datos de hoy,
  - NO lo dispara cuando ya hay datos,
  - evita ráfagas gracias al lock en caché,
  - y que la vista responde 200 en ambos escenarios.
"""

from datetime import date, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import ElectricityPrice
from . import services


class RefreshIfNeededTests(TestCase):
    def setUp(self):
        cache.clear()
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)

    def tearDown(self):
        cache.clear()

    def test_dispara_si_no_hay_datos(self):
        """Sin datos de hoy, refresh_if_needed llama a fetch_prices (síncrono)."""
        with mock.patch.object(
            services, "call_command"
        ) as mocked_call:
            disparado = services.refresh_if_needed(
                today=self.tomorrow, background=False
            )
        self.assertTrue(disparado)
        mocked_call.assert_called_once_with("fetch_prices")

    def test_no_dispara_si_ya_hay_datos(self):
        """Con datos de hoy, no se llama a fetch_prices."""
        ElectricityPrice.objects.create(
            date=self.today, hour=0, price="0.10", status="green"
        )
        with mock.patch.object(services, "call_command") as mocked_call:
            disparado = services.refresh_if_needed(
                today=self.today, background=False
            )
        self.assertFalse(disparado)
        mocked_call.assert_not_called()

    def test_lock_evita_rafagas(self):
        """El lock impide que dos llamadas seguidas lancen dos refrescos."""
        # Primera llamada: dispara y deja el lock puesto (sin datos guardados).
        with mock.patch.object(services, "call_command"):
            primera = services.refresh_if_needed(
                today=self.tomorrow, background=False
            )
        # Segunda llamada dentro del TTL del lock: NO debe disparar.
        with mock.patch.object(services, "call_command") as mocked_call:
            segunda = services.refresh_if_needed(
                today=self.tomorrow, background=False
            )
        self.assertTrue(primera)
        self.assertFalse(segunda)
        mocked_call.assert_not_called()

    def test_error_en_fetch_libera_el_lock(self):
        """Si fetch_prices falla, el lock se libera para permitir reintento."""
        with mock.patch.object(
            services, "call_command", side_effect=RuntimeError("OMIE caído")
        ):
            services.refresh_if_needed(today=self.tomorrow, background=False)
        # El lock debe haberse liberado.
        self.assertTrue(cache.add(services._REFRESH_LOCK_KEY, "1", 60))


@override_settings(ALLOWED_HOSTS=["testserver"])
class VistaSemaforoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.today = timezone.localdate()
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="x")
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def test_vista_200_con_datos(self):
        ElectricityPrice.objects.create(
            date=self.today, hour=0, price="0.10", status="green"
        )
        resp = self.client.get("/electricity/traffic-light/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Estado actual")

    def test_vista_dispara_auto_refresco_sin_datos(self):
        """La vista intenta auto-refrescarse si no hay datos de hoy."""
        with mock.patch.object(
            services, "call_command"
        ) as mocked_call:
            resp = self.client.get("/electricity/traffic-light/")
        self.assertEqual(resp.status_code, 200)
        mocked_call.assert_called_once_with("fetch_prices")
