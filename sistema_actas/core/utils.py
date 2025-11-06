from django.conf import settings
from django.core.mail import send_mail
from actas.services.ia_service import GroqService
import json
import logging

logger = logging.getLogger(__name__)


def extract_json_from_string(text):
    """
    Limpia el texto de la IA buscando el objeto JSON entre {}.
    """
    try:
        # Limpiar markdown code blocks si existen
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Busca el inicio de la primera llave de apertura y la última de cierre
        start_index = text.find('{')
        end_index = text.rfind('}')
        
        if start_index == -1 or end_index == -1:
            raise ValueError("No se encontró el inicio o fin de un objeto JSON.")
        
        json_string = text[start_index : end_index + 1]
        return json.loads(json_string)
        
    except Exception as e:
        raise ValueError(f"Error al limpiar y parsear JSON: {e}")


def generar_acta_con_ia(resumen, usuario):
    """
    Genera contenido de acta usando Groq (reemplaza OpenAI).
    """
    try:
        # Crear instancia del servicio Groq
        servicio_groq = GroqService()
        
        # Verificar conexión
        if not servicio_groq.verificar_conexion():
            raise Exception("No se pudo conectar con el servicio de IA (Groq)")
        
        # Prompt optimizado
        prompt_content = f"""Responde ÚNICAMENTE con un objeto JSON válido. No agregues texto adicional.

El JSON debe tener exactamente estas dos claves:
- "orden_dia": string con puntos numerados (ejemplo: "1. Tema uno\\n2. Tema dos")
- "desarrollo": string con el resumen detallado

Ejemplo:
{{"orden_dia": "1. Verificación de asistencia\\n2. Revisión de temas\\n3. Asignación de tareas", "desarrollo": "Se llevó a cabo la reunión donde se discutieron los siguientes puntos..."}}

Resumen de la reunión:
{resumen}

Responde SOLO con el JSON:"""

        # ⚡ GENERAR CON MODELO CORRECTO
        contenido_json_str = servicio_groq.generar_texto(
            prompt=prompt_content,
            modelo="llama-3.1-8b-instant"  # ✅ Modelo que SÍ funciona
        )
        
        # Limpiar y parsear la respuesta JSON
        data_ia = extract_json_from_string(contenido_json_str)
        
        # Validar claves
        if "orden_dia" not in data_ia or "desarrollo" not in data_ia:
            raise ValueError(f"JSON no contiene las claves esperadas: {data_ia.keys()}")
        
        # Devolver resultado
        return {
            "orden_dia": data_ia.get("orden_dia", "No generado"),
            "desarrollo": data_ia.get("desarrollo", "No generado"),
        }

    except ValueError as e:
        raise ValueError(f"Error de formato JSON: {e}")
    
    except Exception as e:
        raise Exception(f"Error al generar con IA: {e}")


def enviar_notificacion_participantes(participantes, asunto, mensaje):
    """
    Envía una notificación (por correo) a los participantes del acta.
    """
    try:
        destinatarios = [p.email for p in participantes if p.email]
        if destinatarios:
            send_mail(
                subject=asunto,
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=destinatarios,
                fail_silently=True,
            )
    except Exception as e:
        print(f"Error al enviar notificación: {e}")