from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class Acta(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('en_revision', 'En Revisión'),
        ('finalizada', 'Finalizada'),
        ('archivada', 'Archivada'),
    ]
    
    TIPOS_REUNION = [
        ('consejo_academico', 'Consejo Académico'),
        ('comite_evaluacion', 'Comité de Evaluación'),
        ('coordinacion', 'Coordinación'),
        ('administrativa', 'Administrativa'),
        ('tecnica', 'Técnica'),
        ('otra', 'Otra'),
    ]
    
    # Campos básicos
    numero_acta = models.CharField(max_length=20, unique=True, editable=False)
    titulo = models.CharField(max_length=200)
    tipo_reunion = models.CharField(max_length=30, choices=TIPOS_REUNION)
    fecha_reunion = models.DateTimeField()
    lugar_reunion = models.CharField(max_length=200)
    modalidad = models.CharField(max_length=20, choices=[
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('hibrida', 'Híbrida')
    ], default='presencial')
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actas_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Contenido
    orden_dia = models.TextField(help_text='Orden del día de la reunión')
    desarrollo = models.TextField(help_text='Desarrollo de la reunión')
    resumen_ia = models.TextField(blank=True, help_text='Resumen generado por IA')
    observaciones = models.TextField(blank=True)
    
    # Control de firmas
    fecha_limite_firmas = models.DateTimeField(null=True, blank=True)
    silencio_administrativo = models.BooleanField(default=False)
    aplicar_silencio_dias = models.IntegerField(default=7)
    
    # Archivos adjuntos
    archivo_adjunto = models.FileField(upload_to='actas/adjuntos/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Acta'
        verbose_name_plural = 'Actas'
        ordering = ['-fecha_creacion']
        permissions = [
            ("can_finalize_acta", "Puede finalizar actas"),
            ("can_archive_acta", "Puede archivar actas"),
        ]
    
    def save(self, *args, **kwargs):
        if not self.numero_acta:
            year = timezone.now().year
            count = Acta.objects.filter(fecha_creacion__year=year).count() + 1
            self.numero_acta = f"ACT-{year}-{count:03d}"
        
        if not self.fecha_limite_firmas and self.estado == 'en_revision':
            self.fecha_limite_firmas = timezone.now() + timedelta(days=self.aplicar_silencio_dias)
        
        super().save(*args, **kwargs)
    
    def get_participantes(self):
        return self.participantes.all()
    
    def get_firmas_completadas(self):
        return self.firmas.filter(firmado=True).count()
    
    def get_total_firmas(self):
        return self.participantes.count()
    
    def get_porcentaje_firmas(self):
        total = self.get_total_firmas()
        if total == 0:
            return 0
        return (self.get_firmas_completadas() / total) * 100
    
    def puede_aplicar_silencio_administrativo(self):
        if not self.fecha_limite_firmas:
            return False
        return timezone.now() > self.fecha_limite_firmas and self.estado == 'en_revision'
    
    def aplicar_silencio_admin(self):
        if self.puede_aplicar_silencio_administrativo():
            self.estado = 'finalizada'
            self.silencio_administrativo = True
            self.save()
            
            # Marcar firmas pendientes como firmadas automáticamente
            firmas_pendientes = self.firmas.filter(firmado=False)
            for firma in firmas_pendientes:
                firma.firmado = True
                firma.fecha_firma = timezone.now()
                firma.firmado_por_silencio = True
                firma.save()
    
    def __str__(self):
        return f"{self.numero_acta} - {self.titulo}"

class Participante(models.Model):
    acta = models.ForeignKey(Acta, on_delete=models.CASCADE, related_name='participantes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    rol_en_reunion = models.CharField(max_length=100, blank=True)
    obligatorio_firma = models.BooleanField(default=True)
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        unique_together = ['acta', 'usuario']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.acta.numero_acta}"

class Firma(models.Model):
    acta = models.ForeignKey(Acta, on_delete=models.CASCADE, related_name='firmas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    firmado = models.BooleanField(default=False)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    firma_imagen = models.ImageField(upload_to='firmas_actas/', null=True, blank=True)
    firmado_por_silencio = models.BooleanField(default=False)
    comentarios = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Firma'
        verbose_name_plural = 'Firmas'
        unique_together = ['acta', 'usuario']
    
    def firmar(self, request=None):
        self.firmado = True
        self.fecha_firma = timezone.now()
        if self.usuario.firma_digital:
            self.firma_imagen = self.usuario.firma_digital
        if request:
            self.ip_address = self.get_client_ip(request)
        self.save()
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def __str__(self):
        return f"Firma de {self.usuario.get_full_name()} - {self.acta.numero_acta}"

class Compromiso(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('vencido', 'Vencido'),
    ]
    
    acta = models.ForeignKey(Acta, on_delete=models.CASCADE, related_name='compromisos')
    descripcion = models.TextField()
    responsable = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compromisos_asignados')
    fecha_limite = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    porcentaje_avance = models.IntegerField(default=0)
    observaciones = models.TextField(blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Compromiso'
        verbose_name_plural = 'Compromisos'
        ordering = ['fecha_limite']
    
    def save(self, *args, **kwargs):
        if self.porcentaje_avance == 100 and self.estado != 'completado':
            self.estado = 'completado'
            self.fecha_completado = timezone.now()
        elif self.fecha_limite < timezone.now().date() and self.estado not in ['completado']:
            self.estado = 'vencido'
        super().save(*args, **kwargs)
    
    def dias_restantes(self):
        if self.estado == 'completado':
            return 0
        delta = self.fecha_limite - timezone.now().date()
        return delta.days
    
    def esta_vencido(self):
        return self.dias_restantes() < 0 and self.estado != 'completado'
    
    def __str__(self):
        return f"Compromiso {self.id} - {self.acta.numero_acta}"