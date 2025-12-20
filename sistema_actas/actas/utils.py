"""
Utilidades para el módulo de actas
Incluye funciones para detección de roles, generación de códigos y envío de emails
"""

import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def detectar_rol_por_email(email):
    """
    Detecta automáticamente el rol del usuario basándose en su dominio de email.

    Args:
        email (str): Email del usuario

    Returns:
        str: Rol detectado ('aprendiz', 'instructor', o 'invitado')

    Ejemplos:
        >>> detectar_rol_por_email('juan@soy.sena.edu.co')
        'aprendiz'
        >>> detectar_rol_por_email('maria@sena.edu.co')
        'instructor'
        >>> detectar_rol_por_email('carlos@gmail.com')
        'invitado'
    """
    email = email.lower().strip()

    if email.endswith('@soy.sena.edu.co'):
        return 'aprendiz'
    elif email.endswith('@sena.edu.co'):
        return 'instructor'
    else:
        # Cualquier otro dominio (gmail, hotmail, etc.) es invitado
        return 'invitado'


def generar_codigo_verificacion():
    """
    Genera un código de verificación de 6 dígitos numéricos aleatorios.

    Returns:
        str: Código de 6 dígitos (ej: '123456')

    Ejemplos:
        >>> codigo = generar_codigo_verificacion()
        >>> len(codigo)
        6
        >>> codigo.isdigit()
        True
    """
    return ''.join(random.choices(string.digits, k=6))


def enviar_email_verificacion(user, codigo):
    """
    Envía un email con el código de verificación al usuario.

    Args:
        user: Instancia del modelo User
        codigo (str): Código de verificación de 6 dígitos

    Returns:
        bool: True si el email se envió exitosamente, False en caso contrario

    Ejemplo:
        >>> from accounts.models import User
        >>> user = User.objects.get(email='test@example.com')
        >>> enviar_email_verificacion(user, '123456')
        True
    """
    asunto = 'Código de Verificación - Sistema de Actas SENA'

    mensaje = f"""
    Hola {user.first_name} {user.last_name},

    Gracias por registrarte en el Sistema de Gestión de Actas del SENA.

    Tu código de verificación es: {codigo}

    Este código es válido por 15 minutos.

    Por favor, ingresa este código en la aplicación para verificar tu cuenta.

    Si no solicitaste este código, ignora este mensaje.

    ---
    Sistema de Gestión de Actas SENA
    Centro Minero
    """

    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        return False


def crear_codigo_verificacion(user, tipo='registro'):
    """
    Crea un código de verificación para el usuario y lo guarda en la base de datos.

    Args:
        user: Instancia del modelo User
        tipo (str): Tipo de código ('registro' o 'recuperacion')

    Returns:
        CodigoVerificacion: Instancia del código creado

    Ejemplo:
        >>> from accounts.models import User
        >>> user = User.objects.get(email='test@example.com')
        >>> codigo_obj = crear_codigo_verificacion(user, 'registro')
        >>> print(codigo_obj.codigo)
        '123456'
    """
    from accounts.models import CodigoVerificacion

    # Generar código
    codigo = generar_codigo_verificacion()

    # Calcular fecha de expiración (15 minutos desde ahora)
    fecha_expiracion = timezone.now() + timedelta(minutes=15)

    # Crear y guardar el código
    codigo_obj = CodigoVerificacion.objects.create(
        user=user,
        codigo=codigo,
        tipo=tipo,
        fecha_expiracion=fecha_expiracion
    )

    return codigo_obj


def verificar_codigo(user, codigo_ingresado, tipo='registro'):
    """
    Verifica si un código ingresado es válido para el usuario.

    Args:
        user: Instancia del modelo User
        codigo_ingresado (str): Código ingresado por el usuario
        tipo (str): Tipo de código a verificar ('registro' o 'recuperacion')

    Returns:
        tuple: (bool, str) - (es_valido, mensaje_error)

    Ejemplos:
        >>> verificar_codigo(user, '123456', 'registro')
        (True, '')
        >>> verificar_codigo(user, '000000', 'registro')
        (False, 'Código incorrecto')
    """
    from accounts.models import CodigoVerificacion

    try:
        # Buscar el código más reciente del usuario para el tipo especificado
        codigo_obj = CodigoVerificacion.objects.filter(
            user=user,
            tipo=tipo,
            usado=False
        ).order_by('-fecha_creacion').first()

        if not codigo_obj:
            return False, 'No se encontró un código de verificación válido'

        # Verificar si el código coincide
        if codigo_obj.codigo != codigo_ingresado:
            return False, 'Código incorrecto'

        # Verificar si el código ha expirado
        if not codigo_obj.is_valid():
            return False, 'El código ha expirado. Solicita uno nuevo'

        # Código válido
        return True, ''

    except Exception as e:
        return False, f'Error al verificar el código: {str(e)}'


def aprobar_usuario_automaticamente(user):
    """
    Aprueba y verifica automáticamente la cuenta de un usuario.

    Args:
        user: Instancia del modelo User

    Returns:
        User: Usuario actualizado

    Ejemplo:
        >>> user = aprobar_usuario_automaticamente(user)
        >>> user.email_verificado
        True
        >>> user.cuenta_aprobada
        True
    """
    user.email_verificado = True
    user.cuenta_aprobada = True
    user.save()
    return user
