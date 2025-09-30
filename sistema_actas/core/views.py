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