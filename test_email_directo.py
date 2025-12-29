"""
Script para probar envío directo de emails a diferentes dominios
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_actas.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_enviar_email(destinatario, nombre="Usuario de Prueba"):
    """Envía un email de prueba"""
    try:
        print(f"\n{'='*60}")
        print(f"Probando envío a: {destinatario}")
        print(f"{'='*60}")

        resultado = send_mail(
            subject='🧪 Test de Email - Sistema Actas SENA',
            message=f'Hola {nombre},\n\nEste es un email de prueba del sistema de actas.\n\nSi recibes este mensaje, la configuración está funcionando correctamente.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            html_message=f'''
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Hola {nombre}!</h2>
                    <p>Este es un email de prueba del sistema de actas SENA.</p>
                    <p>Si recibes este mensaje, la configuración está funcionando correctamente.</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">Sistema de Gestión de Actas SENA</p>
                </body>
            </html>
            ''',
            fail_silently=False,
        )

        print(f"✅ Email enviado exitosamente!")
        print(f"   Resultado: {resultado}")
        return True

    except Exception as e:
        print(f"❌ Error al enviar email:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        print(f"\n   Detalles completos:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TEST DE ENVÍO DE EMAILS - SISTEMA ACTAS SENA")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")

    # Lista de emails a probar
    # INSTRUCCIONES: Descomenta y agrega los emails que quieras probar
    emails_prueba = [
        ("reyesortegarubendario@gmail.com", "Ruben Reyes (Gmail)"),
        ("rr2685346@gmail.com", "Usuario Test (Gmail)"),
        # Descomenta la siguiente línea y agrega el email de soy.sena.edu.co que quieras probar
        # ("tuusuario@soy.sena.edu.co", "Usuario SENA"),
    ]

    print("\n" + "="*60)
    print("INICIANDO PRUEBAS DE ENVÍO")
    print("="*60)

    resultados = []
    for email, nombre in emails_prueba:
        exito = test_enviar_email(email, nombre)
        resultados.append((email, exito))

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    for email, exito in resultados:
        estado = "✅ ÉXITO" if exito else "❌ FALLÓ"
        print(f"{estado} - {email}")

    print("\n" + "="*60)
    print("PRUEBA COMPLETADA")
    print("="*60)
