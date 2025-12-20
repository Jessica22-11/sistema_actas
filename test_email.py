import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sistema_actas'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_actas.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 80)
print("PRUEBA DE ENVIO DE EMAIL")
print("=" * 80)

print(f"\nConfiguracion de Email:")
print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"  EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NO CONFIGURADO'}")
print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

# Solicitar email de destino
email_destino = input("\nIngresa el email de destino para la prueba: ").strip()

if not email_destino:
    print("ERROR: Debes ingresar un email valido")
    sys.exit(1)

print(f"\nEnviando email de prueba a: {email_destino}")

try:
    resultado = send_mail(
        subject='Prueba de Email - Sistema de Actas SENA',
        message='''
        Hola,

        Este es un email de prueba del Sistema de Gestion de Actas SENA.

        Tu codigo de verificacion es: 123456

        Este codigo es valido por 15 minutos.

        ---
        Sistema de Actas SENA
        Centro Minero
        ''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email_destino],
        fail_silently=False,
    )

    print(f"\nRESULTADO: Email enviado exitosamente!")
    print(f"Cantidad de emails enviados: {resultado}")
    print(f"\nRevisa el correo: {email_destino}")

except Exception as e:
    print(f"\nERROR al enviar email:")
    print(f"  Tipo: {type(e).__name__}")
    print(f"  Mensaje: {str(e)}")

    import traceback
    print(f"\nTraceback completo:")
    traceback.print_exc()

print("\n" + "=" * 80)
