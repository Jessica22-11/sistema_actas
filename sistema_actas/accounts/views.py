from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm


def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Bienvenido {user.get_full_name()}")
            return redirect("dashboard")  # Redirige a tu panel principal
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
            user.username = user.email  # ⚡ Usa el email como username
            user.save()
            messages.success(request, "✅ Cuenta creada correctamente. Ahora puedes iniciar sesión.")
            return redirect("accounts:login")  # 👈 Redirige al login
        else:
            print("❌ Errores en el formulario:", form.errors)  # 👀 Para depurar en consola
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente")
    return redirect("accounts:login")