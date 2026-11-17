-- Deja la matriz de permisos en su estado final y la vuelve reproducible.
--  1) La migración 009 volvió a encender módulos que la 008 había apagado.
--     Mientras no se usen, Notificaciones y los demás quedan apagados.
--  2) El Estudiante consulta (solo lectura) el estado de sus autorizaciones,
--     como ya preveía la migración 010.
--  3) Secretaría deja de ver el catálogo de actividades (no forma parte de su trabajo).
-- Es idempotente: se puede ejecutar más de una vez sin efectos adicionales.

-- 1) Módulos sin uso por ahora: apagados para todos los roles.
UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM modulo m
WHERE mr.modulo_id = m.id
  AND LOWER(TRIM(m.nombre)) IN (
      'administracion', 'auditoria', 'calendario', 'configuracion',
      'cupos', 'eventos', 'notificaciones', 'seguridad'
  )
  AND mr.estado IS TRUE;

UPDATE modulo m
SET estado = FALSE,
    actualizado = statement_timestamp()
WHERE LOWER(TRIM(m.nombre)) IN (
    'administracion', 'auditoria', 'calendario', 'configuracion',
    'cupos', 'eventos', 'notificaciones', 'seguridad'
)
AND m.estado IS TRUE;

-- 2) El Estudiante ve sus propias autorizaciones (la API filtra por su sesión).
UPDATE modulo_rol mr
SET estado = TRUE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'autorizaciones'
  AND mr.estado IS DISTINCT FROM TRUE;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE r.estado IS TRUE
  AND m.estado IS TRUE
  AND LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'autorizaciones'
  AND NOT EXISTS (
      SELECT 1 FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );

-- 3) Secretaría gestiona cuentas, estudiantes y acudientes; no necesita el catálogo de actividades.
UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'secretaria'
  AND LOWER(TRIM(m.nombre)) = 'actividades'
  AND mr.estado IS TRUE;
