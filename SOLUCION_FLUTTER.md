# Solución al Error de Exportación en Flutter

## Problema Identificado

El error `Unsupported operation: Platform._operatingSystem` ocurre en Flutter cuando:
1. Se está ejecutando en Flutter Web y el código intenta acceder a `Platform` de `dart:io`
2. Hay un problema con el paquete HTTP que estás usando en Flutter

## Soluciones para el Código Flutter

### Opción 1: Usar http con manejo de archivos apropiado

```dart
import 'package:http/http.dart' as http;
import 'dart:io';
import 'package:path_provider/path_provider.dart';

Future<void> exportarDatos(String token) async {
  try {
    final url = Uri.parse('http://localhost:53237/api/exportar-datos-usuario/');

    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/zip',
      },
    );

    if (response.statusCode == 200) {
      // Obtener el directorio de descargas
      final directory = await getApplicationDocumentsDirectory();

      // Extraer nombre del archivo del header Content-Disposition
      String filename = 'backup.zip';
      final contentDisposition = response.headers['content-disposition'];
      if (contentDisposition != null) {
        final regex = RegExp(r'filename="([^"]+)"');
        final match = regex.firstMatch(contentDisposition);
        if (match != null) {
          filename = match.group(1)!;
        }
      }

      // Guardar el archivo
      final file = File('${directory.path}/$filename');
      await file.writeAsBytes(response.bodyBytes);

      print('Archivo guardado en: ${file.path}');

      // Mostrar mensaje de éxito al usuario
      // ScaffoldMessenger o similar

    } else {
      throw Exception('Error del servidor: ${response.statusCode}');
    }

  } catch (e) {
    print('Error al exportar: $e');
    throw Exception('Error de conexión: $e');
  }
}
```

### Opción 2: Si estás en Flutter Web

Si tu app de Flutter está corriendo en web, NO puedes usar `dart:io`. Usa esto en su lugar:

```dart
import 'package:http/http.dart' as http;
import 'dart:html' as html; // Solo para web
import 'package:flutter/foundation.dart' show kIsWeb;

Future<void> exportarDatosWeb(String token) async {
  try {
    final url = Uri.parse('http://localhost:53237/api/exportar-datos-usuario/');

    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/zip',
      },
    );

    if (response.statusCode == 200) {
      if (kIsWeb) {
        // Para Flutter Web - descargar directamente en el navegador
        final blob = html.Blob([response.bodyBytes]);
        final url = html.Url.createObjectUrlFromBlob(blob);
        final anchor = html.AnchorElement(href: url)
          ..setAttribute('download', 'backup.zip')
          ..click();
        html.Url.revokeObjectUrl(url);
      } else {
        // Para móvil - guardar en sistema de archivos
        // ... código anterior con path_provider
      }

    } else {
      throw Exception('Error del servidor: ${response.statusCode}');
    }

  } catch (e) {
    print('Error al exportar: $e');
    throw Exception('Error de conexión: $e');
  }
}
```

### Opción 3: Código multiplataforma (Recomendado)

```dart
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io' if (dart.library.html) 'dart:html' as io;
import 'package:path_provider/path_provider.dart';

Future<void> exportarDatos(String token) async {
  try {
    final url = Uri.parse('http://localhost:53237/api/exportar-datos-usuario/');

    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/zip',
      },
    );

    if (response.statusCode == 200) {
      final filename = _extractFilename(response.headers['content-disposition']);

      if (kIsWeb) {
        _downloadForWeb(response.bodyBytes, filename);
      } else {
        await _downloadForMobile(response.bodyBytes, filename);
      }

      return;
    } else {
      final errorBody = utf8.decode(response.bodyBytes);
      throw Exception('Error del servidor: $errorBody');
    }

  } catch (e) {
    print('Error al exportar: $e');
    rethrow;
  }
}

String _extractFilename(String? contentDisposition) {
  if (contentDisposition == null) return 'backup.zip';

  final regex = RegExp(r'filename="([^"]+)"');
  final match = regex.firstMatch(contentDisposition);
  return match?.group(1) ?? 'backup.zip';
}

void _downloadForWeb(List<int> bytes, String filename) {
  // Este código solo se ejecuta en web
  if (kIsWeb) {
    import 'dart:html' as html;

    final blob = html.Blob([bytes]);
    final url = html.Url.createObjectUrlFromBlob(blob);
    final anchor = html.AnchorElement(href: url)
      ..setAttribute('download', filename)
      ..click();
    html.Url.revokeObjectUrl(url);
  }
}

Future<void> _downloadForMobile(List<int> bytes, String filename) async {
  if (!kIsWeb) {
    import 'dart:io';

    final directory = await getApplicationDocumentsDirectory();
    final file = File('${directory.path}/$filename');
    await file.writeAsBytes(bytes);

    print('Archivo guardado en: ${file.path}');
  }
}
```

## Dependencias Requeridas en pubspec.yaml

```yaml
dependencies:
  http: ^1.1.0
  path_provider: ^2.1.1  # Solo para móvil
  # Si usas dio en lugar de http:
  # dio: ^5.3.3
```

## Verificación del Backend

El backend Django ya está configurado correctamente con:
- ✅ CORS habilitado para todos los orígenes (desarrollo)
- ✅ Headers CORS apropiados expuestos
- ✅ Content-Type: application/zip
- ✅ Content-Disposition con nombre de archivo
- ✅ Content-Length incluido

## Cómo Reiniciar el Servidor Django

Después de los cambios realizados, reinicia el servidor:

```bash
# Detén el servidor actual (Ctrl+C)
# Luego ejecuta:
cd sistema_actas
python manage.py runserver 53237
```

## Prueba desde Flutter

1. Asegúrate de que el servidor Django está corriendo
2. Verifica que la URL sea correcta: `http://localhost:53237/api/exportar-datos-usuario/`
3. Asegúrate de enviar el token correcto en el header Authorization
4. Captura y muestra los errores apropiadamente

## Ejemplo de Manejo de Errores

```dart
try {
  await exportarDatos(token);

  // Mostrar mensaje de éxito
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('Datos exportados exitosamente'),
      backgroundColor: Colors.green,
    ),
  );

} catch (e) {
  // Mostrar mensaje de error
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('Error al exportar: ${e.toString()}'),
      backgroundColor: Colors.red,
    ),
  );
}
```

## Notas Importantes

1. **Para Producción**: Cambia `CORS_ALLOW_ALL_ORIGINS = True` a una lista específica de orígenes permitidos
2. **Token de Autenticación**: El sistema actual usa tokens simples. Considera implementar JWT para mayor seguridad
3. **Tamaño de Archivos**: El límite actual es 5MB, puedes ajustarlo en settings.py si es necesario

## Debugging

Si sigues teniendo problemas, agrega logs en Flutter:

```dart
print('URL: $url');
print('Headers: ${response.headers}');
print('Status: ${response.statusCode}');
print('Body length: ${response.bodyBytes.length}');
```
