from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProfileUpdateForm
from .models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required


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
    lista_usuarios = User.objects.all()
    return render(request, "accounts/usuarios.html", {"usuarios": lista_usuarios})

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
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    usuario.delete()
    messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('accounts:usuarios')