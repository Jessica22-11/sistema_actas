"""
Script de prueba para el sistema de notificaciones por email
Ejecutar con: python test_notificaciones.py
"""

import os
import django
import sys

# Configurar Django
sys.path.append('sistema_actas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_actas.settings')
django.setup()

from accounts.models import User
from actas.models import Acta, Compromiso
from actas.email_service import (
    enviar_email_compromiso_asignado,
    enviar_email_solicitud_firma,
    enviar_email_acta_firmada_completa,
    enviar_email_recordatorio_compromiso,
    enviar_email_compromiso_actualizado,
    enviar_email_nuevo_comentario
)

def test_email_configuration():
    """Verifica que la configuración de email esté correcta"""
    from django.conf import settings

    print("\n" + "="*60)
    print("1. VERIFICANDO CONFIGURACIÓN DE EMAIL")
    print("="*60)

    print(f"\n✓ EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"✓ EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"✓ EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"✓ EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"✓ EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"✓ DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

    if settings.EMAIL_HOST_USER and '@' in settings.EMAIL_HOST_USER:
        print(f"\n✅ Configuración de email correcta")
        return True
    else:
        print(f"\n❌ ERROR: EMAIL_HOST_USER no está configurado correctamente")
        print(f"   Verifica tu archivo .env")
        return False


def test_email_compromiso_asignado():
    """Prueba el envío de email de compromiso asignado"""
    print("\n" + "="*60)
    print("2. PROBANDO: Email de Compromiso Asignado")
    print("="*60)

    # Buscar un compromiso de prueba
    compromiso = Compromiso.objects.filter(responsable__isnull=False).first()

    if not compromiso:
        print("❌ No hay compromisos en la base de datos para probar")
        return False

    print(f"\nCompromiso de prueba:")
    print(f"  ID: {compromiso.id}")
    print(f"  Descripción: {compromiso.descripcion[:50]}...")
    print(f"  Responsable: {compromiso.responsable.get_full_name()}")
    print(f"  Email: {compromiso.responsable.email}")

    if not compromiso.responsable.email:
        print("❌ El responsable no tiene email configurado")
        return False

    # Preguntar confirmación
    respuesta = input(f"\n¿Enviar email de prueba a {compromiso.responsable.email}? (s/n): ")

    if respuesta.lower() != 's':
        print("⏭️  Prueba omitida")
        return False

    # Enviar email
    print("\nEnviando email...")
    resultado = enviar_email_compromiso_asignado(compromiso, compromiso.responsable)

    if resultado:
        print("✅ Email enviado correctamente")
        return True
    else:
        print("❌ Error al enviar email (revisa logs/audit.log)")
        return False


def test_email_solicitud_firma():
    """Prueba el envío de email de solicitud de firma"""
    print("\n" + "="*60)
    print("3. PROBANDO: Email de Solicitud de Firma")
    print("="*60)

    # Buscar un acta de prueba con participantes
    acta = Acta.objects.filter(participantes__isnull=False).first()

    if not acta:
        print("❌ No hay actas con participantes para probar")
        return False

    participante = acta.participantes.first().usuario

    print(f"\nActa de prueba:")
    print(f"  ID: {acta.id}")
    print(f"  Título: {acta.titulo}")
    print(f"  Participante: {participante.get_full_name()}")
    print(f"  Email: {participante.email}")

    if not participante.email:
        print("❌ El participante no tiene email configurado")
        return False

    # Preguntar confirmación
    respuesta = input(f"\n¿Enviar email de prueba a {participante.email}? (s/n): ")

    if respuesta.lower() != 's':
        print("⏭️  Prueba omitida")
        return False

    # Enviar email
    print("\nEnviando email...")
    resultado = enviar_email_solicitud_firma(acta, participante)

    if resultado:
        print("✅ Email enviado correctamente")
        return True
    else:
        print("❌ Error al enviar email (revisa logs/audit.log)")
        return False


def test_comando_recordatorios():
    """Prueba el comando de recordatorios en modo dry-run"""
    print("\n" + "="*60)
    print("4. PROBANDO: Comando de Recordatorios (Dry-Run)")
    print("="*60)

    from django.core.management import call_command
    from io import StringIO
    import sys

    # Capturar la salida del comando
    out = StringIO()

    try:
        call_command('enviar_recordatorios', '--dry-run', stdout=out)
        output = out.getvalue()

        print("\nSalida del comando:")
        print(output)

        if "Total de compromisos encontrados" in output:
            print("\n✅ Comando ejecutado correctamente")
            return True
        else:
            print("\n❌ El comando no se ejecutó correctamente")
            return False

    except Exception as e:
        print(f"\n❌ Error al ejecutar comando: {str(e)}")
        return False


def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "="*60)
    print("🧪 SISTEMA DE PRUEBAS DE NOTIFICACIONES POR EMAIL")
    print("="*60)

    resultados = []

    # Prueba 1: Configuración
    resultados.append(("Configuración Email", test_email_configuration()))

    if not resultados[0][1]:
        print("\n⚠️  No se pueden ejecutar más pruebas sin configuración correcta")
        return

    # Prueba 2: Email de compromiso
    resultados.append(("Email Compromiso Asignado", test_email_compromiso_asignado()))

    # Prueba 3: Email de firma
    resultados.append(("Email Solicitud Firma", test_email_solicitud_firma()))

    # Prueba 4: Comando recordatorios
    resultados.append(("Comando Recordatorios", test_comando_recordatorios()))

    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)

    for nombre, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"{estado} - {nombre}")

    total = len(resultados)
    exitosas = sum(1 for _, r in resultados if r)

    print(f"\n📈 Total: {exitosas}/{total} pruebas exitosas")

    if exitosas == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema de notificaciones está listo.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Pruebas canceladas por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
