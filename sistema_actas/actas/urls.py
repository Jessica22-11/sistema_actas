from django.urls import path
from . import views
from . import api_views 


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
    
    # ============================================
    # API para app móvil (AGREGAR AL FINAL)
    # ============================================
    path('api/auth/login/', api_views.login_api, name='api_login'),
    path('api/dashboard/', api_views.dashboard_api, name='api_dashboard'),
    path('api/actas/', api_views.actas_list_api, name='api_actas_list'),
    path('api/actas/<int:acta_id>/', api_views.acta_detalle_api, name='api_acta_detalle'),
    path("api/perfil/", api_views.perfil_api, name="api_perfil"), 
    path('api/cambiar-password/', api_views.cambiar_password_api, name='api_cambiar_password'),
    path('api/usuarios/', api_views.usuarios_list_api, name='api_usuarios_list'),
    path('api/actas/crear/', api_views.crear_acta_api, name='api_crear_acta'),
    path('api/actas/generar-ia/', api_views.generar_acta_ia_api, name='api_generar_ia'),
    path('api/firmas/pendientes/', api_views.actas_pendientes_firma_api, name='api_firmas_pendientes'),
    path('api/firmas/firmar/', api_views.firmar_acta_api, name='api_firmar_acta'), 
    path('api/actas/<int:acta_id>/cambiar-estado/', api_views.cambiar_estado_acta_api, name='api_cambiar_estado'), 
    path('api/compromisos/crear/', api_views.crear_compromiso_api, name='api_crear_compromiso'),
    path('api/actas/<int:acta_id>/editar/', api_views.editar_acta_api, name='api_editar_acta'),
    path('api/actas/<int:acta_id>/pdf/', api_views.generar_pdf_api, name='api_generar_pdf'),
    path('api/compromisos/mis-compromisos/', api_views.mis_compromisos_api, name='api_mis_compromisos'),
    path('api/compromisos/<int:compromiso_id>/actualizar/', api_views.actualizar_compromiso_api, name='api_actualizar_compromiso'),
    path('api/actas/<int:acta_id>/aplicar-silencio/', api_views.aplicar_silencio_administrativo_api, name='api_aplicar_silencio'),
    path('api/auth/register/', api_views.register_api, name='api_register'),
]
