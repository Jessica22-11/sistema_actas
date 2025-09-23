from django.contrib.auth.models import AbstractUser #Importacion del modelo base de usrio de Django
from django.db import models #Importacion de utilidades de modelos Django
from django.core.validators import validate_email # Validar emails de Django
from PIL import Image #Libreria pillow para trabajar con imagenes (Para firma digital)
import os
from django.core.exceptions import ValidationError


#Modelo personalizado de usuario
class User (AbstractUser) :
    ROLES = [
        ('funcionario', 'Funcionario'),
        ('coordinador', 'Coordinador'),
        ('director', 'Director'),
        ('admin', 'Administrador'),
    ]
    
    #Sobreescribimos algunos campos de AbstractUser y agrego nuevos campos
    email = models.EmailField (unique=True)
    rol = models.CharField (max_length=20, choices=ROLES, default='funcionario')
    centro = models.CharField(max_length=100, default='Centro Minero')
    telefono = models.CharField (max_length=15, blank=True)
    firma_digital = models.ImageField(upload_to='firmas/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True) #Fecha de creacion automatica
    activo = models.BooleanField (default=True) #Estado del usuario activo/inactivo
    
    #Configuracion de login: se usara el email en lugar de username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name'] #Campos obligatorios
    
    #Metadatos del proyecto
    class Meta:
        verbose_name = 'Usuario' #Nombre singular del admin
        verbose_name_plural = 'Usuarios' #Nombre plural en el admin
        ordering = ['first_name', 'last_name'] #Orden por nombre y apellido

    #Validaciones personalizadas
    def clean(self):
        super().clean()
        if self.email and not self.email.endswith('@sena.edu.co'):
            raise ValidationError('El correo debe se del domino @sena.edu.co')
    
    #Guardado Personalizado
    def save (self, *args, **kwargs):
        #Redimensionar firma digital si es muy grade
        super().save(*args, **kwargs)
        if self.firma_digital:
            img = Image.open(self.firma_digital.path)
            if img.height > 200 or img.width > 400:
                img.thumbnail ((400, 200))
                img.save (self.firma_digital.path)
    
    #Retorna nombre completo del usuario
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    #Representacion en texto del usuario
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"