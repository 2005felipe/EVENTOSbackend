-- 014_correo_unico_sin_mayusculas.sql
-- El inicio de sesión compara LOWER(TRIM(correo)), pero la restricción única original
-- distingue mayúsculas: "Ana@x.com" y "ana@x.com" podían coexistir y el login elegía una al azar.
-- Esta migración normaliza los correos y crea un índice único sobre el correo normalizado.
-- Es idempotente. Si ya existen correos repetidos (ignorando mayúsculas) NO falla ni borra nada:
-- avisa con un NOTICE para que los corrijas a mano y vuelvas a ejecutarla.

DO $$
DECLARE
    duplicados INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicados FROM (
        SELECT 1 FROM usuario GROUP BY LOWER(TRIM(correo)) HAVING COUNT(*) > 1
    ) d;

    IF duplicados > 0 THEN
        RAISE NOTICE 'Hay % correos repetidos al ignorar mayúsculas/espacios. Corrígelos y vuelve a ejecutar esta migración. Consulta: SELECT LOWER(TRIM(correo)), array_agg(id) FROM usuario GROUP BY 1 HAVING COUNT(*) > 1;', duplicados;
    ELSE
        UPDATE usuario SET correo = LOWER(TRIM(correo)) WHERE correo <> LOWER(TRIM(correo));
        CREATE UNIQUE INDEX IF NOT EXISTS usuario_correo_normalizado_key ON usuario (LOWER(TRIM(correo)));
    END IF;
END $$;
