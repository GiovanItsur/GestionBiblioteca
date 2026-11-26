import mysql.connector
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

    #Funciones para hacer el CRUD completo de los dos siendo libros y usuarios además de tener conceptos importantes en cuenta
    def crear_libro(
            self,
            isbn: str,
            titulo: str,
            id_autor: int,
            id_categoria: int,
            editorial: str,
            anio_publicacion: int,
    ) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO libros (isbn, titulo, id_autor, id_categoria, editorial, anio_publicacion)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (isbn.strip(), titulo.strip(), id_autor, id_categoria, editorial.strip(), anio_publicacion),
                )
                return {
                    "exito": True,
                    "id_libro": cur.lastrowid,
                    "mensaje": "Libro registrado correctamente.",
                }
        except mysql.connector.Error as e:
            if e.errno == 1062:
                return {"exito": False, "id_libro": None, "mensaje": "Ya existe un libro con ese ISBN."}
            if e.errno == 1452:
                return {"exito": False, "id_libro": None,
                        "mensaje": "El autor o la categoría seleccionada no existe."}
            if e.errno == 3819:
                return {"exito": False, "id_libro": None,
                        "mensaje": "El año de publicación debe estar entre 1450 y 2100."}
            return {"exito": False, "id_libro": None, "mensaje": f"Error al crear libro: {e.msg}"}
        finally:
            conn.close()

    def listar_libros(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT l.id_libro, l.isbn, l.titulo, l.id_autor, a.nombre_completo AS autor,
                           l.id_categoria, c.nombre AS categoria, l.editorial, l.anio_publicacion,
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

    def obtener_libro_por_id(self, id_libro: int) -> dict | None:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT l.id_libro, l.isbn, l.titulo, l.id_autor, a.nombre_completo AS autor,
                           l.id_categoria, c.nombre AS categoria, l.editorial, l.anio_publicacion,
                           fn_contar_ejemplares_disponibles(l.id_libro) AS disponibles
                    FROM libros l
                    INNER JOIN autores a ON l.id_autor = a.id_autor
                    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
                    WHERE l.id_libro = %s
                    """,
                    (id_libro,),
                )
                return cur.fetchone()
        finally:
            conn.close()

    def buscar_libros(self, termino: str) -> list[dict]:
        """Busca libros por título, ISBN o nombre del autor."""
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        patron = f"%{termino.strip()}%"
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT l.id_libro, l.isbn, l.titulo, l.id_autor, a.nombre_completo AS autor,
                           l.id_categoria, c.nombre AS categoria, l.editorial, l.anio_publicacion,
                           fn_contar_ejemplares_disponibles(l.id_libro) AS disponibles
                    FROM libros l
                    INNER JOIN autores a ON l.id_autor = a.id_autor
                    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
                    WHERE l.titulo LIKE %s OR l.isbn LIKE %s OR a.nombre_completo LIKE %s
                    ORDER BY l.titulo ASC
                    """,
                    (patron, patron, patron),
                )
                return cur.fetchall()
        finally:
            conn.close()

    def actualizar_libro(
            self,
            id_libro: int,
            isbn: str,
            titulo: str,
            id_autor: int,
            id_categoria: int,
            editorial: str,
            anio_publicacion: int,
    ) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE libros
                    SET isbn = %s,
                        titulo = %s,
                        id_autor = %s,
                        id_categoria = %s,
                        editorial = %s,
                        anio_publicacion = %s
                    WHERE id_libro = %s
                    """,
                    (isbn.strip(), titulo.strip(), id_autor, id_categoria, editorial.strip(), anio_publicacion,
                     id_libro),
                )
                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el libro o no hubo cambios."}
                return {"exito": True, "mensaje": "Libro actualizado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1062:
                return {"exito": False, "mensaje": "Ya existe otro libro con ese ISBN."}
            if e.errno == 1452:
                return {"exito": False, "mensaje": "El autor o la categoría seleccionada no existe."}
            if e.errno == 3819:
                return {"exito": False, "mensaje": "El año de publicación debe estar entre 1450 y 2100."}
            return {"exito": False, "mensaje": f"Error al actualizar libro: {e.msg}"}
        finally:
            conn.close()

    def eliminar_libro(self, id_libro: int) -> dict:
        """Solo ADMIN. Falla limpiamente si el libro aún tiene ejemplares registrados."""
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM libros WHERE id_libro = %s", (id_libro,))
                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el libro especificado."}
                return {"exito": True, "mensaje": "Libro eliminado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1451:
                return {
                    "exito": False,
                    "mensaje": "No se puede eliminar el libro porque tiene ejemplares asociados. Elimina primero sus ejemplares.",
                }
            return {"exito": False, "mensaje": f"Error al eliminar libro: {e.msg}"}
        finally:
            conn.close()

    # 3. CRUD COMPLETO DE USUARIOS DEL SISTEMA (Solo ADMIN)
    def crear_usuario(self, nombre_completo: str, username: str, password: str, rol: str) -> dict:
        verificar_rol(self.sesion, ("ADMIN",))
        rol = rol.strip().upper()
        if rol not in ("ADMIN", "OPERADOR", "CONSULTA"):
            return {"exito": False, "id_usuario": None, "mensaje": "Rol no válido. Usa ADMIN, OPERADOR o CONSULTA."}
        if not password or len(password) < 4:
            return {"exito": False, "id_usuario": None,
                    "mensaje": "La contraseña debe tener al menos 4 caracteres."}

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
                return {
                    "exito": True,
                    "id_usuario": cur.lastrowid,
                    "mensaje": "Usuario creado correctamente.",
                }
        except mysql.connector.Error as e:
            if e.errno == 1062:
                return {"exito": False, "id_usuario": None, "mensaje": "Ese nombre de usuario ya está en uso."}
            return {"exito": False, "id_usuario": None, "mensaje": f"Error al crear usuario: {e.msg}"}
        finally:
            conn.close()

    def listar_usuarios(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT id_usuario, nombre_completo, username, rol, activo, fecha_creacion
                    FROM usuarios
                    ORDER BY id_usuario ASC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()

    def obtener_usuario_por_id(self, id_usuario: int) -> dict | None:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT id_usuario, nombre_completo, username, rol, activo, fecha_creacion
                    FROM usuarios
                    WHERE id_usuario = %s
                    """,
                    (id_usuario,),
                )
                return cur.fetchone()
        finally:
            conn.close()

    def actualizar_usuario(
            self,
            id_usuario: int,
            nombre_completo: str,
            username: str,
            rol: str,
            activo: bool,
            nueva_password: str | None = None,
    ) -> dict:
        """Actualiza datos del usuario. Si nueva_password viene vacía o None, conserva la actual."""
        verificar_rol(self.sesion, ("ADMIN",))
        rol = rol.strip().upper()
        if rol not in ("ADMIN", "OPERADOR", "CONSULTA"):
            return {"exito": False, "mensaje": "Rol no válido. Usa ADMIN, OPERADOR o CONSULTA."}
        if id_usuario == self.sesion.id_usuario and not activo:
            return {"exito": False,
                    "mensaje": "No puedes desactivar tu propia cuenta mientras tienes sesión iniciada."}

        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                if nueva_password and nueva_password.strip():
                    pw_hash = hash_password(nueva_password)
                    cur.execute(
                        """
                        UPDATE usuarios
                        SET nombre_completo = %s,
                            username = %s,
                            password_hash = %s,
                            rol = %s,
                            activo = %s
                        WHERE id_usuario = %s
                        """,
                        (nombre_completo.strip(), username.strip(), pw_hash, rol, int(activo), id_usuario),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE usuarios
                        SET nombre_completo = %s,
                            username = %s,
                            rol = %s,
                            activo = %s
                        WHERE id_usuario = %s
                        """,
                        (nombre_completo.strip(), username.strip(), rol, int(activo), id_usuario),
                    )

                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el usuario o no hubo cambios."}
                return {"exito": True, "mensaje": "Usuario actualizado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1062:
                return {"exito": False, "mensaje": "Ese nombre de usuario ya pertenece a otra cuenta."}
            return {"exito": False, "mensaje": f"Error al actualizar usuario: {e.msg}"}
        finally:
            conn.close()

    def eliminar_usuario(self, id_usuario: int) -> dict:
        """Solo ADMIN. Impide borrarse a sí mismo y protege integridad si registró préstamos."""
        verificar_rol(self.sesion, ("ADMIN",))
        if id_usuario == self.sesion.id_usuario:
            return {"exito": False, "mensaje": "No puedes eliminar tu propio usuario con la sesión activa."}

        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el usuario especificado."}
                return {"exito": True, "mensaje": "Usuario eliminado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1451:
                return {
                    "exito": False,
                    "mensaje": "No se puede eliminar este usuario porque tiene préstamos registrados. Desactívalo en su lugar.",
                }
            return {"exito": False, "mensaje": f"Error al eliminar usuario: {e.msg}"}
        finally:
            conn.close()

    # 4. EJEMPLARES, AUTORES, CATEGORÍAS Y LECTORES
    def listar_ejemplares(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT e.id_ejemplar, e.id_libro, e.codigo_barras, l.titulo, e.ubicacion, e.estado, e.fecha_alta
                    FROM ejemplares e
                    INNER JOIN libros l ON e.id_libro = l.id_libro
                    ORDER BY e.id_ejemplar ASC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()

    def crear_ejemplar(self, id_libro: int, codigo_barras: str, ubicacion: str) -> dict:
        """Agrega una copia física escaneada a un libro ya existente."""
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        codigo = normalizar_codigo_barras(codigo_barras)
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ejemplares (id_libro, codigo_barras, ubicacion, estado) VALUES (%s, %s, %s, 'DISPONIBLE')",
                    (id_libro, codigo, ubicacion.strip()),
                )
                return {"exito": True, "id_ejemplar": cur.lastrowid,
                        "mensaje": "Ejemplar registrado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1062:
                return {"exito": False, "id_ejemplar": None, "mensaje": "Ese código de barras ya está registrado."}
            return {"exito": False, "id_ejemplar": None, "mensaje": f"Error al registrar ejemplar: {e.msg}"}
        finally:
            conn.close()

    def actualizar_ejemplar(self, id_ejemplar: int, ubicacion: str, estado: str) -> dict:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE ejemplares SET ubicacion = %s, estado = %s WHERE id_ejemplar = %s",
                    (ubicacion.strip(), estado.strip().upper(), id_ejemplar),
                )
                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el ejemplar o no hubo cambios."}
                return {"exito": True, "mensaje": "Ejemplar actualizado correctamente."}
        except mysql.connector.Error as e:
            return {"exito": False, "mensaje": f"Error al actualizar ejemplar: {e.msg}"}
        finally:
            conn.close()

    def eliminar_ejemplar(self, id_ejemplar: int) -> dict:
        verificar_rol(self.sesion, ("ADMIN",))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ejemplares WHERE id_ejemplar = %s", (id_ejemplar,))
                if cur.rowcount == 0:
                    return {"exito": False, "mensaje": "No se encontró el ejemplar."}
                return {"exito": True, "mensaje": "Ejemplar eliminado correctamente."}
        except mysql.connector.Error as e:
            if e.errno == 1451:
                return {"exito": False,
                        "mensaje": "No se puede eliminar: el ejemplar tiene historial de préstamos."}
            return {"exito": False, "mensaje": f"Error al eliminar ejemplar: {e.msg}"}
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

    def listar_lectores(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM lectores ORDER BY nombre_completo ASC")
                return cur.fetchall()
        finally:
            conn.close()

    def crear_lector(self, matricula: str, nombre_completo: str, correo: str, telefono: str,
                     tipo: str = "ALUMNO") -> int:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO lectores (matricula, nombre_completo, correo, telefono, tipo, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    """,
                    (matricula.strip(), nombre_completo.strip(), correo.strip(), telefono.strip(), tipo),
                )
                return cur.lastrowid
        finally:
            conn.close()

    def actualizar_estado_lector(self, id_lector: int, activo: bool) -> bool:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE lectores SET activo = %s WHERE id_lector = %s", (int(activo), id_lector))
                return cur.rowcount > 0
        finally:
            conn.close()

    def listar_prestamos_activos(self) -> list[dict]:
        verificar_rol(self.sesion, ("ADMIN", "OPERADOR", "CONSULTA"))
        conn = get_connection(self.sesion.username)
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT p.id_prestamo, e.codigo_barras, l.titulo, lec.matricula,
                           lec.nombre_completo AS lector, p.fecha_prestamo, p.fecha_limite,
                           p.estado, fn_calcular_dias_retraso(p.id_prestamo) AS dias_retraso
                    FROM prestamos p
                    INNER JOIN ejemplares e ON p.id_ejemplar = e.id_ejemplar
                    INNER JOIN libros l ON e.id_libro = l.id_libro
                    INNER JOIN lectores lec ON p.id_lector = lec.id_lector
                    WHERE p.estado IN ('ACTIVO', 'VENCIDO')
                    ORDER BY p.fecha_limite ASC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()

    # 5. REPORTES AVANZADOS Y AUDITORÍA

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
# PRUEBA RÁPIDA EN CONSOLA (Opcional para pruebas locales sin interfaz)
# ======================================================================
if __name__ == "__main__":
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
        print(
            "\n1. Consultar código | 2. Prestar | 3. Devolver | 4. Listar libros | 5. Listar usuarios | 6. Reportes | 7. Auditoría | 0. Salir")
        op = input("Opción: ").strip()
        try:
            if op == "1":
                print(svc.consultar_por_codigo_barras(input("Código de barras: ")))
            elif op == "2":
                cod = input("Código de barras: ")
                mat = input("Matrícula (ej. ISC2026001): ")
                print(svc.registrar_prestamo(cod, mat))
            elif op == "3":
                cod = input("Código de barras: ")
                obs = input("Observaciones (opcional): ")
                print(svc.registrar_devolucion(cod, obs))
            elif op == "4":
                for fila in svc.listar_libros():
                    print(" ", fila)
            elif op == "5":
                for fila in svc.listar_usuarios():
                    print(" ", fila)
            elif op == "6":
                print("-- Más solicitados --")
                for fila in svc.reporte_libros_mas_solicitados():
                    print(" ", fila)
                print("-- Lectores vencidos --")
                for fila in svc.reporte_lectores_vencidos():
                    print(" ", fila)
            elif op == "7":
                for fila in svc.consultar_auditoria():
                    print(" ", fila)
            elif op == "0":
                break
        except PermisoDenegadoError as e:
            print(f"[SEGURIDAD] {e}")
        except Exception as e:
            print(f"[ERROR] {e}")