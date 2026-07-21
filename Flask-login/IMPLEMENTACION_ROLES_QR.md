# Implementación: Sistema de Roles y Validación de QR

## ¿Qué se ha implementado?

Este sistema permite que los administradores gestionen **organizadores de eventos** y que estos puedan validar la entrada de usuarios mediante escaneo de códigos QR o búsqueda por DNI.

### Nuevas Funcionalidades:

1. **Sistema de Roles**
   - **Usuario**: Puede registrarse a eventos e ver sus inscripciones
   - **Organizador**: Además de Usuario, puede validar entradas mediante QR/DNI
   - **Admin**: Controla todo including crear eventos y convertir usuarios en organizadores

2. **Panel de Gestión de Organizadores** (`/admin/organizadores`)
   - Solo accesible por Admin
   - Ver lista de todos los usuarios
   - Convertir usuarios a "Organizador" con un clic
   - Cambiar roles fácilmente

3. **Validación de QR en Eventos** (`/evento/{evento_id}/validar-qr`)
   - Solo accesible por Organizadores y Admin
   - **Escaneo por cámara**: Usa la cámara del dispositivo para leer códigos QR
   - **Validación por DNI**: Buscar usuarios ingresando su DNI manualmente
   - Mensajes de éxito/error en tiempo real
   - API backend (`/api/validar-qr-entrada`) que verifica si el usuario está registrado

---

## Instalación y Configuración

### 1. Actualizar la Base de Datos

Si ya tienes una base de datos existente, ejecuta el script de migración:

```bash
mysql -u root -p flask_login < sql/update_user_rol.sql
```

**O** si es la primera instalación, usa:

```bash
mysql -u root -p flask_login < sql/create_event_table.sql
```

### 2. Cambios en la estructura de carpetas

Se han agregado dos nuevas plantillas:
- `templates/admin_organizadores.html` - Panel de gestión de organizadores
- `templates/validar_qr.html` - Página de validación de QR

### 3. Archivos modificados

**Modelos:**
- `models/entities/users.py` - Agregado campo `rol` y métodos `is_admin()`, `is_organizador()`
- `models/ModeUsers.py` - Métodos actualizados para manejar roles + nuevos métodos `get_all_users()` y `update_rol()`

**Backend:**
- `app.py` - Nuevas rutas:
  - `GET /admin/organizadores` - Panel de gestión
  - `POST /admin/organizadores` - Actualizar rol de usuario
  - `GET /evento/<id>/validar-qr` - Página de validación
  - `POST /api/validar-qr-entrada` - API para validar entrada

**Frontend:**
- `templates/menu.html` - Agregados menús para Organizador y Admin
- `templates/eventos.html` - Botón "Validar QR" para organizadores
- `templates/admin.html` - Enlace a gestión de organizadores

---

## Cómo Usar

### Como Administrador:

1. Inicia sesión como admin (usuario: `admin`, contraseña: `admin`)
2. En el menú, selecciona "👥 Gestionar Organizadores"
3. Busca el usuario que quieres convertir en organizador
4. Haz clic en "Hacer Organizador"

### Como Organizador:

1. El administrador te ha convertido en organizador
2. Cuando veas la lista de eventos, verás un botón **"Validar QR 🔓"**
3. Al hacer clic, puedes:
   - **Escanear QR**: 
     - Haz clic en "📷 Iniciar Cámara"
     - Apunta el código QR hacia la cámara
     - El sistema validará automáticamente
   - **Buscar por DNI**:
     - Ingresa el DNI del usuario en el campo
     - Haz clic en "🔍 Validar por DNI"

4. El sistema mostrará:
   - ✓ **Verde**: Usuario registrado, puede ingresar
   - ✗ **Rojo**: Usuario no registrado, no puede ingresar

---

## Flujo Técnico

### Validación de QR

1. El código QR contiene: `Evento:ID|DNI:xxx|Nombre:xxx|Registro:ID`
2. El JavaScript en el navegador usa `jsQR` para decodificar
3. Se envía al servidor mediante POST a `/api/validar-qr-entrada`
4. El servidor verifica en la tabla `registrados`:
   - Si evento_id y dni_usuario coinciden
   - Si existe, devuelve éxito + nombre del usuario
   - Si no existe, devuelve error

### Validación por DNI

1. Se ingresa el DNI manualmente
2. Se envía al servidor mediante POST a `/api/validar-qr-entrada`
3. El servidor busca en `registrados` por evento_id + dni
4. Mismo flujo que la validación QR

---

## Estructura de la tabla `user` (actualizada)

```sql
CREATE TABLE `user` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(100) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `telefono` VARCHAR(30) DEFAULT NULL,
  `email` VARCHAR(150) NOT NULL,
  `dni` VARCHAR(30) DEFAULT NULL,
  `rol` ENUM('usuario', 'organizador', 'admin') NOT NULL DEFAULT 'usuario',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;
```

---

## Seguridad

- Solo Admin puede acceder a `/admin/organizadores`
- Solo Organizador/Admin puede acceder a `/evento/<id>/validar-qr`
- La API `/api/validar-qr-entrada` verifica autenticación y rol
- Los códigos QR contienen validación de evento_id para evitar fraudes

---

## Próximas Mejoras (Opcional)

- [ ] Registrar log de entradas validadas
- [ ] Sistema de confirmación de entrada (marcar como ingresado)
- [ ] Reportes de asistencia
- [ ] Notificaciones cuando se valida entrada
- [ ] Exportar lista de asistentes en PDF/Excel

---

## Contacto / Soporte

Si encuentras problemas:
1. Verifica que la BD esté actualizada con los cambios de `rol`
2. Asegúrate de tener los templates nuevos en `templates/`
3. Revisa los logs de Flask para errores específicos
