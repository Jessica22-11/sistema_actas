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



from .models import Acta, Participante, Firma, Compromiso, ComentarioActa
from core.utils import generar_acta_con_ia, enviar_notificacion_participantes
from notifications.models import Notification
from accounts.models import User



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
    participantes = acta.participantes.select_related("usuario").all()
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
        'puede_comentar': request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director', 'aprendiz'],
    }

    return render(request, "actas/detalle.html", context)


@login_required
def editar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id, creador=request.user)
    
    if request.user.rol == 'aprendiz':
        messages.error(request, "No tienes permisos para editar esta acta.")
        return redirect("actas:list")
    
    if request.user.rol == 'aprendiz':
        messages.error(request, "No tienes permisos para editar esta acta.")
        return redirect("actas:list")

    if acta.estado != "borrador":
        messages.error(request, "Solo de pueden editar actas en estado de borrador.")
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
        acta.participantes.all().delete()  # Limpiar participantes existentes

        for email in participantes_emails:
            try:
                from accounts.models import User

                usuario = User.objects.get(email=email)
                Participante.objects.create(
                    acta=acta,
                    usuario=usuario,
                    rol_en_reunion=request.POST.get(f"rol_{email}", ""),
                    obligatorio_firma=True,
                )
            except User.DoesNotExist:
                messages.warning(request, f"Usuario con email {email} no encontrado.")

        # Actualizar compromisos
        compromisos_data = []
        for key in request.POST.keys():
            if key.startswith("compromiso_desc_"):
                index = key.split("_")[-1]
                if request.POST.get(f"compromiso_desc_{index}").strip():
                    compromisos_data.append(
                        {
                            "descripcion": request.POST.get(f"compromiso_desc_{index}"),
                            "responsable_email": request.POST.get(
                                f"compromiso_resp_{index}"
                            ),
                            "fecha_limite": request.POST.get(
                                f"compromiso_fecha_{index}"
                            ),
                        }
                    )

        # Limpiar compromisos existentes y crear nuevos
        acta.compromisos.all().delete()
        for comp_data in compromisos_data:
            try:
                from accounts.models import User

                responsable = User.objects.get(email=comp_data["responsable_email"])
                Compromiso.objects.create(
                    acta=acta,
                    descripcion=comp_data["descripcion"],
                    responsable=responsable,
                    fecha_limite=comp_data["fecha_limite"],
                )
            except User.DoesNotExist:
                messages.warning(
                    request,
                    f'Responsable {comp_data["responsable_email"]} no encontrado.',
                )

        messages.success(request, "Acta actualizada exitosamente.")
        return redirect("actas:detalle", acta_id=acta.id)

    context = {
        "acta": acta,
        "tipos_reunion": Acta.TIPOS_REUNION,
        "participantes": acta.participantes.all(),
        "compromisos": acta.compromisos.all(),
    }
    return render(request, "actas/editar.html", context)


@login_required
@require_POST
def firmar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    
    if not acta.participantes.filter(usuario=request.user).exists():
        return JsonResponse(
            {"success": False, "message": "No eres participante de esta acta."}
        )
    
    if not acta.participantes.filter(usuario=request.user).exists():
        return JsonResponse(
            {"success": False, "message": "No eres participante de esta acta."}
        )

    try:
        firma = Firma.objects.get(acta=acta, usuario=request.user)

        if firma.firmado:
            return JsonResponse(
                {"success": False, "message": "Ya has firmado esta acta."}
            )

        if acta.estado != "en_revision":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Esta acta no está en estado de revisión.",
                }
            )

        # Procesar Firma
        firma.comentarios = comentarios
        firma.firmado = True
        firma.fecha_firma = timezone.now()

        # Si el usuario tiene una firma digital guardada, úsala
        if request.user.firma_digital:
            firma.firma_imagen = request.user.firma_digital

        # Guarda dirección IP si quieres mantenerla
        firma.ip_address = firma.get_client_ip(request)
        firma.save()
        # Crear notificaciones para el creador del acta
        Notification.objects.create(
            usuario=acta.creador,
            tipo="firma_completada",
            titulo="Nueva firma en acta",
            mensaje=f"{request.user.get_full_name()} ha firmado el acta {acta.numero_acta}",
            enlace=f"/actas/{acta.id}/",
        )

        # Verificar si todas las firmas estan completas
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
            {"success": False, "message": "No tienes permisos para firmar esta acta."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error al firmar: {str(e)}"})


@login_required
@require_POST
def enviar_revision(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id, creador=request.user)

    if acta.estado != "borrador":
        messages.error(
            request, "Solo de pueden enviar revisiones en estado de borrador."
        )
        return redirect("actas:detalle", acta_id=acta_id)

    if not acta.participantes.exists():
        messages.error(
            request, "Debe agregar al menos un participante antes de enviar a revisión."
        )
        return redirect("actas:editar", acta_id=acta_id)

    # Cambiar estado y crear firmas
    acta.estado = "en_revision"
    acta.save()

    # Crear registros de firma para cada participante
    for participante in acta.participantes.all():
        Firma.objects.get_or_create(
            acta=acta, usuario=participante.usuario, defaults={"firmado": False}
        )

    # Enviar notificaciones a participantes
    enviar_notificacion_participantes(acta)

    messages.success(
        request, "Acta enviada a revisión. Los participantes han sido notificados."
    )
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
        messages.error(request, "No tienes permiso para desargar esta acta.")
        return redirect("actas:list")

    # Crear PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="acta_{acta.numero_acta}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=letter)
    style = getSampleStyleSheet()
    story = []

    # Estilo personalizado para el encabezado
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=style["Title"],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Centrado
    )

    # Encabezado
    story.append(Paragraph("SERVICIO NACIONAL DE APRENDIZAJE- SENA", title_style))
    story.append(Paragraph("CENTRO MINERO", title_style))
    story.append(Paragraph(f"ACTA DE REUNIÓN - {acta.numero_acta}", title_style))
    story.append(Paragraph(Spacer(1, 20)))

    # Información general
    info_data = [
        ["Título:", acta.titulo],
        ["Tipo de Reunión:", acta.get_tipo_reunion_display()],
        ["Fecha y Hora:", acta.fecha_reunion.strftime("%d/%m/%Y %H:%M")],
        ["Lugar:", acta.lugar_reunion],
        ["Modalidad:", acta.get_modalidad_display()],
        ["Estado:", acta.get_estado_display()],
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 20))

    # Participantes
    story.append(Paragraph("PARTICIPANTES", style["Heading2"]))
    participantes_data = [["Nombre", "Email", "Rol", "Firmado"]]

    for participante in acta.participantes.select_related("usuario").all():
        firma = acta.firmas.filter(usuario=participante.usuario).first()
        firmado = "Sí" if firma and firma.firmado else "No"
        participantes_data.append(
            [
                participante.usuario.get_full_name(),
                participante.usuario.email,
                participante.rol_en_reunion or "-",
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
    if acta.roden_dia:
        story.append(Paragraph("ORDEN DEL DÍA", style["Heading2"]))
        story.append(Paragraph(acta.orden_dia.replace("\n", "<br/>"), style["Normal"]))
        story.append(Spacer(1, 15))

    # Desarrollo
    if acta.desarrollo:
        story.append(Paragraph("DESARROLLO DE LA REUNIÓN", style["Heading2"]))
        story.append(Paragraph(acta.desarrollo.replace("\n", "<br/>"), style["Normal"]))
        story.append(Spacer(1, 15))

    # Compromisos
    if acta.compromisos.exists():
        story.append(Paragraph("COMPROMISOS", style["Heading2"]))
        compromisos_data = [["Descripción", "Responsable", "Fecha Límite", "Estado"]]

        for compromiso in acta.compromisos.select_related("responsable").all():
            compromisos_data.append(
                [
                    (
                        compromiso.descripcion[:50] + "..."
                        if len(compromiso.descripcion) > 50
                        else compromiso.descripcion
                    ),
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
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        story.append(compromisos_table)
        story.append(Spacer(1, 20))

        # Observaciones
        if acta.observaciones:
            story.append(Paragraph("OBSERVACIONES", style["Heading2"]))
            story.append(
                Paragraph(acta.observaciones.replace("\n", "<br/>"), style["Normal"])
            )
            story.append(Spacer(1, 15))

        # Firmas
        story.append(Paragraph("FIRMAS", style["Heading2"]))
        if acta.silencio_administrativo:
            story.append(
                Paragraph(
                    "* Algunas firmas fueron aplicadas por silencio administrativo",
                    style["Italic"],
                )
            )
        story.append(Spacer(1, 20))

        # Pie de pagina
        story.append(
            Paragraph(
                f"Documento generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                style["Normal"],
            )
        )
        story.append(Paragraph("Centro Minero - SENA", style["Normal"]))

        doc.build(story)
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
        ). distinct()
    
    elif request.user.rol == 'admin' or request.user.is_superuser:
        actas = Acta.objects.all()
    else:
        actas = Acta.objects.none()
        
    if request.user.rol == 'aprendiz':
        actas = Acta.objects.filter(participantes__usuario=request.user).distinct()
        
    elif request.user.rol in ['instructor', 'funcionario', 'coordinador', 'director']:
        actas = Acta.objects.filter(
            Q(creador=request.user) | Q(participantes__usuario=request.user)
        ). distinct()
    
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
        return redirect("actas:list")
    
    
    if request.user.rol == 'aprendiz':
        messages.error(request, "No tienes permisos para crear actas.")
        return redirect("actas:list")
    
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
@permission_required("actas.can_finalize_acta", raise_exception=True)
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
@login_required
@permission_required("actas.can_archive_acta", raise_exception=True)
def archivar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id)
    
    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        messages.error(request, "No tienes permisos para archivar actas.")
        return redirect("actas:detalle", acta_id=acta.id)
    
    if request.user.rol not in ['instructor', 'funcionario', 'coordinador', 'director', 'admin']:
        messages.error(request, "No tienes permisos para archivar actas.")
        return redirect("actas:detalle", acta_id=acta.id)

    if acta.estado != "finalizada":
        messages.warning(request, "Solo las actas finalizadas se pueden archivar.")
        return redirect("actas:detalle", acta_id=acta.id)

    acta.estado = "archivada"
    acta.fecha_modificacion = timezone.now()
    acta.save()

    messages.info(request, "El acta ha sido archivada.")
    return redirect("actas:detalle", acta_id=acta.id)

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
    if request.method == "POST":
        compromiso.descripcion = request.POST.get("descripcion")
        compromiso.fecha_limite = request.POST.get("fecha_limite")
        compromiso.estado = request.POST.get("estado")
        compromiso.save()
        return redirect("actas:lista_compromisos", acta_id=compromiso.acta.id)
    return render(request, "actas/compromisos/form.html", {"compromiso": compromiso})

@login_required
def eliminar_compromiso(request, compromiso_id):
    compromiso = get_object_or_404(Compromiso, id=compromiso_id)
    acta_id = compromiso.acta.id
    compromiso.delete()
    return redirect("actas:lista_compromisos", acta_id=acta_id)

def mis_compromisos(request):
    compromisos = Compromiso.objects.all()  # luego lo puedes filtrar por usuario
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