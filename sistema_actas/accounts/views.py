from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProfileUpdateForm
from .models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q


def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Bienvenido {user.get_full_name()}")
            return redirect("core:dashboard")  # Redirige a tu panel principal
        else:
            messages.error(request, "Correo o contraseña incorrectos")
    else:
        form = CustomAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)

            # ✅ Asignar firma digital si se subió
            firma = request.FILES.get("firma_digital")
            if firma:
                user.firma_digital = firma

            # ✅ Generar username único basado en el email
            base_username = user.email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user.username = username

            # ✅ Guardar usuario en la base de datos
            user.save()

            messages.success(request, "✅ Cuenta creada correctamente. Ahora puedes iniciar sesión.")
            return redirect("accounts:login")
        else:
            messages.error(request, "⚠️ Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente")
    return redirect("accounts:login")

@login_required
def profile(request):
    return render(request, "accounts/profile.html")

@login_required
def settings_view(request):
    user = request.user

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)

            new_password = form.cleaned_data.get('password')
            password_changed = False

            # 🔐 Si hay una nueva contraseña, la actualizamos
            if new_password:
                user.set_password(new_password)
                password_changed = True

            user.save()

            if password_changed:
                # 👇 Cierra sesión para obligar al usuario a iniciar con la nueva contraseña
                messages.info(request, "🔐 Tu contraseña se actualizó. Vuelve a iniciar sesión.")
                logout(request)
                return redirect('accounts:login')
            else:
                # 👇 Si solo actualizó otros datos, mantiene la sesión activa
                update_session_auth_hash(request, user)
                messages.success(request, "✅ Perfil actualizado correctamente.")
                return redirect('accounts:profile')
        else:
            messages.error(request, "⚠️ Corrige los errores en el formulario.")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'accounts/settings.html', {'form': form})


def usuarios(request):
    # Obtener parámetros de búsqueda y filtros
    search = request.GET.get('search', '')
    rol = request.GET.get('rol', '')
    estado = request.GET.get('estado', '')
    
    # Filtrar usuarios
    lista_usuarios = User.objects.all().order_by('-fecha_registro')
    
    # Aplicar búsqueda
    if search:
        lista_usuarios = lista_usuarios.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Aplicar filtro por rol
    if rol:
        lista_usuarios = lista_usuarios.filter(rol=rol)
    
    # Aplicar filtro por estado
    if estado == 'activo':
        lista_usuarios = lista_usuarios.filter(is_active=True)
    elif estado == 'inactivo':
        lista_usuarios = lista_usuarios.filter(is_active=False)
    
    # Paginación
    paginator = Paginator(lista_usuarios, 10)  # 10 usuarios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para los filtros
    roles = User.ROLES
    
    estados = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]
    
    context = {
        'page_obj': page_obj,
        'usuarios': page_obj,
        'roles': roles,
        'estados': estados,
        'filtros': {
            'search': search,
            'rol': rol,
            'estado': estado,
        }
    }
    
    return render(request, "accounts/usuarios.html", context)

def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # Obtenemos los valores del formulario
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        rol = request.POST.get('rol')
        password = request.POST.get('password')
        firma = request.FILES.get('firma_digital')

        # Actualizamos los campos
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email
        usuario.telefono = telefono
        usuario.rol = rol

        # Si se subió una nueva firma digital
        if firma:
            usuario.firma_digital = firma

        # Si se ingresó una nueva contraseña, la ciframos
        if password:
            usuario.set_password(password)
            password_changed = True
        else:
            password_changed = False

        usuario.save()

        # Si cambió la contraseña y el usuario está logueado, actualizar sesión
        if password_changed:
            update_session_auth_hash(request, usuario)

        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('accounts:usuarios')

    return render(request, 'accounts/editar_usuario.html', {'usuario': usuario})

# Vista para eliminar usuario
@login_required
def eliminar_usuario(request, user_id):
    # Verificar que el usuario tenga permisos (solo admin y director pueden eliminar)
    if request.user.rol not in ['admin', 'director']:
        messages.error(request, 'No tienes permisos para eliminar usuarios.')
        return redirect('accounts:usuarios')

    usuario = get_object_or_404(User, id=user_id)

    # Evitar que el usuario se elimine a sí mismo
    if usuario.id == request.user.id:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('accounts:usuarios')

    # Evitar eliminar al superusuario principal
    if usuario.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
        messages.error(request, 'No se puede eliminar el único superusuario del sistema.')
        return redirect('accounts:usuarios')

    usuario.delete()
    messages.success(request, f'Usuario {usuario.get_full_name()} eliminado correctamente.')
    return redirect('accounts:usuarios')