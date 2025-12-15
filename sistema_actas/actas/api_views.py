from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings
from rest_framework.authtoken.models import Token
from .models import Acta, Participante, Firma, Compromiso, ComentarioActa
import json
import logging
import os
import zipfile
import tempfile
from django.http import FileResponse


User = get_user_model()
logger = logging.getLogger(__name__)


def handle_error(e, custom_message="Error procesando la solicitud"):
    """
    Maneja errores de forma segura sin exponer detalles internos
    Registra el error completo en logs
    """
    logger.error(f"{custom_message}: {str(e)}", exc_info=True)
    return custom_message


def get_user_from_token(request):
    """
    Helper para autenticar al usuario usando el token del header Authorization.

    Retorna:
        - (user, None) si el token es válido
        - (None, JsonResponse) si el token es inválido o falta

    Uso:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        # Continuar con user autenticado
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None, JsonResponse({
            'success': False,
            'error': 'No autenticado. Header Authorization requerido.'
        }, status=401)

    token_key = auth_header.replace('Bearer ', '').strip()

    if not token_key:
        return None, JsonResponse({
            'success': False,
            'error': 'Token vacío'
        }, status=401)

    try:
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user, None
    except Token.DoesNotExist:
        return None, JsonResponse({
            'success': False,
            'error': 'Token inválido o expirado'
        }, status=401)


@csrf_exempt
def login_api(request):
    """
    API de login para la app móvil Flutter.

    Recibe:
        - username (email del usuario)
        - password

    Retorna:
        - token: Token aleatorio seguro de 40 caracteres
        - user: Datos del usuario autenticado

    Seguridad:
        - Genera un token criptográfico único por usuario
        - El token se almacena en la base de datos
        - Si el usuario ya tiene un token, se retorna el existente
    """
    if request.method == 'POST':
        try:
            # Leer datos del request
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario y contraseña son requeridos'
                }, status=400)

            # Autenticar usuario
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Obtener o crear token para el usuario
                token, created = Token.objects.get_or_create(user=user)

                # Login exitoso
                return JsonResponse({
                    'success': True,
                    'token': token.key,  # Token seguro de 40 caracteres
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'rol': user.rol,
                        'firma_digital': user.firma_digital.url if user.firma_digital else None,
                    }
                })
            else:
                # Credenciales incorrectas
                return JsonResponse({
                    'success': False,
                    'error': 'Credenciales incorrectas'
                }, status=401)
                
        except Exception as e:
            # Error del servidor
            return JsonResponse({
                'success': False,
                'error': handle_error(e, "Error durante el login")
            }, status=500)
    
    # Método no permitido
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


@csrf_exempt
def logout_api(request):
    """
    API de logout para la app móvil Flutter.

    Elimina el token del usuario de la base de datos, invalidando la sesión.

    Header requerido:
        Authorization: Bearer <token>

    Retorna:
        - success: True si el logout fue exitoso
    """
    if request.method == 'POST':
        try:
            user, error_response = get_user_from_token(request)
            if error_response:
                return error_response

            # Eliminar el token del usuario
            Token.objects.filter(user=user).delete()

            return JsonResponse({
                'success': True,
                'message': 'Sesión cerrada exitosamente'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': handle_error(e, "Error durante el logout")
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


# ============================================
#  API de Dashboard
# ============================================
@csrf_exempt
def dashboard_api(request):
    """
    API para obtener estadísticas del dashboard

    Header requerido:
        Authorization: Bearer <token>

    Retorna estadísticas del usuario autenticado.
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)

    try:
        # Autenticar usuario con token seguro
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        # Estadísticas
        total_actas = Acta.objects.filter(creador=user).count()
        
        # Firmas pendientes (donde el usuario es participante y no ha firmado)
        firmas_pendientes_count = Firma.objects.filter(
            usuario=user,
            firmado=False,
            acta__estado='en_revision'
        ).count()
        
        # Compromisos activos
        compromisos_activos = Compromiso.objects.filter(
            responsable=user,
            estado__in=['pendiente', 'en_progreso']
        ).count()
        
        # Compromisos vencidos
        compromisos_vencidos = Compromiso.objects.filter(
            responsable=user,
            estado='vencido'
        ).count()
        
        # Actas recientes (últimas 5)
        actas_recientes = Acta.objects.filter(
            creador=user
        ).order_by('-fecha_creacion')[:5]
        
        actas_recientes_data = [{
            'id': acta.id,
            'numero_acta': acta.numero_acta,
            'titulo': acta.titulo,
            'estado': acta.estado,
            'fecha_reunion': acta.fecha_reunion.isoformat(),
            'fecha_creacion': acta.fecha_creacion.isoformat(),
        } for acta in actas_recientes]
        
        # Firmas pendientes (lista completa)
        firmas_pendientes_lista = Firma.objects.filter(
            usuario=user,
            firmado=False,
            acta__estado='en_revision'
        ).select_related('acta')[:5]
        
        firmas_pendientes_data = [{
            'id': firma.id,
            'acta': {
                'id': firma.acta.id,
                'numero_acta': firma.acta.numero_acta,
                'titulo': firma.acta.titulo,
                'fecha_reunion': firma.acta.fecha_reunion.isoformat(),
            }
        } for firma in firmas_pendientes_lista]
        
        # Compromisos próximos
        compromisos_proximos = Compromiso.objects.filter(
            responsable=user,
            estado__in=['pendiente', 'en_progreso']
        ).order_by('fecha_limite')[:5]
        
        compromisos_proximos_data = [{
            'id': compromiso.id,
            'descripcion': compromiso.descripcion,
            'fecha_limite': compromiso.fecha_limite.isoformat(),
            'estado': compromiso.estado,
            'porcentaje_avance': compromiso.porcentaje_avance,
            'dias_restantes': compromiso.dias_restantes(),
            'acta': {
                'id': compromiso.acta.id,
                'numero_acta': compromiso.acta.numero_acta,
                'titulo': compromiso.acta.titulo,
                'fecha_reunion': compromiso.acta.fecha_reunion.isoformat(),
            }
        } for compromiso in compromisos_proximos]
        
        return JsonResponse({
            'success': True,
            'data': {
                'estadisticas': {
                    'total_actas': total_actas,
                    'firmas_pendientes': firmas_pendientes_count,
                    'compromisos_activos': compromisos_activos,
                    'compromisos_vencidos': compromisos_vencidos,
                },
                'actas_recientes': actas_recientes_data,
                'firmas_pendientes': firmas_pendientes_data,
                'compromisos_proximos': compromisos_proximos_data,
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        

@csrf_exempt
def actas_list_api(request):
    """
    API para listar actas del usuario
    Soporta filtros por estado y búsqueda
    Soporta paginación: ?page=1&limit=20
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)

    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)

        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)

        # Obtener parámetros de filtro
        estado = request.GET.get('estado', None)  # borrador, en_revision, finalizada, archivada
        search = request.GET.get('search', None)  # búsqueda por título o número

        # Parámetros de paginación
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            limit = min(limit, 100)  # Máximo 100 registros por página
        except ValueError:
            page = 1
            limit = 20

        # Query base - actas creadas por el usuario
        actas = Acta.objects.filter(creador=user)

        # Aplicar filtro de estado
        if estado and estado != 'todos':
            actas = actas.filter(estado=estado)

        # Aplicar búsqueda
        if search:
            from django.db.models import Q
            actas = actas.filter(
                Q(titulo__icontains=search) |
                Q(numero_acta__icontains=search)
            )

        # Ordenar por fecha de creación (más recientes primero)
        actas = actas.order_by('-fecha_creacion')

        # Contar total antes de paginar
        total_count = actas.count()

        # Aplicar paginación
        start = (page - 1) * limit
        end = start + limit
        actas_paginadas = actas[start:end]

        # Serializar datos
        actas_data = []
        for acta in actas_paginadas:
            # Calcular estadísticas de firmas
            total_firmas = acta.participantes.count()
            firmas_completadas = acta.firmas.filter(firmado=True).count()
            porcentaje_firmas = (firmas_completadas / total_firmas * 100) if total_firmas > 0 else 0

            actas_data.append({
                'id': acta.id,
                'numero_acta': acta.numero_acta,
                'titulo': acta.titulo,
                'tipo_reunion': acta.tipo_reunion,
                'estado': acta.estado,
                'fecha_reunion': acta.fecha_reunion.isoformat(),
                'fecha_creacion': acta.fecha_creacion.isoformat(),
                'lugar_reunion': acta.lugar_reunion,
                'modalidad': acta.modalidad,
                'generada_con_ia': acta.generada_con_ia,
                'creador': {
                    'id': acta.creador.id,
                    'nombre_completo': acta.creador.get_full_name(),
                },
                'estadisticas_firmas': {
                    'total': total_firmas,
                    'completadas': firmas_completadas,
                    'porcentaje': round(porcentaje_firmas, 1),
                }
            })

        # Calcular paginación
        total_pages = (total_count + limit - 1) // limit

        return JsonResponse({
            'success': True,
            'data': {
                'actas': actas_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1,
                }
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        

@csrf_exempt
def acta_detalle_api(request, acta_id):
    """
    API para obtener el detalle completo de un acta
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener acta
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar permisos (debe ser creador o participante)
        es_creador = acta.creador == user
        es_participante = acta.participantes.filter(usuario=user).exists()
        
        if not (es_creador or es_participante):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para ver esta acta'
            }, status=403)
        
        # Obtener participantes
        participantes_data = []
        for participante in acta.participantes.all():
            # Buscar firma del participante
            firma = acta.firmas.filter(usuario=participante.usuario).first()
            
            participantes_data.append({
                'id': participante.id,
                'usuario': {
                    'id': participante.usuario.id,
                    'nombre_completo': participante.usuario.get_full_name(),
                    'email': participante.usuario.email,
                    'rol': participante.usuario.rol,
                },
                'rol_en_reunion': participante.rol_en_reunion,
                'obligatorio_firma': participante.obligatorio_firma,
                'firma': {
                    'firmado': firma.firmado if firma else False,
                    'fecha_firma': firma.fecha_firma.isoformat() if firma and firma.fecha_firma else None,
                    'tiene_firma': bool(firma),
                } if firma else None,
            })
        
        # Obtener compromisos
        compromisos_data = []
        for compromiso in acta.compromisos.all():
            compromisos_data.append({
                'id': compromiso.id,
                'descripcion': compromiso.descripcion,
                'responsable': {
                    'id': compromiso.responsable.id,
                    'nombre_completo': compromiso.responsable.get_full_name(),
                },
                'fecha_limite': compromiso.fecha_limite.isoformat(),
                'estado': compromiso.estado,
                'porcentaje_avance': compromiso.porcentaje_avance,
                'dias_restantes': compromiso.dias_restantes(),
                'observaciones': compromiso.observaciones,
            })
        
        # Calcular estadísticas
        total_firmas = acta.participantes.count()
        firmas_completadas = acta.firmas.filter(firmado=True).count()
        porcentaje_firmas = (firmas_completadas / total_firmas * 100) if total_firmas > 0 else 0
        
        # Datos del acta
        acta_data = {
            'id': acta.id,
            'numero_acta': acta.numero_acta,
            'titulo': acta.titulo,
            'tipo_reunion': acta.tipo_reunion,
            'estado': acta.estado,
            'fecha_reunion': acta.fecha_reunion.isoformat(),
            'fecha_creacion': acta.fecha_creacion.isoformat(),
            'fecha_modificacion': acta.fecha_modificacion.isoformat(),
            'lugar_reunion': acta.lugar_reunion,
            'modalidad': acta.modalidad,
            'orden_dia': acta.orden_dia,
            'desarrollo': acta.desarrollo,
            'observaciones': acta.observaciones,
            'generada_con_ia': acta.generada_con_ia,
            'prompt_original': acta.prompt_original if acta.generada_con_ia else None,
            'modelo_ia_usado': acta.modelo_ia_usado if acta.generada_con_ia else None,
            'fecha_limite_firmas': acta.fecha_limite_firmas.isoformat() if acta.fecha_limite_firmas else None,
            'silencio_administrativo': acta.silencio_administrativo,
            'puede_aplicar_silencio': acta.puede_aplicar_silencio_administrativo(),
            'creador': {
                'id': acta.creador.id,
                'nombre_completo': acta.creador.get_full_name(),
                'email': acta.creador.email,
                'rol': acta.creador.rol,
            },
            'participantes': participantes_data,
            'compromisos': compromisos_data,
            'estadisticas_firmas': {
                'total': total_firmas,
                'completadas': firmas_completadas,
                'porcentaje': round(porcentaje_firmas, 1),
            },
            'permisos_usuario': {
                'es_creador': es_creador,
                'es_participante': es_participante,
                'puede_editar': es_creador and acta.estado == 'borrador',
                'puede_firmar': es_participante and acta.estado == 'en_revision',
            }
        }
        
        return JsonResponse({
            'success': True,
            'data': acta_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        


""" API para obtener y actualizar el perfil del usuario"""
@csrf_exempt
def perfil_api(request):
    
    # Obtener token del header
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token or not token.startswith('token_'):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    try:
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # GET - Obtener perfil
        if request.method == 'GET':
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'rol': user.rol,
                'fecha_registro': user.date_joined.isoformat(),
                'ultimo_login': user.last_login.isoformat() if user.last_login else None,
                'firma_digital': user.firma_digital.url if user.firma_digital else None,
                'tiene_firma': bool(user.firma_digital),
            }
            
            # Estadísticas del usuario
            stats = {
                'total_actas_creadas': Acta.objects.filter(creador=user).count(),
                'actas_en_borrador': Acta.objects.filter(creador=user, estado='borrador').count(),
                'actas_finalizadas': Acta.objects.filter(creador=user, estado='finalizada').count(),
                'compromisos_asignados': Compromiso.objects.filter(responsable=user).count(),
                'compromisos_completados': Compromiso.objects.filter(responsable=user, estado='completado').count(),
                'firmas_pendientes': Firma.objects.filter(usuario=user, firmado=False).count(),
            }
            
            return JsonResponse({
                'success': True,
                'data': {
                    'user': user_data,
                    'stats': stats,
                }
            })
        
        # PUT - Actualizar perfil
        elif request.method == 'PUT':
            data = json.loads(request.body)
            
            # Actualizar campos permitidos
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Perfil actualizado correctamente',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'rol': user.rol,
                }
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Método no permitido'
            }, status=405)
            
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)


@csrf_exempt
def cambiar_password_api(request):
    """
    API para cambiar la contraseña del usuario
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener datos del request
        data = json.loads(request.body)
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Faltan datos requeridos'
            }, status=400)
        
        # Verificar contraseña actual
        if not user.check_password(current_password):
            return JsonResponse({
                'success': False,
                'error': 'La contraseña actual es incorrecta'
            }, status=400)
        
        # Validar nueva contraseña
        password_errors = []

        if len(new_password) < 8:
            password_errors.append('La contraseña debe tener al menos 8 caracteres')

        if not any(char.isupper() for char in new_password):
            password_errors.append('La contraseña debe contener al menos una letra mayúscula')

        if not any(char.islower() for char in new_password):
            password_errors.append('La contraseña debe contener al menos una letra minúscula')

        if not any(char.isdigit() for char in new_password):
            password_errors.append('La contraseña debe contener al menos un número')

        if password_errors:
            return JsonResponse({
                'success': False,
                'error': 'Contraseña débil',
                'detalles': password_errors
            }, status=400)
        
        # Cambiar contraseña
        user.set_password(new_password)
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Contraseña actualizada correctamente'
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)


""""api para obtener la lista de usuarios para agregar participantes al acta"""
@csrf_exempt
def usuarios_list_api(request):
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener todos los usuarios activos
        usuarios = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        usuarios_data = []
        for u in usuarios:
            usuarios_data.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'nombre_completo': u.get_full_name(),
                'rol': u.rol,
            })
        
        return JsonResponse({
            'success': True,
            'data': usuarios_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
    
@csrf_exempt
def crear_acta_api(request):
    """
    API para crear una nueva acta (manual o con IA)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener datos del request
        data = json.loads(request.body)
        
        # Validar campos requeridos
        required_fields = ['titulo', 'fecha_reunion', 'lugar_reunion', 'tipo_reunion', 'modalidad']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({
                    'success': False,
                    'error': f'El campo {field} es requerido'
                }, status=400)
        
        # Crear acta
        acta = Acta.objects.create(
            titulo=data['titulo'],
            fecha_reunion=data['fecha_reunion'],
            lugar_reunion=data['lugar_reunion'],
            tipo_reunion=data['tipo_reunion'],
            modalidad=data['modalidad'],
            orden_dia=data.get('orden_dia', ''),
            desarrollo=data.get('desarrollo', ''),
            observaciones=data.get('observaciones', ''),
            creador=user,
            estado='borrador',
            generada_con_ia=data.get('generada_con_ia', False),
            prompt_original=data.get('prompt_original', ''),
            modelo_ia_usado=data.get('modelo_ia_usado', ''),
        )
        
        # Agregar participantes
        participantes_data = data.get('participantes', [])
        for participante_info in participantes_data:
            try:
                participante_usuario = User.objects.get(id=participante_info['usuario_id'])
                participante = Participante.objects.create(
                    acta=acta,
                    usuario=participante_usuario,
                    rol_en_reunion=participante_info.get('rol_en_reunion', ''),
                    obligatorio_firma=participante_info.get('obligatorio_firma', True),
                )
                
                # Crear registro de firma
                Firma.objects.create(
                    acta=acta,
                    usuario=participante_usuario,
                    firmado=False,
                )
            except User.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': 'Acta creada correctamente',
            'data': {
                'acta_id': acta.id,
                'numero_acta': acta.numero_acta,
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)


@csrf_exempt
def generar_acta_ia_api(request):
    """
    API para generar contenido de acta usando IA (Groq)
    CORREGIDO: Ahora usa la misma función que Django Web (utils.py)
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener datos del request
        data = json.loads(request.body)
        prompt = data.get('prompt', '')
        
        if not prompt:
            return JsonResponse({
                'success': False,
                'error': 'El prompt es requerido'
            }, status=400)
        
        # ✅ USAR LA MISMA FUNCIÓN QUE DJANGO WEB
        try:
            from core.utils import generar_acta_con_ia
            
            # Esta función devuelve {"orden_dia": "...", "desarrollo": "..."}
            resultado = generar_acta_con_ia(prompt, user)
            
            return JsonResponse({
                'success': True,
                'data': {
                    'orden_dia': resultado['orden_dia'],      # ← SEPARADO
                    'desarrollo': resultado['desarrollo'],    # ← SEPARADO
                    'modelo_usado': 'llama-3.1-8b-instant',
                }
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': handle_error(e, 'Error de formato en respuesta de IA')
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': handle_error(e, 'Error al generar contenido con IA')
            }, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)

@csrf_exempt
def actas_pendientes_firma_api(request):
    """
    API para obtener actas que el usuario debe firmar
    Soporta paginación: ?page=1&limit=20
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)

    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)

        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)

        # Parámetros de paginación
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            limit = min(limit, 100)  # Máximo 100 registros por página
        except ValueError:
            page = 1
            limit = 20

        # Obtener firmas pendientes del usuario
        firmas_pendientes = Firma.objects.filter(
            usuario=user,
            firmado=False,
            acta__estado='en_revision'  # Solo actas en revisión
        ).select_related('acta', 'acta__creador').order_by('-acta__fecha_creacion')

        # Contar total antes de paginar
        total_count = firmas_pendientes.count()

        # Aplicar paginación
        start = (page - 1) * limit
        end = start + limit
        firmas_paginadas = firmas_pendientes[start:end]

        actas_data = []
        for firma in firmas_paginadas:
            acta = firma.acta

            # Contar cuántos han firmado
            total_participantes = Participante.objects.filter(acta=acta).count()
            firmados = Firma.objects.filter(acta=acta, firmado=True).count()

            actas_data.append({
                'firma_id': firma.id,
                'acta': {
                    'id': acta.id,
                    'numero_acta': acta.numero_acta,
                    'titulo': acta.titulo,
                    'fecha_reunion': acta.fecha_reunion.isoformat(),
                    'lugar_reunion': acta.lugar_reunion,
                    'tipo_reunion': acta.tipo_reunion,
                    'modalidad': acta.modalidad,
                    'estado': acta.estado,
                    'orden_dia': acta.orden_dia,
                    'desarrollo': acta.desarrollo,
                    'observaciones': acta.observaciones,
                    'creador': {
                        'nombre_completo': acta.creador.get_full_name(),
                        'username': acta.creador.username,
                    }
                },
                'firmas_completadas': f'{firmados}/{total_participantes}',
                'porcentaje_firmado': int((firmados / total_participantes) * 100) if total_participantes > 0 else 0,
            })

        # Calcular paginación
        total_pages = (total_count + limit - 1) // limit

        return JsonResponse({
            'success': True,
            'data': {
                'actas': actas_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1,
                }
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)

@csrf_exempt
def firmar_acta_api(request):
    """
    API para firmar un acta
    Recibe la firma como imagen en base64
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener datos del request
        data = json.loads(request.body)
        firma_id = data.get('firma_id')
        firma_imagen_base64 = data.get('firma_imagen')  # Base64 de la imagen
        
        if not firma_id:
            return JsonResponse({
                'success': False,
                'error': 'ID de firma requerido'
            }, status=400)
        
        if not firma_imagen_base64:
            return JsonResponse({
                'success': False,
                'error': 'Imagen de firma requerida'
            }, status=400)
        
        # Obtener registro de firma
        try:
            firma = Firma.objects.get(id=firma_id, usuario=user)
        except Firma.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Firma no encontrada o no tienes permiso'
            }, status=404)
        
        # Verificar que no esté ya firmada
        if firma.firmado:
            return JsonResponse({
                'success': False,
                'error': 'Ya has firmado esta acta'
            }, status=400)
        
        # Guardar la imagen de firma
        import base64
        from django.core.files.base import ContentFile
        
        try:
            # Decodificar base64
            format, imgstr = firma_imagen_base64.split(';base64,')
            ext = format.split('/')[-1]
            
            # Crear archivo
            firma_file = ContentFile(base64.b64decode(imgstr), name=f'firma_{user.id}_{firma.id}.{ext}')
            
            # Guardar en el modelo
            firma.firma_imagen = firma_file
            firma.firmado = True
            firma.fecha_firma = timezone.now()
            firma.save()
            
            # Verificar si todos han firmado para cambiar estado del acta
            acta = firma.acta
            total_firmas = Firma.objects.filter(acta=acta).count()
            firmas_completadas = Firma.objects.filter(acta=acta, firmado=True).count()
            
            if total_firmas == firmas_completadas:
                # Todos firmaron, cambiar estado a finalizada
                acta.estado = 'finalizada'
                acta.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Firma guardada correctamente. El acta ha sido finalizada.',
                    'acta_finalizada': True
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Firma guardada correctamente',
                    'acta_finalizada': False,
                    'firmas_completadas': f'{firmas_completadas}/{total_firmas}'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': handle_error(e, 'Error al procesar la imagen de firma')
            }, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)

@csrf_exempt
def cambiar_estado_acta_api(request, acta_id):
    """
    API para cambiar el estado de un acta
    Solo el creador puede cambiar el estado
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener acta
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar que sea el creador
        if acta.creador != user:
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para cambiar el estado de esta acta'
            }, status=403)
        
        # Obtener nuevo estado del request
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        estados_validos = ['borrador', 'en_revision', 'finalizada', 'archivada']
        if nuevo_estado not in estados_validos:
            return JsonResponse({
                'success': False,
                'error': 'Estado no válido'
            }, status=400)
        
        # Validaciones según el estado
        if nuevo_estado == 'en_revision':
            # Verificar que tenga participantes
            participantes_count = Participante.objects.filter(acta=acta).count()
            if participantes_count == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'El acta debe tener al menos un participante para enviar a revisión'
                }, status=400)
        
        # Cambiar estado
        estado_anterior = acta.estado
        acta.estado = nuevo_estado
        acta.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Estado cambiado de {estado_anterior} a {nuevo_estado}',
            'data': {
                'acta_id': acta.id,
                'numero_acta': acta.numero_acta,
                'estado_anterior': estado_anterior,
                'estado_nuevo': nuevo_estado,
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
    

@csrf_exempt
def crear_compromiso_api(request):
    """
    API para crear un compromiso desde la app móvi.
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener datos del request
        data = json.loads(request.body)
        acta_id = data.get('acta_id')
        descripcion = data.get('descripcion')
        responsable_id = data.get('responsable_id')
        fecha_limite = data.get('fecha_limite')
        observaciones = data.get('observaciones', '')
        
        # Validaciones
        if not acta_id or not descripcion or not responsable_id or not fecha_limite:
            return JsonResponse({
                'success': False,
                'error': 'Faltan campos obligatorios (acta_id, descripcion, responsable_id, fecha_limite)'
            }, status=400)
        
        # Verificar que el acta existe
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar que el usuario tenga permiso (debe ser creador o participante)
        es_creador = acta.creador == user
        es_participante = Participante.objects.filter(acta=acta, usuario=user).exists()
        
        if not (es_creador or es_participante):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para agregar compromisos a esta acta'
            }, status=403)
        
        # Verificar que el responsable existe
        try:
            responsable = User.objects.get(id=responsable_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuario responsable no encontrado'
            }, status=404)
        
        # Validar formato de fecha
        from datetime import datetime
        try:
            fecha_limite_obj = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }, status=400)
        
        # Validar que la fecha no sea en el pasado
        from datetime import date
        if fecha_limite_obj < date.today():
            return JsonResponse({
                'success': False,
                'error': 'La fecha límite no puede ser en el pasado'
            }, status=400)
        
        # Crear el compromiso
        compromiso = Compromiso.objects.create(
            acta=acta,
            descripcion=descripcion,
            responsable=responsable,
            fecha_limite=fecha_limite_obj,
            observaciones=observaciones,
            estado='pendiente',
            porcentaje_avance=0
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Compromiso creado exitosamente',
            'data': {
                'id': compromiso.id,
                'descripcion': compromiso.descripcion,
                'responsable': {
                    'id': responsable.id,
                    'nombre_completo': responsable.get_full_name(),
                    'username': responsable.username,
                },
                'fecha_limite': compromiso.fecha_limite.isoformat(),
                'estado': compromiso.estado,
                'porcentaje_avance': compromiso.porcentaje_avance,
                'acta': {
                    'id': acta.id,
                    'numero_acta': acta.numero_acta,
                    'titulo': acta.titulo,
                }
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        
@csrf_exempt
def editar_acta_api(request, acta_id):
    """
    API para editar un acta (solo en estado borrador)
    Permite edición por creador y participantes
    Registra quién hizo los cambios
    """
    if request.method != 'PUT':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener el acta
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar que el acta esté en borrador
        if acta.estado != 'borrador':
            return JsonResponse({
                'success': False,
                'error': 'Solo se pueden editar actas en estado Borrador'
            }, status=403)
        
        # Verificar permisos: creador O participante
        es_creador = acta.creador == user
        es_participante = Participante.objects.filter(acta=acta, usuario=user).exists()
        
        if not (es_creador or es_participante):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para editar esta acta'
            }, status=403)
        
        # Obtener datos del request
        data = json.loads(request.body)
        
        # Registrar cambios (para auditoría)
        cambios_realizados = []
        
        # Actualizar campos básicos
        if 'titulo' in data and data['titulo'] != acta.titulo:
            cambios_realizados.append(f"Título: '{acta.titulo}' → '{data['titulo']}'")
            acta.titulo = data['titulo']
        
        if 'fecha_reunion' in data:
            nueva_fecha = datetime.fromisoformat(data['fecha_reunion'].replace('Z', '+00:00'))
            if nueva_fecha != acta.fecha_reunion:
                cambios_realizados.append(f"Fecha reunión cambiada")
                acta.fecha_reunion = nueva_fecha
        
        if 'lugar_reunion' in data and data['lugar_reunion'] != acta.lugar_reunion:
            cambios_realizados.append(f"Lugar: '{acta.lugar_reunion}' → '{data['lugar_reunion']}'")
            acta.lugar_reunion = data['lugar_reunion']
        
        if 'tipo_reunion' in data and data['tipo_reunion'] != acta.tipo_reunion:
            cambios_realizados.append(f"Tipo reunión cambiado")
            acta.tipo_reunion = data['tipo_reunion']
        
        if 'modalidad' in data and data['modalidad'] != acta.modalidad:
            cambios_realizados.append(f"Modalidad cambiada")
            acta.modalidad = data['modalidad']
        
        if 'orden_dia' in data and data['orden_dia'] != acta.orden_dia:
            cambios_realizados.append("Orden del día modificado")
            acta.orden_dia = data['orden_dia']
        
        if 'desarrollo' in data and data['desarrollo'] != acta.desarrollo:
            cambios_realizados.append("Desarrollo modificado")
            acta.desarrollo = data['desarrollo']
        
        if 'observaciones' in data and data['observaciones'] != acta.observaciones:
            cambios_realizados.append("Observaciones modificadas")
            acta.observaciones = data['observaciones']
        
        # Marcar como editada manualmente (si fue generada con IA)
        if acta.generada_con_ia and len(cambios_realizados) > 0:
            acta.editada_despues_ia = True
            acta.fecha_ultima_edicion_manual = timezone.now()
        
        # Guardar acta
        acta.save()
        
        # Actualizar participantes si se enviaron
        if 'participantes' in data:
            # Eliminar participantes actuales
            Participante.objects.filter(acta=acta).delete()
            
            # Agregar nuevos participantes
            for participante_data in data['participantes']:
                usuario_id = participante_data.get('usuario_id')
                rol = participante_data.get('rol_en_reunion', '')
                
                try:
                    usuario = User.objects.get(id=usuario_id)
                    Participante.objects.create(
                        acta=acta,
                        usuario=usuario,
                        rol_en_reunion=rol,
                        obligatorio_firma=True
                    )
                except User.DoesNotExist:
                    continue
            
            cambios_realizados.append("Participantes actualizados")
        
        # Crear comentario de auditoría con los cambios
        if cambios_realizados:
            from .models import ComentarioActa
            ComentarioActa.objects.create(
                acta=acta,
                autor=user,
                texto=f"[EDICIÓN] {user.get_full_name()} editó el acta:\n" + "\n".join(f"- {cambio}" for cambio in cambios_realizados)
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Acta actualizada correctamente',
            'data': {
                'acta_id': acta.id,
                'numero_acta': acta.numero_acta,
                'cambios_realizados': cambios_realizados,
                'editado_por': user.get_full_name(),
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        
@csrf_exempt
def generar_pdf_api(request, acta_id):
    """
    API para generar y descargar PDF del acta
    Réplica de la función generar_pdf pero con autenticación por token
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener acta
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar permisos
        es_creador = acta.creador == user
        es_participante = Participante.objects.filter(acta=acta, usuario=user).exists()
        
        if not (es_creador or es_participante or user.is_staff):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para descargar esta acta'
            }, status=403)
        
        # === GENERAR PDF (mismo código que views.generar_pdf) ===
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from datetime import timedelta
        import os
        from django.conf import settings
        from django.http import HttpResponse
        
        # Crear PDF
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="ACTA_{acta.numero_acta}.pdf"'
        
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Logo SENA (usar la ruta correcta que ya funciona)
        try:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-sena.png')
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1*inch, height=1*inch)
                story.append(logo)
        except:
            pass
        
        story.append(Spacer(1, 10))
        
        # ACTA No.
        acta_header = Table(
            [[Paragraph(f"<b>ACTA No. {acta.numero_acta}</b>", styles['Title'])]],
            colWidths=[7*inch]
        )
        acta_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ]))
        story.append(acta_header)
        
        # NOMBRE DEL COMITÉ
        comite_table = Table(
            [
                [Paragraph("<b>NOMBRE DEL COMITÉ O DE LA REUNIÓN:</b>", styles['Normal'])],
                [Paragraph(acta.titulo, styles['Normal'])]
            ],
            colWidths=[7*inch]
        )
        comite_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(comite_table)
        
        # CIUDAD/FECHA y HORA
        fecha_str = acta.fecha_reunion.strftime("%d/%m/%Y")
        hora_inicio = acta.fecha_reunion.strftime("%H:%M")
        hora_fin = (acta.fecha_reunion + timedelta(hours=2)).strftime("%H:%M")
        
        info_table = Table(
            [
                [
                    Paragraph("<b>CIUDAD Y FECHA:</b>", styles['Normal']),
                    Paragraph(f"{acta.lugar_reunion}, {fecha_str}", styles['Normal']),
                    Paragraph("<b>HORA INICIO:</b>", styles['Normal']),
                    Paragraph(hora_inicio, styles['Normal']),
                    Paragraph("<b>HORA FIN:</b>", styles['Normal']),
                    Paragraph(hora_fin, styles['Normal']),
                ]
            ],
            colWidths=[1.3*inch, 1.7*inch, 1*inch, 0.7*inch, 0.8*inch, 0.7*inch]
        )
        info_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(info_table)
        
        # LUGAR/ENLACE
        lugar_table = Table(
            [
                [
                    Paragraph("<b>LUGAR Y/O ENLACE:</b>", styles['Normal']),
                    Paragraph(acta.lugar_reunion, styles['Normal']),
                    Paragraph("<b>DIRECCIÓN / REGIONAL / CENTRO:</b>", styles['Normal']),
                    Paragraph("Centro Minero SENA", styles['Normal']),
                ]
            ],
            colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch]
        )
        lugar_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(lugar_table)

        # AGENDA - minimizar espacio completamente
        agenda_content = acta.orden_dia if acta.orden_dia else "No especificada"

        # Crear estilo compacto sin espacios
        from reportlab.lib.styles import ParagraphStyle
        style_compacto = ParagraphStyle(
            'Compacto',
            parent=styles['Normal'],
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=0,
            rightIndent=0,
        )

        # Si el contenido es muy corto, usar una sola fila compacta
        if len(agenda_content.strip()) < 50:
            agenda_table = Table(
                [
                    [Paragraph("<b>AGENDA O PUNTOS PARA DESARROLLAR:</b><br/>" + agenda_content.replace('\n', '<br/>'), style_compacto)]
                ],
                colWidths=[7*inch],
                rowHeights=[0.6*inch],
                splitByRow=1  # Altura fija muy pequeña
            )
        else:
            # Contenido largo: altura automática
            agenda_table = Table(
                [
                    [Paragraph("<b>AGENDA O PUNTOS PARA DESARROLLAR:</b>", styles['Normal'])],
                    [Paragraph(agenda_content.replace('\n', '<br/>'), styles['Normal'])]
                ],
                colWidths=[7*inch],
                splitByRow=1
            )

        agenda_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),      # Padding superior mínimo
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),   # Padding inferior mínimo
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(agenda_table)
        
        # OBJETIVOS
        objetivo = f"Reunión de tipo {acta.get_tipo_reunion_display()}"
        if acta.generada_con_ia:
            objetivo += " (Generada con IA)"
        
        objetivo_table = Table(
            [
                [Paragraph("<b>OBJETIVO(S) DE LA REUNIÓN:</b>", styles['Normal'])],
                [Paragraph(objetivo, styles['Normal'])]
            ],
            colWidths=[7*inch],
            splitByRow=1
        )
        objetivo_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(objetivo_table)
        
        # DESARROLLO
        desarrollo_content = acta.desarrollo if acta.desarrollo else "No especificado"
        desarrollo_table = Table(
            [
                [Paragraph("<b>DESARROLLO DE LA REUNIÓN</b>", styles['Normal'])],
                [Paragraph(desarrollo_content.replace('\n', '<br/>'), styles['Normal'])]
            ],
            colWidths=[7*inch],
            splitByRow=1
        )
        desarrollo_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(desarrollo_table)
        
        # CONCLUSIONES
        conclusiones = acta.observaciones if acta.observaciones else "Sin observaciones adicionales"
        conclusiones_table = Table(
            [
                [Paragraph("<b>CONCLUSIONES</b>", styles['Normal'])],
                [Paragraph(conclusiones.replace('\n', '<br/>'), styles['Normal'])]
            ],
            colWidths=[7*inch]
        )
        conclusiones_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(conclusiones_table)
        
        # COMPROMISOS
        compromisos_data = [
            [
                Paragraph("<b>ACTIVIDAD/DECISIÓN</b>", styles['Normal']),
                Paragraph("<b>FECHA</b>", styles['Normal']),
                Paragraph("<b>RESPONSABLE</b>", styles['Normal']),
                Paragraph("<b>FIRMA</b>", styles['Normal']),
            ]
        ]
        
        if acta.compromisos.exists():
            for comp in acta.compromisos.all():
                compromisos_data.append([
                    Paragraph(comp.descripcion, styles['Normal']),
                    Paragraph(comp.fecha_limite.strftime("%d/%m/%Y"), styles['Normal']),
                    Paragraph(comp.responsable.get_full_name(), styles['Normal']),
                    Paragraph("", styles['Normal']),
                ])
        else:
            compromisos_data.append([
                Paragraph("No se registraron compromisos", styles['Normal']),
                "", "", ""
            ])
        
        compromisos_table = Table(compromisos_data, colWidths=[2.5*inch, 1.2*inch, 1.8*inch, 1.5*inch])
        compromisos_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        story.append(compromisos_table)

        # ASISTENTES
        story.append(Spacer(1, 10))

        asistentes_data = [
            [
                Paragraph("<b>NOMBRE</b>", styles['Normal']),
                Paragraph("<b>DEPENDENCIA/EMPRESA</b>", styles['Normal']),
                Paragraph("<b>APRUEBA (SI/NO)</b>", styles['Normal']),
                Paragraph("<b>FIRMA</b>", styles['Normal']),
            ]
        ]

        for participante in acta.participantes.select_related('usuario').all():
            firma_obj = acta.firmas.filter(usuario=participante.usuario).first()

            if firma_obj and firma_obj.firmado:
                # Intentar cargar la imagen de la firma
                firma_cell = None

                # OPCIÓN 1: Buscar en firma_imagen (campo del modelo Firma)
                if firma_obj.firma_imagen:
                    try:
                        firma_path = os.path.join(settings.MEDIA_ROOT, str(firma_obj.firma_imagen))
                        if os.path.exists(firma_path):
                            firma_cell = Image(firma_path, width=1.5*inch, height=0.6*inch)
                    except Exception as e:
                        print(f"Error cargando firma_imagen: {e}")

                # OPCIÓN 2: Buscar en firma_digital del usuario (si existe)
                if not firma_cell and hasattr(participante.usuario, 'firma_digital') and participante.usuario.firma_digital:
                    try:
                        firma_path = os.path.join(settings.MEDIA_ROOT, str(participante.usuario.firma_digital))
                        if os.path.exists(firma_path):
                            firma_cell = Image(firma_path, width=1.5*inch, height=0.6*inch)
                    except Exception as e:
                        print(f"Error cargando firma_digital: {e}")

                # Si no se pudo cargar imagen, usar texto
                if not firma_cell:
                    firma_cell = Paragraph(
                        "✓ Firmado<br/><font size=6>({fecha})</font>".format(
                            fecha=firma_obj.fecha_firma.strftime("%d/%m/%Y") if firma_obj.fecha_firma else "N/A"
                        ),
                        styles['Normal']
                    )
            else:
                firma_cell = Paragraph("<font color='red'>Pendiente</font>", styles['Normal'])

            asistentes_data.append([
                Paragraph(participante.usuario.get_full_name(), styles['Normal']),
                Paragraph(participante.rol_en_reunion or "Participante", styles['Normal']),
                Paragraph("SÍ" if firma_obj and firma_obj.firmado else "NO", styles['Normal']),
                firma_cell
            ])

        asistentes_table = Table(asistentes_data, colWidths=[1.8*inch, 1.8*inch, 1.2*inch, 2.2*inch])
        asistentes_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        story.append(asistentes_table)
        
        # NOTA LEGAL
        story.append(Spacer(1, 10))
        nota_legal = Paragraph(
            "<font size=7>De acuerdo con La Ley 1581 de 2012, Protección de Datos Personales, el Servicio Nacional de Aprendizaje SENA, "
            "se compromete a garantizar la seguridad y protección de los datos personales que se encuentran almacenados en este "
            "documento, y les dará el tratamiento correspondiente en cumplimiento de lo establecido legalmente.</font>",
            styles['Normal']
        )
        story.append(nota_legal)
        
        # FOOTER
        story.append(Spacer(1, 20))
        footer = Paragraph("<font size=8><b>GOR-F-084 V02</b></font>", styles['Normal'])
        story.append(footer)
        
        # Construir PDF
        doc.build(story)
        
        return response
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        
@csrf_exempt
def mis_compromisos_api(request):
    """
    API para obtener los compromisos asignados al usuario autenticado
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener compromisos del usuario
        compromisos = Compromiso.objects.filter(
            responsable=user
        ).select_related('acta', 'responsable').order_by('-fecha_limite')
        
        # Serializar compromisos
        compromisos_data = []
        for comp in compromisos:
            compromisos_data.append({
                'id': comp.id,
                'descripcion': comp.descripcion,
                'fecha_limite': comp.fecha_limite.strftime('%Y-%m-%d'),
                'estado': comp.estado,
                'porcentaje_avance': comp.porcentaje_avance,
                'dias_restantes': comp.dias_restantes(),
                'observaciones': comp.observaciones,
                'reporte_cumplimiento': comp.reporte_cumplimiento,
                'acta': {
                    'id': comp.acta.id,
                    'numero_acta': comp.acta.numero_acta,
                    'titulo': comp.acta.titulo,
                },
                'responsable': {
                    'id': comp.responsable.id,
                    'nombre_completo': comp.responsable.get_full_name(),
                }
            })
        
        return JsonResponse({
            'success': True,
            'data': compromisos_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)


@csrf_exempt
def actualizar_compromiso_api(request, compromiso_id):
    """
    API para actualizar el estado, porcentaje y reporte de un compromiso
    Solo el responsable puede actualizar
    """
    if request.method != 'PUT':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener compromiso
        try:
            compromiso = Compromiso.objects.get(id=compromiso_id)
        except Compromiso.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Compromiso no encontrado'
            }, status=404)
        
        # Verificar que el usuario es el responsable
        if compromiso.responsable != user:
            return JsonResponse({
                'success': False,
                'error': 'Solo el responsable puede actualizar este compromiso'
            }, status=403)
        
        # Obtener datos del request
        data = json.loads(request.body)
        
        # Actualizar campos
        estado = data.get('estado')
        porcentaje_avance = data.get('porcentaje_avance')
        reporte_cumplimiento = data.get('reporte_cumplimiento', '')
        
        # Validar estado
        estados_validos = ['pendiente', 'en_progreso', 'completado', 'vencido']
        if estado and estado not in estados_validos:
            return JsonResponse({
                'success': False,
                'error': f'Estado inválido. Debe ser: {", ".join(estados_validos)}'
            }, status=400)
        
        # Validar porcentaje
        if porcentaje_avance is not None:
            try:
                porcentaje_avance = int(porcentaje_avance)
                if porcentaje_avance < 0 or porcentaje_avance > 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'El porcentaje debe estar entre 0 y 100'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Porcentaje inválido'
                }, status=400)
        
        # Actualizar compromiso
        if estado:
            compromiso.estado = estado
        
        if porcentaje_avance is not None:
            compromiso.porcentaje_avance = porcentaje_avance
            
            # Si llega a 100%, marcar como completado
            if porcentaje_avance == 100:
                compromiso.estado = 'completado'
                compromiso.fecha_completado = timezone.now()
        
        if reporte_cumplimiento:
            compromiso.reporte_cumplimiento = reporte_cumplimiento
        
        compromiso.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Compromiso actualizado exitosamente',
            'data': {
                'id': compromiso.id,
                'estado': compromiso.estado,
                'porcentaje_avance': compromiso.porcentaje_avance,
                'reporte_cumplimiento': compromiso.reporte_cumplimiento,
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        
@csrf_exempt
def aplicar_silencio_administrativo_api(request, acta_id):
    """
    API para aplicar silencio administrativo a un acta
    POST: Aplica silencio administrativo si cumple condiciones
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
        # Obtener el acta
        try:
            acta = Acta.objects.get(id=acta_id)
        except Acta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acta no encontrada'
            }, status=404)
        
        # Verificar que puede aplicar silencio
        if not acta.puede_aplicar_silencio_administrativo():
            # Dar razón específica
            if not acta.fecha_limite_firmas:
                razon = 'El acta no tiene fecha límite de firmas establecida'
            elif acta.estado != 'en_revision':
                razon = f'El acta debe estar en estado "En Revisión" (actual: {acta.get_estado_display()})'
            elif timezone.now() <= acta.fecha_limite_firmas:
                dias_restantes = (acta.fecha_limite_firmas - timezone.now()).days
                razon = f'Aún no ha vencido el plazo de firmas (faltan {dias_restantes} días)'
            else:
                razon = 'No se puede aplicar silencio administrativo'
            
            return JsonResponse({
                'success': False,
                'error': razon
            }, status=400)
        
        # Aplicar silencio administrativo
        acta.aplicar_silencio_admin()
        
        # Crear notificación para participantes
        from notifications.models import Notification
        participantes = acta.participantes.all()
        
        for participante in participantes:
            Notification.objects.create(
                usuario=participante.usuario,
                tipo='silencio_administrativo',
                titulo='Silencio Administrativo Aplicado',
                mensaje=f'Se ha aplicado silencio administrativo al Acta {acta.numero_acta} - {acta.titulo}',
                enlace=f'/actas/{acta.id}/',
                metadata={
                    'acta_id': acta.id,
                    'acta_numero': acta.numero_acta,
                }
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Silencio administrativo aplicado exitosamente',
            'data': {
                'acta_id': acta.id,
                'numero_acta': acta.numero_acta,
                'estado': acta.estado,
                'silencio_administrativo': acta.silencio_administrativo,
                'firmas_aplicadas': acta.firmas.filter(firmado_por_silencio=True).count(),
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': handle_error(e)
        }, status=500)
        
@csrf_exempt
def register_api(request):
    """
    API para registro de nuevos usuarios
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Obtener datos
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        rol = data.get('rol', 'aprendiz')
        telefono = data.get('telefono', '').strip()
        
        # Validaciones básicas
        if not all([first_name, last_name, email, password]):
            return JsonResponse({
                'success': False,
                'error': 'Todos los campos son obligatorios'
            }, status=400)
        
        # Validar email
        if not '@' in email:
            return JsonResponse({
                'success': False,
                'error': 'Email inválido'
            }, status=400)
        
        # Validar contraseña
        if len(password) < 8:
            return JsonResponse({
                'success': False,
                'error': 'La contraseña debe tener al menos 8 caracteres'
            }, status=400)
        
        # Validar que el email no exista
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Este correo ya está registrado'
            }, status=400)
        
        # Validar rol
        roles_validos = ['aprendiz', 'instructor', 'funcionario', 'coordinador', 'director']
        if rol not in roles_validos:
            return JsonResponse({
                'success': False,
                'error': 'Rol inválido'
            }, status=400)
        
        # No permitir registro como admin
        if rol == 'admin':
            return JsonResponse({
                'success': False,
                'error': 'No puedes registrarte como Administrador'
            }, status=400)
        
        # Validar dominio de email según rol
        if rol == 'aprendiz':
            dominios_validos = ['@soy.sena.edu.co', '@gmail.com']
            if not any(email.endswith(d) for d in dominios_validos):
                return JsonResponse({
                    'success': False,
                    'error': 'El correo del aprendiz debe ser @soy.sena.edu.co o @gmail.com'
                }, status=400)
        elif rol in ['funcionario', 'coordinador', 'director', 'instructor']:
            dominios_validos = ['@sena.edu.co', '@gmail.com']
            if not any(email.endswith(d) for d in dominios_validos):
                return JsonResponse({
                    'success': False,
                    'error': 'El correo debe ser @sena.edu.co o @gmail.com'
                }, status=400)
        
        # Generar username único
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            rol=rol,
            telefono=telefono,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Cuenta creada correctamente. Ahora puedes iniciar sesión.',
            'data': {
                'id': user.id,
                'email': user.email,
                'nombre_completo': user.get_full_name(),
                'rol': user.rol,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def actualizar_firma_api(request):
    """
    API para actualizar firma digital del usuario
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    # Verificar autenticación
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    try:
        token_obj = Token.objects.get(key=token)
        user = token_obj.user
    except Token.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    # Verificar que se envió una imagen
    if 'firma_digital' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No se envió ninguna imagen'
        }, status=400)
    
    firma = request.FILES['firma_digital']
    
    # Validar tamaño (máximo 2 MB)
    if firma.size > 2 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'error': 'La imagen no debe superar los 2 MB'
        }, status=400)
    
    # Validar formato
    extensiones_permitidas = ['.png', '.jpg', '.jpeg']
    extension = os.path.splitext(firma.name)[1].lower()
    if extension not in extensiones_permitidas:
        return JsonResponse({
            'success': False,
            'error': 'Solo se permiten imágenes PNG, JPG o JPEG'
        }, status=400)
    
    try:
        # Eliminar firma anterior si existe
        if user.firma_digital:
            if os.path.isfile(user.firma_digital.path):
                os.remove(user.firma_digital.path)
        
        # Guardar nueva firma
        user.firma_digital = firma
        user.save()
        
        # URL completa de la firma
        firma_url = request.build_absolute_uri(user.firma_digital.url) if user.firma_digital else None
        
        return JsonResponse({
            'success': True,
            'message': 'Firma digital actualizada correctamente',
            'data': {
                'firma_digital': firma_url,
                'tiene_firma': True,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al guardar firma: {str(e)}'
        }, status=500)
        
@csrf_exempt
def solicitar_codigo_recuperacion_api(request):
    """
    API para solicitar código de recuperación de contraseña
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').lower().strip()
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email es requerido'
            }, status=400)
        
        # Buscar usuario
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Por seguridad, no revelar si el email existe o no
            return JsonResponse({
                'success': True,
                'message': 'Si el correo existe, recibirás un código de recuperación'
            })
        
        # Generar código de 6 dígitos
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Crear registro de código (expira en 15 minutos)
        from datetime import timedelta
        from accounts.models import PasswordResetCode
        
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Enviar email
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = 'Código de Recuperación - Sistema Actas SENA'
        message = f"""
Hola {user.get_full_name()},

Has solicitado recuperar tu contraseña en el Sistema de Gestión de Actas SENA.

Tu código de recuperación es:

    {code}

Este código expira en 15 minutos.

Si no solicitaste este código, ignora este mensaje.

---
Sistema de Gestión de Actas
SENA Centro Minero
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Código de recuperación enviado al correo'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al enviar código: {str(e)}'
        }, status=500)


@csrf_exempt
def verificar_codigo_recuperacion_api(request):
    """
    API para verificar código de recuperación
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').lower().strip()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return JsonResponse({
                'success': False,
                'error': 'Email y código son requeridos'
            }, status=400)
        
        # Buscar usuario
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Código inválido o expirado'
            }, status=400)
        
        # Buscar código válido
        from accounts.models import PasswordResetCode
        
        try:
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                used=False
            ).latest('created_at')
            
            if not reset_code.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Código expirado. Solicita uno nuevo.'
                }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': 'Código verificado correctamente'
            })
            
        except PasswordResetCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Código inválido o expirado'
            }, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al verificar código: {str(e)}'
        }, status=500)


@csrf_exempt
def resetear_password_api(request):
    """
    API para establecer nueva contraseña con código de recuperación
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').lower().strip()
        code = data.get('code', '').strip()
        new_password = data.get('new_password', '')
        
        if not email or not code or not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Email, código y nueva contraseña son requeridos'
            }, status=400)
        
        # Validar contraseña
        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'error': 'La contraseña debe tener al menos 8 caracteres'
            }, status=400)
        
        # Buscar usuario
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Código inválido o expirado'
            }, status=400)
        
        # Buscar código válido
        from accounts.models import PasswordResetCode
        
        try:
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                used=False
            ).latest('created_at')
            
            if not reset_code.is_valid():
                return JsonResponse({
                    'success': False,
                    'error': 'Código expirado. Solicita uno nuevo.'
                }, status=400)
            
            # Cambiar contraseña
            user.set_password(new_password)
            user.save()
            
            # Marcar código como usado
            reset_code.used = True
            reset_code.save()
            
            # Invalidar todos los otros códigos del usuario
            PasswordResetCode.objects.filter(
                user=user,
                used=False
            ).exclude(id=reset_code.id).update(used=True)
            
            return JsonResponse({
                'success': True,
                'message': 'Contraseña actualizada correctamente'
            })
            
        except PasswordResetCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Código inválido o expirado'
            }, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al resetear contraseña: {str(e)}'
        }, status=500)
        
@csrf_exempt
def firmas_pendientes_api(request):
    """
    API para obtener lista completa de actas pendientes de firma
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    # Verificar autenticación (sistema personalizado)
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    # Sistema de token personalizado: token_{id}
    if not token.startswith('token_'):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)

    try:
        # Obtener firmas pendientes del usuario
        firmas_pendientes = Firma.objects.filter(
            usuario=user,
            firmado=False,
            acta__estado='en_revision'
        ).select_related('acta', 'acta__creador').order_by('-acta__fecha_creacion')
        
        # Construir respuesta con información completa
        firmas_data = []
        for firma in firmas_pendientes:
            acta = firma.acta
            
            # Calcular estadísticas de firmas del acta
            total_firmas = acta.participantes.count()
            firmas_completadas = acta.firmas.filter(firmado=True).count()
            porcentaje_firmado = round((firmas_completadas / total_firmas * 100), 1) if total_firmas > 0 else 0
            
            firmas_data.append({
                'firma_id': firma.id,  # ← Cambiado de 'id' a 'firma_id'
                'acta': {
                    'id': acta.id,
                    'numero_acta': acta.numero_acta,
                    'titulo': acta.titulo,
                    'fecha_reunion': acta.fecha_reunion.isoformat(),
                    'lugar_reunion': acta.lugar_reunion,
                    'tipo_reunion': acta.tipo_reunion,  # ← Agregado
                    'modalidad': acta.modalidad,  # ← Agregado
                    'estado': acta.estado,
                    'orden_dia': acta.orden_dia or '',  # ← Agregado
                    'desarrollo': acta.desarrollo or '',  # ← Agregado
                    'observaciones': acta.observaciones or '',  # ← Agregado
                    'creador': {
                        'id': acta.creador.id,
                        'nombre_completo': acta.creador.get_full_name(),
                        'username': acta.creador.username,  # ← Agregado
                        'email': acta.creador.email,
                    }
                },
                'firmas_completadas': f"{firmas_completadas}/{total_firmas}",
                'porcentaje_firmado': int(porcentaje_firmado),  # ← Convertir a int
            })
        
        return JsonResponse({
            'success': True,
            'data': firmas_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al cargar firmas pendientes: {str(e)}'
        }, status=500)
    
@csrf_exempt
def exportar_datos_usuario_api(request):
    """
    API para exportar todos los datos del usuario actual
    Genera un archivo ZIP con:
    - Perfil del usuario (JSON)
    - Actas creadas por el usuario (JSON)
    - Compromisos asignados (JSON)
    - Firmas realizadas (JSON)
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    # Autenticación
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    if not token.startswith('token_'):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        import zipfile
        import tempfile
        from django.http import FileResponse
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_file.name, 'w') as backup_zip:
            # 1. Perfil del usuario
            perfil_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'rol': user.rol,
                'telefono': user.telefono,
                'fecha_exportacion': timezone.now().isoformat(),
            }
            backup_zip.writestr('perfil.json', json.dumps(perfil_data, indent=2, ensure_ascii=False))
            
            # 2. Actas creadas por el usuario
            actas = Acta.objects.filter(creador=user)
            actas_data = []
            for acta in actas:
                actas_data.append({
                    'id': acta.id,
                    'numero_acta': acta.numero_acta,
                    'titulo': acta.titulo,
                    'fecha_reunion': acta.fecha_reunion.isoformat(),
                    'lugar_reunion': acta.lugar_reunion,
                    'tipo_reunion': acta.tipo_reunion,
                    'modalidad': acta.modalidad,
                    'orden_dia': acta.orden_dia,
                    'desarrollo': acta.desarrollo,
                    'observaciones': acta.observaciones,
                    'estado': acta.estado,
                    'fecha_creacion': acta.fecha_creacion.isoformat(),
                })
            backup_zip.writestr('actas.json', json.dumps(actas_data, indent=2, ensure_ascii=False))
            
            # 3. Compromisos donde es responsable
            compromisos = Compromiso.objects.filter(responsable=user)
            compromisos_data = []
            for compromiso in compromisos:
                compromisos_data.append({
                    'id': compromiso.id,
                    'descripcion': compromiso.descripcion,
                    'fecha_limite': compromiso.fecha_limite.isoformat(),
                    'estado': compromiso.estado,
                    'porcentaje_avance': compromiso.porcentaje_avance,
                    'acta_numero': compromiso.acta.numero_acta,
                    'fecha_completado': compromiso.fecha_completado.isoformat() if compromiso.fecha_completado else None,
                    'observaciones': compromiso.observaciones,
                })
            backup_zip.writestr('compromisos.json', json.dumps(compromisos_data, indent=2, ensure_ascii=False))
            
            # 4. Firmas realizadas
            firmas = Firma.objects.filter(usuario=user, firmado=True)
            firmas_data = []
            for firma in firmas:
                firmas_data.append({
                    'acta_numero': firma.acta.numero_acta,
                    'acta_titulo': firma.acta.titulo,
                    'fecha_firma': firma.fecha_firma.isoformat() if firma.fecha_firma else None,
                })
            backup_zip.writestr('firmas.json', json.dumps(firmas_data, indent=2, ensure_ascii=False))
            
            # 5. README con información
            readme = f"""
EXPORTACIÓN DE DATOS PERSONALES
Sistema de Gestión de Actas SENA

Usuario: {user.get_full_name()}
Email: {user.email}
Fecha de exportación: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Contenido:
- perfil.json: Información de tu perfil
- actas.json: {actas.count()} acta(s) creada(s) por ti
- compromisos.json: {compromisos.count()} compromiso(s) asignado(s)
- firmas.json: {firmas.count()} firma(s) realizada(s)

Para importar estos datos:
1. Ve a tu perfil en la aplicación
2. Click en "Importar mis datos"
3. Selecciona este archivo ZIP

Nota: Solo puedes importar tus propios datos.
            """
            backup_zip.writestr('README.txt', readme)
        
        # Leer el contenido del archivo
        temp_file.close()
        with open(temp_file.name, 'rb') as f:
            file_content = f.read()

        # Eliminar archivo temporal
        try:
            os.unlink(temp_file.name)
        except:
            pass

        # Nombre del archivo
        filename = f'backup_{user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip'

        # Crear respuesta HTTP con el contenido
        from django.http import HttpResponse
        response = HttpResponse(file_content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_content)
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'

        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al exportar datos: {str(e)}'
        }, status=500)

@csrf_exempt
def importar_datos_usuario_api(request):
    """
    API para importar datos del usuario desde un archivo ZIP
    Valida que solo se importen datos del mismo usuario
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    # Autenticación
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    if not token.startswith('token_'):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        import zipfile
        import tempfile
        
        # Obtener archivo del request
        if 'backup_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó ningún archivo'
            }, status=400)
        
        backup_file = request.FILES['backup_file']
        
        # Validar extensión
        if not backup_file.name.endswith('.zip'):
            return JsonResponse({
                'success': False,
                'error': 'El archivo debe ser un ZIP'
            }, status=400)
        
        # Validar tamaño (máximo 10 MB)
        if backup_file.size > 10 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'El archivo es demasiado grande (máximo 10 MB)'
            }, status=400)
        
        # Guardar temporalmente
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        for chunk in backup_file.chunks():
            temp_file.write(chunk)
        temp_file.close()
        
        # Leer contenido del ZIP
        with zipfile.ZipFile(temp_file.name, 'r') as backup_zip:
            # Verificar archivos esperados
            expected_files = ['perfil.json', 'actas.json', 'compromisos.json', 'firmas.json']
            zip_files = backup_zip.namelist()
            
            for expected in expected_files:
                if expected not in zip_files:
                    os.unlink(temp_file.name)
                    return JsonResponse({
                        'success': False,
                        'error': f'Archivo ZIP inválido: falta {expected}'
                    }, status=400)
            
            # Leer perfil
            perfil_content = backup_zip.read('perfil.json')
            perfil_data = json.loads(perfil_content)
            
            # Validar que el backup es del mismo usuario
            if perfil_data['email'] != user.email:
                os.unlink(temp_file.name)
                return JsonResponse({
                    'success': False,
                    'error': 'Este backup pertenece a otro usuario. Solo puedes importar tus propios datos.'
                }, status=403)
            
            # Leer actas
            actas_content = backup_zip.read('actas.json')
            actas_data = json.loads(actas_content)
            
            # Leer compromisos
            compromisos_content = backup_zip.read('compromisos.json')
            compromisos_data = json.loads(compromisos_content)
        
        # Eliminar archivo temporal
        os.unlink(temp_file.name)
        
        # Estadísticas de importación
        stats = {
            'actas_en_backup': len(actas_data),
            'compromisos_en_backup': len(compromisos_data),
            'actas_actuales': Acta.objects.filter(creador=user).count(),
            'compromisos_actuales': Compromiso.objects.filter(responsable=user).count(),
        }
        
        return JsonResponse({
            'success': True,
            'message': 'Backup validado correctamente',
            'stats': stats,
            'advertencia': 'IMPORTANTE: La importación sobrescribirá tus datos actuales. ¿Deseas continuar?'
        })
        
    except zipfile.BadZipFile:
        return JsonResponse({
            'success': False,
            'error': 'Archivo ZIP corrupto o inválido'
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos en el backup'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al importar datos: {str(e)}'
        }, status=500)


@csrf_exempt
def confirmar_importacion_datos_api(request):
    """
    API para confirmar y ejecutar la importación de datos
    Este endpoint ejecuta la restauración real de los datos
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    # Autenticación
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    if not token.startswith('token_'):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Token inválido'
        }, status=401)
    
    try:
        import zipfile
        import tempfile
        from django.db import transaction
        
        # Obtener archivo del request
        if 'backup_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó ningún archivo'
            }, status=400)
        
        backup_file = request.FILES['backup_file']
        
        # Guardar temporalmente
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        for chunk in backup_file.chunks():
            temp_file.write(chunk)
        temp_file.close()
        
        # Ejecutar importación en una transacción
        with transaction.atomic():
            with zipfile.ZipFile(temp_file.name, 'r') as backup_zip:
                # Leer datos
                actas_content = backup_zip.read('actas.json')
                actas_data = json.loads(actas_content)
                
                compromisos_content = backup_zip.read('compromisos.json')
                compromisos_data = json.loads(compromisos_content)
                
                # Eliminar actas actuales del usuario
                Acta.objects.filter(creador=user).delete()
                
                # Restaurar actas
                actas_restauradas = 0
                for acta_data in actas_data:
                    try:
                        Acta.objects.create(
                            creador=user,
                            numero_acta=acta_data['numero_acta'],
                            titulo=acta_data['titulo'],
                            fecha_reunion=datetime.fromisoformat(acta_data['fecha_reunion']),
                            lugar_reunion=acta_data['lugar_reunion'],
                            tipo_reunion=acta_data['tipo_reunion'],
                            modalidad=acta_data['modalidad'],
                            orden_dia=acta_data['orden_dia'],
                            desarrollo=acta_data['desarrollo'],
                            observaciones=acta_data['observaciones'],
                            estado=acta_data['estado'],
                        )
                        actas_restauradas += 1
                    except Exception as e:
                        # Si falla una acta, continuar con las demás
                        continue
        
        # Eliminar archivo temporal
        os.unlink(temp_file.name)
        
        return JsonResponse({
            'success': True,
            'message': 'Datos importados correctamente',
            'stats': {
                'actas_restauradas': actas_restauradas,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al importar datos: {str(e)}'
        }, status=500)

