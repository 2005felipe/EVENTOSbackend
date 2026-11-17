"""Crea la primera cuenta de Administrador en una base de datos nueva.

Úsalo una sola vez, después de ejecutar las migraciones 000 a 014 (la base nueva no tiene usuarios,
y sin uno no se puede iniciar sesión). Desde la carpeta del backend, con el entorno virtual activo:
    python crear_administrador_inicial.py
La contraseña se pide por teclado y se guarda cifrada; nunca queda escrita en el código.
"""

from getpass import getpass
import sys

from dotenv import load_dotenv

from app.core.database import Database
from app.core.passwords import hash_password


def main() -> int:
    load_dotenv()
    nombre = input("Nombre completo del administrador: ").strip()
    correo = input("Correo electrónico: ").strip().lower()
    password = getpass("Contraseña (8 a 128 caracteres): ")
    if getpass("Confirma la contraseña: ") != password:
        print("Las contraseñas no coinciden. No se creó nada.", file=sys.stderr)
        return 1
    if not nombre or "@" not in correo or not 8 <= len(password) <= 128:
        print("Revisa los datos: nombre, correo válido y contraseña de 8 a 128 caracteres.", file=sys.stderr)
        return 1

    conn = Database().get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM rol WHERE LOWER(TRIM(nombre)) = 'administrador' AND estado IS TRUE;")
            rol = cursor.fetchone()
            if rol is None:
                print("No existe el rol Administrador. Ejecuta antes 000_esquema_base.sql.", file=sys.stderr)
                return 1
            cursor.execute("SELECT 1 FROM usuario WHERE LOWER(TRIM(correo)) = %s;", (correo,))
            if cursor.fetchone() is not None:
                print("Ese correo ya está registrado. No se creó nada.", file=sys.stderr)
                return 1
            cursor.execute(
                "INSERT INTO usuario (nombre, correo, password, rol_id, estado) VALUES (%s, %s, %s, %s, TRUE) RETURNING id;",
                (nombre, correo, hash_password(password), rol["id"]),
            )
            cursor.fetchone()
        conn.commit()
        print(f"Administrador creado. Entra con {correo} y el perfil Administrador.")
        return 0
    except Exception as error:
        conn.rollback()
        print(f"No se pudo crear el administrador: {error}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
