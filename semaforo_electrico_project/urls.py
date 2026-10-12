# semaforo_electrico_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views # Importado para otras vistas auth

# Importa tus formularios y vistas personalizadas desde tu aplicación users
from users.forms import CustomAuthenticationForm # Tu formulario de autenticación personalizado
from users.views import SignUpView, CustomPasswordResetView # Tu vista de registro y la personalizada de restablecimiento
from .pwa_views import service_worker, health, refresh_prices # Vista PWA, salud y refresco de precios

urlpatterns = [
    path('health/', health, name='health'), # Endpoint de salud (para despliegue)
    path('tasks/refresh-prices/', refresh_prices, name='refresh_prices'), # Refresco diario protegido por token
    path('sw.js', service_worker, name='service_worker'), # PWA: Service Worker en la raíz
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')), # Incluye las URLs de tu app 'users'
    path('electricity/', include('electricity_prices.urls', namespace='electricity')),

    # Rutas de autenticación de Django
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html', form_class=CustomAuthenticationForm), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),

    # Rutas de restablecimiento de contraseña (¡usando tu vista personalizada!)
    path('accounts/password_reset/', CustomPasswordResetView.as_view(), name='password_reset'), # Usa CustomPasswordResetView
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Redirección de la raíz a la página de inicio de users
    path('', RedirectView.as_view(url='/users/home/', permanent=True), name='root_redirect'),
]

