from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'rol', 'telefono', 'firma_digital']

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        rol = self.cleaned_data.get("rol")

        if rol == 'aprendiz':
            dominios_validos = ['@soy.sena.edu.co', '@gmail.com']
            if not any(email.endswith(d) for d in dominios_validos):
                raise forms.ValidationError(
                    "El correo del aprendiz debe ser institucional @soy.sena.edu.co o @gmail.com"
                )

        elif rol in ['funcionario', 'coordinador', 'director', 'instructor']:
            dominios_validos = ['@sena.edu.co', '@gmail.com']
            if not any(email.endswith(d) for d in dominios_validos):
                raise forms.ValidationError(
                    "El correo debe ser institucional @sena.edu.co o @gmail.com"
                )

        elif rol == 'admin':
            raise forms.ValidationError(
                "No puedes registrarte como Administrador. Este rol solo puede ser asignado por el sistema."
            )

        return email

    def clean_firma_digital(self):
        firma = self.cleaned_data.get("firma_digital")
        if firma:
            if firma.size > 2 * 1024 * 1024:
                raise forms.ValidationError("La firma no debe superar los 2 MB.")
            if not firma.name.lower().endswith((".png", ".jpg", ".jpeg")):
                raise forms.ValidationError("Solo se permiten archivos PNG, JPG o JPEG.")
        return firma

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
        

class ProfileUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label="Nueva Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Deja vacío si no deseas cambiarla'
        }),
        required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telefono', 'firma_digital', 'password']  # 👈 agregamos 'password'
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'firma_digital': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return password


    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        dominios_validos = ['@sena.edu.co', '@soy.sena.edu.co', '@gmail.com']

        # ✅ Solo valida si el usuario cambió el correo
        if email != self.instance.email:
            if not any(email.endswith(d) for d in dominios_validos):
                raise forms.ValidationError("El correo debe ser institucional @sena.edu.co o @gmail.com")
        return email


    def clean_firma_digital(self):
        firma = self.cleaned_data.get("firma_digital")
        if firma:
            # Validar tamaño (máximo 2 MB)
            if firma.size > 2 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe superar los 2 MB.")
            # Validar formato permitido
            if not firma.name.lower().endswith((".png", ".jpg", ".jpeg")):
                raise forms.ValidationError("Solo se permiten imágenes PNG, JPG o JPEG.")
        return firma