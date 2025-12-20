# 🔒 Instrucciones para Limpiar Credenciales del Historial de Git

## ⚠️ PROBLEMA DETECTADO

Las credenciales de email **YA ESTÁN en el historial de Git y GitHub**:
- Email: `gestionactassena@gmail.com`
- Contraseña: `vhvnbtdfgmpawsde`

Esto fue subido en commits anteriores y es **MUY PELIGROSO**.

---

## ✅ SOLUCIÓN YA APLICADA

1. ✅ Las credenciales se movieron a archivo `.env` (no se sube a GitHub)
2. ✅ `settings.py` actualizado para usar variables de entorno
3. ✅ Creado `.env.example` como plantilla pública
4. ✅ Verificado que `.env` está en `.gitignore`

---

## 🚨 ACCIONES URGENTES REQUERIDAS

### Opción 1: Cambiar la Contraseña del Correo (MÁS SEGURO)

**RECOMENDADO:** Como las credenciales ya están públicas en GitHub:

1. **Ve a tu cuenta de Gmail:**
   - https://myaccount.google.com/apppasswords

2. **Revoca la contraseña actual** (`vhvnbtdfgmpawsde`)

3. **Genera una nueva contraseña de aplicación:**
   - Nombre: "Sistema Actas SENA"
   - Copia la nueva contraseña (16 caracteres)

4. **Actualiza el archivo `.env`:**
   ```env
   EMAIL_HOST_PASSWORD=tu-nueva-contraseña-aqui
   ```

5. **Reinicia el servidor Django:**
   ```bash
   cd sistema_actas
   python manage.py runserver 53237
   ```

**Con esto, aunque alguien tenga la contraseña antigua, ya no podrá usarla.**

---

### Opción 2: Limpiar el Historial de Git (MÁS COMPLEJO)

Si además quieres **eliminar las credenciales del historial de Git**, sigue estos pasos:

#### ⚠️ ADVERTENCIA
- Esto reescribe el historial de Git
- Todos los colaboradores deben hacer `git pull --force` después
- Es irreversible

#### Pasos:

1. **Instala git-filter-repo** (herramienta de limpieza):
   ```bash
   pip install git-filter-repo
   ```

2. **Haz backup del repositorio:**
   ```bash
   cd ..
   cp -r sistema_actas sistema_actas_backup
   ```

3. **Crea un archivo con los textos a eliminar:**
   ```bash
   cd sistema_actas
   cat > passwords.txt << EOF
   gestionactassena@gmail.com
   vhvnbtdfgmpawsde
   EOF
   ```

4. **Ejecuta la limpieza:**
   ```bash
   git filter-repo --replace-text passwords.txt --force
   ```

5. **Fuerza el push al remoto:**
   ```bash
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   git push origin --force --all
   git push origin --force --tags
   ```

6. **Notifica a los colaboradores:**
   - Todos deben eliminar su copia local
   - Hacer un nuevo `git clone`

---

## 📋 Checklist Final

- [ ] Revocar contraseña antigua en Gmail
- [ ] Generar nueva contraseña de aplicación
- [ ] Actualizar `.env` con nueva contraseña
- [ ] Probar que el envío de correos funciona
- [ ] (Opcional) Limpiar historial con git-filter-repo
- [ ] Hacer commit con los cambios actuales
- [ ] Push a GitHub

---

## 🧪 Probar que Funciona

Después de cambiar la contraseña, prueba el envío de correos:

```bash
cd sistema_actas
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Prueba de correo',
    'Este es un correo de prueba.',
    'gestionactassena@gmail.com',
    ['tu-correo@ejemplo.com'],
    fail_silently=False,
)
```

Si no hay errores, ¡funciona correctamente!

---

## 📝 Resumen de Archivos

```
sistema_actas/
├── .env                    ← Credenciales REALES (NO se sube a GitHub)
├── .env.example            ← Plantilla pública (SÍ se sube)
├── .gitignore              ← Tiene .env incluido ✅
└── sistema_actas/
    └── settings.py         ← Usa config() para leer .env ✅
```

---

## 🎯 Próximos Pasos

1. **AHORA MISMO:** Cambia la contraseña de la aplicación de Gmail
2. **Actualiza `.env`** con la nueva contraseña
3. **Haz el commit** de los cambios actuales (sin credenciales)
4. **Push a GitHub** - ahora está seguro

---

## ❓ Preguntas Frecuentes

**P: ¿Por qué no simplemente eliminar el commit?**
R: Porque ya está en GitHub y otros pueden haberlo descargado. Es más seguro cambiar la contraseña.

**P: ¿Alguien puede haber robado mi contraseña?**
R: Es posible. Por eso es CRÍTICO cambiarla inmediatamente.

**P: ¿Cuándo debo usar git-filter-repo?**
R: Solo si necesitas limpiar el historial para cumplir políticas de seguridad o auditorías. No es estrictamente necesario si cambias la contraseña.

**P: ¿El archivo .env se sincroniza entre computadoras?**
R: NO. Cada desarrollador debe crear su propio `.env` copiando `.env.example`.

---

## 🔐 Buenas Prácticas para el Futuro

1. ✅ **NUNCA** escribir credenciales directamente en el código
2. ✅ **SIEMPRE** usar variables de entorno (`.env`)
3. ✅ **VERIFICAR** que `.env` está en `.gitignore`
4. ✅ **REVISAR** antes de cada commit si hay secretos
5. ✅ **ROTAR** contraseñas periódicamente

---

**¿Necesitas ayuda?** Pregunta antes de hacer cambios irreversibles en Git.
