# electricity_prices/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import ElectricityPrice


@login_required
def traffic_light_display(request):
    """
    Vista para mostrar el semáforo de precios de electricidad.

    Muestra el precio de la hora actual (con su color) y, además, un gráfico
    con los precios de las 24 horas del día para saber de un vistazo qué
    tramos son los más baratos.
    """
    now = timezone.localtime(timezone.now())
    today = now.date()
    current_hour = now.hour

    current_price_data = None
    status_color = 'gray'  # Por defecto, si no hay datos
    message = "No hay datos de precios disponibles para hoy."

    try:
        current_price_data = ElectricityPrice.objects.get(date=today, hour=current_hour)
        status_color = current_price_data.status
        message = f"Precio actual ({current_hour:02d}h): {current_price_data.price} €/kWh"
    except ElectricityPrice.DoesNotExist:
        # Si no hay datos para la hora exacta, intenta obtener el último del día.
        latest_price = ElectricityPrice.objects.filter(date=today).order_by('-hour').first()
        if latest_price:
            current_price_data = latest_price
            status_color = latest_price.status
            message = f"Último precio disponible ({latest_price.hour:02d}h): {latest_price.price} €/kWh"

    # Precios de todas las horas del día (para el gráfico de barras).
    day_prices = ElectricityPrice.objects.filter(date=today).order_by('hour')

    # Hora con el precio más barato del día (para resaltarla).
    cheapest_hour = None
    if day_prices:
        cheapest_hour = min(
            day_prices, key=lambda p: p.price
        ).hour

    # Última fecha con datos disponibles (por si no hay datos de hoy).
    latest_date = (
        ElectricityPrice.objects.order_by('-date')
        .values_list('date', flat=True)
        .first()
    )

    context = {
        'status_color': status_color,
        'message': message,
        'current_price_data': current_price_data,
        'day_prices': day_prices,
        'current_hour': current_hour,
        'cheapest_hour': cheapest_hour,
        'today': today,
        'latest_date': latest_date,
    }
    return render(request, 'electricity_prices/price_display.html', context)
