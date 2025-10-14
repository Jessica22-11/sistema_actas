from openai import OpenAI
from django.conf import settings
from django.core.mail import send_mail
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def extract_json_from_string(text):
    """Limpia el texto de la IA buscando el objeto JSON entre {}."""
    try:
        # Busca el inicio de la primera llave de apertura y la última de cierre
        start_index = text.find('{')
        end_index = text.rfind('}')
        
        if start_index == -1 or end_index == -1:
            raise ValueError("No se encontró el inicio o fin de un objeto JSON.")
            
        json_string = text[start_index : end_index + 1]
        return json.loads(json_string)
    except Exception as e:
        # Si la limpieza falla, elevamos un error de formato
        raise ValueError(f"Error al limpiar y parsear JSON. Respuesta: {text[:100]}...")


def generar_acta_con_ia(resumen, usuario):
    try:
        # --- FUNCIÓN DE PYTHON CON EL PROMPT MODIFICADO ---
        prompt_content = f"""
        Eres un asistente experto en redacción de actas institucionales del SENA.
        A partir del siguiente resumen, genera la Orden del Día y el Desarrollo (resumen de la discusión y conclusiones) del acta.

        DEBES RESPONDER EXCLUSIVAMENTE CON UN OBJETO JSON VÁLIDO. NUNCA USES TEXTO EXPLICATIVO FUERA DEL JSON.
        El JSON debe contener DOS claves: "orden_dia" (string, puntos de la agenda en formato numerado) y "desarrollo" (string, resumen detallado de la reunión y conclusiones).

        Ejemplo de formato de salida JSON:
        {{"orden_dia": "1. Verificación del Quórum\\n2. Revisión de desempeño ADSO...", "desarrollo": "Se analizó el informe del instructor y se concluyó..."}}

        Resumen de la reunión: {resumen}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu única respuesta debe ser el objeto JSON."},
                {"role": "user", "content": prompt_content},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        contenido_json_str = response.choices[0].message.content.strip()
        
        # Usamos la función de limpieza y parsing
        data_ia = extract_json_from_string(contenido_json_str)

        # Devolvemos el diccionario estructurado que el JavaScript espera
        return {
            "orden_dia": data_ia.get("orden_dia", "Error: Contenido IA no generado."),
            "desarrollo": data_ia.get("desarrollo", "Error: Contenido IA no generado."),
        }

    except ValueError as e:
        # Captura errores de formato de JSON
        raise ValueError(f"Error de formato JSON: {e}")
    
    except Exception as e:
        # Captura otros errores (API Key, conexión)
        raise Exception(f"Fallo en la llamada a la API de IA: {e}")


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
