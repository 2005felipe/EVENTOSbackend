INSERT INTO modulo (nombre, descripcion, estado)
SELECT 'Tablero', 'Tablero con indicadores y gráficos de inscripciones.', TRUE
WHERE NOT EXISTS (SELECT 1 FROM modulo WHERE LOWER(nombre) = 'tablero');

UPDATE modulo SET estado = TRUE WHERE LOWER(nombre) = 'tablero' AND CAST(estado AS INTEGER) IS DISTINCT FROM 1;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r CROSS JOIN modulo m
WHERE (
    LOWER(r.nombre) = 'administrador'
    OR LOWER(r.nombre) = 'coordinador'
    OR LOWER(r.nombre) = 'director'
  )
  AND r.estado = 1
  AND LOWER(m.nombre) = 'tablero'
  AND NOT EXISTS (SELECT 1 FROM modulo_rol mr WHERE mr.rol_id = r.id AND mr.modulo_id = m.id);

UPDATE modulo_rol
SET estado = TRUE
FROM rol r, modulo m
WHERE modulo_rol.rol_id = r.id
  AND modulo_rol.modulo_id = m.id
  AND (
      LOWER(r.nombre) = 'administrador'
      OR LOWER(r.nombre) = 'coordinador'
      OR LOWER(r.nombre) = 'director'
    )
  AND LOWER(m.nombre) = 'tablero'
  AND CAST(modulo_rol.estado AS INTEGER) IS DISTINCT FROM 1;

  