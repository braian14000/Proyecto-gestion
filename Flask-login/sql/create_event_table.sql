-- Crea la base de datos (si no existe) y las tablas `user` y `event`
CREATE DATABASE IF NOT EXISTS flask_login
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE flask_login;

CREATE TABLE IF NOT EXISTS `user` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(100) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `telefono` VARCHAR(30) DEFAULT NULL,
  `email` VARCHAR(150) NOT NULL,
  `dni` VARCHAR(30) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_email` (`email`),
  UNIQUE KEY `uq_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `event` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `titulo` VARCHAR(200) NOT NULL,
  `fecha` DATE NOT NULL,
  `descripcion` TEXT,
  `lugar` VARCHAR(200),
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `registrados` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `evento_id` INT UNSIGNED NOT NULL,
  `dni_usuario` VARCHAR(30) NOT NULL,
  `nombre_usuario` VARCHAR(150) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_registrados_evento_dni` (`evento_id`, `dni_usuario`),
  CONSTRAINT `fk_registrados_evento` FOREIGN KEY (`evento_id`) REFERENCES `event` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `event` (titulo, fecha, descripcion, lugar) VALUES
('Concierto de Rock', '2026-07-15', 'Una noche increíble con las mejores bandas locales.', 'Estadio Principal');
