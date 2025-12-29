# Sistema de Notificaciones por Email - SENA Actas

## 📧 Descripción General

Sistema completo de notificaciones automáticas por email para el sistema de gestión de actas SENA. Envía emails profesionales en formato HTML para mantener informados a los usuarios sobre eventos importantes.

---

## 🎯 Tipos de Notificaciones Implementadas

### 1. **Compromiso Asignado** 🔔
- **Cuándo:** Al crear un compromiso y asignar un responsable
- **Destinatario:** Usuario asignado como responsable
- **Contenido:**
  - Título del compromiso
  - Descripción
  - Fecha de vencimiento
  - Nombre de quien lo asignó
  - Enlace para ver el compromiso

### 2. **Solicitud de Firma** ✍️
- **Cuándo:** Al crear un acta con participantes que deben firmar
- **Destinatario:** Cada participante del acta
- **Contenido:**
  - Título del acta
  - Fecha y lugar de reunión
  - Resumen del acta
  - Nombre del creador
  - Enlace para firmar

### 3. **Acta Firmada Completamente** ✅
- **Cuándo:** Cuando todos los participantes han firmado un acta
- **Destinatario:** Creador del acta
- **Contenido:**
  - Título del acta
  - Fecha de reunión
  - Total de participantes y firmas
  - Enlace para ver el acta

### 4. **Recordatorio de Compromiso Próximo a Vencer** ⏰
- **Cuándo:** 24 horas antes del vencimiento (ejecutado por comando)
- **Destinatario:** Usuario responsable del compromiso
- **Contenido:**
  - Título del compromiso
  - Descripción
  - Fecha de vencimiento
  - Tiempo restante
  - Estado actual
  - Enlace para ver el compromiso

### 5. **Compromiso Actualizado** 📊
- **Cuándo:** Al cambiar el estado de un compromiso
- **Destinatario:** Usuario responsable del compromiso
- **Contenido:**
  - Título del compromiso
  - Estado anterior y nuevo
  - Fecha de vencimiento
  - Nombre de quien actualizó
  - Mensaje contextual según el cambio
  - Enlace para ver el compromiso

### 6. **Nuevo Comentario en Acta** 💬
- **Cuándo:** Al agregar un comentario en un acta
- **Destinatarios:** Todos los participantes del acta (excepto el autor del comentario)
- **Contenido:**
  - Título del acta
  - Autor del comentario
  - Texto del comentario
  - Fecha del comentario
  - Enlace para ver el acta

---

## 📁 Archivos Creados/Modificados

### Archivos Nuevos:

1. **`actas/email_templates.py`**
   - 6 templates HTML profesionales
   - Diseño responsive con colores SENA
   - Estilos consistentes y modernos

2. **`actas/email_service.py`**
   - 6 funciones de envío de emails
   - Manejo de errores robusto
   - Logging de todas las operaciones

3. **`actas/management/commands/enviar_recordatorios.py`**
   - Comando Django para recordatorios automáticos
   - Busca compromisos que vencen en 24 horas
   - Modo dry-run para pruebas

### Archivos Modificados:

1. **`actas/api_views.py`**
   - Integración en `crear_compromiso_api()` (línea ~1618)
   - Integración en `crear_acta_api()` (línea ~1171)
   - Integración en `firmar_acta_api()` (línea ~1434)
   - Integración en `actualizar_compromiso_api()` (línea ~2342)

2. **`sistema_actas/settings.py`**
   - Agregado logger para `actas.email_service` (línea ~279)

---

## ⚙️ Configuración Requerida

### 1. Variables de Entorno (.env)

Asegúrate de tener configuradas estas variables:

```env
# Email Configuration
EMAIL_HOST_USER=gestionactassena@gmail.com
EMAIL_HOST_PASSWORD=vhvn btdf gmpaw sde
DEFAULT_FROM_EMAIL=Sistema Actas SENA <gestionactassena@gmail.com>

# Site Domain (para enlaces en emails)
SITE_DOMAIN=127.0.0.1:8000  # En producción: tu dominio real
```

### 2. Verificar settings.py

La configuración de email ya está lista en `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
```

---

## 🚀 Uso

### Notificaciones Automáticas en la API

Las notificaciones se envían automáticamente cuando:

1. **Se crea un compromiso:**
   ```python
   # En crear_compromiso_api()
   # Automáticamente envía email al responsable
   ```

2. **Se crea un acta:**
   ```python
   # En crear_acta_api()
   # Automáticamente envía emails a cada participante
   ```

3. **Se firma un acta:**
   ```python
   # En firmar_acta_api()
   # Si es la última firma, notifica al creador
   ```

4. **Se actualiza un compromiso:**
   ```python
   # En actualizar_compromiso_api()
   # Si cambia el estado, notifica al responsable
   ```

### Comando de Recordatorios

#### Ejecución Manual

```bash
# Enviar recordatorios de compromisos que vencen en 24 horas
python manage.py enviar_recordatorios

# Modo de prueba (sin enviar emails reales)
python manage.py enviar_recordatorios --dry-run

# Personalizar días de anticipación
python manage.py enviar_recordatorios --dias 2
```

#### Programar Ejecución Automática

**En Linux/Mac (crontab):**

```bash
# Editar crontab
crontab -e

# Agregar esta línea para ejecutar diariamente a las 9:00 AM
0 9 * * * cd /ruta/a/sistema_actas && /ruta/a/python manage.py enviar_recordatorios
```

**En Windows (Programador de Tareas):**

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Nombre: "Recordatorios SENA Actas"
4. Desencadenador: Diariamente a las 9:00 AM
5. Acción: Iniciar programa
   - Programa: `C:\ruta\a\python.exe`
   - Argumentos: `manage.py enviar_recordatorios`
   - Iniciar en: `C:\ruta\a\sistema_actas\sistema_actas`

---

## 📊 Logging

Todos los envíos de email se registran en `logs/audit.log`:

```
INFO 2025-12-19 20:00:00 email_service Email de compromiso asignado enviado a usuario@example.com (Compromiso ID: 123)
INFO 2025-12-19 20:01:00 email_service Email de solicitud de firma enviado a usuario2@example.com (Acta ID: 45)
WARNING 2025-12-19 20:02:00 email_service Usuario juan.perez no tiene email configurado
```

---

## 🧪 Pruebas

### Probar Envío de Email Manual

```python
# En Django shell
python manage.py shell

from actas.models import Compromiso
from actas.email_service import enviar_email_compromiso_asignado

# Obtener un compromiso de prueba
compromiso = Compromiso.objects.first()
responsable = compromiso.responsable

# Enviar email
resultado = enviar_email_compromiso_asignado(compromiso, responsable)
print(f"Email enviado: {resultado}")
```

### Probar Recordatorios en Modo Dry-Run

```bash
# Ver qué emails se enviarían sin enviarlos realmente
python manage.py enviar_recordatorios --dry-run
```

---

## 🎨 Personalización de Templates

Los templates HTML están en `actas/email_templates.py`. Puedes personalizar:

### Colores
```python
# Cambiar el verde SENA
"background-color: #39A900"  # Verde principal
"background-color: #2d8000"  # Verde oscuro
```

### Logo/Encabezado
```html
<div class="header">
    <h1>🎓 Sistema de Actas SENA</h1>
    <!-- Agregar logo aquí -->
</div>
```

### Estilos
Todos los templates comparten `BASE_STYLES`. Modifica esta variable para cambios globales.

---

## 🔒 Seguridad

- **No expone información sensible:** Los emails solo incluyen datos necesarios
- **Validación de destinatarios:** Verifica que el usuario tenga email antes de enviar
- **Manejo de errores:** Los fallos en envío no interrumpen el flujo principal
- **Logging:** Registra todos los intentos de envío para auditoría

---

## ⚠️ Consideraciones Importantes

### Emails Institucionales (@sena.edu.co)

Los emails a dominios institucionales pueden llegar a spam debido a políticas SPF/DKIM/DMARC. Para solucionar:

1. **Solicitar cuenta SMTP institucional** al departamento de IT
2. **Configurar SPF/DKIM** si usas Gmail corporativo
3. **Pedir a usuarios agregar** gestionactassena@gmail.com a contactos

### Límites de Gmail

Gmail tiene límites de envío:
- **500 emails/día** para cuentas gratuitas
- **2000 emails/día** para Google Workspace

Si necesitas más:
- Considera usar **SendGrid**, **Amazon SES**, o **Mailgun**
- Implementa cola de emails con **Celery**

### Performance

Los emails se envían **síncronamente** en cada request. Para mejor performance:

```python
# Opción 1: Envío en background con threading
import threading

def enviar_en_background():
    enviar_email_compromiso_asignado(compromiso, responsable)

threading.Thread(target=enviar_en_background).start()

# Opción 2: Usar Celery (recomendado para producción)
from celery import shared_task

@shared_task
def tarea_enviar_email(compromiso_id, usuario_id):
    compromiso = Compromiso.objects.get(id=compromiso_id)
    usuario = User.objects.get(id=usuario_id)
    enviar_email_compromiso_asignado(compromiso, usuario)
```

---

## 📞 Soporte

Para problemas o preguntas:

1. Revisa los logs en `logs/audit.log`
2. Verifica configuración de email en `.env`
3. Prueba con `--dry-run` primero
4. Contacta al equipo de desarrollo

---

## ✅ Checklist de Implementación

- [x] Templates HTML creados (6 tipos)
- [x] Funciones de envío implementadas (6 funciones)
- [x] Integración en API endpoints (4 puntos)
- [x] Comando de recordatorios creado
- [x] Logging configurado
- [x] Variables de entorno documentadas
- [ ] Probar envío de cada tipo de email
- [ ] Configurar tarea programada para recordatorios
- [ ] (Opcional) Implementar envío asíncrono con Celery

---

## 📝 Notas de Desarrollo

**Versión:** 1.0.0
**Fecha:** Diciembre 2024
**Desarrollado con:** Claude Code + Django 4.2.7
**Cuenta de Email:** gestionactassena@gmail.com
