import os
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import timedelta 
from datetime import datetime
from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse


from .models import Acta, Participante, Firma, Compromiso, ComentarioActa
from core.utils import generar_acta_con_ia, enviar_notificacion_participantes
from notifications.models import Notification
from accounts.models import User
from .forms import ReporteCompromisoForm


# Create your views here.
@login_required
def detalle_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)

    # Verificar permisos
    if not (
        acta.creador == request.user
        or acta.participantes.filter(usuario=request.user).exists()
        or request.user.is_staff
    ):
        messages.error(request, "No tienes permisos para ver esta acta.")
        return redirect("actas:list")

    # Obtener información personal
    participantes = acta.participantes.select_related("usuario").prefetch_related('firmas').all()
    firmas = acta.firmas.select_related("usuario").all()
    compromisos = acta.compromisos.select_related("responsable").all()

    # Verificar si el usuario puede firmar
    puede_firmar = (
        acta.estado == "en_revision"
        and acta.firmas.filter(usuario=request.user, firmado=False).exists()
    )

    if request.user.rol == 'aprendiz':
        compromisos = compromisos.filter(responsable=request.user)

    context = {
        "acta": acta,
        "participantes": participantes,
        "firmas": firmas,
        "compromisos": compromisos,
        "puede_firmar": puede_firmar,
        "puede_editar": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "borrador"
        ),
        "puede_enviar_revision": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "borrador"
        ),
        "puede_finalizar": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "en_revision"
        ),
        'puede_comentar': request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director', 'aprendiz'],
        "puede_editar": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "borrador"
        ),
        "puede_enviar_revision": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "borrador"
        ),
        "puede_finalizar": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "en_revision"
        ),
        "puede_archivar": (
            request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']
            and acta.creador == request.user
            and acta.estado == "finalizada"
),
        'puede_comentar': request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director', 'aprendiz'],
    }
    return render(request, "actas/detalle.html", context)

@login_required
def editar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id, creador=request.user)
    if acta.estado != "borrador":
        messages.error(request, "Solo se pueden editar actas en estado de borrador.")
        return redirect("actas:detalle", acta_id=acta_id)

    if request.method == "POST":
        # Actualizar campos básicos
        acta.titulo = request.POST.get("titulo")
        acta.tipo_reunion = request.POST.get("tipo_reunion")
        acta.fecha_reunion = request.POST.get("fecha_reunion")
        acta.lugar_reunion = request.POST.get("lugar_reunion")
        acta.modalidad = request.POST.get("modalidad")
        acta.orden_dia = request.POST.get("orden_dia")
        acta.desarrollo = request.POST.get("desarrollo")
        acta.observaciones = request.POST.get("observaciones", "")
        acta.save()

        # Actualizar participantes
        participantes_emails = request.POST.getlist("participantes")

        # Eliminar participantes que ya no están en la lista
        for participante in acta.participantes.all():
            if participante.usuario.email not in participantes_emails:
                participante.delete()

        # Añadir o actualizar participantes
        for email in participantes_emails:
            try:
                usuario = User.objects.get(email=email)
                rol = request.POST.get(f"rol_{email}", "")
                participante, created = Participante.objects.get_or_create(
                    acta=acta,
                    usuario=usuario,
                    defaults={
                        'rol_en_reunion': rol,
                        'obligatorio_firma': True,
                    }
                )
                if not created and rol:
                    participante.rol_en_reunion = rol
                    participante.save()
            except User.DoesNotExist:
                messages.warning(request, f"Usuario con email {email} no encontrado.")

        # Actualizar compromisos
        compromisos_data = []
        for key in request.POST.keys():
            if key.startswith("compromiso_desc_"):
                index = key.split("_")[-1]
                descripcion = request.POST.get(f"compromiso_desc_{index}").strip()
                responsable_email = request.POST.get(f"compromiso_resp_{index}")
                fecha_limite = request.POST.get(f"compromiso_fecha_{index}")

                if descripcion and responsable_email and fecha_limite:
                    compromisos_data.append({
                        "descripcion": descripcion,
                        "responsable_email": responsable_email,
                        "fecha_limite": fecha_limite,
                    })

        # Eliminar compromisos existentes
        acta.compromisos.all().delete()

        # Añadir nuevos compromisos
        for comp_data in compromisos_data:
            try:
                responsable = User.objects.get(email=comp_data["responsable_email"])
                Compromiso.objects.create(
                    acta=acta,
                    descripcion=comp_data["descripcion"],
                    responsable=responsable,
                    fecha_limite=comp_data["fecha_limite"],
                )
            except User.DoesNotExist:
                messages.warning(request, f'Responsable {comp_data["responsable_email"]} no encontrado.')

        messages.success(request, "Acta actualizada exitosamente.")
        return redirect("actas:detalle", acta_id=acta.id)

    context = {
        "acta": acta,
        "tipos_reunion": Acta.TIPOS_REUNION,
        "participantes": acta.participantes.all(),
        "compromisos": acta.compromisos.all(),
        "usuarios": User.objects.all(),
    }
    return render(request, "actas/editar.html", context)



@login_required
@require_POST
def firmar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)

    if not acta.participantes.filter(usuario=request.user).exists():
        return JsonResponse(
            {"success": False, "message": "No eres participante de esta acta."},
            status=403
        )

    try:
        firma = Firma.objects.get(acta=acta, usuario=request.user)
        if firma.firmado:
            return JsonResponse(
                {"success": False, "message": "Ya has firmado esta acta."},
                status=400
            )
        if acta.estado != "en_revision":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Esta acta no está en estado de revisión.",
                },
                status=400
            )

        # Obtener comentarios del POST
        comentarios = request.POST.get("comentarios", "")

        # Procesar Firma
        firma.comentarios = comentarios
        firma.firmado = True
        firma.fecha_firma = timezone.now()
        if request.user.firma_digital:
            firma.firma_imagen = request.user.firma_digital
        firma.save()

        # Crear notificaciones para el creador del acta
        Notification.objects.create(
            usuario=acta.creador,
            tipo="firma_completada",
            titulo="Nueva firma en acta",
            mensaje=f"{request.user.get_full_name()} ha firmado el acta {acta.numero_acta}",
            enlace=f"/actas/{acta.id}/",
        )

        # Verificar si todas las firmas están completas
        if acta.get_firmas_completadas() == acta.get_total_firmas():
            # Notificar al creador que el acta puede ser finalizada
            Notification.objects.create(
                usuario=acta.creador,
                tipo="acta_lista_finalizar",
                titulo="Acta lista para finalizar",
                mensaje=f"El acta {acta.numero_acta} tiene todas las firmas necesarias",
                enlace=f"/actas/{acta.id}/",
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Acta firmada exitosamente.",
                "firmas_completadas": acta.get_firmas_completadas(),
                "total_firmas": acta.get_total_firmas(),
            }
        )
    except Firma.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "No tienes permisos para firmar esta acta."},
            status=403
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error al firmar: {str(e)}"}, status=500)


@login_required
@require_POST
def enviar_revision(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id, creador=request.user)

    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        messages.error(request, "No tienes permisos para enviar actas a revisión.")
        return redirect("actas:detalle", acta_id=acta_id)

    if acta.estado != "borrador":
        messages.error(request, "Solo se pueden enviar a revisión actas en estado de borrador.")
        return redirect("actas:detalle", acta_id=acta_id)

    # Verificar que hay participantes
    if not acta.participantes.exists():
        messages.error(request, "No hay participantes asignados a esta acta.")
        return redirect("actas:detalle", acta_id=acta_id)

    # Cambiar el estado del acta
    acta.estado = "en_revision"
    acta.fecha_limite_firmas = timezone.now() + timedelta(days=acta.aplicar_silencio_dias)
    acta.save()

    participantes_notificados = 0
    for participante in acta.participantes.all():
    # Crear o recuperar firma
        firma, created = Firma.objects.get_or_create(
        acta=acta,
        usuario=participante.usuario,
        defaults={"firmado": False}
    )
    
    # Crear notificación para que le aparezca al participante
    Notification.objects.create(
        usuario=participante.usuario,
        tipo="firma_pendiente",
        titulo="📝 Nueva acta pendiente de firma",
        mensaje=f"Tienes pendiente firmar el acta '{acta.numero_acta} - {acta.titulo}'. Fecha límite: {acta.fecha_limite_firmas.strftime('%d/%m/%Y')}",
        enlace=f"/actas/{acta.id}/",
    )
    participantes_notificados += 1
    print(f"✅ Notificación enviada a: {participante.usuario.email}")  # Para debu

    messages.success(request, f"Acta enviada a revisión. {participantes_notificados} participantes han sido notificados.")
    return redirect("actas:detalle", acta_id=acta_id)



@login_required
@require_POST
def procesar_con_ia(request):
    resumen = request.POST.get("resumen", "").strip()

    if not resumen:
        return JsonResponse(
            {"success": False, "message": "Debe proporcionar un resumen de la reunión."}
        )

    try:
        resultado = generar_acta_con_ia(resumen, request.user)
        return JsonResponse({"success": True, "data": resultado})
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error al procesar con IA: {str(e)}"}
        )

@login_required
def generar_pdf(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)

    # Verificar permisos
    if not (
        acta.creador == request.user
        or acta.participantes.filter(usuario=request.user).exists()
        or request.user.is_staff
    ):
        messages.error(request, "No tienes permiso para descargar esta acta.")
        return redirect("actas:list")

    # Crear PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="acta_{acta.numero_acta}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Estilo personalizado para el encabezado
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=20,
        alignment=1,  # Centrado
    )

    body_style = styles["Normal"]
    body_style.wordWrap = "CJK"  # Permite el ajuste de línea en palabras largas

    # Encabezado
    story.append(Paragraph("SERVICIO NACIONAL DE APRENDIZAJE - SENA", title_style))
    story.append(Paragraph("CENTRO MINERO", title_style))
    story.append(Paragraph(f"ACTA DE REUNIÓN - {acta.numero_acta}", title_style))
    story.append(Spacer(1, 20))

    # Información general
    info_data = [
        ["Título:", Paragraph(acta.titulo, body_style)],
        ["Tipo de Reunión:", acta.get_tipo_reunion_display()],
        ["Fecha y Hora:", acta.fecha_reunion.strftime("%d/%m/%Y %H:%M")],
        ["Lugar:", Paragraph(acta.lugar_reunion, body_style)],
        ["Modalidad:", acta.get_modalidad_display()],
        ["Estado:", acta.get_estado_display()],
    ]

    info_table = Table(info_data, colWidths=[1.5 * inch, 4.5 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                # --- CORRECCIÓN AQUÍ ---
                # Se agregó el grosor de línea (1) que faltaba en el comando GRID.
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 20))

    # Participantes
    story.append(Paragraph("PARTICIPANTES", styles["Heading2"]))
    participantes_data = [["Nombre", "Email", "Rol", "Firmado"]]

    for participante in acta.participantes.select_related("usuario").all():
        firma = acta.firmas.filter(usuario=participante.usuario).first()
        firmado = "Sí" if firma and firma.firmado else "No"
        participantes_data.append(
            [
                participante.usuario.get_full_name(),
                participante.usuario.email,
                participante.rol_en_reunion or "-",
                firmado,  # Se corrigió para que muestre el valor de la variable
            ]
        )

    participantes_table = Table(
        participantes_data, colWidths=[2 * inch, 2 * inch, 1.5 * inch, 0.7 * inch]
    )
    participantes_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(participantes_table)
    story.append(Spacer(1, 20))

    # Orden del día
    if acta.orden_dia:
        story.append(Paragraph("ORDEN DEL DÍA", styles["Heading2"]))
        story.append(Paragraph(acta.orden_dia.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 15))

    # Desarrollo
    if acta.desarrollo:
        story.append(Paragraph("DESARROLLO DE LA REUNIÓN", styles["Heading2"]))
        story.append(Paragraph(acta.desarrollo.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 15))

    # Compromisos
    if acta.compromisos.exists():
        story.append(Paragraph("COMPROMISOS", styles["Heading2"]))
        compromisos_data = [["Descripción", "Responsable", "Fecha Límite", "Estado"]]

        for compromiso in acta.compromisos.select_related("responsable").all():
            # Mejora: Usar Paragraph para que el texto largo se ajuste automáticamente
            descripcion_paragraph = Paragraph(compromiso.descripcion, body_style)

            compromisos_data.append(
                [
                    descripcion_paragraph,
                    compromiso.responsable.get_full_name(),
                    compromiso.fecha_limite.strftime("%d/%m/%Y"),
                    compromiso.get_estado_display(),
                ]
            )

        compromisos_table = Table(
            compromisos_data, colWidths=[2.5 * inch, 1.5 * inch, 1 * inch, 1 * inch]
        )
        compromisos_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(compromisos_table)
        story.append(Spacer(1, 20))

    # --- CORRECCIÓN DE INDENTACIÓN ---
    # Los siguientes bloques (Observaciones, Firmas, Pie de página y la construcción del PDF)
    # se han movido fuera del bloque `if acta.compromisos.exists():`.
    # Esto asegura que el PDF se genere siempre, incluso si no hay compromisos.

    # Observaciones
    if acta.observaciones:
        story.append(Paragraph("OBSERVACIONES", styles["Heading2"]))
        story.append(Paragraph(acta.observaciones.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 15))

    # Firmas
    story.append(Paragraph("FIRMAS", styles["Heading2"]))
    if acta.silencio_administrativo:
        story.append(
            Paragraph(
                "* Algunas firmas fueron aplicadas por silencio administrativo.",
                styles["Italic"],
            )
        )
    story.append(Spacer(1, 40))  # Más espacio para firmas manuales si es necesario

    # Pie de pagina
    footer_style = styles["Normal"]
    footer_style.alignment = 1  # Centrado
    story.append(
        Paragraph(
            f"Documento generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}",
            footer_style,
        )
    )
    story.append(Paragraph("Centro Minero - SENA", footer_style))

    try:
        doc.build(story)
    except Exception as e:
        # Es una buena práctica registrar el error si algo más falla
        print(f"Error al construir el PDF: {e}")
        messages.error(request, "Ocurrió un error inesperado al generar el PDF.")
        return redirect("actas:list")

    return response


@login_required
def actas_list(request):
    # Filtros
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    search = request.GET.get('search')

    if request.user.rol == 'aprendiz':
        actas = Acta.objects.filter(participantes__usuario=request.user).distinct()

    elif request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']:
        actas = Acta.objects.filter(
            Q(creador=request.user) | Q(participantes__usuario=request.user)
        ).distinct()

    elif request.user.rol == 'admin' or request.user.is_superuser:
        actas = Acta.objects.all()
    else:
        actas = Acta.objects.none()

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
        },
        'es_aprendiz': request.user.rol == "aprendiz",
    }

    return render(request, 'actas/actas_list.html', context)


@login_required
def crear_acta(request):
    
    if request.user.rol == 'aprendiz':
        messages.error(request, "No tienes permisos para crear actas.")
        return redirect("actas:actas_list")
    
    
    if request.user.rol == 'aprendiz':
        messages.error(request, "No tienes permisos para crear actas.")
        return redirect("actas:actas_list")
    
    if request.method == 'POST':
        try:
            # Procesar con IA si se proporciona resumen
            resumen = request.POST.get('resumen_reunion', '').strip()
            
            if resumen:
                try:
                    contenido_ia = generar_acta_con_ia(resumen, request.user)
                    orden_dia = contenido_ia.get('orden_dia', '')
                    desarrollo = contenido_ia.get('desarrollo', '')
                except Exception as e:
                    messages.warning(request, f'No se pudo procesar con IA: {str(e)}')
                    orden_dia = request.POST.get('orden_dia', '')
                    desarrollo = request.POST.get('desarrollo', '')
            else:
                # Sin IA, tomar datos del formulario
                orden_dia = request.POST.get('orden_dia', '')
                desarrollo = request.POST.get('desarrollo', '')
            
            # Crear el acta
            acta = Acta.objects.create(
                titulo=request.POST.get('titulo'),
                tipo_reunion=request.POST.get('tipo_reunion'),
                fecha_reunion=request.POST.get('fecha_reunion'),
                lugar_reunion=request.POST.get('lugar_reunion'),
                modalidad=request.POST.get('modalidad'),
                orden_dia=orden_dia,
                desarrollo=desarrollo,
                observaciones=request.POST.get('observaciones', ''),
                resumen_ia=resumen if resumen else '',
                creador=request.user
            )
            
            # ========================================
            # PROCESAR PARTICIPANTES
            # ========================================
            participantes_emails = request.POST.getlist('participantes')
            participantes_agregados = set()  # Para evitar duplicados
            
            for email in participantes_emails:
                email = email.strip()
                if email and email not in participantes_agregados:  # ← Validar duplicados
                    try:
                        usuario = User.objects.get(email=email)
                        
                        # Verificar si ya existe
                        if not Participante.objects.filter(acta=acta, usuario=usuario).exists():
                            # Buscar el rol de este participante
                            rol = ''
                            for key in request.POST.keys():
                                if key.startswith('rol_participante_') or key.startswith(f'rol_{email}'):
                                    rol = request.POST.get(key, '')
                                    break
                            
                            # Crear participante
                            Participante.objects.create(
                                acta=acta,
                                usuario=usuario,
                                rol_en_reunion=rol if rol else 'Participante',
                                obligatorio_firma=True
                            )
                            participantes_agregados.add(email)
                            print(f"✅ Participante creado: {usuario.email}")
                        
                    except User.DoesNotExist:
                        messages.warning(request, f'Usuario con email {email} no encontrado.')
            
            # ========================================
            # PROCESAR COMPROMISOS
            # ========================================
            from datetime import datetime
            
            compromisos_data = []
            
            # Buscar todos los compromisos en el POST
            for key in request.POST.keys():
                if key.startswith('compromiso_desc_'):
                    index = key.split('_')[-1]
                    descripcion = request.POST.get(f'compromiso_desc_{index}', '').strip()
                    responsable_email = request.POST.get(f'compromiso_resp_{index}', '').strip()
                    fecha_limite_str = request.POST.get(f'compromiso_fecha_{index}', '').strip()
                    
                    if descripcion and responsable_email and fecha_limite_str:
                        # Convertir string a fecha
                        try:
                            fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
                            compromisos_data.append({
                                'descripcion': descripcion,
                                'responsable_email': responsable_email,
                                'fecha_limite': fecha_limite
                            })
                        except ValueError:
                            messages.warning(request, f'Fecha inválida para compromiso: {fecha_limite_str}')
            
            # Crear los compromisos
            for comp_data in compromisos_data:
                try:
                    responsable = User.objects.get(email=comp_data['responsable_email'])
                    Compromiso.objects.create(
                        acta=acta,
                        descripcion=comp_data['descripcion'],
                        responsable=responsable,
                        fecha_limite=comp_data['fecha_limite']  # Ya es un objeto date
                    )
                    print(f"✅ Compromiso creado para: {responsable.email}")
                    
                except User.DoesNotExist:
                    messages.warning(request, f'Responsable {comp_data["responsable_email"]} no encontrado.')
            
            # Mensaje de éxito
            messages.success(request, f'Acta {acta.numero_acta} creada exitosamente con {participantes_agregados.__len__()} participantes.')
            return redirect('actas:detalle', acta_id=acta.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el acta: {str(e)}')
            import traceback
            traceback.print_exc()
    
    # GET request - mostrar formulario
    context = {
        'tipos_reunion': Acta.TIPOS_REUNION,
    }
    
    return render(request, 'actas/crear.html', context)

@login_required
def eliminar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    
    # Solo el creador o un admin pueden eliminar
    if request.user != acta.creador and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para eliminar esta acta.")
        return redirect("actas:detalle", acta_id=acta.id)

    acta.delete()
    messages.success(request, "El acta ha sido eliminada correctamente.")
    return redirect("actas:actas_list")

# ✅ Finalizar Acta
@login_required
def finalizar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    
    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        messages.error(request, "No tienes permisos para finalizar actas.")
        return redirect("actas:detalle", acta_id=acta.id)
    
    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        messages.error(request, "No tienes permisos para finalizar actas.")
        return redirect("actas:detalle", acta_id=acta.id)

    if acta.estado not in ["borrador", "en_revision"]:
        messages.warning(request, "El acta no se puede finalizar en este estado.")
        return redirect("actas:detalle", acta_id=acta.id)

    # Antes de finalizar, verificamos firmas
    if acta.get_firmas_completadas() < acta.get_total_firmas():
        messages.warning(request, "No se puede finalizar el acta porque aún faltan firmas.")
        return redirect("actas:detalle", acta_id=acta.id)

    acta.estado = "finalizada"
    acta.fecha_modificacion = timezone.now()
    acta.save()

    messages.success(request, "El acta ha sido finalizada con éxito.")
    return redirect("actas:detalle", acta_id=acta.id)

# 📂 Archivar Acta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

@login_required
@require_POST
def archivar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    
    # Verificar permisos
    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        return JsonResponse({
            'success': False,
            'message': 'No tienes permisos para archivar actas.'
        }, status=403)
    
    # Verificar que sea el creador
    if acta.creador != request.user and not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'message': 'Solo el creador puede archivar esta acta.'
        }, status=403)

    # Verificar estado
    if acta.estado != "finalizada":
        return JsonResponse({
            'success': False,
            'message': 'Solo las actas finalizadas se pueden archivar.'
        }, status=400)

    # Archivar
    acta.estado = "archivada"
    acta.fecha_modificacion = timezone.now()
    acta.save()

    return JsonResponse({
        'success': True,
        'message': 'El acta ha sido archivada exitosamente.'
    })

# ✍️ Firmas pendientes (solo las del usuario autenticado)
@login_required
def firmas_pendientes(request):
    firmas = Firma.objects.filter(usuario=request.user, firmado=False, acta__estado="en_revision")

    return render(request, "actas/firmas_pendientes.html", {
        "firmas": firmas
    })
    
@login_required
def lista_compromisos(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    compromisos = acta.compromisos.all()
    return render(request, "actas/compromisos/lista.html", {"acta": acta, "compromisos": compromisos})

@login_required
def crear_compromiso(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    if request.method == "POST":
        descripcion = request.POST.get("descripcion")
        responsable_id = request.POST.get("responsable")
        fecha_limite = request.POST.get("fecha_limite")

        Compromiso.objects.create(
            acta=acta,
            descripcion=descripcion,
            responsable_id=responsable_id,
            fecha_limite=fecha_limite
        )
        return redirect("actas:lista_compromisos", acta_id=acta.id)
    return render(request, "actas/compromisos/form.html", {"acta": acta})

@login_required
def editar_compromiso(request, compromiso_id):
    compromiso = get_object_or_404(Compromiso, id=compromiso_id)
    
    # *** 1. Validar que el usuario es el responsable ***
    if request.user != compromiso.responsable:
        # Si no es el responsable, lo rediriges o le das un error 403 (Prohibido)
        # Por ahora, simplemente lo redirigiremos a su lista de compromisos.
        return redirect("actas:mis_compromisos") 
    
    # *** 2. Usar el formulario de reporte ***
    if request.method == "POST":
        form = ReporteCompromisoForm(request.POST, instance=compromiso)
        if form.is_valid():
            compromiso_guardado = form.save(commit=False)
            
            # Si el responsable marca 100%, Git actualiza el estado a 'completado' 
            # (tu método save() ya lo hace)
            if compromiso_guardado.porcentaje_avance == 100:
                compromiso_guardado.fecha_completado = timezone.now()
            
            compromiso_guardado.save()
            # Puedes usar messages.success para notificar al usuario.
            return redirect("actas:mis_compromisos")
    else:
        form = ReporteCompromisoForm(instance=compromiso)
        
    context = {
        "compromiso": compromiso,
        "form": form
    }
    # NOTA: Debes crear la template 'actas/compromisos/reporte_form.html'
    return render(request, "actas/reporte_form.html", context)

@login_required
def eliminar_compromiso(request, compromiso_id):
    compromiso = get_object_or_404(Compromiso, id=compromiso_id)
    acta_id = compromiso.acta.id
    compromiso.delete()
    return redirect("actas:lista_compromisos", acta_id=acta_id)

@login_required
def mis_compromisos(request):
    compromisos = Compromiso.objects.filter(responsable=request.user).order_by('-fecha_limite')
    return render(request, "actas/mis_compromisos.html", {"compromisos": compromisos})


@login_required
@require_POST
def agregar_comentario(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)

    if request.user.rol != "aprendiz":
        return JsonResponse({"success": False, "message": "Solo los aprendices pueden comentar."})

    texto = request.POST.get("comentario", "").strip()
    if not texto:
        return JsonResponse({"success": False, "message": "El comentario no puede estar vacío."})

    ComentarioActa.objects.create(acta=acta, autor=request.user, texto=texto)
    return JsonResponse({"success": True, "message": "Comentario agregado correctamente."})

@login_required
def aprendiz_pendientes(request):
    if request.user.rol != 'aprendiz':
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('actas:actas_list')

    # Filtramos las actas que están en revisión y que el aprendiz debe firmar
    firmas = Firma.objects.filter(
        usuario=request.user,
        firmado=False,
        acta__estado='en_revision'
    ).select_related('acta')

    context = {
        'firmas': firmas,
        'titulo': "Actas pendientes por firmar"
    }
    return render(request, 'actas/aprendiz/pendientes.html', context)

@login_required
def aprendiz_compromisos(request):
    if request.user.rol != 'aprendiz':
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('actas:actas_list')

    compromisos = Compromiso.objects.filter(
        responsable=request.user
    ).select_related('acta').order_by('-fecha_limite')

    context = {
        'compromisos': compromisos,
        'titulo': "Mis compromisos asignados"
    }
    return render(request, 'actas/aprendiz/compromisos.html', context)

def crear_copia_seguridad(request):
    try:
        # Ruta base del proyecto
        base_dir = settings.BASE_DIR
        # Carpeta donde se guardará el backup
        backups_dir = os.path.join(base_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)

        # Nombre del archivo de backup con fecha
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{fecha}.zip"
        backup_path = os.path.join(backups_dir, backup_filename)

        # Archivos o carpetas a incluir en el backup
        incluir = ["db.sqlite3", "actas", "accounts", "core"]

        shutil.make_archive(backup_path.replace(".zip", ""), "zip", base_dir)

        return JsonResponse(
            {"mensaje": f"Copia de seguridad creada: {backup_filename}"}
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def generar_backup(request):
    try:
        # Ejecuta el comando personalizado
        call_command("backup_db")

        # Busca el archivo más reciente
        backups_dir = os.path.join(settings.BASE_DIR, "backups")
        files = sorted(
            [
                os.path.join(backups_dir, f)
                for f in os.listdir(backups_dir)
                if f.endswith(".zip")
            ],
            key=os.path.getmtime,
            reverse=True,
        )

        if files:
            latest_backup = files[0]
            response = FileResponse(open(latest_backup, "rb"))
            response["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(latest_backup)}"'
            )
            return response
        else:
            return HttpResponse("No se encontró ningún backup.", status=404)

    except Exception as e:
        return HttpResponse(f"Error al generar el backup: {str(e)}", status=500)