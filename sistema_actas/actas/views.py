from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
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

from .models import Acta, Participante, Firma, Compromiso
from .utils import generar_acta_con_ia, enviar_notificacion_participantes
from notifications.models import Notification


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

    context = {
        "acta": acta,
        "participantes": participantes,
        "firmas": firmas,
        "compromisos": compromisos,
        "puede_firmar": puede_firmar,
        "puede_editar": acta.creador == request.user and acta.estado == "borrador",
        "puede_enviar_revision": acta.creador == request.user
        and acta.estado == "borrador",
        "puede_finalizar": acta.creador == request.user
        and acta.estado == "en_revision",
    }

    return render(request, "actas/detalle.html", context)


@login_required
def editar_acta(request, acta_id):
    acta = get_object_or_404(Acta, id=acta_id, creador=request.user)

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
            if key.startswitch("compromiso_desc_"):
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
        comentarios = request.POST.get("comentarios", "")
        firma.comentarios = comentarios
        firma.firmar(request)

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
                ("FONTSIZE", (0, 0), (-1, -1), 10)(
                    "GRID", (0, 0), (-1, -1), colors.black
                ),
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
