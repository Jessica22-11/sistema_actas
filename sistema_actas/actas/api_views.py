from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Acta, Participante, Firma, Compromiso
import json
from .models import Acta, Compromiso, Firma

User = get_user_model()  

@csrf_exempt
def login_api(request):
    """
    API de login para la app móvil Flutter.
    
    Recibe:
        - username (email del usuario)
        - password
    
    Retorna:
        - token (por ahora simple, luego JWT)
        - user (datos del usuario)
    """
    if request.method == 'POST':
        try:
            # Leer datos del request
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            # Autenticar usuario
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Login exitoso
                return JsonResponse({
                    'success': True,
                    'token': f'token_{user.id}',  # TODO: Implementar JWT real después
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
                'error': str(e)
            }, status=500)
    
    # Método no permitido
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
    """
    if request.method != 'GET':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)
    
    try:
        # Obtener token del header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        # Por ahora, extraer user_id del token simple
        if not token or not token.startswith('token_'):
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        user_id = int(token.replace('token_', ''))
        user = User.objects.get(id=user_id)
        
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
                'numero_acta': compromiso.acta.numero_acta,
                'titulo': compromiso.acta.titulo,
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
            'error': str(e)
        }, status=500)
        

@csrf_exempt
def actas_list_api(request):
    """
    API para listar actas del usuario
    Soporta filtros por estado y búsqueda
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
        
        # Serializar datos
        actas_data = []
        for acta in actas:
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
        
        return JsonResponse({
            'success': True,
            'data': {
                'total': len(actas_data),
                'actas': actas_data,
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
            'error': str(e)
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
            'error': str(e)
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
            'error': str(e)
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
        if len(new_password) < 6:
            return JsonResponse({
                'success': False,
                'error': 'La nueva contraseña debe tener al menos 6 caracteres'
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
            'error': str(e)
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
            'error': str(e)
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
            'error': str(e)
        }, status=500)


@csrf_exempt
def generar_acta_ia_api(request):
    """
    API para generar contenido de acta usando IA (Groq)
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
        
        # Intentar generar con Groq
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            system_prompt = """Eres un asistente especializado en generar actas de reuniones académicas.
Genera el contenido solicitado en formato estructurado y profesional.
Responde SOLO con el contenido del acta, sin explicaciones adicionales."""
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            contenido = completion.choices[0].message.content
            
            return JsonResponse({
                'success': True,
                'data': {
                    'contenido': contenido,
                    'modelo_usado': 'llama-3.3-70b-versatile',
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar con IA: {str(e)}'
            }, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def actas_pendientes_firma_api(request):
    """
    API para obtener actas que el usuario debe firmar
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
        
        # Obtener firmas pendientes del usuario
        firmas_pendientes = Firma.objects.filter(
            usuario=user,
            firmado=False,
            acta__estado='en_revision'  # Solo actas en revisión
        ).select_related('acta', 'acta__creador').order_by('-acta__fecha_creacion')
        
        actas_data = []
        for firma in firmas_pendientes:
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
        
        return JsonResponse({
            'success': True,
            'data': actas_data
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
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
                'error': f'Error al procesar la firma: {str(e)}'
            }, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Usuario no encontrado'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
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
            'error': str(e)
        }, status=500)