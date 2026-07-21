-- INSTRUCCIONES CRÍTICAS DE ACTUALIZACIÓN

-- Si la tabla `user` YA EXISTE SIN la columna `rol`, ejecuta PRIMERO esto:
ALTER TABLE `user` 
ADD COLUMN `rol` ENUM('estudiante', 'organizador', 'admin') NOT NULL DEFAULT 'estudiante' 
AFTER `dni`;

-- Luego, asegúrate que el admin tenga rol 'admin':
UPDATE `user` SET `rol` = 'admin' WHERE `email` = 'admin' OR `username` = 'admin';

-- Si estás creando la BD desde cero, la tabla usuarios_registrados.yml ya incluye esta columna.

-- Verificar que los datos se actualizaron correctamente:
SELECT id, username, email, rol FROM `user` LIMIT 10;

-- El admin debe tener rol='admin':
SELECT * FROM `user` WHERE email='admin' OR username='admin';
