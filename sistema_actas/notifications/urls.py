# notifications/urls.py
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # Listado de notificaciones
    path("", views.notifications_list, name="list"),

    # Marcar como leídas (varias o todas)
    path("mark-as-read/", views.mark_as_read, name="mark_as_read"),

    # Marcar como no leída (una sola)
    path("mark-as-unread/<int:notification_id>/", views.mark_as_unread, name="mark_as_unread"),

    # Eliminar notificación
    path("delete/<int:notification_id>/", views.delete_notification, name="delete"),

    # Configuración de notificaciones
    path("settings/", views.notification_settings, name="settings"),
]
