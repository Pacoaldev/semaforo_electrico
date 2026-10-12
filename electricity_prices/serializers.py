# electricity_prices/serializers.py

from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import ElectricityPrice


class ElectricityPriceSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ElectricityPrice, usado en la API.

    - `price`: valor numérico original (ej. "0.19908"), para cálculos.
    - `price_display`: mismo precio en formato español (ej. "0,19908").
    """

    price_display = serializers.SerializerMethodField()

    class Meta:
        model = ElectricityPrice
        fields = ['date', 'hour', 'price', 'price_display', 'status']

    def get_price_display(self, obj) -> str:
        try:
            return f"{Decimal(str(obj.price)):.5f}".replace(".", ",")
        except (InvalidOperation, ValueError, TypeError):
            return str(obj.price)
