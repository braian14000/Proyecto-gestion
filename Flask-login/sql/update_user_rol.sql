-- Script para actualizar la tabla user existente y agregar la columna rol
-- Ejecutar esto si la tabla user ya existe sin la columna rol

ALTER TABLE `user` 
ADD COLUMN `rol` ENUM('estudiante', 'organizador', 'admin') NOT NULL DEFAULT 'estudiante' 
AFTER `dni`;

-- Opcional: Convertir el admin existente (si existe) a admin
UPDATE `user` SET `rol` = 'admin' WHERE `email` = 'admin' OR `username` = 'admin';
