from django.urls import path
from . import views

app_name = "actas"

urlpatterns = [
    path("", views.actas_list, name="list"),
    path("crear/", views.crear_acta, name="crear"),
    path("<int:acta_id>/", views.detalle_acta, name="detalle"),
    path("<int:acta_id>/editar/", views.editar_acta, name="editar"),
    path("<int:acta_id>/firmar/", views.firmar_acta, name="firmar"),
    path("<int:acta_id>/eliminar/", views.eliminar_acta, name="eliminar"),
    path("<int:acta_id>/pdf/", views.generar_pdf, name="pdf"),
    path(
        "<int:acta_id>/enviar-revision/", views.enviar_revision, name="enviar_revision"
    ),
    path("<int:acta_id>/finalizar/", views.finalizar_acta, name="finalizar"),
    path("<int:acta_id>/archivar/", views.archivar_acta, name="archivar"),
    path("firmas-pendientes/", views.firmas_pendientes, name="firmas_pendientes"),
    path("procesar-ia/", views.procesar_con_ia, name="procesar_ia"),
]
