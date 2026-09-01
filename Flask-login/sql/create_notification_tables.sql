-- Tabla para almacenar mensajes de contacto al organizador
CREATE TABLE IF NOT EXISTS `mensajes_organizador` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `organizador_id` INT UNSIGNED NOT NULL,
  `remitente_id` INT UNSIGNED NULL,
  `evento_id` INT UNSIGNED NOT NULL,
  `asunto` VARCHAR(255) NOT NULL,
  `mensaje` TEXT NOT NULL,
  `leido` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_organizador` (`organizador_id`),
  KEY `idx_evento` (`evento_id`),
  KEY `idx_remitente` (`remitente_id`),
  KEY `idx_leido` (`leido`),
  CONSTRAINT fk_mensajes_organizador FOREIGN KEY (`organizador_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
  CONSTRAINT fk_mensajes_remitente FOREIGN KEY (`remitente_id`) REFERENCES `user`(`id`) ON DELETE SET NULL,
  CONSTRAINT fk_mensajes_evento FOREIGN KEY (`evento_id`) REFERENCES `event`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla para respuestas del organizador a los mensajes
CREATE TABLE IF NOT EXISTS `respuestas_organizador` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `mensaje_id` INT UNSIGNED NOT NULL,
  `organizador_id` INT UNSIGNED NOT NULL,
  `destinatario_id` INT UNSIGNED NULL,
  `autor_id` INT UNSIGNED NULL,
  `respuesta` TEXT NOT NULL,
  `leido_destinatario` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_mensaje` (`mensaje_id`),
  KEY `idx_organizador` (`organizador_id`),
  KEY `idx_destinatario` (`destinatario_id`),
  KEY `idx_autor` (`autor_id`),
  CONSTRAINT fk_respuestas_mensaje FOREIGN KEY (`mensaje_id`) REFERENCES `mensajes_organizador`(`id`) ON DELETE CASCADE,
  CONSTRAINT fk_respuestas_organizador FOREIGN KEY (`organizador_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
  CONSTRAINT fk_respuestas_destinatario FOREIGN KEY (`destinatario_id`) REFERENCES `user`(`id`) ON DELETE SET NULL,
  CONSTRAINT fk_respuestas_autor FOREIGN KEY (`autor_id`) REFERENCES `user`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla para gestionar seguidores de usuarios (organizadores)
CREATE TABLE IF NOT EXISTS `seguidores` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `seguidor_id` INT UNSIGNED NOT NULL,
  `seguido_id` INT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_seguidor` (`seguidor_id`, `seguido_id`),
  KEY `idx_seguidor` (`seguidor_id`),
  KEY `idx_seguido` (`seguido_id`),
  CONSTRAINT fk_seguidores_seguidor FOREIGN KEY (`seguidor_id`) REFERENCES `user`(`id`) ON DELETE CASCADE,
  CONSTRAINT fk_seguidores_seguido FOREIGN KEY (`seguido_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agregar columna de foto de perfil a tabla user (si no existe)
-- Si la tabla user ya existe, estas columnas las agrega automáticamente la aplicación.
