# 📧 Estructura de Templates de Email - Sistema de Notificaciones

## 📁 Organización de Archivos

Los templates de email están organizados siguiendo la estructura estándar de Django:

```
sistema_actas/
└── templates/
    └── emails/
        ├── base_email.html                  # Template base con estilos compartidos
        ├── compromiso_asignado.html        # Email de compromiso asignado
        ├── solicitud_firma.html            # Email de solicitud de firma
        ├── acta_firmada_completa.html      # Email de acta completamente firmada
        ├── recordatorio_compromiso.html    # Email de recordatorio de vencimiento
        ├── compromiso_actualizado.html     # Email de cambio de estado
        └── nuevo_comentario.html           # Email de nuevo comentario
```

---

## 🎨 Template Base: base_email.html

Este template contiene:
- **Estructura HTML base** para todos los emails
- **Estilos CSS** compartidos (colores SENA, tipografía, responsive)
- **Header** con logo del sistema
- **Footer** con información institucional
- **Bloque content** para ser extendido por templates hijos

### Características:
- ✅ Diseño responsive (max-width: 600px)
- ✅ Colores corporativos SENA (#39A900, #2d8000)
- ✅ Compatible con todos los clientes de email
- ✅ Estilos inline y en `<style>` tag

### Uso:
```django
{% extends "emails/base_email.html" %}

{% block content %}
    <!-- Contenido del email aquí -->
{% endblock %}
```

---

## 📄 Templates de Email

### 1. **compromiso_asignado.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del destinatario
- `titulo_compromiso`: Título del compromiso
- `descripcion`: Descripción detallada
- `fecha_vencimiento`: Fecha límite (formato: DD/MM/YYYY)
- `creador`: Nombre de quien asignó el compromiso
- `enlace_compromiso`: URL para ver el compromiso

**Elementos visuales:**
- Info box con detalles del compromiso
- Botón "Ver Compromiso"
- Icono 📋

---

### 2. **solicitud_firma.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del destinatario
- `titulo_acta`: Título del acta
- `fecha_reunion`: Fecha y hora de la reunión
- `lugar`: Lugar de la reunión
- `creador`: Nombre de quien creó el acta
- `resumen`: Resumen del acta (máx 200 caracteres)
- `enlace_acta`: URL para ver y firmar el acta

**Elementos visuales:**
- Info box con detalles del acta
- Botón "✍️ Firmar Acta"
- Icono 📄

---

### 3. **acta_firmada_completa.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del creador del acta
- `titulo_acta`: Título del acta
- `fecha_reunion`: Fecha y hora de la reunión
- `total_participantes`: Número total de participantes
- `total_firmas`: Número de firmas recibidas
- `enlace_acta`: URL para ver el acta

**Elementos visuales:**
- Success box (verde) con mensaje de éxito
- Info box con estadísticas
- Botón "Ver Acta Completa"
- Icono ✅

---

### 4. **recordatorio_compromiso.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del responsable
- `titulo_compromiso`: Título del compromiso
- `descripcion`: Descripción detallada
- `fecha_vencimiento`: Fecha límite (formato: DD/MM/YYYY)
- `tiempo_restante`: Tiempo hasta vencimiento (ej: "Vence mañana", "2 días")
- `estado`: Estado actual del compromiso
- `enlace_compromiso`: URL para ver el compromiso

**Elementos visuales:**
- Alert box amarillo (warning)
- Info box con detalles
- Botón "Ver Compromiso"
- Icono ⏰

---

### 5. **compromiso_actualizado.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del responsable
- `titulo_compromiso`: Título del compromiso
- `descripcion`: Descripción detallada
- `estado_anterior`: Estado previo
- `estado_nuevo`: Estado actualizado
- `fecha_vencimiento`: Fecha límite
- `actualizador`: Nombre de quien actualizó
- `mensaje_adicional`: HTML con mensaje contextual (safe)
- `enlace_compromiso`: URL para ver el compromiso

**Elementos visuales:**
- Info box con detalles del cambio
- Mensaje dinámico según el tipo de cambio
- Botón "Ver Compromiso"
- Icono 📊

---

### 6. **nuevo_comentario.html**

**Variables del contexto:**
- `nombre_usuario`: Nombre completo del participante
- `titulo_acta`: Título del acta
- `fecha_reunion`: Fecha y hora de la reunión
- `autor_comentario`: Nombre de quien comentó
- `comentario`: Texto del comentario (máx 300 caracteres)
- `fecha_comentario`: Fecha del comentario
- `enlace_acta`: URL para ver el acta

**Elementos visuales:**
- Comment box (azul) con el comentario
- Info box con detalles del acta
- Botón "Ver Acta"
- Icono 💬

---

## 🔧 Cómo Usar los Templates en el Código

### Renderizar un template:

```python
from django.template.loader import render_to_string

# Preparar contexto
contexto = {
    'nombre_usuario': 'Juan Pérez',
    'titulo_compromiso': 'Completar informe',
    'descripcion': 'Entregar informe mensual de actividades',
    'fecha_vencimiento': '25/12/2024',
    'creador': 'María González',
    'enlace_compromiso': 'http://sistema.com/compromisos/123/',
}

# Renderizar template HTML
html_message = render_to_string('emails/compromiso_asignado.html', contexto)

# Enviar email
send_mail(
    subject='Nuevo Compromiso Asignado',
    message='Versión texto plano del email',
    from_email='sistema@sena.edu.co',
    recipient_list=['juan@example.com'],
    html_message=html_message,
    fail_silently=False,
)
```

---

## 🎨 Personalización de Estilos

### Cambiar colores SENA:

Edita `base_email.html`:

```css
/* Verde principal */
background: linear-gradient(135deg, #39A900, #2d8000);

/* Verde para elementos */
.info-box {
    border-left: 4px solid #39A900;
}

.button {
    background-color: #39A900;
}
```

### Agregar logo:

En `base_email.html`, dentro del `.header`:

```html
<div class="header">
    <img src="http://tudominio.com/logo.png" alt="Logo SENA" style="height: 40px; margin-bottom: 10px;">
    <h1>🎓 Sistema de Actas SENA</h1>
</div>
```

---

## 📱 Responsive Design

Los templates son responsive automáticamente:

```css
@media only screen and (max-width: 600px) {
    .container {
        margin: 0;
        border-radius: 0;
    }
    .content {
        padding: 20px;
    }
}
```

Se adaptan perfectamente a:
- 📧 Clientes de escritorio (Outlook, Thunderbird, Apple Mail)
- 📱 Apps móviles (Gmail, Outlook móvil, iOS Mail)
- 🌐 Webmail (Gmail web, Outlook web)

---

## ✅ Ventajas de Esta Estructura

### 1. **Mantenibilidad**
- Un solo lugar para cambiar estilos (base_email.html)
- Fácil de actualizar templates individuales
- Código organizado y limpio

### 2. **Consistencia**
- Todos los emails tienen el mismo look & feel
- Mismos colores, tipografía y estructura
- Experiencia uniforme para usuarios

### 3. **Reutilización**
- Template base se reutiliza en todos los emails
- Componentes (info-box, buttons) compartidos
- Menos código duplicado

### 4. **Django Best Practices**
- Usa el sistema de templates de Django
- Aprovecha herencia de templates
- Compatible con internacionalización (i18n)

### 5. **Fácil Testing**
- Puedes renderizar templates en tests
- Preview en navegador antes de enviar
- Debugging más sencillo

---

## 🧪 Probar Templates Visualmente

### Crear vista de preview (opcional):

```python
# En views.py
from django.shortcuts import render
from django.template.loader import render_to_string

def preview_email(request, template_name):
    """Vista para previsualizar templates de email"""

    # Datos de ejemplo
    contextos = {
        'compromiso_asignado': {
            'nombre_usuario': 'Juan Pérez',
            'titulo_compromiso': 'Completar informe mensual',
            'descripcion': 'Entregar informe de actividades del mes',
            'fecha_vencimiento': '25/12/2024',
            'creador': 'María González',
            'enlace_compromiso': '#',
        },
        # ... más contextos de ejemplo
    }

    contexto = contextos.get(template_name, {})
    html = render_to_string(f'emails/{template_name}.html', contexto)

    return HttpResponse(html)
```

**Acceder en navegador:**
```
http://localhost:8000/preview/compromiso_asignado/
http://localhost:8000/preview/solicitud_firma/
```

---

## 📝 Notas Importantes

### Compatibilidad con Clientes de Email:

- ✅ **Gmail:** Soporta bien CSS moderno
- ✅ **Outlook 2016+:** Soporta estilos básicos
- ⚠️ **Outlook 2013:** Motor antiguo, evitar CSS avanzado
- ✅ **Apple Mail:** Excelente soporte CSS
- ✅ **Móviles:** Responsive funciona perfectamente

### Limitaciones:

- No usar JavaScript en emails
- Evitar posicionamiento absoluto
- No usar Google Fonts (algunos clientes los bloquean)
- Usar colores hexadecimales, no nombres
- Probar en múltiples clientes antes de producción

---

**Creado:** Diciembre 2024
**Actualizado:** Diciembre 2024
**Versión:** 2.0 (Templates separados en archivos)
