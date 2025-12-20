# 🔐 Mejora del Sistema de Autenticación

## Resumen Ejecutivo

Se ha implementado un sistema de autenticación **SEGURO** usando tokens criptográficos de Django REST Framework, reemplazando el sistema inseguro anterior.

---

## ❌ Sistema ANTERIOR (Inseguro)

### Cómo funcionaba:

1. **Login:**
   ```json
   POST /api/login/
   {
     "username": "usuario@ejemplo.com",
     "password": "contraseña123"
   }

   Respuesta:
   {
     "success": true,
     "token": "token_2",    ← ID del usuario en texto plano
     "user": { ... }
   }
   ```

2. **Uso del token:**
   ```
   GET /api/dashboard/
   Headers:
     Authorization: Bearer token_2

   Backend:
   1. Extrae "2" del token
   2. Busca usuario con ID=2
   3. ¡Permite el acceso SIN verificar nada más!
   ```

### 🚨 Problemas Críticos:

1. **Token Predecible:**
   - Token = `token_` + `user_id`
   - Si sabes que hay un usuario con ID 1 (admin), solo escribes `token_1`

2. **Sin Validación:**
   - No hay verificación de que el token sea válido
   - No está almacenado en ninguna parte
   - Cualquiera puede falsificarlo

3. **Suplantación de Identidad:**
   ```javascript
   // Atacante puede hacer esto:
   fetch('http://servidor/api/dashboard/', {
     headers: {
       'Authorization': 'Bearer token_1'  // ¡Se hace pasar por el admin!
     }
   })
   ```

4. **No se puede revocar:**
   - No hay forma de cerrar sesión (el "token" es solo el ID del usuario)
   - Si alguien roba el token, no puedes invalidarlo

---

## ✅ Sistema NUEVO (Seguro)

### Cómo funciona:

1. **Login:**
   ```json
   POST /api/login/
   {
     "username": "usuario@ejemplo.com",
     "password": "contraseña123"
   }

   Respuesta:
   {
     "success": true,
     "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",  ← Token aleatorio de 40 caracteres
     "user": { ... }
   }
   ```

2. **Almacenamiento del Token (Backend):**
   - El token se guarda en la tabla `authtoken_token` de la base de datos:

   | key (token)                              | user_id | created              |
   |------------------------------------------|---------|----------------------|
   | 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b | 2       | 2024-12-12 15:30:00 |

3. **Uso del token:**
   ```
   GET /api/dashboard/
   Headers:
     Authorization: Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

   Backend:
   1. Busca el token en la base de datos
   2. Si existe → obtiene el usuario asociado
   3. Si NO existe → rechaza con 401 Unauthorized
   ```

### 🛡️ Ventajas de Seguridad:

1. **Token Criptográfico:**
   - 40 caracteres hexadecimales
   - Generado con algoritmos criptográficos seguros
   - **Imposible de adivinar** (2^160 combinaciones posibles)

2. **Validación Real:**
   - Cada petición verifica que el token existe en la base de datos
   - Token vinculado a un usuario específico

3. **Protección contra Suplantación:**
   ```javascript
   // Atacante intenta:
   fetch('http://servidor/api/dashboard/', {
     headers: {
       'Authorization': 'Bearer token_1'  // ❌ Token inválido
     }
   })
   // Backend responde: 401 Unauthorized, "Token inválido"
   ```

4. **Se puede revocar:**
   ```json
   POST /api/logout/
   Headers:
     Authorization: Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

   → El token se ELIMINA de la base de datos
   → Sesión cerrada permanentemente
   → El token ya no funciona para ninguna petición
   ```

---

## 🔧 Cambios Implementados

### 1. Configuración (settings.py)

```python
INSTALLED_APPS = [
    ...
    "rest_framework.authtoken",  # ← AGREGADO
    ...
]
```

### 2. Base de Datos

```bash
python manage.py migrate
```

Esto crea la tabla `authtoken_token`:
```sql
CREATE TABLE authtoken_token (
    key VARCHAR(40) PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    created DATETIME NOT NULL
);
```

### 3. Función Helper (api_views.py)

```python
def get_user_from_token(request):
    """
    Helper para autenticar usuario usando el token del header.

    Retorna:
        - (user, None) si el token es válido
        - (None, JsonResponse con error) si el token es inválido
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None, JsonResponse({
            'success': False,
            'error': 'No autenticado'
        }, status=401)

    token_key = auth_header.replace('Bearer ', '').strip()

    try:
        # Buscar token en la base de datos
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user, None  # Token válido
    except Token.DoesNotExist:
        return None, JsonResponse({
            'success': False,
            'error': 'Token inválido o expirado'
        }, status=401)
```

### 4. Login Actualizado

**ANTES:**
```python
if user is not None:
    return JsonResponse({
        'token': f'token_{user.id}',  # ❌ Inseguro
        ...
    })
```

**DESPUÉS:**
```python
if user is not None:
    # Obtener o crear token
    token, created = Token.objects.get_or_create(user=user)

    return JsonResponse({
        'token': token.key,  # ✅ Token seguro de 40 caracteres
        ...
    })
```

### 5. Logout Implementado

```python
@csrf_exempt
def logout_api(request):
    """Cierra la sesión eliminando el token"""
    if request.method == 'POST':
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response

        # Eliminar token de la base de datos
        Token.objects.filter(user=user).delete()

        return JsonResponse({
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        })
```

### 6. Funciones API Actualizadas

**ANTES (INSEGURO):**
```python
@csrf_exempt
def dashboard_api(request):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token or not token.startswith('token_'):  # ❌
            return JsonResponse({'error': 'No autenticado'}, status=401)

        user_id = int(token.replace('token_', ''))  # ❌ Extrae ID directamente
        user = User.objects.get(id=user_id)  # ❌ Sin verificación

        # ... resto del código
```

**DESPUÉS (SEGURO):**
```python
@csrf_exempt
def dashboard_api(request):
    try:
        # Autenticar usuario con token seguro
        user, error_response = get_user_from_token(request)  # ✅
        if error_response:
            return error_response  # ✅ Rechaza si token inválido

        # ... resto del código (¡sin cambios!)
```

---

## 📱 Cambios Necesarios en Flutter

### NINGÚN cambio necesario en Flutter

El código de Flutter **NO requiere modificaciones** porque:

1. **Misma estructura de respuesta:**
   ```json
   {
     "success": true,
     "token": "...",  // Solo cambia el valor
     "user": { ... }
   }
   ```

2. **Mismo header:**
   ```dart
   headers: {
     'Authorization': 'Bearer $token'
   }
   ```

3. **Flutter solo debe:**
   - Guardar el token que recibe del login
   - Enviarlo en cada petición (ya lo hace)
   - Eliminar el token al hacer logout

---

## 🔄 Comparación Lado a Lado

| Aspecto | Sistema Anterior | Sistema Nuevo |
|---------|-----------------|---------------|
| **Token** | `token_2` | `9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b` |
| **Generación** | Concatenación de strings | Algoritmo criptográfico |
| **Almacenamiento** | ❌ No se almacena | ✅ Base de datos |
| **Validación** | ❌ Solo extrae el ID | ✅ Verifica existencia en BD |
| **Seguridad** | ⚠️ Crítica | ✅ Alta |
| **Predecible** | ✅ Sí (ID del usuario) | ❌ No (aleatorio) |
| **Revocable** | ❌ No | ✅ Sí (eliminar de BD) |
| **Logout** | ❌ No funciona | ✅ Funciona perfectamente |

---

## 🧪 Pruebas

### Probar el Login:

```bash
curl -X POST http://localhost:53237/api/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tu_email@ejemplo.com",
    "password": "tu_contraseña"
  }'
```

**Respuesta esperada:**
```json
{
  "success": true,
  "token": "a1b2c3d4e5f6...40caracteres",
  "user": {
    "id": 2,
    "username": "usuario",
    "email": "usuario@ejemplo.com",
    ...
  }
}
```

### Probar el Dashboard con el nuevo token:

```bash
curl -X GET http://localhost:53237/api/dashboard/ \
  -H "Authorization: Bearer a1b2c3d4e5f6...40caracteres"
```

### Probar con token inválido:

```bash
curl -X GET http://localhost:53237/api/dashboard/ \
  -H "Authorization: Bearer token_invalido"
```

**Respuesta esperada:**
```json
{
  "success": false,
  "error": "Token inválido o expirado"
}
```

### Probar el Logout:

```bash
curl -X POST http://localhost:53237/api/logout/ \
  -H "Authorization: Bearer a1b2c3d4e5f6...40caracteres"
```

---

## 📊 Impacto en Funciones Existentes

Hay aproximadamente **20 funciones** en `api_views.py` que necesitan actualización:

### Funciones que usan autenticación:

1. `dashboard_api` - ✅ Ya actualizada
2. `lista_actas_api` - ⏳ Pendiente
3. `detalle_acta_api` - ⏳ Pendiente
4. `crear_acta_api` - ⏳ Pendiente
5. `editar_acta_api` - ⏳ Pendiente
6. ... y más

### El cambio es simple:

Cada una solo necesita reemplazar ~10 líneas de código antiguo por **3 líneas**:

```python
# Estas 3 líneas reemplazan todo el código de autenticación inseguro:
user, error_response = get_user_from_token(request)
if error_response:
    return error_response
```

---

## ⚠️ Consideraciones Importantes

### 1. Tokens Existentes (del sistema antiguo)

Los usuarios que actualmente tienen sesión abierta en Flutter:
- **Sus tokens antiguos (`token_2`) NO funcionarán más**
- Deberán hacer **logout y login nuevamente**
- Recibirán el nuevo token seguro

### 2. Compatibilidad

**Opción A: Cambio inmediato (Recomendado)**
- Actualizar todo el backend de una vez
- Usuarios deben volver a hacer login
- Máxima seguridad desde el inicio

**Opción B: Migración gradual (No recomendado)**
- Soportar ambos sistemas temporalmente
- Más complejo, menos seguro

### 3. Futuras Mejoras

Este sistema es mucho mejor, pero aún puede mejorarse:

1. **Expiración de tokens:**
   - Agregar campo `expires_at` a los tokens
   - Tokens expiran después de X días/horas

2. **JWT (JSON Web Tokens):**
   - Tokens sin estado (no requieren BD)
   - Incluyen claims (permisos, roles)
   - Refresh tokens

3. **Rate Limiting:**
   - Limitar intentos de login fallidos
   - Prevenir ataques de fuerza bruta

---

## 🎯 Recomendación

**Implementar el cambio completo AHORA:**

1. ✅ Ya está configurado el sistema nuevo
2. ✅ Ya funcionan login_api, logout_api y dashboard_api
3. ⏳ Actualizar las ~17 funciones restantes (10 minutos)
4. ✅ Reiniciar servidor Django
5. ✅ Probar login desde Flutter
6. ✅ Verificar que todo funcione

**Alternativa conservadora:**

Si prefieres probar primero:
1. Mantener solo 3 funciones con el nuevo sistema (login, logout, dashboard)
2. Probar exhaustivamente desde Flutter
3. Una vez confirmado, actualizar el resto

---

## 💡 Conclusión

El nuevo sistema:
- 🔒 **Mucho más seguro** (tokens criptográficos vs IDs predecibles)
- ✅ **Mismo esfuerzo para el usuario** (login/logout igual)
- 🎯 **Sin cambios en Flutter** (misma API)
- 🚀 **Mejora inmediata** de seguridad
- 🛡️ **Previene suplantación** de identidad
- 🔄 **Permite logout real** (revocación de tokens)

¿Quieres que actualice TODAS las funciones ahora o prefieres hacerlo gradualmente?
