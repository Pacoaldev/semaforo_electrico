# electricity_prices/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import ElectricityPrice

@login_required
def traffic_light_display(request):
    """
    Vista para mostrar el semáforo de precios de electricidad.
    Obtiene el precio actual y determina el color.
    """
    now = timezone.localtime(timezone.now())
    today = now.date()
    current_hour = now.hour

    current_price_data = None
    status_color = 'gray' # Por defecto, si no hay datos
    message = "Cargando datos..."

    try:
        current_price_data = ElectricityPrice.objects.get(date=today, hour=current_hour)
        price_value = current_price_data.price
        status_color = current_price_data.status

        message = f"Precio actual ({current_hour:02d}h): {price_value} €/kWh"

    except ElectricityPrice.DoesNotExist:
        # Si no hay datos para la hora exacta, intenta obtener el último precio del día
        latest_price = ElectricityPrice.objects.filter(date=today).order_by('-hour').first()
        if latest_price:
            current_price_data = latest_price
            price_value = latest_price.price
            status_color = latest_price.status
            message = f"Último precio disponible ({latest_price.hour:02d}h): {price_value} €/kWh"
        else:
            message = "No hay datos de precios disponibles para hoy."

    context = {
        'status_color': status_color,
        'message': message,
        'current_price_data': current_price_data,
    }
    return render(request, 'electricity_prices/price_display.html', context)
