# electricity_prices/management/commands/fetch_prices.py

"""
Comando para capturar los precios horarios de la electricidad desde OMIE.es.

Formato del archivo OMIE `marginalpdbc_YYYYMMDD.1`:
    MARGINALPDBC;
    2026;10;12;1;216.54;216.54;
    2026;10;12;2;210.4;210.4;
    ...
    *

- El campo "Hora" va de 1 a 96 (Precios CUARTO-horarios, 4 por cada hora).
  La hora real (0-23) se calcula como `(hora_omie - 1) // 4`.
- Los precios vienen en €/MWh. Se convierten a €/kWh dividiendo entre 1000.
- Si hay varios cuartos en la misma hora, se guarda el precio MEDIO de esa hora.
"""

from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone

from electricity_prices.models import ElectricityPrice

# Umbrales del semáforo (€/kWh).
#
# IMPORTANTE: estos precios son de MERCADO (OMIE), SIN impuestos ni peajes.
# No confundir con el PVPC final que paga el consumidor (que ronda 0,15-0,28).
# Escala calibrada a la serie real de OMIE:
#   < 0.08        -> 'dark-green' (muy barato)
#   0.08 - 0.13   -> 'green'      (barato)
#   0.13 - 0.19   -> 'yellow'     (medio)
#   >= 0.19       -> 'red'        (caro)
PRICE_DARKGREEN_MAX = 0.08   # < 0.08 -> dark-green
PRICE_GREEN_MAX = 0.13       # 0.08 - 0.13 -> green
PRICE_YELLOW_MAX = 0.19      # 0.13 - 0.19 -> yellow ; >= 0.19 -> red


def classify_status(price_kwh: float) -> str:
    """Devuelve el color del semáforo para un precio de mercado en €/kWh."""
    if price_kwh < PRICE_DARKGREEN_MAX:
        return "dark-green"
    if price_kwh < PRICE_GREEN_MAX:
        return "green"
    if price_kwh < PRICE_YELLOW_MAX:
        return "yellow"
    return "red"


class Command(BaseCommand):
    help = "Captura los precios diarios de electricidad desde OMIE.es y los guarda en la BD."

    OMIE_FILE_LIST_URL = (
        "https://www.omie.es/es/file-access-list"
        "?parents=/Mercado%20Diario/1.%20Precios"
        "&dir=Precios%20horarios%20del%20mercado%20diario%20en%20Espa%C3%B1a"
        "&realdir=marginalpdbc"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Fecha a capturar en formato YYYY-MM-DD (por defecto, hoy).",
            default=None,
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Iniciando captura de precios desde OMIE.es...")
        )

        # Fecha objetivo
        if options.get("date"):
            from datetime import datetime

            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR("Formato de fecha inválido. Usa YYYY-MM-DD.")
                )
                return
        else:
            target_date = timezone.localdate()

        date_str_file = target_date.strftime("%Y%m%d")

        try:
            prices_by_hour = self._download_and_parse(date_str_file)
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error de red/HTTP con OMIE.es: {e}"))
            return
        except Exception as e:  # noqa: BLE001 - queremos loguear cualquier fallo
            self.stdout.write(self.style.ERROR(f"Error inesperado: {e}"))
            return

        if not prices_by_hour:
            self.stdout.write(
                self.style.WARNING(
                    f"No se pudieron extraer precios para el día {target_date}."
                )
            )
            return

        saved = 0
        for hour in sorted(prices_by_hour):
            price_kwh = prices_by_hour[hour]
            status = classify_status(price_kwh)
            ElectricityPrice.objects.update_or_create(
                date=target_date,
                hour=hour,
                defaults={"price": price_kwh, "status": status},
            )
            saved += 1
            self.stdout.write(
                f"  {target_date} - {hour:02d}h: {price_kwh:.5f} €/kWh ({status})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Captura completada: {saved} horas guardadas para {target_date}."
            )
        )

    # --- Internos -----------------------------------------------------------
    def _download_and_parse(self, date_str_file: str) -> dict[int, float]:
        """Descarga el archivo de OMIE y devuelve {hora_0_23: precio_medio_kwh}."""
        response = requests.get(self.OMIE_FILE_LIST_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        target_file_link = self._find_file_link(soup, date_str_file)
        if not target_file_link:
            self.stdout.write(
                self.style.WARNING(
                    f"No se encontró el archivo marginalpdbc_{date_str_file}.1 en OMIE.es."
                )
            )
            return {}

        self.stdout.write(f"Archivo encontrado: {target_file_link}")
        file_response = requests.get(target_file_link, timeout=30)
        file_response.raise_for_status()

        hourly_prices: dict[int, list[float]] = defaultdict(list)

        for line in file_response.text.splitlines():
            line = line.strip()
            if not line or line.startswith("MARGINALPDBC"):
                continue

            parts = line.split(";")
            if len(parts) < 5:
                continue

            try:
                omie_hour = int(parts[3].strip())
                price_mwh = float(parts[4].strip().replace(",", "."))
            except (ValueError, IndexError):
                continue

            # Hora de OMIE (1-96) -> hora real (0-23)
            if not 1 <= omie_hour <= 96:
                continue
            real_hour = (omie_hour - 1) // 4
            price_kwh = price_mwh / 1000.0
            hourly_prices[real_hour].append(price_kwh)

        # Precio medio por hora (media de los cuartos de hora)
        return {
            hour: sum(values) / len(values)
            for hour, values in hourly_prices.items()
            if values
        }

    def _find_file_link(self, soup: BeautifulSoup, date_str_file: str) -> str | None:
        """Busca el enlace de descarga del archivo de precios de la fecha dada."""
        import re

        pattern = re.compile(rf"marginalpdbc_{date_str_file}\.1", re.IGNORECASE)
        for link in soup.find_all("a", href=True):
            if pattern.search(link.text) or pattern.search(link["href"]):
                href = link["href"]
                if href.startswith("/"):
                    return f"https://www.omie.es{href}"
                return href
        return None
