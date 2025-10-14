from django.urls import path
from . import views

app_name = "actas"

urlpatterns = [
    path("", views.actas_list, name="actas_list"),
    path("crear/", views.crear_acta, name="crear"),
    path("<int:acta_id>/", views.detalle_acta, name="detalle"),
    path("<int:acta_id>/editar/", views.editar_acta, name="editar"),
    path("<int:acta_id>/firmar/", views.firmar_acta, name="firmar"),
    path("<int:acta_id>/eliminar/", views.eliminar_acta, name="eliminar"),
    path("<int:acta_id>/pdf/", views.generar_pdf, name="pdf"),
    path("<int:acta_id>/enviar-revision/", views.enviar_revision, name="enviar_revision"),
    path("<int:acta_id>/finalizar/", views.finalizar_acta, name="finalizar"),
    path("<int:acta_id>/archivar/", views.archivar_acta, name="archivar"),
    path("firmas-pendientes/", views.firmas_pendientes, name="firmas_pendientes"),
    
    path("procesar-ia/", views.procesar_con_ia, name="procesar_ia"),

    # Rutas de compromisos
    path("<int:acta_id>/compromisos/", views.lista_compromisos, name="lista_compromisos"),
    path("compromisos/", views.mis_compromisos, name="mis_compromisos"),
    path("<int:acta_id>/compromisos/nuevo/", views.crear_compromiso, name="crear_compromiso"),
    path("compromisos/<int:compromiso_id>/editar/", views.editar_compromiso, name="editar_compromiso"),
    path("compromisos/<int:compromiso_id>/eliminar/", views.eliminar_compromiso, name="eliminar_compromiso"),

    # Rutas para aprendices
    path("aprendiz/pendientes/", views.aprendiz_pendientes, name="aprendiz_pendientes"),
    path("aprendiz/compromisos/", views.aprendiz_compromisos, name="aprendiz_compromisos"),
    path("backup/", views.crear_copia_seguridad, name="crear_backup"),
    # otras rutas...
    path("generar-backup/", views.generar_backup, name="generar_backup"),
]
