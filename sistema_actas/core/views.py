import os
import shutil
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
from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse, HttpResponse
from datetime import timedelta 
from datetime import datetime
from core import views
import zipfile

BACKUP_DIR = os.path.join(settings.BASE_DIR, "backups")

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
def crear_copia_seguridad(request):
    """
    Crea una copia de seguridad ZIP válida solo con los archivos importantes.
    """
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{fecha}.zip"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Archivos y carpetas a incluir
        incluir = [
            "db.sqlite3",
            "actas",
            "accounts",
            "core",
        ]

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in incluir:
                ruta_item = os.path.join(settings.BASE_DIR, item)
                if os.path.exists(ruta_item):
                    if os.path.isfile(ruta_item):
                        zipf.write(ruta_item, arcname=item)
                    else:
                        for root, dirs, files in os.walk(ruta_item):
                            for archivo in files:
                                if "_pycache_" not in root:
                                    ruta_completa = os.path.join(root, archivo)
                                    arcname = os.path.relpath(ruta_completa, settings.BASE_DIR)
                                    zipf.write(ruta_completa, arcname)

        messages.success(request, f"✅ Copia de seguridad creada correctamente: {backup_filename}")
        return redirect("core:vista_backup")

    except Exception as e:
        messages.error(request, f"❌ Error al crear la copia de seguridad: {str(e)}")
        return redirect("core:vista_backup")


@login_required
def vista_backup(request):
    """
    Muestra una lista de las copias de seguridad disponibles.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)

    archivos = []
    for archivo in os.listdir(BACKUP_DIR):
        ruta = os.path.join(BACKUP_DIR, archivo)
        if os.path.isfile(ruta) and archivo.endswith(".zip"):
            tamaño_mb = os.path.getsize(ruta) / (1024 * 1024)
            fecha_mod = datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M:%S")
            archivos.append({
                "nombre": archivo,
                "tamaño": f"{tamaño_mb:.2f} MB",
                "fecha": fecha_mod,
            })

    archivos.sort(key=lambda x: x["fecha"], reverse=True)
    return render(request, "actas/backup.html", {"archivos": archivos})


@login_required
def restaurar_backup(request, nombre_archivo):
    """
    Restaura una copia de seguridad existente desde la lista.
    """
    ruta_backup = os.path.join(BACKUP_DIR, nombre_archivo)

    if not os.path.exists(ruta_backup):
        messages.error(request, "❌ El archivo seleccionado no existe.")
        return redirect("core:vista_backup")

    try:
        with zipfile.ZipFile(ruta_backup, "r") as zip_ref:
            zip_ref.extractall(settings.BASE_DIR)

        messages.success(request, f"✅ El backup '{nombre_archivo}' fue restaurado correctamente.")
    except zipfile.BadZipFile:
        messages.error(request, f"❌ Error: el archivo '{nombre_archivo}' no es un archivo ZIP válido.")
    except Exception as e:
        messages.error(request, f"❌ Error al restaurar '{nombre_archivo}': {str(e)}")

    return redirect("core:vista_backup")