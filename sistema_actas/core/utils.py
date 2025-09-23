import openai
from django.conf import settings
from datetime import datetime

def generar_acta_con_ia(resumen_reunion, usuario):
    """
    Genera contenido de acta usando IA basado en el resumen de la reunión
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("API Key de OpenAI no configurada")
    
    openai.api_key = settings.OPENAI_API_KEY
    
    prompt = f"""
    Como asistente de IA del SENA Centro Minero, genera un acta de reunión profesional y estructurada basada en el siguiente resumen:

    RESUMEN DE LA REUNIÓN:
    {resumen_reunion}

    INFORMACIÓN DEL USUARIO:
    - Nombre: {usuario.get_full_name()}
    - Email: {usuario.email}
    - Rol: {usuario.get_rol_display()}
    - Centro: {usuario.centro}

    Genera un JSON con la siguiente estructura:
    {{
        "orden_dia": "Lista numerada de los puntos del orden del día extraídos del resumen",
        "desarrollo": "Desarrollo detallado de la reunión siguiendo el formato institucional del SENA, organizando la información de manera clara y profesional",
        "compromisos_sugeridos": [
            {{
                "descripcion": "Descripción del compromiso",
                "responsable_sugerido": "email o nombre del responsable si se menciona",
                "fecha_limite_sugerida": "fecha en formato YYYY-MM-DD"
            }}
        ]
    }}

    INSTRUCCIONES ESPECÍFICAS:
    1. Usa el formato oficial del SENA para actas
    2. Incluye verificación de quórum al inicio
    3. Estructura clara con numeración
    4. Lenguaje formal y técnico apropiado
    5. Extrae compromisos específicos mencionados en el resumen
    6. Si no hay información suficiente para algún campo, usa texto placeholder apropiado

    Responde únicamente con el JSON, sin texto adicional.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en la creación de actas institucionales para el SENA."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        import json
        resultado = json.loads(response.choices[0].message.content)
        
        # Formatear el desarrollo con información institucional
        desarrollo_completo = f"""
ACTA DE REUNIÓN - CENTRO MINERO SENA
=====================================

INFORMACIÓN GENERAL:
- Fecha: {datetime.now().strftime('%d de %B de %Y')}
- Lugar: Centro Minero SENA
- Modalidad: [Por definir]

PARTICIPANTES:
- {usuario.get_full_name()} ({usuario.email}) - {usuario.get_rol_display()}
- [Otros participantes por definir]

VERIFICACIÓN DEL QUÓRUM:
Se verifica la asistencia de los participantes y se declara la existencia del quórum necesario para el desarrollo de la reunión.

DESARROLLO DE LA REUNIÓN:
{resultado.get('desarrollo', 'Desarrollo por completar basado en el resumen proporcionado.')}

COMPROMISOS ADQUIRIDOS:
{chr(10).join([f"• {comp['descripcion']}" for comp in resultado.get('compromisos_sugeridos', [])])}

CIERRE:
No habiendo más asuntos que tratar, se da por terminada la reunión.

FIRMAS:
[Pendientes de completar por los participantes]
        """
        
        return {
            'orden_dia': resultado.get('orden_dia', '1. Verificación del quórum\n2. Desarrollo de la reunión\n3. Compromisos y acuerdos\n4. Varios'),
            'desarrollo': desarrollo_completo.strip(),
            'compromisos_sugeridos': resultado.get('compromisos_sugeridos', [])
        }
        
    except Exception as e:
        # En caso de error con la IA, devolver estructura básica
        return {
            'orden_dia': '1. Verificación del quórum\n2. Lectura y aprobación del orden del día\n3. Desarrollo de la reunión\n4. Compromisos y acuerdos\n5. Varios',
            'desarrollo': f"""
ACTA DE REUNIÓN - CENTRO MINERO SENA
=====================================

INFORMACIÓN GENERAL:
- Fecha: {datetime.now().strftime('%d de %B de %Y')}
- Responsable: {usuario.get_full_name()} ({usuario.email})

RESUMEN DE LA REUNIÓN:
{resumen_reunion}

DESARROLLO:
[El contenido será estructurado según el formato institucional del SENA]

COMPROMISOS:
[Por definir según el desarrollo de la reunión]
            """.strip(),
            'compromisos_sugeridos': []
        }