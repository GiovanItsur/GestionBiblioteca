from dataclasses import dataclass
import bcrypt
from backend.ConexionBD import get_connection

@dataclass
class SesionUsuario:
    id_usuario: int
    nombre_completo: str
    username: str
    rol: str  # 'ADMIN', 'OPERADOR', 'CONSULTA'

class PermisoDenegadoError(PermissionError):
    pass


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def iniciar_sesion(username: str, password: str) -> SesionUsuario | None:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT id_usuario, nombre_completo, username, password_hash, rol, activo
                FROM usuarios
                WHERE username = %s
                """,
                (username.strip(),),
            )
            user = cur.fetchone()
            if not user or not user["activo"]:
                return None

            if verify_password(password, user["password_hash"]):
                return SesionUsuario(
                    id_usuario=user["id_usuario"],
                    nombre_completo=user["nombre_completo"],
                    username=user["username"],
                    rol=user["rol"],
                )
            return None
    finally:
        conn.close()


def verificar_rol(sesion: SesionUsuario, roles_permitidos: tuple[str, ...]):
    if sesion.rol not in roles_permitidos:
        raise PermisoDenegadoError(
            f"Acceso denegado: el rol '{sesion.rol}' no tiene permisos para esta operación."
        )

