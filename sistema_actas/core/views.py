from django.shortcuts import render, redirect, get_list_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.core.paginator import Paginator

from actas.models import Acta, Compromiso, Firma
from notifications.models import Notification
from core.utils import generar_acta_con_ia

@login_required
def dashboard(request):
    user = request.user
    
    # Estadísticas generales
    stats = {
        'total_actas': Acta.objects.filter(
            Q(creador=user) | Q(participantes__usuario=user)
        ).distinct().count(),
        'actas_pendientes_firma': Firma.objects.filter(
            usuario=user, firmado=False, acta__estado='en_revision'
        ).count(),
        'compromisos_pendientes': Compromiso.objects.filter(
            responsable=user, estado__in=['pendiente', 'en_progreso']
        ).count(),
        'compromisos_vencidos': Compromiso.objects.filter(
            responsable=user, estado='vencido'
        ).count()
    }
    
    # Actas recientes del usuario
    actas_recientes = Acta.objects.filter(
        Q(creador=user) | Q(participantes__usuario=user)
    ).distinct().order_by('-fecha_creacion')[:5]
    
    # Compromisos próximos a vencer
    compromisos_proximos = Compromiso.objects.filter(
        responsable=user,
        estado__in=['pendiente', 'en_progreso'],
        fecha_limite__lte=timezone.now().date() + timedelta(days=7)
    ).order_by('fecha_limite')[:5]
    
    # Actas pendientes de firma
    firmas_pendientes = Firma.objects.filter(
        usuario=user,
        firmado=False,
        acta__estado='en_revision'
    ).select_related('acta')[:5]
    
    # Notificaciones recientes
    notificaciones = Notification.objects.filter(
        usuario=user, leida=False
    ).order_by('-fecha_creacion')[:5]
    
    context = {
        'stats': stats,
        'actas_recientes': actas_recientes,
        'compromisos_proximos': compromisos_proximos,
        'firmas_pendientes': firmas_pendientes,
        'notificaciones': notificaciones,
    }
    
    return render(request, 'dashboard/index.html', context)

@login_required
def actas_list(request):
    # Filtros
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    search = request.GET.get('search')
    
    actas = Acta.objects.filter(
        Q(creador=request.user) | Q(participantes__usuario=request.user)
    ).distinct()
    
    if estado:
        actas = actas.filter(estado=estado)
    if tipo:
        actas = actas.filter(tipo_reunion=tipo)
    if search:
        actas = actas.filter(
            Q(titulo__icontains=search) |
            Q(numero_acta__icontains=search) |
            Q(desarrollo__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(actas.order_by('-fecha_creacion'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estados': Acta.ESTADOS,
        'tipos_reunion': Acta.TIPOS_REUNION,
        'filtros': {
            'estado': estado,
            'tipo': tipo,
            'search': search,
        }
    }
    
    return render(request, 'actas/list.html', context)

@login_required
def crear_acta(request):
    if request.method == 'POST':
        # Procesar con IA si se proporciona resumen
        resumen = request.POST.get('resumen_reunion', '').strip()
        
        if resumen:
            try:
                contenido_ia = generar_acta_con_ia(resumen, request.user)
                
                acta = Acta.objects.create(
                    titulo=request.POST.get('titulo'),
                    tipo_reunion=request.POST.get('tipo_reunion'),
                    fecha_reunion=request.POST.get('fecha_reunion'),
                    lugar_reunion=request.POST.get('lugar_reunion'),
                    modalidad=request.POST.get('modalidad'),
                    orden_dia=contenido_ia.get('orden_dia', ''),
                    desarrollo=contenido_ia.get('desarrollo', ''),
                    resumen_ia=resumen,
                    creador=request.user
                )
                
                messages.success(request, 'Acta creada exitosamente con asistencia de IA.')
                return redirect('actas:detalle', acta_id=acta.id)
                
            except Exception as e:
                messages.error(request, f'Error al procesar con IA: {str(e)}')
        else:
            # Crear acta normal sin IA
            acta = Acta.objects.create(
                titulo=request.POST.get('titulo'),
                tipo_reunion=request.POST.get('tipo_reunion'),
                fecha_reunion=request.POST.get('fecha_reunion'),
                lugar_reunion=request.POST.get('lugar_reunion'),
                modalidad=request.POST.get('modalidad'),
                orden_dia=request.POST.get('orden_dia', ''),
                desarrollo=request.POST.get('desarrollo', ''),
                creador=request.user
            )
            
            messages.success(request, 'Acta creada exitosamente.')
            return redirect('actas:detalle', acta_id=acta.id)
    
    context = {
        'tipos_reunion': Acta.TIPOS_REUNION,
    }
    
    return render(request, 'actas/crear.html', context)