import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sistema_actas'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_actas.settings')
django.setup()

from accounts.models import User, CodigoVerificacion
from actas.utils import detectar_rol_por_email, generar_codigo_verificacion

print("=" * 80)
print("VERIFICACION DEL SISTEMA DE PERMISOS Y AUTENTICACION")
print("=" * 80)

# 1. Verificar usuarios existentes
print("\n1. USUARIOS EN LA BASE DE DATOS:")
print("-" * 80)
users = User.objects.all()
print(f"Total usuarios: {users.count()}")
print()
for u in users:
    print(f"Email: {u.email}")
    print(f"  - Rol: {u.rol}")
    print(f"  - Email verificado: {u.email_verificado}")
    print(f"  - Cuenta aprobada: {u.cuenta_aprobada}")
    print(f"  - Activo: {u.activo}")
    print()

# 2. Probar detección de roles
print("\n2. PRUEBA DE DETECCION AUTOMATICA DE ROLES:")
print("-" * 80)
test_emails = [
    "estudiante@soy.sena.edu.co",
    "profesor@sena.edu.co",
    "invitado@gmail.com",
    "otro@hotmail.com"
]

for email in test_emails:
    rol = detectar_rol_por_email(email)
    print(f"{email:40} => Rol: {rol}")

# 3. Probar generación de códigos
print("\n3. PRUEBA DE GENERACION DE CODIGOS:")
print("-" * 80)
for i in range(3):
    codigo = generar_codigo_verificacion()
    print(f"Codigo {i+1}: {codigo} (longitud: {len(codigo)}, es numerico: {codigo.isdigit()})")

# 4. Verificar modelos
print("\n4. VERIFICACION DE MODELOS:")
print("-" * 80)
print(f"Modelo User: OK")
print(f"Modelo CodigoVerificacion: OK")
print(f"Total codigos de verificacion en BD: {CodigoVerificacion.objects.count()}")

print("\n" + "=" * 80)
print("TODAS LAS VERIFICACIONES COMPLETADAS EXITOSAMENTE")
print("=" * 80)
