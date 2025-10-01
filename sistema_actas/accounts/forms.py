from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'rol', 'telefono', 'firma_digital']

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email.endswith(("@sena.edu.co", "@gmail.com")):
            raise forms.ValidationError("El correo debe ser institucional @sena.edu.co o @gmail.com")
        return email


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo Institucional",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "id": "email",
            "placeholder": "usuario@sena.edu.co o usuario@gmail.com",
        })
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "id": "password",
            "placeholder": "Contraseña",
        }),
    )

    def confirm_login_allowed(self, user):
        if not user.activo:
            raise forms.ValidationError("La cuenta está inactiva", code="inactive")
