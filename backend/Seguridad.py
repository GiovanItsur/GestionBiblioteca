from dataclasses import dataclass
import hashlib
import hmac
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
    """Genera el hash SHA-256 compatible 100% con SHA2(texto, 256) de MySQL."""
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Compara el hash generado con el guardado en la base de datos."""
    calculated_hash = hash_password(plain_password)
    return hmac.compare_digest(calculated_hash, stored_hash)


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