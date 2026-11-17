-- 000_esquema_base.sql
-- Esquema base de la aplicación y catálogos iniciales (roles, módulos y permisos).
-- Debe ejecutarse ANTES de las migraciones 001 a 013, que lo van completando
-- (fechas de auditoría, vínculo acudiente-estudiante, notas en asistencia, etc.).
--
-- Reconstruido a partir del código de la API y de las migraciones; ver el LEEME
-- para comparar con tu base real. Es seguro ejecutarlo sobre una base que ya existe:
-- no modifica tablas ni datos que ya estén creados.

-- ============================================================================
-- TABLAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS rol (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(500),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS modulo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(500),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS modulo_rol (
    id SERIAL PRIMARY KEY,
    rol_id INTEGER NOT NULL REFERENCES rol(id),
    modulo_id INTEGER NOT NULL REFERENCES modulo(id),
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (rol_id, modulo_id)
);

CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    correo VARCHAR(254) NOT NULL CONSTRAINT usuario_correo_key UNIQUE,
    password TEXT NOT NULL,
    rol_id INTEGER NOT NULL REFERENCES rol(id),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS estudiante (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuario(id),
    codigo_estudiante VARCHAR(30) NOT NULL UNIQUE,
    grado VARCHAR(30) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS acudiente (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL CONSTRAINT acudiente_usuario_id_key UNIQUE REFERENCES usuario(id),
    documento VARCHAR(30) NOT NULL CONSTRAINT acudiente_documento_key UNIQUE,
    telefono VARCHAR(30) NOT NULL,
    parentesco VARCHAR(50),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS categoria_actividad (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS actividad (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    lugar VARCHAR(150) NOT NULL,
    cupo INTEGER NOT NULL CHECK (cupo >= 1),
    categoria_id INTEGER NOT NULL REFERENCES categoria_actividad(id),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS actividad_docente (
    id SERIAL PRIMARY KEY,
    actividad_id INTEGER NOT NULL REFERENCES actividad(id),
    docente_id INTEGER NOT NULL REFERENCES usuario(id),
    rol_en_actividad VARCHAR(100) DEFAULT 'Acompañante',
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (actividad_id, docente_id)
);

CREATE TABLE IF NOT EXISTS inscripcion (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES estudiante(id),
    actividad_id INTEGER NOT NULL REFERENCES actividad(id),
    fecha_inscripcion DATE NOT NULL DEFAULT CURRENT_DATE,
    estado BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (estudiante_id, actividad_id)
);

CREATE TABLE IF NOT EXISTS autorizacion (
    id SERIAL PRIMARY KEY,
    inscripcion_id INTEGER NOT NULL REFERENCES inscripcion(id),
    acudiente_id INTEGER NOT NULL REFERENCES acudiente(id),
    estado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_autorizacion DATE
);

CREATE TABLE IF NOT EXISTS asistencia (
    id SERIAL PRIMARY KEY,
    inscripcion_id INTEGER NOT NULL UNIQUE REFERENCES inscripcion(id),
    asistio BOOLEAN NOT NULL,
    observacion TEXT,
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS notificacion (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    titulo VARCHAR(150) NOT NULL,
    mensaje TEXT NOT NULL,
    actividad_id INTEGER REFERENCES actividad(id),
    fecha_envio TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    estado BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================================
-- CATÁLOGOS INICIALES (solo se insertan los que faltan; nunca se modifican)
-- ============================================================================

INSERT INTO rol (nombre, descripcion)
SELECT v.nombre, v.descripcion
FROM (VALUES
    ('Administrador', 'Administra usuarios, roles, permisos y la información del sistema.'),
    ('Coordinador', 'Gestiona actividades, categorías, inscripciones, autorizaciones y asistencia.'),
    ('Secretaria', 'Gestiona las cuentas y los registros de estudiantes y acudientes.'),
    ('Docente', 'Consulta sus actividades y estudiantes inscritos; registra asistencia y retroalimentación.'),
    ('Entrenador', 'Acompaña sus actividades y registra asistencia y retroalimentación.'),
    ('Estudiante', 'Consulta actividades, inscripciones y asistencia, y se inscribe en actividades.'),
    ('Acudiente', 'Consulta la información de sus acudidos y gestiona sus inscripciones y autorizaciones.'),
    ('Director', 'Consulta resúmenes institucionales de inscripciones, asistencia y autorizaciones.'),
    ('Bienestar', 'Hace seguimiento de estudiantes, participaciones y asistencia mediante resúmenes.'),
    ('Orientador', 'Hace seguimiento de estudiantes, participaciones y asistencia mediante resúmenes.')
) AS v(nombre, descripcion)
WHERE NOT EXISTS (
    SELECT 1 FROM rol r WHERE LOWER(TRIM(r.nombre)) = LOWER(TRIM(v.nombre))
);

INSERT INTO modulo (nombre, descripcion, estado)
SELECT v.nombre, v.descripcion, v.estado
FROM (VALUES
    ('Actividades', 'Catálogo y gestión de actividades extracurriculares.', TRUE),
    ('Acudientes', 'Registro de acudientes y vínculos con estudiantes.', TRUE),
    ('Analitica', 'Indicadores generales del portal.', TRUE),
    ('Asistencia', 'Registro y consulta de asistencia, notas y retroalimentación.', TRUE),
    ('Autorizaciones', 'Autorización digital de la participación de los estudiantes.', TRUE),
    ('Bienestar', 'Seguimiento de estudiantes y participación.', TRUE),
    ('Categorias', 'Categorías de las actividades.', TRUE),
    ('Estudiantes', 'Registro de estudiantes.', TRUE),
    ('Inscripciones', 'Inscripción de estudiantes en las actividades.', TRUE),
    ('Reportes', 'Reportes institucionales por actividad.', TRUE),
    ('Roles', 'Roles y permisos por módulo.', TRUE),
    ('Usuarios', 'Cuentas de acceso al portal.', TRUE),
    ('Administracion', 'Reservado para una versión futura.', FALSE),
    ('Auditoria', 'Reservado para una versión futura.', FALSE),
    ('Calendario', 'Reservado para una versión futura.', FALSE),
    ('Configuracion', 'Reservado para una versión futura.', FALSE),
    ('Cupos', 'Reservado para una versión futura.', FALSE),
    ('Eventos', 'Reservado para una versión futura.', FALSE),
    ('Notificaciones', 'Reservado: envío y consulta de avisos a los usuarios.', FALSE),
    ('Seguridad', 'Reservado para una versión futura.', FALSE)
) AS v(nombre, descripcion, estado)
WHERE NOT EXISTS (
    SELECT 1 FROM modulo m WHERE LOWER(TRIM(m.nombre)) = LOWER(TRIM(v.nombre))
);

-- Permisos por rol: 71 relaciones tomadas de la matriz de la base en uso.
-- Las migraciones 006 a 013 la dejan en su estado final.
INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, v.asignado
FROM (VALUES
    ('Acudiente', 'Actividades', TRUE),
    ('Acudiente', 'Asistencia', TRUE),
    ('Acudiente', 'Autorizaciones', TRUE),
    ('Acudiente', 'Inscripciones', TRUE),
    ('Acudiente', 'Notificaciones', FALSE),
    ('Administrador', 'Actividades', TRUE),
    ('Administrador', 'Acudientes', TRUE),
    ('Administrador', 'Administracion', FALSE),
    ('Administrador', 'Analitica', TRUE),
    ('Administrador', 'Asistencia', TRUE),
    ('Administrador', 'Auditoria', FALSE),
    ('Administrador', 'Autorizaciones', TRUE),
    ('Administrador', 'Bienestar', TRUE),
    ('Administrador', 'Calendario', FALSE),
    ('Administrador', 'Categorias', TRUE),
    ('Administrador', 'Configuracion', FALSE),
    ('Administrador', 'Cupos', FALSE),
    ('Administrador', 'Estudiantes', TRUE),
    ('Administrador', 'Eventos', FALSE),
    ('Administrador', 'Inscripciones', TRUE),
    ('Administrador', 'Notificaciones', FALSE),
    ('Administrador', 'Reportes', TRUE),
    ('Administrador', 'Roles', TRUE),
    ('Administrador', 'Seguridad', FALSE),
    ('Administrador', 'Usuarios', TRUE),
    ('Bienestar', 'Actividades', TRUE),
    ('Bienestar', 'Analitica', TRUE),
    ('Bienestar', 'Bienestar', TRUE),
    ('Bienestar', 'Inscripciones', FALSE),
    ('Bienestar', 'Notificaciones', FALSE),
    ('Coordinador', 'Actividades', TRUE),
    ('Coordinador', 'Analitica', TRUE),
    ('Coordinador', 'Asistencia', TRUE),
    ('Coordinador', 'Autorizaciones', TRUE),
    ('Coordinador', 'Calendario', FALSE),
    ('Coordinador', 'Categorias', TRUE),
    ('Coordinador', 'Eventos', FALSE),
    ('Coordinador', 'Inscripciones', TRUE),
    ('Coordinador', 'Notificaciones', FALSE),
    ('Coordinador', 'Reportes', TRUE),
    ('Director', 'Actividades', TRUE),
    ('Director', 'Analitica', TRUE),
    ('Director', 'Asistencia', FALSE),
    ('Director', 'Autorizaciones', FALSE),
    ('Director', 'Calendario', FALSE),
    ('Director', 'Eventos', FALSE),
    ('Director', 'Inscripciones', FALSE),
    ('Director', 'Notificaciones', FALSE),
    ('Director', 'Reportes', TRUE),
    ('Docente', 'Actividades', TRUE),
    ('Docente', 'Asistencia', TRUE),
    ('Docente', 'Inscripciones', TRUE),
    ('Docente', 'Notificaciones', FALSE),
    ('Entrenador', 'Actividades', TRUE),
    ('Entrenador', 'Asistencia', TRUE),
    ('Entrenador', 'Inscripciones', TRUE),
    ('Entrenador', 'Notificaciones', FALSE),
    ('Estudiante', 'Actividades', TRUE),
    ('Estudiante', 'Asistencia', TRUE),
    ('Estudiante', 'Inscripciones', TRUE),
    ('Estudiante', 'Notificaciones', FALSE),
    ('Orientador', 'Actividades', TRUE),
    ('Orientador', 'Analitica', TRUE),
    ('Orientador', 'Bienestar', TRUE),
    ('Orientador', 'Inscripciones', FALSE),
    ('Orientador', 'Notificaciones', FALSE),
    ('Secretaria', 'Actividades', TRUE),
    ('Secretaria', 'Acudientes', TRUE),
    ('Secretaria', 'Estudiantes', TRUE),
    ('Secretaria', 'Roles', FALSE),
    ('Secretaria', 'Usuarios', TRUE)
) AS v(rol, modulo, asignado)
JOIN rol r ON LOWER(TRIM(r.nombre)) = LOWER(TRIM(v.rol))
JOIN modulo m ON LOWER(TRIM(m.nombre)) = LOWER(TRIM(v.modulo))
WHERE NOT EXISTS (
    SELECT 1 FROM modulo_rol mr WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
);
