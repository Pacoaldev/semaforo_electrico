# electricity_prices/management/commands/reclassify_prices.py

"""
Recalcula el campo `status` (color del semáforo) de todos los precios ya
guardados usando los umbrales actuales de `fetch_prices`.

Útil cuando se ajustan los umbrales: no hace falta volver a descargar de OMIE,
solo reevaluar lo que ya está en base de datos.

Uso:
    python manage.py reclassify_prices
    python manage.py reclassify_prices --date 2026-10-12
"""

from django.core.management.base import BaseCommand

from electricity_prices.models import ElectricityPrice
from electricity_prices.management.commands.fetch_prices import classify_status


class Command(BaseCommand):
    help = "Recalcula el color (status) de los precios guardados según los umbrales actuales."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Recalcula solo una fecha (YYYY-MM-DD). Por defecto, todas.",
            default=None,
        )

    def handle(self, *args, **options):
        qs = ElectricityPrice.objects.all()
        if options.get("date"):
            qs = qs.filter(date=options["date"])

        updated = 0
        for price in qs.iterator():
            nuevo = classify_status(float(price.price))
            if nuevo != price.status:
                price.status = nuevo
                price.save(update_fields=["status"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalificados {updated} registros (de {qs.count()} revisados)."
            )
        )
