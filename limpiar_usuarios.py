import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sistema_actas'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_actas.settings')
django.setup()

from accounts.models import User

print("=" * 80)
print("LIMPIEZA DE USUARIOS DE PRUEBA")
print("=" * 80)

# Email a conservar
email_conservar = 'reyesortegarubendario@gmail.com'

print(f"\nUsuarios actuales en la base de datos:")
print("-" * 80)

todos_usuarios = User.objects.all().order_by('id')
usuarios_a_borrar = []

for user in todos_usuarios:
    conservar = user.email == email_conservar
    print(f"ID: {user.id:3d} | Email: {user.email:40s} | {'CONSERVAR' if conservar else 'BORRAR'}")
    if not conservar:
        usuarios_a_borrar.append(user)

print("-" * 80)
print(f"\nTotal usuarios: {todos_usuarios.count()}")
print(f"Usuarios a conservar: 1 ({email_conservar})")
print(f"Usuarios a borrar: {len(usuarios_a_borrar)}")

if not usuarios_a_borrar:
    print("\nNo hay usuarios para borrar. Todos los usuarios actuales se conservarán.")
    sys.exit(0)

print("\nUsuarios que se borrarán:")
for user in usuarios_a_borrar:
    print(f"  - {user.get_full_name()} ({user.email}) - Rol: {user.rol}")

confirmacion = input("\n¿Confirmas que deseas borrar estos usuarios? (escribe 'SI' para confirmar): ").strip()

if confirmacion.upper() == 'SI':
    print("\nBorrando usuarios...")
    count = 0
    for user in usuarios_a_borrar:
        nombre_completo = user.get_full_name()
        email = user.email
        user.delete()
        count += 1
        print(f"  ✓ Borrado: {nombre_completo} ({email})")

    print(f"\n✅ Se borraron {count} usuarios exitosamente.")
    print(f"✅ Se conservó el usuario: {email_conservar}")

    # Mostrar usuarios restantes
    print("\nUsuarios restantes en el sistema:")
    for user in User.objects.all():
        print(f"  - {user.get_full_name()} ({user.email}) - Rol: {user.rol}")
else:
    print("\n❌ Operación cancelada. No se borraron usuarios.")

print("\n" + "=" * 80)
