from backend.ConexionBD import get_connection
from backend.Seguridad import hash_password

USUARIOS_INICIALES = {
    "admin": "Admin123!",
    "operador": "Operador123!",
    "consulta": "Consulta123!",
}

def main():
    conn = get_connection("setup_passwords")
    try:
        with conn.cursor() as cur:
            for username, plain_pw in USUARIOS_INICIALES.items():
                cur.execute(
                    "UPDATE usuarios SET password_hash = %s WHERE username = %s",
                    (hash_password(plain_pw), username),
                )
        print("Contraseñas encriptadas con bcrypt actualizadas en Azure.")
        print("Credenciales listas -> admin / Admin123! | operador / Operador123! | consulta / Consulta123!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()