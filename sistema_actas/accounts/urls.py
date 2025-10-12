# accounts/urls.py

from django.urls import path, reverse_lazy # <-- ¡IMPORTACIÓN NECESARIA!
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    # Vistas personalizadas existentes
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("settings/", views.settings_view, name="settings"),
    
    path("usuarios/", views.usuarios, name="usuarios"),
    path('usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    
    # ==========================================================
    # FLUJO DE RECUPERACIÓN DE CONTRASEÑA (RUTAS CORREGIDAS)
    # ==========================================================
    
    # 1. Formulario de Solicitud de Correo: /accounts/password_reset/
    # Se agrega success_url para evitar el error NoReverseMatch: 'password_reset_done'
    path('password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            success_url=reverse_lazy('accounts:password_reset_done') # <-- CORRECCIÓN CRÍTICA
        ),
        name='password_reset'),

    # 2. Confirmación de Envío: /accounts/password_reset/done/
    path("password_reset/done/", 
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ), 
        name="password_reset_done"),

    # 3. Formulario para la Nueva Contraseña (usa uidb64 y token de la URL)
    # Ruta: /accounts/reset/<uidb64>/<token>/
    path("reset/<uidb64>/<token>/", 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html'
        ), 
        name="password_reset_confirm"),

    # 4. Éxito Final: /accounts/reset/done/
    path("reset/done/", 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ), 
        name="password_reset_complete"),
]