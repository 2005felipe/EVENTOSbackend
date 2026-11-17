"""Muestra qué correos existen para cada rol, para probar el portal sin buscarlos a mano.

Solo lee la base de datos: no muestra ni cambia contraseñas.
Uso (desde la carpeta del backend, con el entorno virtual activo):
    python listar_cuentas_por_rol.py
"""

from dotenv import load_dotenv

from app.core.database import Database

POR_ROL = 2  # cuántas cuentas activas mostrar por rol


def main() -> int:
    load_dotenv()
    conn = Database().get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.nombre AS rol, u.nombre, u.correo, u.estado
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE r.estado IS TRUE
                ORDER BY r.nombre, u.estado DESC, u.id;
                """
            )
            filas = cursor.fetchall()
    finally:
        conn.close()

    if not filas:
        print("No hay cuentas registradas.")
        return 1

    mostrados: dict[str, int] = {}
    print(f"{'ROL':<16} {'CORREO':<44} NOMBRE")
    print("-" * 90)
    for fila in filas:
        if not fila["estado"]:
            continue
        rol = fila["rol"]
        if mostrados.get(rol, 0) >= POR_ROL:
            continue
        mostrados[rol] = mostrados.get(rol, 0) + 1
        print(f"{rol:<16} {fila['correo']:<44} {fila['nombre']}")

    sin_cuenta = sorted({fila["rol"] for fila in filas} - set(mostrados))
    if sin_cuenta:
        print("\nRoles sin cuentas activas:", ", ".join(sin_cuenta))
    print("\nLa contraseña es la que definiste con asignar_clave_general.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
