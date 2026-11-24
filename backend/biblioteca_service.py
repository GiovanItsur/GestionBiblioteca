from backend.ConexionBD import get_connection
from backend.Seguridad import (
    SesionUsuario,
    PermisoDenegadoError,
    hash_password,
    iniciar_sesion,
    verificar_rol,
)

def normalizar_codigo_barras(codigo: str) -> str:
    #Limpia espacios y recorta sufijo EAN-5 si el lector lo pega al EAN-13.
    #Es es el formaato que utilizan los codigo de barras de los libros, eso lo tuve que investigar porque me confundió un monton
    limpio = codigo.strip()
    if len(limpio) == 18 and limpio.isdigit() and limpio.startswith(("978", "979")):
        return limpio[:13]
    return limpio


class BibliotecaService:
    def __init__(self, sesion: SesionUsuario):
        self.sesion = sesion


    # Es este apartado se realizan las operaciones las cuales se definieron como los procedimientos almacenados
    def consultar_por_codigo_barras(self, codigo_barras: str) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        codigo = normalizar_codigo_barras(codigo_barras)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                args = cur.callproc("sp_consultar_ejemplar_por_codigo", [codigo, 0])
                disponible = bool(args[1])

                detalle = None
                for result in cur.stored_results():
                    row = result.fetchone()
                    if row:
                        detalle = dict(zip(result.column_names, row))

                return {
                    "encontrado": detalle is not None,
                    "disponible": disponible,
                    "ejemplar": detalle,
                }
        finally:
            conn.close()

    def registrar_prestamo(self, codigo_barras: str, matricula_lector: str, dias: int = 7) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        codigo = normalizar_codigo_barras(codigo_barras)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                args = cur.callproc(
                    "sp_registrar_prestamo",
                    [codigo, matricula_lector.strip(), self.sesion.id_usuario, dias, 0, ""],
                )
                return {
                    "exito": args[4] is not None,
                    "id_prestamo": args[4],
                    "mensaje": args[5],
                }
        finally:
            conn.close()

    def registrar_devolucion(self, codigo_barras: str, observaciones: str = "") -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        codigo = normalizar_codigo_barras(codigo_barras)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                args = cur.callproc(
                    "sp_registrar_devolucion",
                    [codigo, observaciones.strip(), 0, ""],
                )
                exito = not str(args[3]).startswith("Transacción cancelada")
                return {
                    "exito": exito,
                    "dias_retraso": args[2],
                    "mensaje": args[3],
                }
        finally:
            conn.close()

    def registrar_libro_y_ejemplar(
            self,
            isbn: str,
            titulo: str,
            id_autor: int,
            id_categoria: int,
            editorial: str,
            anio: int,
            codigo_barras: str,
            ubicacion: str,
    ) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        codigo = normalizar_codigo_barras(codigo_barras)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                args = cur.callproc(
                    "sp_registrar_ejemplar_completo",
                    [
                        isbn.strip(),
                        titulo.strip(),
                        id_autor,
                        id_categoria,
                        editorial.strip(),
                        anio,
                        codigo,
                        ubicacion.strip(),
                        0,
                        "",
                    ],
                )
                return {
                    "exito": args[8] is not None,
                    "id_ejemplar": args[8],
                    "mensaje": args[9],
                }
        finally:
            conn.close()

# En este apartado se realizan los CRUD y almacenan como el catalogo de los libros que se van a registrar o con lo que se van a trabajar

    def listar_libros(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT l.id_libro, l.isbn, l.titulo, a.nombre_completo AS autor,
                           c.nombre AS categoria, l.editorial, l.anio_publicacion,
                           fn_contar_ejemplares_disponibles(l.id_libro) AS disponibles
                    FROM libros l
                    INNER JOIN autores a ON l.id_autor = a.id_autor
                    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
                    ORDER BY l.titulo ASC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()

    def listar_ejemplares(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT e.id_ejemplar, e.codigo_barras, l.titulo, e.ubicacion, e.estado, e.fecha_alta
                    FROM ejemplares e
                    INNER JOIN libros l ON e.id_libro = l.id_libro
                    ORDER BY e.id_ejemplar ASC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()

    def actualizar_ejemplar(self, id_ejemplar: int, ubicacion: str, estado: str) -> bool:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE ejemplares SET ubicacion = %s, estado = %s WHERE id_ejemplar = %s",
                    (ubicacion.strip(), estado, id_ejemplar),
                )
                return cur.rowcount > 0
        finally:
            conn.close()

    def eliminar_ejemplar(self, id_ejemplar: int) -> bool:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ejemplares WHERE id_ejemplar = %s", (id_ejemplar,))
                return cur.rowcount > 0
        finally:
            conn.close()

    def listar_autores(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM autores ORDER BY nombre_completo ASC")
                return cur.fetchall()
        finally:
            conn.close()

    def crear_autor(self, nombre_completo: str) -> int:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO autores (nombre_completo) VALUES (%s)", (nombre_completo.strip(),))
                return cur.lastrowid
        finally:
            conn.close()

    def listar_categorias(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM categorias ORDER BY nombre ASC")
                return cur.fetchall()
        finally:
            conn.close()

    def crear_categoria(self, nombre: str) -> int:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre.strip(),))
                return cur.lastrowid
        finally:
            conn.close()

    #En ese siguiente apartado se realizan el listado y los CRUD correspondientes de los usuarios

    def listar_usuarios(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    "SELECT id_usuario, nombre_completo, username, rol, activo, fecha_creacion FROM usuarios ORDER BY id_usuario ASC"
                )
                return cur.fetchall()
        finally:
            conn.close()

    def crear_usuario(self, nombre_completo: str, username: str, password: str, rol: str) -> int:
        verificar_rol(self.sesion, ("ADMIN",))
        pw_hash = hash_password(password)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuarios (nombre_completo, username, password_hash, rol, activo)
                    VALUES (%s, %s, %s, %s, 1)
                    """,
                    (nombre_completo.strip(), username.strip(), pw_hash, rol),
                )
                return cur.lastrowid
        finally:
            conn.close()

    def cambiar_estado_usuario(self, id_usuario: int, activo: bool) -> bool:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE usuarios SET activo = %s WHERE id_usuario = %s", (int(activo), id_usuario))
                return cur.rowcount > 0
        finally:
            conn.close()


    #Auditorias de ciertas cosxas importantes a anotar


    def reporte_libros_mas_solicitados(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM vw_reporte_libros_mas_solicitados")
                return cur.fetchall()
        finally:
            conn.close()

    def reporte_lectores_vencidos(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM vw_reporte_lectores_vencidos")
                return cur.fetchall()
        finally:
            conn.close()

    def consultar_auditoria(self, limite: int = 30) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM auditoria ORDER BY fecha_hora DESC LIMIT %s", (limite,))
                return cur.fetchall()
        finally:
            conn.close()

# ======================================================================
# PRUEBA RÁPIDA EN CONSOLA (Para probar con tu lector de barras físico)
# ======================================================================

# NO le hagas caso a esto es una prueba en consola que hice para verificar que todo si funcionara correctamente y que si se pudiera ver
"""if __name__ == "__main__":
    print("=== PRUEBA BACKEND BIBLIOTECA ===")
    user = input("Usuario (admin / operador / consulta): ")
    pw = input("Contraseña: ")

    sesion = iniciar_sesion(user, pw)
    if not sesion:
        print("Credenciales inválidas o cuenta inactiva.")
        raise SystemExit

    print(f"\nBienvenido, {sesion.nombre_completo} [{sesion.rol}]")
    svc = BibliotecaService(sesion)

    while True:
        print("\n1. Consultar (escanear) | 2. Prestar | 3. Devolver | 4. Rep. Solicitados | 5. Rep. Vencidos | 6. Auditoría | 0. Salir")
        op = input("Opción: ").strip()
        try:
            if op == "1":
                print(svc.consultar_por_codigo_barras(input("Escanea código de barras: ")))
            elif op == "2":
                cod = input("Escanea código de barras: ")
                mat = input("Matrícula (ej. ISC2026001): ")
                print(svc.registrar_prestamo(cod, mat))
            elif op == "3":
                cod = input("Escanea código de barras: ")
                obs = input("Observaciones (opcional): ")
                print(svc.registrar_devolucion(cod, obs))
            elif op == "4":
                for fila in svc.reporte_libros_mas_solicitados():
                    print(" ", fila)
            elif op == "5":
                for fila in svc.reporte_lectores_vencidos():
                    print(" ", fila)
            elif op == "6":
                for fila in svc.consultar_auditoria():
                    print(" ", fila)
            elif op == "0":
                break
        except PermisoDenegadoError as e:
            print(f"[SEGURIDAD] {e}")
        except Exception as e:
            print(f"[ERROR] {e}")"""