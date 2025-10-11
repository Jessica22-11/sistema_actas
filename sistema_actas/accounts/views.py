from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProfileUpdateForm
from .models import User


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

@login_required
def settings_view(request):
    user = request.user

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            profile = form.save(commit=False)

            # Si el usuario cambia la contraseña
            new_password = form.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)

            profile.save()
            messages.success(request, "✅ Perfil actualizado correctamente.")
            return redirect('accounts:settings')
        else:
            messages.error(request, "⚠️ Corrige los errores en el formulario.")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'accounts/settings.html', {'form': form})

def usuarios(request):
    lista_usuarios = User.objects.all()
    return render(request, "accounts/usuarios.html", {"usuarios": lista_usuarios})