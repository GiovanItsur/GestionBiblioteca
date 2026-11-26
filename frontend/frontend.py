import json
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import mysql.connector

from backend.Seguridad import SesionUsuario, PermisoDenegadoError, iniciar_sesion
from backend.biblioteca_service import BibliotecaService

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ======================================================================
# PALETA EDITORIAL / BIBLIOTECA RETRO
# ======================================================================
COLOR_CREAM = "#FAF6EB"         # Fondo principal (papel cálido)
COLOR_PAPER = "#FFFDF7"         # Tarjetas y campos de texto
COLOR_SAND = "#F2E8D5"          # Sidebar y contenedores suaves
COLOR_SAND_ALT = "#F5EFE0"      # Filas alternas en tablas
COLOR_BORDER = "#DFCFAE"        # Bordes sutiles
COLOR_HONEY = "#F7CE76"         # Amarillo miel cálido (acentos / selección)
COLOR_HONEY_HOVER = "#EEBE5B"
COLOR_CARAMEL = "#D99B62"       # Caramelo / terracota suave (CTA principal)
COLOR_CARAMEL_HOVER = "#C5864D"
COLOR_ESPRESSO = "#4A3728"      # Café oscuro (texto principal / headers)
COLOR_ESPRESSO_HOVER = "#38281D"
COLOR_COCOA = "#856C56"         # Café medio (subtítulos y texto secundario)

# Colores semánticos armonizados con la paleta cálida
COLOR_SAGE = "#5A7D56"          # Verde olivo (Disponible / Guardar / Préstamo)
COLOR_SAGE_HOVER = "#496746"
COLOR_AMBER = "#C97532"         # Ámbar quemado (Editar / Devolver / Operador)
COLOR_AMBER_HOVER = "#B06224"
COLOR_BRICK = "#B84A39"         # Rojo ladrillo (Eliminar / Cerrar sesión / Admin)
COLOR_BRICK_HOVER = "#993B2C"


def configurar_estilo_treeview():
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Bib.Treeview",
        background=COLOR_PAPER,
        foreground=COLOR_ESPRESSO,
        rowheight=30,
        fieldbackground=COLOR_PAPER,
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Bib.Treeview.Heading",
        background=COLOR_ESPRESSO,
        foreground=COLOR_CREAM,
        relief="flat",
        padding=(8, 6),
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Bib.Treeview",
        background=[("selected", COLOR_HONEY)],
        foreground=[("selected", COLOR_ESPRESSO)],
    )
    style.map("Bib.Treeview.Heading", background=[("active", COLOR_ESPRESSO_HOVER)])


def crear_tabla(parent, columnas: list[tuple[str, str, int]], alto_filas: int = 8) -> ttk.Treeview:
    """Crea un Treeview con estética cálida, filas alternas y scrollbars."""
    contenedor = ctk.CTkFrame(
        parent,
        fg_color=COLOR_PAPER,
        corner_radius=12,
        border_width=1,
        border_color=COLOR_BORDER,
    )
    contenedor.pack(fill="both", expand=True, padx=14, pady=(6, 10))

    col_ids = [c[0] for c in columnas]
    tree = ttk.Treeview(
        contenedor,
        columns=col_ids,
        show="headings",
        style="Bib.Treeview",
        height=alto_filas,
    )

    for col_id, titulo, ancho in columnas:
        tree.heading(col_id, text=titulo)
        tree.column(col_id, width=ancho, minwidth=55, anchor="w")

    tree.tag_configure("par", background=COLOR_PAPER)
    tree.tag_configure("impar", background=COLOR_SAND_ALT)

    scroll_y = ttk.Scrollbar(contenedor, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
    scroll_y.grid(row=0, column=1, sticky="ns", pady=(6, 0))
    scroll_x.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))

    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_columnconfigure(0, weight=1)
    return tree


def llenar_tabla(tree: ttk.Treeview, filas: list[dict], claves: list[str]):
    for item in tree.get_children():
        tree.delete(item)
    for idx, fila in enumerate(filas):
        valores = ["" if fila.get(k) is None else str(fila.get(k)) for k in claves]
        tag = "par" if idx % 2 == 0 else "impar"
        tree.insert("", "end", values=valores, tags=(tag,))


def estilizar_entry(parent, **kwargs) -> ctk.CTkEntry:
    defaults = dict(
        fg_color=COLOR_PAPER,
        border_color=COLOR_ESPRESSO,
        border_width=1,
        text_color=COLOR_ESPRESSO,
        placeholder_text_color=COLOR_COCOA,
        corner_radius=10,
        height=36,
    )
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)


def estilizar_optionmenu(parent, values: list[str], **kwargs) -> ctk.CTkOptionMenu:
    defaults = dict(
        values=values,
        fg_color=COLOR_SAND,
        button_color=COLOR_CARAMEL,
        button_hover_color=COLOR_CARAMEL_HOVER,
        text_color=COLOR_ESPRESSO,
        dropdown_fg_color=COLOR_PAPER,
        dropdown_text_color=COLOR_ESPRESSO,
        dropdown_hover_color=COLOR_HONEY,
        corner_radius=10,
        height=34,
    )
    defaults.update(kwargs)
    return ctk.CTkOptionMenu(parent, **defaults)


def crear_modal_scrollable(parent, titulo: str, ancho: int, alto: int) -> tuple[ctk.CTkToplevel, ctk.CTkScrollableFrame, ctk.CTkFrame]:
    """Crea una ventana modal centrada con cuerpo desplazable y pie fijo para botones."""
    root = parent.winfo_toplevel()
    win = ctk.CTkToplevel(root)
    win.title(titulo)
    win.configure(fg_color=COLOR_CREAM)
    win.transient(root)

    # Limita la altura del modal para que nunca rebase la pantalla
    max_h = max(360, win.winfo_screenheight() - 120)
    alto_final = min(alto, max_h)
    x = root.winfo_rootx() + max(20, (root.winfo_width() - ancho) // 2)
    y = root.winfo_rooty() + max(20, (root.winfo_height() - alto_final) // 2)
    win.geometry(f"{ancho}x{alto_final}+{x}+{y}")
    win.minsize(min(ancho, 380), min(alto_final, 320))

    cuerpo = ctk.CTkScrollableFrame(
        win,
        fg_color=COLOR_CREAM,
        scrollbar_button_color=COLOR_CARAMEL,
        scrollbar_button_hover_color=COLOR_CARAMEL_HOVER,
    )
    cuerpo.pack(fill="both", expand=True, padx=14, pady=(12, 6))

    pie = ctk.CTkFrame(win, fg_color=COLOR_SAND, corner_radius=0, height=58)
    pie.pack(fill="x", side="bottom")

    win.grab_set()
    win.after(60, win.focus_force)
    return win, cuerpo, pie


def formatear_json_legible(valor: str) -> str:
    if not valor or valor == "NULL":
        return "NULL"
    try:
        obj = json.loads(valor)
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(valor)


# ======================================================================
# PANTALLA DE INICIO DE SESIÓN (ESTILO EDITORIAL RETRO CON ONDAS)
# ======================================================================
class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=COLOR_HONEY)
        self.on_login_success = on_login_success
        self._construir_ui()

    def _construir_ui(self):
        card = ctk.CTkFrame(
            self,
            width=840,
            height=520,
            corner_radius=24,
            fg_color=COLOR_CREAM,
            border_width=2,
            border_color=COLOR_ESPRESSO,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # Panel izquierdo decorativo (Canvas con ondas retro)
        izq = ctk.CTkFrame(card, width=360, corner_radius=20, fg_color=COLOR_CREAM)
        izq.pack(side="left", fill="y", padx=(8, 0), pady=8)
        izq.pack_propagate(False)

        canvas = tk.Canvas(izq, width=360, height=504, bg=COLOR_CREAM, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Onda superior (miel + caramelo)
        canvas.create_polygon(
            0, 0, 360, 0, 360, 95, 270, 125, 170, 75, 70, 130, 0, 105,
            smooth=True, fill=COLOR_HONEY, outline="",
        )
        canvas.create_polygon(
            0, 0, 360, 0, 360, 62, 260, 92, 165, 48, 70, 95, 0, 72,
            smooth=True, fill=COLOR_CARAMEL, outline="",
        )

        # Onda inferior (caramelo + miel)
        canvas.create_polygon(
            0, 504, 360, 504, 360, 355, 265, 325, 170, 380, 75, 340, 0, 380,
            smooth=True, fill=COLOR_HONEY, outline="",
        )
        canvas.create_polygon(
            0, 504, 360, 504, 360, 415, 270, 385, 175, 440, 80, 405, 0, 440,
            smooth=True, fill=COLOR_CARAMEL, outline="",
        )

        # Emblema de biblioteca
        canvas.create_oval(135, 150, 225, 240, fill=COLOR_ESPRESSO, outline=COLOR_CARAMEL, width=4)
        canvas.create_oval(162, 177, 198, 213, fill=COLOR_CREAM, outline=COLOR_HONEY, width=3)
        canvas.create_text(180, 195, text="B", fill=COLOR_ESPRESSO, font=("Georgia", 18, "bold"))

        canvas.create_text(180, 274, text="BIBLIOTECA", fill=COLOR_ESPRESSO, font=("Georgia", 22, "bold"))
        canvas.create_text(
            180,
            304,
            text="Sistema de Gestión y Préstamos",
            fill=COLOR_COCOA,
            font=("Segoe UI", 10, "italic"),
        )
        canvas.create_text(
            180,
            455,
            text="Taller de Bases de Datos",
            fill=COLOR_CREAM,
            font=("Segoe UI", 10, "bold"),
        )

        # Panel derecho: Formulario de inicio de sesión
        der = ctk.CTkFrame(card, fg_color=COLOR_CREAM)
        der.pack(side="right", fill="both", expand=True, padx=34, pady=22)

        ctk.CTkLabel(
            der,
            text="Bienvenido de nuevo",
            text_color=COLOR_CARAMEL,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(18, 2))

        ctk.CTkLabel(
            der,
            text="Iniciar Sesión",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=26, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            der,
            text="Nombre de usuario",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        self.entry_user = estilizar_entry(der, height=40, placeholder_text="Ej. admin, operador, consulta")
        self.entry_user.pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(
            der,
            text="Contraseña",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        self.entry_pass = estilizar_entry(der, height=40, show="•", placeholder_text="Ingresa tu contraseña")
        self.entry_pass.pack(fill="x", pady=(4, 10))

        self.var_mostrar = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            der,
            text="Mostrar contraseña",
            variable=self.var_mostrar,
            text_color=COLOR_COCOA,
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            border_color=COLOR_ESPRESSO,
            command=self._toggle_password,
        ).pack(anchor="w", pady=(0, 10))

        self.lbl_error = ctk.CTkLabel(
            der,
            text="",
            text_color=COLOR_BRICK,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=360,
            anchor="w",
            justify="left",
        )
        self.lbl_error.pack(fill="x", pady=(0, 10))

        self.btn_login = ctk.CTkButton(
            der,
            text="Entrar a la Biblioteca",
            height=44,
            corner_radius=12,
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._intentar_login,
        )
        self.btn_login.pack(fill="x", pady=(4, 0))

        self.entry_user.bind("<Return>", lambda _e: self.entry_pass.focus_set())
        self.entry_pass.bind("<Return>", lambda _e: self._intentar_login())
        self.after(150, self.entry_user.focus_set)

    def _toggle_password(self):
        self.entry_pass.configure(show="" if self.var_mostrar.get() else "•")

    def _intentar_login(self):
        usuario = self.entry_user.get().strip()
        password = self.entry_pass.get()

        if not usuario or not password:
            self.lbl_error.configure(text="Ingresa usuario y contraseña.")
            return

        self.lbl_error.configure(text="")
        self.btn_login.configure(state="disabled", text="Verificando...")
        self.update_idletasks()
        try:
            sesion = iniciar_sesion(usuario, password)
            if sesion:
                self.on_login_success(sesion)
            else:
                self.lbl_error.configure(text="Credenciales incorrectas o cuenta inactiva.")
        except Exception as e:
            self.lbl_error.configure(text=f"Error de conexión a la BD: {e}")
        finally:
            if self.winfo_exists():
                self.btn_login.configure(state="normal", text="Entrar a la Biblioteca")


# ======================================================================
# PANEL PRINCIPAL DEL SISTEMA
# ======================================================================
class MainFrame(ctk.CTkFrame):
    def __init__(self, master, sesion: SesionUsuario, on_logout):
        super().__init__(master, fg_color=COLOR_CREAM)
        self.sesion = sesion
        self.service = BibliotecaService(sesion)
        self.on_logout = on_logout
        self.botones_nav: dict[str, ctk.CTkButton] = {}

        self._construir_layout()
        self.mostrar_vista("circulacion")

    def _construir_layout(self):
        sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=COLOR_SAND,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand_bar = ctk.CTkFrame(sidebar, fg_color=COLOR_HONEY, corner_radius=14)
        brand_bar.pack(fill="x", padx=14, pady=(14, 10))

        ctk.CTkLabel(
            brand_bar,
            text="BIBLIOTECA",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=19, weight="bold"),
        ).pack(pady=(10, 0))
        ctk.CTkLabel(
            brand_bar,
            text="Catálogo y Circulación",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 8))

        color_rol = {
            "ADMIN": COLOR_BRICK,
            "OPERADOR": COLOR_AMBER,
            "CONSULTA": COLOR_SAGE,
        }.get(self.sesion.rol, COLOR_CARAMEL)

        user_box = ctk.CTkFrame(
            sidebar,
            fg_color=COLOR_PAPER,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        user_box.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(
            user_box,
            text=f"Hola, {self.sesion.nombre_completo}",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=190,
        ).pack(pady=(8, 2), padx=10)

        ctk.CTkLabel(
            user_box,
            text=f"@{self.sesion.username}",
            text_color=COLOR_COCOA,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            user_box,
            text=f"ROL: {self.sesion.rol}",
            fg_color=color_rol,
            text_color=COLOR_PAPER,
            corner_radius=8,
            padx=10,
            pady=2,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            sidebar,
            text="MENÚ PRINCIPAL",
            text_color=COLOR_COCOA,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 4))

        menu_items = [
            ("circulacion", "Mostrador y Escáner", ("ADMIN", "OPERADOR", "CONSULTA")),
            ("catalogo", "Libros y Ejemplares", ("ADMIN", "OPERADOR", "CONSULTA")),
            ("lectores", "Lectores", ("ADMIN", "OPERADOR")),
            ("reportes", "Reportes Avanzados", ("ADMIN", "OPERADOR", "CONSULTA")),
            ("usuarios", "Usuarios y Seguridad", ("ADMIN",)),
            ("auditoria", "Bitácora de Auditoría", ("ADMIN",)),
        ]

        for clave, texto, roles in menu_items:
            if self.sesion.rol in roles:
                btn = ctk.CTkButton(
                    sidebar,
                    text=f"  {texto}",
                    anchor="w",
                    height=38,
                    corner_radius=10,
                    fg_color="transparent",
                    hover_color=COLOR_HONEY,
                    text_color=COLOR_ESPRESSO,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    command=lambda c=clave: self.mostrar_vista(c),
                )
                btn.pack(fill="x", padx=14, pady=2)
                self.botones_nav[clave] = btn

        ctk.CTkButton(
            sidebar,
            text="Cerrar Sesión",
            height=38,
            corner_radius=10,
            fg_color=COLOR_BRICK,
            hover_color=COLOR_BRICK_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_logout,
        ).pack(side="bottom", fill="x", padx=14, pady=16)

        self.contenido = ctk.CTkFrame(self, fg_color=COLOR_CREAM, corner_radius=0)
        self.contenido.pack(side="right", fill="both", expand=True)

    def mostrar_vista(self, nombre: str):
        for clave, btn in self.botones_nav.items():
            if clave == nombre:
                btn.configure(fg_color=COLOR_ESPRESSO, text_color=COLOR_CREAM, hover_color=COLOR_ESPRESSO_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_ESPRESSO, hover_color=COLOR_HONEY)

        for widget in self.contenido.winfo_children():
            widget.destroy()

        vistas = {
            "circulacion": self._vista_circulacion,
            "catalogo": self._vista_catalogo,
            "lectores": self._vista_lectores,
            "reportes": self._vista_reportes,
            "usuarios": self._vista_usuarios,
            "auditoria": self._vista_auditoria,
        }
        vistas[nombre]()

    def _crear_encabezado(self, titulo: str, subtitulo: str) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self.contenido, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(14, 6))

        izq = ctk.CTkFrame(header, fg_color="transparent")
        izq.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            izq,
            text=titulo,
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=22, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            izq,
            text=subtitulo,
            text_color=COLOR_COCOA,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x")
        return header

    def _crear_tabview(self) -> ctk.CTkTabview:
        tabs = ctk.CTkTabview(
            self.contenido,
            fg_color=COLOR_CREAM,
            segmented_button_fg_color=COLOR_SAND,
            segmented_button_selected_color=COLOR_HONEY,
            segmented_button_selected_hover_color=COLOR_HONEY_HOVER,
            segmented_button_unselected_color=COLOR_SAND,
            segmented_button_unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            corner_radius=12,
        )
        tabs.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        return tabs

    def _manejar_error(self, e: Exception, parent=None):
        if isinstance(e, PermisoDenegadoError):
            messagebox.showwarning("Acceso Denegado", str(e), parent=parent)
        elif isinstance(e, mysql.connector.Error):
            if e.errno == 1062:
                msg = "Ya existe un registro con ese dato único (código, matrícula, correo, ISBN o usuario)."
            elif e.errno == 1451:
                msg = "No se puede eliminar este registro porque tiene información asociada."
            elif e.errno == 1452:
                msg = "El registro relacionado seleccionado no existe en la base de datos."
            elif e.errno == 1644:
                msg = str(e.msg)
            else:
                msg = f"Código {e.errno}: {e.msg}"
            messagebox.showerror("Error de Base de Datos", msg, parent=parent)
        else:
            messagebox.showerror("Error", str(e), parent=parent)

    # ------------------------------------------------------------------
    # VISTA 1: MOSTRADOR INTUITIVO (PASO 1: ESCANEAR -> PASO 2: ACTUAR)
    # ------------------------------------------------------------------
    def _vista_circulacion(self):
        puede_operar = self.sesion.rol in ("ADMIN", "OPERADOR")
        self._cache_prestamos: list[dict] = []
        self._ejemplar_actual: dict | None = None

        self._crear_encabezado(
            "Mostrador de Préstamos y Devoluciones",
            "Paso 1: Escanea el código de barras del libro.   Paso 2: Confirma el préstamo o la devolución.",
        )

        # --- PASO 1: BARRA ÚNICA DE ESCANEO ---
        scan_card = ctk.CTkFrame(
            self.contenido,
            fg_color=COLOR_HONEY,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_CARAMEL,
        )
        scan_card.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            scan_card,
            text="1. Escanea o escribe el código de barras del libro",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(8, 4))

        fila_scan = ctk.CTkFrame(scan_card, fg_color="transparent")
        fila_scan.pack(fill="x", padx=14, pady=(0, 4))

        self.entry_codigo = estilizar_entry(
            fila_scan,
            height=40,
            placeholder_text="Apunta el lector al código de barras del libro (Enter automático)...",
            font=ctk.CTkFont(size=14),
        )
        self.entry_codigo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_codigo.bind("<Return>", lambda _e: self._escanear_libro())

        ctk.CTkButton(
            fila_scan,
            text="Buscar Libro",
            width=120,
            height=40,
            corner_radius=10,
            fg_color=COLOR_ESPRESSO,
            hover_color=COLOR_ESPRESSO_HOVER,
            text_color=COLOR_CREAM,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._escanear_libro,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            fila_scan,
            text="Limpiar",
            width=82,
            height=40,
            corner_radius=10,
            fg_color=COLOR_SAND,
            hover_color=COLOR_PAPER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_CARAMEL,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._limpiar_mostrador,
        ).pack(side="left")

        self.lbl_estado_scan = ctk.CTkLabel(
            scan_card,
            text="Esperando lectura del escáner...",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(size=12),
        )
        self.lbl_estado_scan.pack(anchor="w", padx=14, pady=(0, 8))

        # --- PASO 2: GRID PROPORCIONAL (SIN RECORTE VERTICAL) ---
        medio = ctk.CTkFrame(self.contenido, fg_color="transparent")
        medio.pack(fill="x", padx=20, pady=(0, 8))
        medio.grid_columnconfigure(0, weight=1)
        if puede_operar:
            medio.grid_columnconfigure(1, weight=0, minsize=430)

        # Tarjeta izquierda: Ficha del libro escaneado
        ficha = ctk.CTkFrame(
            medio,
            fg_color=COLOR_PAPER,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        ficha.grid(row=0, column=0, sticky="nsew", padx=(0, 12 if puede_operar else 0))

        ficha_hdr = ctk.CTkFrame(ficha, fg_color=COLOR_SAND, corner_radius=10)
        ficha_hdr.pack(fill="x", padx=10, pady=(10, 8))
        ctk.CTkLabel(
            ficha_hdr,
            text="Libro Escaneado",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
        ).pack(side="left", padx=12, pady=6)

        self.badge_disp = ctk.CTkLabel(
            ficha_hdr,
            text="SIN LECTURA",
            fg_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            corner_radius=8,
            padx=10,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.badge_disp.pack(side="right", padx=10, pady=6)

        self.lbl_titulo_libro = ctk.CTkLabel(
            ficha,
            text="Ningún libro seleccionado",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=17, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.lbl_titulo_libro.pack(fill="x", padx=16, pady=(4, 6))

        self.lbl_ficha = ctk.CTkLabel(
            ficha,
            text="Escanea un código de barras arriba o haz doble clic en un préstamo de la tabla inferior.",
            justify="left",
            anchor="nw",
            text_color=COLOR_COCOA,
            font=ctk.CTkFont(size=13),
            wraplength=420,
        )
        self.lbl_ficha.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.lbl_prestamo_actual = ctk.CTkLabel(
            ficha,
            text="",
            justify="left",
            anchor="w",
            text_color=COLOR_AMBER,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=420,
        )
        self.lbl_prestamo_actual.pack(fill="x", padx=16, pady=(0, 12))

        def _ajustar_wrap_ficha(event):
            ancho_texto = max(240, event.width - 36)
            self.lbl_titulo_libro.configure(wraplength=ancho_texto)
            self.lbl_ficha.configure(wraplength=ancho_texto)
            self.lbl_prestamo_actual.configure(wraplength=ancho_texto)

        ficha.bind("<Configure>", _ajustar_wrap_ficha)

        # Tarjeta derecha: Pestañas claras (altura completa garantizada)
        if puede_operar:
            ops = ctk.CTkFrame(
                medio,
                fg_color=COLOR_PAPER,
                corner_radius=14,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            ops.grid(row=0, column=1, sticky="nsew")

            ctk.CTkLabel(
                ops,
                text="2. ¿Qué deseas hacer con este libro?",
                text_color=COLOR_ESPRESSO,
                font=ctk.CTkFont(family="Georgia", size=14, weight="bold"),
            ).pack(anchor="w", padx=14, pady=(10, 4))

            self.tabs_accion = ctk.CTkTabview(
                ops,
                width=404,
                height=280,
                fg_color=COLOR_CREAM,
                segmented_button_fg_color=COLOR_SAND,
                segmented_button_selected_color=COLOR_HONEY,
                segmented_button_selected_hover_color=COLOR_HONEY_HOVER,
                segmented_button_unselected_color=COLOR_SAND,
                segmented_button_unselected_hover_color=COLOR_BORDER,
                text_color=COLOR_ESPRESSO,
                corner_radius=10,
            )
            self.tabs_accion.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            tab_prestar = self.tabs_accion.add("Prestar libro")
            tab_devolver = self.tabs_accion.add("Recibir devolución")

            # --- Pestaña A: Prestar libro ---
            self.lbl_hint_prestar = ctk.CTkLabel(
                tab_prestar,
                text="Escanea un libro disponible para iniciar el préstamo.",
                text_color=COLOR_COCOA,
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
                justify="left",
                wraplength=365,
            )
            self.lbl_hint_prestar.pack(fill="x", padx=8, pady=(4, 8))

            self._mapa_lectores: dict[str, str] = {}
            opciones_lector = self._cargar_opciones_lectores()

            ctk.CTkLabel(
                tab_prestar, text="¿A qué lector se entrega?", text_color=COLOR_ESPRESSO, anchor="w"
            ).pack(fill="x", padx=8)
            self.combo_lector = ctk.CTkComboBox(
                tab_prestar,
                values=opciones_lector,
                fg_color=COLOR_PAPER,
                border_color=COLOR_BORDER,
                button_color=COLOR_CARAMEL,
                button_hover_color=COLOR_CARAMEL_HOVER,
                text_color=COLOR_ESPRESSO,
                dropdown_fg_color=COLOR_PAPER,
                dropdown_text_color=COLOR_ESPRESSO,
                dropdown_hover_color=COLOR_HONEY,
                corner_radius=10,
                height=34,
            )
            self.combo_lector.pack(fill="x", padx=8, pady=(2, 10))
            if opciones_lector:
                self.combo_lector.set(opciones_lector[0])

            fila_dias = ctk.CTkFrame(tab_prestar, fg_color="transparent")
            fila_dias.pack(fill="x", padx=8, pady=(0, 12))
            ctk.CTkLabel(fila_dias, text="Plazo (días):", text_color=COLOR_ESPRESSO).pack(side="left")
            self.entry_dias = estilizar_entry(fila_dias, width=54, height=32)
            self.entry_dias.insert(0, "7")
            self.entry_dias.pack(side="left", padx=(6, 8))

            for d in (3, 7, 15):
                ctk.CTkButton(
                    fila_dias,
                    text=f"{d} d",
                    width=42,
                    height=28,
                    corner_radius=8,
                    fg_color=COLOR_SAND,
                    hover_color=COLOR_HONEY,
                    text_color=COLOR_ESPRESSO,
                    border_width=1,
                    border_color=COLOR_BORDER,
                    command=lambda dias=d: self._fijar_dias(dias),
                ).pack(side="left", padx=2)

            ctk.CTkButton(
                tab_prestar,
                text="Confirmar Préstamo",
                height=38,
                corner_radius=10,
                fg_color=COLOR_SAGE,
                hover_color=COLOR_SAGE_HOVER,
                text_color=COLOR_PAPER,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self._ejecutar_prestamo,
            ).pack(fill="x", padx=8, pady=(4, 6))

            # --- Pestaña B: Recibir devolución ---
            self.lbl_hint_devolver = ctk.CTkLabel(
                tab_devolver,
                text="Escanea un libro prestado o haz doble clic en la tabla inferior.",
                text_color=COLOR_COCOA,
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
                justify="left",
                wraplength=365,
            )
            self.lbl_hint_devolver.pack(fill="x", padx=8, pady=(6, 12))

            ctk.CTkLabel(
                tab_devolver, text="Observaciones de entrega (opcional)", text_color=COLOR_ESPRESSO, anchor="w"
            ).pack(fill="x", padx=8)
            self.entry_obs = estilizar_entry(
                tab_devolver, height=36, placeholder_text="Ej. Entregado en buen estado"
            )
            self.entry_obs.pack(fill="x", padx=8, pady=(4, 16))
            self.entry_obs.bind("<Return>", lambda _e: self._ejecutar_devolucion())

            ctk.CTkButton(
                tab_devolver,
                text="Confirmar Devolución",
                height=38,
                corner_radius=10,
                fg_color=COLOR_CARAMEL,
                hover_color=COLOR_CARAMEL_HOVER,
                text_color=COLOR_PAPER,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self._ejecutar_devolucion,
            ).pack(fill="x", padx=8, pady=(4, 6))

        # --- TABLA INFERIOR: PRÉSTAMOS ACTIVOS Y VENCIDOS ---
        cab_tabla = ctk.CTkFrame(self.contenido, fg_color="transparent")
        cab_tabla.pack(fill="x", padx=20, pady=(2, 0))
        ctk.CTkLabel(
            cab_tabla,
            text="Préstamos Activos y Vencidos (doble clic para seleccionar y recibir devolución)",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=14, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            cab_tabla,
            text="Refrescar",
            width=95,
            height=30,
            corner_radius=8,
            fg_color=COLOR_SAND,
            hover_color=COLOR_HONEY,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self._cargar_prestamos_activos,
        ).pack(side="right")

        self.tree_prestamos = crear_tabla(
            self.contenido,
            [
                ("id_prestamo", "ID", 50),
                ("codigo_barras", "Código Barras", 130),
                ("titulo", "Título", 230),
                ("matricula", "Matrícula", 100),
                ("lector", "Lector", 165),
                ("fecha_prestamo", "Préstamo", 135),
                ("fecha_limite", "Fecha Límite", 135),
                ("estado", "Estado", 80),
                ("dias_retraso", "Días Retraso", 85),
            ],
            alto_filas=6,
        )
        self.tree_prestamos.bind("<Double-1>", self._seleccionar_prestamo_para_devolver)
        self._cargar_prestamos_activos()
        self.after(100, self.entry_codigo.focus_set)

    def _fijar_dias(self, dias: int):
        self.entry_dias.delete(0, "end")
        self.entry_dias.insert(0, str(dias))

    def _limpiar_mostrador(self):
        self._ejemplar_actual = None
        self.entry_codigo.delete(0, "end")
        self.lbl_estado_scan.configure(text="Esperando lectura del escáner...", text_color=COLOR_ESPRESSO)
        self.badge_disp.configure(text="SIN LECTURA", fg_color=COLOR_BORDER, text_color=COLOR_ESPRESSO)
        self.lbl_titulo_libro.configure(text="Ningún libro seleccionado")
        self.lbl_ficha.configure(
            text="Escanea un código de barras arriba o haz doble clic en un préstamo de la tabla inferior.",
            text_color=COLOR_COCOA,
        )
        self.lbl_prestamo_actual.configure(text="")
        if hasattr(self, "lbl_hint_prestar"):
            self.lbl_hint_prestar.configure(
                text="Escanea un libro disponible para iniciar el préstamo.", text_color=COLOR_COCOA
            )
            self.lbl_hint_devolver.configure(
                text="Escanea un libro prestado o haz doble clic en la tabla inferior.", text_color=COLOR_COCOA
            )
            self.entry_obs.delete(0, "end")
        self.entry_codigo.focus_set()

    def _cargar_opciones_lectores(self) -> list[str]:
        try:
            lectores = self.service.listar_lectores()
            opciones = []
            self._mapa_lectores.clear()
            for lec in lectores:
                etiqueta = f"{lec['matricula']} - {lec['nombre_completo']}" + ("" if lec["activo"] else " [INACTIVO]")
                opciones.append(etiqueta)
                self._mapa_lectores[etiqueta] = lec["matricula"]
            return opciones if opciones else ["(Sin lectores registrados)"]
        except Exception:
            return ["(Sin lectores registrados)"]

    def _obtener_matricula_seleccionada(self) -> str:
        texto = self.combo_lector.get().strip()
        if texto == "(Sin lectores registrados)":
            return ""
        if texto in self._mapa_lectores:
            return self._mapa_lectores[texto]
        return texto.split(" - ")[0].strip()

    def _seleccionar_prestamo_para_devolver(self, _event):
        sel = self.tree_prestamos.selection()
        if not sel:
            return
        vals = self.tree_prestamos.item(sel[0], "values")
        if vals:
            self.entry_codigo.delete(0, "end")
            self.entry_codigo.insert(0, vals[1])
            self._consultar_y_mostrar(vals[1])

    def _escanear_libro(self):
        codigo = self.entry_codigo.get().strip()
        if not codigo:
            self.lbl_estado_scan.configure(
                text="Escanea o escribe un código de barras para buscar el libro.", text_color=COLOR_BRICK
            )
            return
        self._consultar_y_mostrar(codigo)
        self.entry_codigo.select_range(0, "end")
        self.entry_codigo.focus_set()

    def _consultar_y_mostrar(self, codigo: str):
        try:
            res = self.service.consultar_por_codigo_barras(codigo)
            if not res["encontrado"]:
                self._ejemplar_actual = None
                self.lbl_estado_scan.configure(
                    text=f"No se encontró ningún ejemplar con el código '{codigo}'.",
                    text_color=COLOR_BRICK,
                )
                self.badge_disp.configure(text="NO ENCONTRADO", fg_color=COLOR_BRICK, text_color=COLOR_PAPER)
                self.lbl_titulo_libro.configure(text="Código no registrado")
                self.lbl_ficha.configure(
                    text="Verifica la etiqueta o registra este ejemplar desde 'Libros y Ejemplares'.",
                    text_color=COLOR_BRICK,
                )
                self.lbl_prestamo_actual.configure(text="")
                return

            ej = res["ejemplar"]
            self._ejemplar_actual = ej

            # Si no está disponible, sincroniza la lista de préstamos para mostrar datos exactos
            if not res["disponible"]:
                self._cargar_prestamos_activos()

            prestamo_activo = next(
                (p for p in self._cache_prestamos if str(p["codigo_barras"]) == str(ej["codigo_barras"])),
                None,
            )

            self.lbl_titulo_libro.configure(text=ej["titulo"])
            texto_ficha = (
                f"Autor: {ej['autor']}   •   Categoría: {ej['categoria']}\n"
                f"ISBN: {ej['isbn']}   •   Editorial: {ej['editorial']} ({ej['anio_publicacion']})\n"
                f"Código: {ej['codigo_barras']}   •   Ubicación: {ej['ubicacion']}\n"
                f"Copias disponibles de este título: {ej['copias_disponibles_titulo']}"
            )
            self.lbl_ficha.configure(text=texto_ficha, text_color=COLOR_ESPRESSO)

            if res["disponible"]:
                self.badge_disp.configure(text="DISPONIBLE", fg_color=COLOR_SAGE, text_color=COLOR_PAPER)
                self.lbl_estado_scan.configure(
                    text="Libro disponible. En el paso 2 elige al lector y presiona 'Confirmar Préstamo'.",
                    text_color=COLOR_ESPRESSO,
                )
                self.lbl_prestamo_actual.configure(text="")
                if hasattr(self, "tabs_accion"):
                    self.tabs_accion.set("Prestar libro")
                    self.lbl_hint_prestar.configure(
                        text=f"Listo para prestar: {ej['titulo']}", text_color=COLOR_SAGE
                    )
                    self.lbl_hint_devolver.configure(
                        text="Este ejemplar está disponible (no tiene préstamo activo).", text_color=COLOR_COCOA
                    )
            else:
                estado_ej = str(ej["estado_ejemplar"])
                color_badge = COLOR_AMBER if estado_ej == "PRESTADO" else COLOR_BRICK
                self.badge_disp.configure(text=estado_ej, fg_color=color_badge, text_color=COLOR_PAPER)

                if prestamo_activo:
                    retraso = int(prestamo_activo["dias_retraso"] or 0)
                    aviso_retraso = f" ({retraso} día(s) de retraso)" if retraso > 0 else " (a tiempo)"
                    info_prest = (
                        f"Prestado a: {prestamo_activo['lector']} ({prestamo_activo['matricula']})\n"
                        f"Fecha límite: {prestamo_activo['fecha_limite']}{aviso_retraso}"
                    )
                    self.lbl_prestamo_actual.configure(
                        text=info_prest, text_color=COLOR_BRICK if retraso > 0 else COLOR_AMBER
                    )
                    self.lbl_estado_scan.configure(
                        text=f"Libro actualmente prestado a {prestamo_activo['lector']}. Listo para recibir devolución.",
                        text_color=COLOR_ESPRESSO,
                    )
                else:
                    info_prest = f"Estado actual del ejemplar: {estado_ej}"
                    self.lbl_prestamo_actual.configure(text=info_prest, text_color=COLOR_BRICK)
                    self.lbl_estado_scan.configure(
                        text=f"El libro se encuentra en estado '{estado_ej}'.", text_color=COLOR_ESPRESSO
                    )

                if hasattr(self, "tabs_accion"):
                    self.tabs_accion.set("Recibir devolución")
                    self.lbl_hint_devolver.configure(
                        text=info_prest, text_color=COLOR_AMBER if prestamo_activo else COLOR_BRICK
                    )
                    self.lbl_hint_prestar.configure(
                        text=f"No disponible ({estado_ej}).",
                        text_color=COLOR_BRICK,
                    )
        except Exception as e:
            self._manejar_error(e)

    def _ejecutar_prestamo(self):
        codigo = (
            self._ejemplar_actual["codigo_barras"]
            if self._ejemplar_actual
            else self.entry_codigo.get().strip()
        )
        if not codigo:
            messagebox.showwarning("Paso 1 pendiente", "Primero escanea o busca el código de barras del libro.")
            return
        matricula = self._obtener_matricula_seleccionada()
        if not matricula:
            messagebox.showwarning("Lector requerido", "Selecciona un lector válido (regístralo primero en Lectores).")
            return
        try:
            dias = int(self.entry_dias.get().strip())
        except ValueError:
            messagebox.showwarning("Plazo inválido", "Ingresa un número entero positivo de días.")
            return

        try:
            res = self.service.registrar_prestamo(codigo, matricula, dias)
            self._cargar_prestamos_activos()
            if res["exito"]:
                messagebox.showinfo("Préstamo Registrado", f"Folio #{res['id_prestamo']}\n{res['mensaje']}")
                self._consultar_y_mostrar(codigo)
            else:
                self.lbl_estado_scan.configure(text=res["mensaje"], text_color=COLOR_BRICK)
                messagebox.showerror("Préstamo Rechazado", res["mensaje"])
        except Exception as e:
            self._manejar_error(e)

    def _ejecutar_devolucion(self):
        codigo = (
            self._ejemplar_actual["codigo_barras"]
            if self._ejemplar_actual
            else self.entry_codigo.get().strip()
        )
        if not codigo:
            messagebox.showwarning("Paso 1 pendiente", "Primero escanea el libro o da doble clic en un préstamo.")
            return
        obs = self.entry_obs.get().strip()
        try:
            res = self.service.registrar_devolucion(codigo, obs)
            self._cargar_prestamos_activos()
            if res["exito"]:
                messagebox.showinfo("Devolución Registrada", res["mensaje"])
                self.entry_obs.delete(0, "end")
                self._consultar_y_mostrar(codigo)
            else:
                self.lbl_estado_scan.configure(text=res["mensaje"], text_color=COLOR_BRICK)
                messagebox.showerror("Devolución Rechazada", res["mensaje"])
        except Exception as e:
            self._manejar_error(e)

    def _cargar_prestamos_activos(self):
        try:
            self._cache_prestamos = self.service.listar_prestamos_activos()
            llenar_tabla(
                self.tree_prestamos,
                self._cache_prestamos,
                [
                    "id_prestamo",
                    "codigo_barras",
                    "titulo",
                    "matricula",
                    "lector",
                    "fecha_prestamo",
                    "fecha_limite",
                    "estado",
                    "dias_retraso",
                ],
            )
        except Exception as e:
            self._manejar_error(e)

    # ------------------------------------------------------------------
    # VISTA 2: CATÁLOGO DE LIBROS, EJEMPLARES, AUTORES Y CATEGORÍAS
    # ------------------------------------------------------------------
    def _vista_catalogo(self):
        puede_editar = self.sesion.rol in ("ADMIN", "OPERADOR")
        es_admin = self.sesion.rol == "ADMIN"

        self._crear_encabezado(
            "Catálogo de Libros y Ejemplares",
            "Administra títulos, copias físicas con código de barras, autores y categorías.",
        )

        tabs = self._crear_tabview()
        tab_libros = tabs.add("Libros")
        tab_ejemplares = tabs.add("Ejemplares (Códigos de Barras)")
        tab_aux = tabs.add("Autores y Categorías")

        # --- TAB LIBROS (dos filas limpias para no desbordar nunca) ---
        barra_busq = ctk.CTkFrame(tab_libros, fg_color="transparent")
        barra_busq.pack(fill="x", padx=14, pady=(6, 4))

        self.entry_buscar_libro = estilizar_entry(
            barra_busq, placeholder_text="Buscar por título, ISBN o autor..."
        )
        self.entry_buscar_libro.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_buscar_libro.bind("<Return>", lambda _e: self._buscar_libros())

        ctk.CTkButton(
            barra_busq,
            text="Buscar",
            width=90,
            fg_color=COLOR_ESPRESSO,
            hover_color=COLOR_ESPRESSO_HOVER,
            text_color=COLOR_CREAM,
            command=self._buscar_libros,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            barra_busq,
            text="Ver Todos",
            width=90,
            fg_color=COLOR_SAND,
            hover_color=COLOR_HONEY,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self._cargar_libros,
        ).pack(side="left")

        if puede_editar:
            barra_acc = ctk.CTkFrame(tab_libros, fg_color="transparent")
            barra_acc.pack(fill="x", padx=14, pady=(2, 2))

            ctk.CTkButton(
                barra_acc,
                text="+ Libro y Ejemplar (SP)",
                fg_color=COLOR_SAGE,
                hover_color=COLOR_SAGE_HOVER,
                text_color=COLOR_PAPER,
                font=ctk.CTkFont(weight="bold"),
                command=self._dialogo_libro_y_ejemplar,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                barra_acc,
                text="+ Solo Libro",
                fg_color=COLOR_CARAMEL,
                hover_color=COLOR_CARAMEL_HOVER,
                text_color=COLOR_PAPER,
                command=lambda: self._dialogo_libro(),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                barra_acc,
                text="Editar Seleccionado",
                fg_color=COLOR_AMBER,
                hover_color=COLOR_AMBER_HOVER,
                text_color=COLOR_PAPER,
                command=self._editar_libro_seleccionado,
            ).pack(side="left", padx=(0, 6))
            if es_admin:
                ctk.CTkButton(
                    barra_acc,
                    text="Eliminar",
                    width=95,
                    fg_color=COLOR_BRICK,
                    hover_color=COLOR_BRICK_HOVER,
                    text_color=COLOR_PAPER,
                    command=self._eliminar_libro_seleccionado,
                ).pack(side="right")

        self.tree_libros = crear_tabla(
            tab_libros,
            [
                ("id_libro", "ID", 50),
                ("isbn", "ISBN", 125),
                ("titulo", "Título", 240),
                ("autor", "Autor", 160),
                ("categoria", "Categoría", 130),
                ("editorial", "Editorial", 150),
                ("anio_publicacion", "Año", 60),
                ("disponibles", "Disponibles", 85),
            ],
        )
        if puede_editar:
            self.tree_libros.bind("<Double-1>", lambda _e: self._editar_libro_seleccionado())
        self._cargar_libros()

        # --- TAB EJEMPLARES ---
        barra_ej = ctk.CTkFrame(tab_ejemplares, fg_color="transparent")
        barra_ej.pack(fill="x", padx=14, pady=6)

        ctk.CTkButton(
            barra_ej,
            text="Refrescar",
            width=95,
            fg_color=COLOR_SAND,
            hover_color=COLOR_HONEY,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self._cargar_ejemplares,
        ).pack(side="left")

        if puede_editar:
            ctk.CTkButton(
                barra_ej,
                text="+ Agregar Ejemplar",
                fg_color=COLOR_SAGE,
                hover_color=COLOR_SAGE_HOVER,
                text_color=COLOR_PAPER,
                font=ctk.CTkFont(weight="bold"),
                command=self._dialogo_nuevo_ejemplar,
            ).pack(side="left", padx=(8, 6))
            ctk.CTkButton(
                barra_ej,
                text="Editar Ubicación / Estado",
                fg_color=COLOR_AMBER,
                hover_color=COLOR_AMBER_HOVER,
                text_color=COLOR_PAPER,
                command=self._dialogo_editar_ejemplar,
            ).pack(side="left", padx=(0, 6))
        if es_admin:
            ctk.CTkButton(
                barra_ej,
                text="Eliminar",
                width=95,
                fg_color=COLOR_BRICK,
                hover_color=COLOR_BRICK_HOVER,
                text_color=COLOR_PAPER,
                command=self._eliminar_ejemplar_seleccionado,
            ).pack(side="right")

        self.tree_ejemplares = crear_tabla(
            tab_ejemplares,
            [
                ("id_ejemplar", "ID", 55),
                ("codigo_barras", "Código de Barras", 145),
                ("titulo", "Título del Libro", 250),
                ("ubicacion", "Ubicación", 200),
                ("estado", "Estado", 115),
                ("fecha_alta", "Fecha Alta", 145),
            ],
        )
        if puede_editar:
            self.tree_ejemplares.bind("<Double-1>", lambda _e: self._dialogo_editar_ejemplar())
        self._cargar_ejemplares()

        # --- TAB AUTORES Y CATEGORÍAS (50% / 50% uniforme) ---
        cont_aux = ctk.CTkFrame(tab_aux, fg_color="transparent")
        cont_aux.pack(fill="both", expand=True, padx=6, pady=6)
        cont_aux.grid_columnconfigure(0, weight=1, uniform="aux")
        cont_aux.grid_columnconfigure(1, weight=1, uniform="aux")
        cont_aux.grid_rowconfigure(0, weight=1)

        panel_izq = ctk.CTkFrame(
            cont_aux, fg_color=COLOR_SAND, corner_radius=12, border_width=1, border_color=COLOR_BORDER
        )
        panel_izq.grid(row=0, column=0, sticky="nsew", padx=(4, 6))
        ctk.CTkLabel(
            panel_izq,
            text="Autores",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
        ).pack(pady=(10, 4))

        if puede_editar:
            f_aut = ctk.CTkFrame(panel_izq, fg_color="transparent")
            f_aut.pack(fill="x", padx=12, pady=4)
            self.entry_nuevo_autor = estilizar_entry(f_aut, placeholder_text="Nombre completo del autor")
            self.entry_nuevo_autor.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.entry_nuevo_autor.bind("<Return>", lambda _e: self._agregar_autor())
            ctk.CTkButton(
                f_aut,
                text="Agregar",
                width=85,
                fg_color=COLOR_CARAMEL,
                hover_color=COLOR_CARAMEL_HOVER,
                text_color=COLOR_PAPER,
                command=self._agregar_autor,
            ).pack(side="right")

        self.tree_autores = crear_tabla(panel_izq, [("id_autor", "ID", 60), ("nombre_completo", "Nombre", 260)])

        panel_der = ctk.CTkFrame(
            cont_aux, fg_color=COLOR_SAND, corner_radius=12, border_width=1, border_color=COLOR_BORDER
        )
        panel_der.grid(row=0, column=1, sticky="nsew", padx=(6, 4))
        ctk.CTkLabel(
            panel_der,
            text="Categorías",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
        ).pack(pady=(10, 4))

        if puede_editar:
            f_cat = ctk.CTkFrame(panel_der, fg_color="transparent")
            f_cat.pack(fill="x", padx=12, pady=4)
            self.entry_nueva_cat = estilizar_entry(f_cat, placeholder_text="Nombre de la categoría")
            self.entry_nueva_cat.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.entry_nueva_cat.bind("<Return>", lambda _e: self._agregar_categoria())
            ctk.CTkButton(
                f_cat,
                text="Agregar",
                width=85,
                fg_color=COLOR_CARAMEL,
                hover_color=COLOR_CARAMEL_HOVER,
                text_color=COLOR_PAPER,
                command=self._agregar_categoria,
            ).pack(side="right")

        self.tree_categorias = crear_tabla(panel_der, [("id_categoria", "ID", 60), ("nombre", "Categoría", 260)])
        self._cargar_autores_y_categorias()

    def _cargar_libros(self):
        try:
            self._cache_libros = self.service.listar_libros()
            llenar_tabla(
                self.tree_libros,
                self._cache_libros,
                ["id_libro", "isbn", "titulo", "autor", "categoria", "editorial", "anio_publicacion", "disponibles"],
            )
        except Exception as e:
            self._manejar_error(e)

    def _buscar_libros(self):
        termino = self.entry_buscar_libro.get().strip()
        if not termino:
            self._cargar_libros()
            return
        try:
            self._cache_libros = self.service.buscar_libros(termino)
            llenar_tabla(
                self.tree_libros,
                self._cache_libros,
                ["id_libro", "isbn", "titulo", "autor", "categoria", "editorial", "anio_publicacion", "disponibles"],
            )
        except Exception as e:
            self._manejar_error(e)

    def _cargar_ejemplares(self):
        try:
            self._cache_ejemplares = self.service.listar_ejemplares()
            llenar_tabla(
                self.tree_ejemplares,
                self._cache_ejemplares,
                ["id_ejemplar", "codigo_barras", "titulo", "ubicacion", "estado", "fecha_alta"],
            )
        except Exception as e:
            self._manejar_error(e)

    def _cargar_autores_y_categorias(self):
        try:
            llenar_tabla(self.tree_autores, self.service.listar_autores(), ["id_autor", "nombre_completo"])
            llenar_tabla(self.tree_categorias, self.service.listar_categorias(), ["id_categoria", "nombre"])
        except Exception as e:
            self._manejar_error(e)

    def _agregar_autor(self):
        nombre = self.entry_nuevo_autor.get().strip()
        if not nombre:
            messagebox.showwarning("Campo vacío", "Escribe el nombre completo del autor.")
            return
        try:
            self.service.crear_autor(nombre)
            self.entry_nuevo_autor.delete(0, "end")
            self._cargar_autores_y_categorias()
            messagebox.showinfo("Autor", "Autor registrado correctamente.")
        except Exception as e:
            self._manejar_error(e)

    def _agregar_categoria(self):
        nombre = self.entry_nueva_cat.get().strip()
        if not nombre:
            messagebox.showwarning("Campo vacío", "Escribe el nombre de la categoría.")
            return
        try:
            self.service.crear_categoria(nombre)
            self.entry_nueva_cat.delete(0, "end")
            self._cargar_autores_y_categorias()
            messagebox.showinfo("Categoría", "Categoría registrada correctamente.")
        except Exception as e:
            self._manejar_error(e)

    def _dialogo_libro(self, libro_actual: dict | None = None):
        autores = self.service.listar_autores()
        categorias = self.service.listar_categorias()
        if not autores or not categorias:
            messagebox.showwarning("Catálogos vacíos", "Primero registra al menos un autor y una categoría.")
            return

        win, cuerpo, pie = crear_modal_scrollable(
            self, "Editar Libro" if libro_actual else "Registrar Libro", 460, 520
        )
        mapa_aut = {f"{a['id_autor']} - {a['nombre_completo']}": a["id_autor"] for a in autores}
        mapa_cat = {f"{c['id_categoria']} - {c['nombre']}": c["id_categoria"] for c in categorias}

        def campo(etiqueta, valor=""):
            ctk.CTkLabel(cuerpo, text=etiqueta, text_color=COLOR_ESPRESSO, anchor="w").pack(
                fill="x", padx=10, pady=(8, 2)
            )
            e = estilizar_entry(cuerpo)
            e.insert(0, str(valor))
            e.pack(fill="x", padx=10)
            return e

        e_isbn = campo("ISBN *", libro_actual["isbn"] if libro_actual else "")
        e_titulo = campo("Título *", libro_actual["titulo"] if libro_actual else "")

        ctk.CTkLabel(cuerpo, text="Autor *", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        opt_aut = estilizar_optionmenu(cuerpo, list(mapa_aut.keys()))
        opt_aut.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Categoría *", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(8, 2)
        )
        opt_cat = estilizar_optionmenu(cuerpo, list(mapa_cat.keys()))
        opt_cat.pack(fill="x", padx=10)

        if libro_actual:
            for k, v in mapa_aut.items():
                if v == libro_actual["id_autor"]:
                    opt_aut.set(k)
            for k, v in mapa_cat.items():
                if v == libro_actual["id_categoria"]:
                    opt_cat.set(k)

        e_editorial = campo("Editorial *", libro_actual["editorial"] if libro_actual else "")
        e_anio = campo("Año de publicación *", libro_actual["anio_publicacion"] if libro_actual else "2024")

        def guardar():
            if not e_isbn.get().strip() or not e_titulo.get().strip() or not e_editorial.get().strip():
                messagebox.showwarning("Campos obligatorios", "ISBN, título y editorial son obligatorios.", parent=win)
                return
            try:
                anio = int(e_anio.get().strip())
            except ValueError:
                messagebox.showwarning("Año inválido", "El año debe ser un número entero.", parent=win)
                return

            try:
                if libro_actual:
                    res = self.service.actualizar_libro(
                        libro_actual["id_libro"],
                        e_isbn.get(),
                        e_titulo.get(),
                        mapa_aut[opt_aut.get()],
                        mapa_cat[opt_cat.get()],
                        e_editorial.get(),
                        anio,
                    )
                else:
                    res = self.service.crear_libro(
                        e_isbn.get(),
                        e_titulo.get(),
                        mapa_aut[opt_aut.get()],
                        mapa_cat[opt_cat.get()],
                        e_editorial.get(),
                        anio,
                    )
                if res["exito"]:
                    messagebox.showinfo("Éxito", res["mensaje"], parent=win)
                    win.destroy()
                    self._cargar_libros()
                else:
                    messagebox.showerror("Error", res["mensaje"], parent=win)
            except Exception as ex:
                self._manejar_error(ex, parent=win)

        ctk.CTkButton(
            pie,
            text="Cancelar",
            width=110,
            height=36,
            fg_color=COLOR_PAPER,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=win.destroy,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(
            pie,
            text="Guardar Libro",
            height=36,
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=guardar,
        ).pack(side="right", fill="x", expand=True, padx=(0, 16), pady=10)

    def _dialogo_libro_y_ejemplar(self):
        autores = self.service.listar_autores()
        categorias = self.service.listar_categorias()
        if not autores or not categorias:
            messagebox.showwarning("Catálogos vacíos", "Primero registra al menos un autor y una categoría.")
            return

        win, cuerpo, pie = crear_modal_scrollable(
            self, "Registrar Libro + Ejemplar (SP Transaccional)", 480, 600
        )
        mapa_aut = {f"{a['id_autor']} - {a['nombre_completo']}": a["id_autor"] for a in autores}
        mapa_cat = {f"{c['id_categoria']} - {c['nombre']}": c["id_categoria"] for c in categorias}

        def campo(etiqueta, placeholder="", valor=""):
            ctk.CTkLabel(cuerpo, text=etiqueta, text_color=COLOR_ESPRESSO, anchor="w").pack(
                fill="x", padx=10, pady=(6, 2)
            )
            e = estilizar_entry(cuerpo, placeholder_text=placeholder)
            if valor:
                e.insert(0, valor)
            e.pack(fill="x", padx=10)
            return e

        e_cod = campo("Código de barras (escanea aquí) *", "Escanea el libro físico...")
        e_isbn = campo("ISBN (si ya existe, solo agrega la copia) *", "Ej. 978607...")
        e_titulo = campo("Título *")

        ctk.CTkLabel(cuerpo, text="Autor *", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10, pady=(6, 2))
        opt_aut = estilizar_optionmenu(cuerpo, list(mapa_aut.keys()))
        opt_aut.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Categoría *", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(6, 2)
        )
        opt_cat = estilizar_optionmenu(cuerpo, list(mapa_cat.keys()))
        opt_cat.pack(fill="x", padx=10)

        e_editorial = campo("Editorial *")
        e_anio = campo("Año de publicación *", valor="2024")
        e_ubic = campo("Ubicación física *", valor="Estantería General")

        def al_escanear(_e):
            if not e_isbn.get().strip():
                e_isbn.insert(0, e_cod.get().strip()[:13])
            e_titulo.focus_set()

        e_cod.bind("<Return>", al_escanear)
        win.after(120, e_cod.focus_set)

        def guardar():
            if not e_isbn.get().strip() or not e_titulo.get().strip() or not e_editorial.get().strip():
                messagebox.showwarning("Campos obligatorios", "ISBN, título y editorial son obligatorios.", parent=win)
                return
            try:
                anio = int(e_anio.get().strip())
            except ValueError:
                messagebox.showwarning("Año inválido", "Ingresa un año numérico válido.", parent=win)
                return
            try:
                res = self.service.registrar_libro_y_ejemplar(
                    e_isbn.get(),
                    e_titulo.get(),
                    mapa_aut[opt_aut.get()],
                    mapa_cat[opt_cat.get()],
                    e_editorial.get(),
                    anio,
                    e_cod.get(),
                    e_ubic.get() or "Estantería General",
                )
                if res["exito"]:
                    messagebox.showinfo("Éxito", f"Ejemplar #{res['id_ejemplar']}\n{res['mensaje']}", parent=win)
                    win.destroy()
                    self._cargar_libros()
                    self._cargar_ejemplares()
                else:
                    messagebox.showerror("Error", res["mensaje"], parent=win)
            except Exception as ex:
                self._manejar_error(ex, parent=win)

        ctk.CTkButton(
            pie,
            text="Cancelar",
            width=110,
            height=36,
            fg_color=COLOR_PAPER,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=win.destroy,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(
            pie,
            text="Registrar con Transacción",
            height=36,
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=guardar,
        ).pack(side="right", fill="x", expand=True, padx=(0, 16), pady=10)

    def _editar_libro_seleccionado(self):
        sel = self.tree_libros.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un libro de la tabla.")
            return
        id_libro = int(self.tree_libros.item(sel[0], "values")[0])
        libro = next((l for l in self._cache_libros if l["id_libro"] == id_libro), None)
        if libro:
            self._dialogo_libro(libro)

    def _eliminar_libro_seleccionado(self):
        sel = self.tree_libros.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un libro para eliminar.")
            return
        vals = self.tree_libros.item(sel[0], "values")
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el libro '{vals[2]}'?"):
            return
        try:
            res = self.service.eliminar_libro(int(vals[0]))
            if res["exito"]:
                messagebox.showinfo("Eliminado", res["mensaje"])
                self._cargar_libros()
            else:
                messagebox.showerror("No permitido", res["mensaje"])
        except Exception as e:
            self._manejar_error(e)

    def _dialogo_nuevo_ejemplar(self):
        libros = self.service.listar_libros()
        if not libros:
            messagebox.showwarning("Sin libros", "Registra primero un libro.")
            return

        win, cuerpo, pie = crear_modal_scrollable(self, "Agregar Ejemplar a Libro Existente", 460, 350)
        mapa_lib = {f"{l['id_libro']} - {l['titulo']}": l["id_libro"] for l in libros}

        ctk.CTkLabel(cuerpo, text="Libro", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10, pady=(6, 2))
        opt_lib = estilizar_optionmenu(cuerpo, list(mapa_lib.keys()))
        opt_lib.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Código de barras (escanea aquí)", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(10, 2)
        )
        e_cod = estilizar_entry(cuerpo, placeholder_text="Escanea o escribe el código...")
        e_cod.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Ubicación", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(10, 2)
        )
        e_ubic = estilizar_entry(cuerpo)
        e_ubic.insert(0, "Estantería General")
        e_ubic.pack(fill="x", padx=10)

        win.after(120, e_cod.focus_set)

        def guardar():
            # Se envía tal cual el código para permitir demostrar trg_validar_codigo_barras en MySQL
            try:
                res = self.service.crear_ejemplar(
                    mapa_lib[opt_lib.get()], e_cod.get(), e_ubic.get() or "Estantería General"
                )
                if res["exito"]:
                    messagebox.showinfo("Éxito", res["mensaje"], parent=win)
                    win.destroy()
                    self._cargar_ejemplares()
                    self._cargar_libros()
                else:
                    messagebox.showerror("Error", res["mensaje"], parent=win)
            except Exception as ex:
                self._manejar_error(ex, parent=win)

        ctk.CTkButton(
            pie,
            text="Cancelar",
            width=110,
            height=36,
            fg_color=COLOR_PAPER,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=win.destroy,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(
            pie,
            text="Guardar Ejemplar",
            height=36,
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=guardar,
        ).pack(side="right", fill="x", expand=True, padx=(0, 16), pady=10)

    def _dialogo_editar_ejemplar(self):
        sel = self.tree_ejemplares.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un ejemplar de la tabla.")
            return
        vals = self.tree_ejemplares.item(sel[0], "values")
        id_ej, cod, titulo, ubic_actual, estado_actual = int(vals[0]), vals[1], vals[2], vals[3], vals[4]

        win, cuerpo, pie = crear_modal_scrollable(self, f"Editar Ejemplar #{id_ej}", 450, 330)

        ctk.CTkLabel(
            cuerpo,
            text=f"{titulo}\nCódigo: {cod}",
            justify="left",
            text_color=COLOR_ESPRESSO,
            font=ctk.CTkFont(family="Georgia", size=14, weight="bold"),
            wraplength=390,
        ).pack(anchor="w", padx=10, pady=(6, 10))

        ctk.CTkLabel(cuerpo, text="Ubicación", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10)
        e_ubic = estilizar_entry(cuerpo)
        e_ubic.insert(0, ubic_actual)
        e_ubic.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkLabel(cuerpo, text="Estado", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10)
        opt_est = estilizar_optionmenu(cuerpo, ["DISPONIBLE", "PRESTADO", "MANTENIMIENTO", "BAJA"])
        opt_est.set(estado_actual)
        opt_est.pack(fill="x", padx=10, pady=(2, 10))

        def guardar():
            if not e_ubic.get().strip():
                messagebox.showwarning("Ubicación requerida", "Indica la ubicación física del ejemplar.", parent=win)
                return
            try:
                res = self.service.actualizar_ejemplar(id_ej, e_ubic.get(), opt_est.get())
                if res["exito"]:
                    messagebox.showinfo("Actualizado", res["mensaje"], parent=win)
                    win.destroy()
                    self._cargar_ejemplares()
                    self._cargar_libros()
                else:
                    messagebox.showerror("Error", res["mensaje"], parent=win)
            except Exception as ex:
                self._manejar_error(ex, parent=win)

        ctk.CTkButton(
            pie,
            text="Cancelar",
            width=110,
            height=36,
            fg_color=COLOR_PAPER,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=win.destroy,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(
            pie,
            text="Guardar Cambios",
            height=36,
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=guardar,
        ).pack(side="right", fill="x", expand=True, padx=(0, 16), pady=10)

    def _eliminar_ejemplar_seleccionado(self):
        sel = self.tree_ejemplares.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un ejemplar para eliminar.")
            return
        vals = self.tree_ejemplares.item(sel[0], "values")
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el ejemplar con código '{vals[1]}'?"):
            return
        try:
            res = self.service.eliminar_ejemplar(int(vals[0]))
            if res["exito"]:
                messagebox.showinfo("Eliminado", res["mensaje"])
                self._cargar_ejemplares()
                self._cargar_libros()
            else:
                messagebox.showerror("No permitido", res["mensaje"])
        except Exception as e:
            self._manejar_error(e)

    # ------------------------------------------------------------------
    # VISTA 3: LECTORES (ADMIN / OPERADOR)
    # ------------------------------------------------------------------
    def _vista_lectores(self):
        self._crear_encabezado(
            "Administración de Lectores",
            "Registra alumnos, docentes o externos y controla si su credencial está activa para préstamos.",
        )

        form = ctk.CTkFrame(
            self.contenido, fg_color=COLOR_PAPER, corner_radius=14, border_width=1, border_color=COLOR_BORDER
        )
        form.pack(fill="x", padx=20, pady=(2, 8))

        f1 = ctk.CTkFrame(form, fg_color="transparent")
        f1.pack(fill="x", padx=14, pady=(10, 6))

        self.e_lec_mat = estilizar_entry(f1, width=130, placeholder_text="Matrícula *")
        self.e_lec_mat.pack(side="left", padx=4)
        self.e_lec_nom = estilizar_entry(f1, width=210, placeholder_text="Nombre completo *")
        self.e_lec_nom.pack(side="left", fill="x", expand=True, padx=4)
        self.e_lec_cor = estilizar_entry(f1, width=200, placeholder_text="Correo electrónico *")
        self.e_lec_cor.pack(side="left", fill="x", expand=True, padx=4)

        f2 = ctk.CTkFrame(form, fg_color="transparent")
        f2.pack(fill="x", padx=14, pady=(0, 10))

        self.e_lec_tel = estilizar_entry(f2, width=140, placeholder_text="Teléfono")
        self.e_lec_tel.pack(side="left", padx=4)
        self.opt_lec_tipo = estilizar_optionmenu(f2, ["ALUMNO", "DOCENTE", "EXTERNO"], width=130)
        self.opt_lec_tipo.pack(side="left", padx=4)

        ctk.CTkButton(
            f2,
            text="Registrar Lector",
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=self._crear_lector,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            f2,
            text="Activar / Desactivar Seleccionado",
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=self._toggle_lector,
        ).pack(side="right", padx=4)

        self.tree_lectores = crear_tabla(
            self.contenido,
            [
                ("id_lector", "ID", 50),
                ("matricula", "Matrícula", 110),
                ("nombre_completo", "Nombre Completo", 220),
                ("correo", "Correo", 220),
                ("telefono", "Teléfono", 110),
                ("tipo", "Tipo", 90),
                ("activo", "Estado", 85),
            ],
        )
        self._cargar_lectores()

    def _cargar_lectores(self):
        try:
            lectores = self.service.listar_lectores()
            filas = []
            for lec in lectores:
                copia = dict(lec)
                copia["activo"] = "ACTIVO" if lec["activo"] else "INACTIVO"
                filas.append(copia)
            llenar_tabla(
                self.tree_lectores,
                filas,
                ["id_lector", "matricula", "nombre_completo", "correo", "telefono", "tipo", "activo"],
            )
        except Exception as e:
            self._manejar_error(e)

    def _crear_lector(self):
        mat = self.e_lec_mat.get().strip()
        nom = self.e_lec_nom.get().strip()
        cor = self.e_lec_cor.get().strip()
        tel = self.e_lec_tel.get().strip()
        if not mat or not nom or not cor:
            messagebox.showwarning("Campos obligatorios", "Matrícula, nombre y correo son obligatorios.")
            return
        try:
            self.service.crear_lector(mat, nom, cor, tel, self.opt_lec_tipo.get())
            for e in (self.e_lec_mat, self.e_lec_nom, self.e_lec_cor, self.e_lec_tel):
                e.delete(0, "end")
            self._cargar_lectores()
            messagebox.showinfo("Lector", "Lector registrado correctamente.")
        except Exception as e:
            self._manejar_error(e)

    def _toggle_lector(self):
        sel = self.tree_lectores.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un lector de la tabla.")
            return
        vals = self.tree_lectores.item(sel[0], "values")
        nuevo_estado = vals[6] != "ACTIVO"
        etiqueta = "ACTIVO" if nuevo_estado else "INACTIVO"
        try:
            self.service.actualizar_estado_lector(int(vals[0]), nuevo_estado)
            self._cargar_lectores()
            messagebox.showinfo("Estado actualizado", f"El lector '{vals[2]}' ahora está {etiqueta}.")
        except Exception as e:
            self._manejar_error(e)

    # ------------------------------------------------------------------
    # VISTA 4: REPORTES AVANZADOS (VISTAS SQL)
    # ------------------------------------------------------------------
    def _vista_reportes(self):
        cab = self._crear_encabezado(
            "Reportes Avanzados",
            "Consultas con vistas SQL, CTE, DENSE_RANK, EXISTS, agregaciones y funciones almacenadas.",
        )
        ctk.CTkButton(
            cab,
            text="Actualizar Reportes",
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=self._cargar_reportes,
        ).pack(side="right", pady=6)

        tabs = self._crear_tabview()
        tab1 = tabs.add("Libros Más Solicitados")
        tab2 = tabs.add("Lectores con Préstamos Vencidos")

        self.lbl_resumen_rep1 = ctk.CTkLabel(
            tab1, text="", text_color=COLOR_COCOA, font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        )
        self.lbl_resumen_rep1.pack(fill="x", padx=16, pady=(6, 0))

        self.tree_rep_libros = crear_tabla(
            tab1,
            [
                ("ranking", "Rank", 55),
                ("isbn", "ISBN", 125),
                ("titulo", "Título", 240),
                ("autor", "Autor", 160),
                ("categoria", "Categoría", 130),
                ("total_prestamos", "Total Préstamos", 115),
                ("ejemplares_usados", "Ejemplares Usados", 120),
                ("disponibles_actualmente", "Disponibles Hoy", 110),
            ],
        )

        self.lbl_resumen_rep2 = ctk.CTkLabel(
            tab2, text="", text_color=COLOR_COCOA, font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        )
        self.lbl_resumen_rep2.pack(fill="x", padx=16, pady=(6, 0))

        self.tree_rep_vencidos = crear_tabla(
            tab2,
            [
                ("matricula", "Matrícula", 105),
                ("lector", "Lector", 180),
                ("tipo", "Tipo", 85),
                ("correo", "Correo", 190),
                ("prestamos_vencidos", "Vencidos", 75),
                ("max_dias_retraso", "Máx. Retraso (días)", 130),
                ("libros_pendientes", "Libros Pendientes [Código]", 300),
            ],
        )
        self._cargar_reportes()

    def _cargar_reportes(self):
        try:
            rep_libros = self.service.reporte_libros_mas_solicitados()
            llenar_tabla(
                self.tree_rep_libros,
                rep_libros,
                [
                    "ranking",
                    "isbn",
                    "titulo",
                    "autor",
                    "categoria",
                    "total_prestamos",
                    "ejemplares_usados",
                    "disponibles_actualmente",
                ],
            )
            self.lbl_resumen_rep1.configure(
                text=f"Mostrando {len(rep_libros)} título(s) con historial de préstamos."
                if rep_libros
                else "Aún no hay préstamos registrados para calcular el ranking."
            )

            rep_venc = self.service.reporte_lectores_vencidos()
            llenar_tabla(
                self.tree_rep_vencidos,
                rep_venc,
                [
                    "matricula",
                    "lector",
                    "tipo",
                    "correo",
                    "prestamos_vencidos",
                    "max_dias_retraso",
                    "libros_pendientes",
                ],
            )
            self.lbl_resumen_rep2.configure(
                text=f"Atención: {len(rep_venc)} lector(es) con préstamos vencidos actualmente."
                if rep_venc
                else "Excelente: no hay lectores con préstamos vencidos en este momento.",
                text_color=COLOR_BRICK if rep_venc else COLOR_SAGE,
            )
        except Exception as e:
            self._manejar_error(e)

    # ------------------------------------------------------------------
    # VISTA 5: USUARIOS DEL SISTEMA (SOLO ADMIN)
    # ------------------------------------------------------------------
    def _vista_usuarios(self):
        self._crear_encabezado(
            "Usuarios y Seguridad",
            "Gestiona cuentas de acceso, roles (ADMIN, OPERADOR, CONSULTA) y contraseñas con hash SHA-256.",
        )

        barra = ctk.CTkFrame(self.contenido, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(2, 4))

        ctk.CTkButton(
            barra,
            text="+ Nuevo Usuario",
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self._dialogo_usuario(),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            barra,
            text="Editar Seleccionado",
            fg_color=COLOR_AMBER,
            hover_color=COLOR_AMBER_HOVER,
            text_color=COLOR_PAPER,
            command=self._editar_usuario,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            barra,
            text="Refrescar",
            width=95,
            fg_color=COLOR_SAND,
            hover_color=COLOR_HONEY,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self._cargar_usuarios,
        ).pack(side="left")
        ctk.CTkButton(
            barra,
            text="Eliminar",
            width=95,
            fg_color=COLOR_BRICK,
            hover_color=COLOR_BRICK_HOVER,
            text_color=COLOR_PAPER,
            command=self._eliminar_usuario,
        ).pack(side="right")

        self.tree_usuarios = crear_tabla(
            self.contenido,
            [
                ("id_usuario", "ID", 55),
                ("nombre_completo", "Nombre Completo", 230),
                ("username", "Usuario", 130),
                ("rol", "Rol", 100),
                ("activo", "Estado", 90),
                ("fecha_creacion", "Fecha Creación", 150),
            ],
        )
        self.tree_usuarios.bind("<Double-1>", lambda _e: self._editar_usuario())
        self._cargar_usuarios()

    def _cargar_usuarios(self):
        try:
            self._cache_usuarios = self.service.listar_usuarios()
            filas = []
            for u in self._cache_usuarios:
                copia = dict(u)
                copia["activo"] = "ACTIVO" if u["activo"] else "INACTIVO"
                filas.append(copia)
            llenar_tabla(
                self.tree_usuarios,
                filas,
                ["id_usuario", "nombre_completo", "username", "rol", "activo", "fecha_creacion"],
            )
        except Exception as e:
            self._manejar_error(e)

    def _dialogo_usuario(self, usuario_actual: dict | None = None):
        win, cuerpo, pie = crear_modal_scrollable(
            self, "Editar Usuario" if usuario_actual else "Nuevo Usuario", 450, 450
        )

        ctk.CTkLabel(cuerpo, text="Nombre completo *", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(6, 2)
        )
        e_nom = estilizar_entry(cuerpo)
        e_nom.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Nombre de usuario (login) *", text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(10, 2)
        )
        e_user = estilizar_entry(cuerpo)
        e_user.pack(fill="x", padx=10)

        lbl_pw = "Nueva contraseña (dejar vacío para conservar)" if usuario_actual else "Contraseña (mín. 4 caracteres) *"
        ctk.CTkLabel(cuerpo, text=lbl_pw, text_color=COLOR_ESPRESSO, anchor="w").pack(
            fill="x", padx=10, pady=(10, 2)
        )
        e_pw = estilizar_entry(cuerpo, show="•")
        e_pw.pack(fill="x", padx=10)

        ctk.CTkLabel(cuerpo, text="Rol *", text_color=COLOR_ESPRESSO, anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        opt_rol = estilizar_optionmenu(cuerpo, ["ADMIN", "OPERADOR", "CONSULTA"])
        opt_rol.pack(fill="x", padx=10)

        var_activo = tk.BooleanVar(value=True)
        if usuario_actual:
            e_nom.insert(0, usuario_actual["nombre_completo"])
            e_user.insert(0, usuario_actual["username"])
            opt_rol.set(usuario_actual["rol"])
            var_activo.set(bool(usuario_actual["activo"]))
            ctk.CTkCheckBox(
                cuerpo,
                text="Cuenta activa",
                variable=var_activo,
                text_color=COLOR_ESPRESSO,
                fg_color=COLOR_CARAMEL,
                hover_color=COLOR_CARAMEL_HOVER,
                border_color=COLOR_ESPRESSO,
            ).pack(anchor="w", padx=10, pady=(12, 4))

        def guardar():
            if not e_nom.get().strip() or not e_user.get().strip():
                messagebox.showwarning(
                    "Campos obligatorios", "Nombre completo y nombre de usuario son obligatorios.", parent=win
                )
                return
            try:
                if usuario_actual:
                    res = self.service.actualizar_usuario(
                        usuario_actual["id_usuario"],
                        e_nom.get(),
                        e_user.get(),
                        opt_rol.get(),
                        var_activo.get(),
                        e_pw.get() or None,
                    )
                else:
                    res = self.service.crear_usuario(e_nom.get(), e_user.get(), e_pw.get(), opt_rol.get())
                if res["exito"]:
                    messagebox.showinfo("Éxito", res["mensaje"], parent=win)
                    win.destroy()
                    self._cargar_usuarios()
                else:
                    messagebox.showerror("Error", res["mensaje"], parent=win)
            except Exception as ex:
                self._manejar_error(ex, parent=win)

        ctk.CTkButton(
            pie,
            text="Cancelar",
            width=110,
            height=36,
            fg_color=COLOR_PAPER,
            hover_color=COLOR_BORDER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            command=win.destroy,
        ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(
            pie,
            text="Guardar Usuario",
            height=36,
            fg_color=COLOR_SAGE,
            hover_color=COLOR_SAGE_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=guardar,
        ).pack(side="right", fill="x", expand=True, padx=(0, 16), pady=10)

    def _editar_usuario(self):
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un usuario de la tabla.")
            return
        id_u = int(self.tree_usuarios.item(sel[0], "values")[0])
        usr = next((u for u in self._cache_usuarios if u["id_usuario"] == id_u), None)
        if usr:
            self._dialogo_usuario(usr)

    def _eliminar_usuario(self):
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showinfo("Selección", "Selecciona un usuario para eliminar.")
            return
        vals = self.tree_usuarios.item(sel[0], "values")
        if not messagebox.askyesno("Confirmar", f"¿Eliminar al usuario '{vals[2]}'?"):
            return
        try:
            res = self.service.eliminar_usuario(int(vals[0]))
            if res["exito"]:
                messagebox.showinfo("Eliminado", res["mensaje"])
                self._cargar_usuarios()
            else:
                messagebox.showerror("No permitido", res["mensaje"])
        except Exception as e:
            self._manejar_error(e)

    # ------------------------------------------------------------------
    # VISTA 6: AUDITORÍA (SOLO ADMIN)
    # ------------------------------------------------------------------
    def _vista_auditoria(self):
        cab = self._crear_encabezado(
            "Bitácora de Auditoría",
            "Registro automático generado por triggers de MySQL con valores anteriores y nuevos en JSON.",
        )

        self.opt_limite = estilizar_optionmenu(
            cab, ["30", "100", "250"], width=85, command=lambda _v: self._cargar_auditoria()
        )
        self.opt_limite.set("30")
        self.opt_limite.pack(side="right", padx=(6, 0), pady=6)
        ctk.CTkButton(
            cab,
            text="Refrescar",
            width=95,
            fg_color=COLOR_CARAMEL,
            hover_color=COLOR_CARAMEL_HOVER,
            text_color=COLOR_PAPER,
            font=ctk.CTkFont(weight="bold"),
            command=self._cargar_auditoria,
        ).pack(side="right", pady=6)

        self.tree_auditoria = crear_tabla(
            self.contenido,
            [
                ("id_movimiento", "ID", 55),
                ("fecha_hora", "Fecha y Hora", 145),
                ("usuario_responsable", "Usuario", 120),
                ("tabla_afectada", "Tabla", 100),
                ("tipo_operacion", "Operación", 85),
                ("datos_anteriores", "Datos Anteriores", 250),
                ("datos_nuevos", "Datos Nuevos", 250),
            ],
        )
        self.tree_auditoria.bind("<<TreeviewSelect>>", self._mostrar_detalle_auditoria)

        self.txt_detalle_audit = ctk.CTkTextbox(
            self.contenido,
            height=135,
            fg_color=COLOR_PAPER,
            text_color=COLOR_ESPRESSO,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            font=("Consolas", 11),
        )
        self.txt_detalle_audit.pack(fill="x", padx=14, pady=(0, 12))
        self.txt_detalle_audit.insert("1.0", "Selecciona un movimiento de la tabla para ver el detalle completo.")
        self.txt_detalle_audit.configure(state="disabled")

        self._cargar_auditoria()

    def _cargar_auditoria(self):
        try:
            limite = int(self.opt_limite.get())
            datos = self.service.consultar_auditoria(limite)
            llenar_tabla(
                self.tree_auditoria,
                datos,
                [
                    "id_movimiento",
                    "fecha_hora",
                    "usuario_responsable",
                    "tabla_afectada",
                    "tipo_operacion",
                    "datos_anteriores",
                    "datos_nuevos",
                ],
            )
        except Exception as e:
            self._manejar_error(e)

    def _mostrar_detalle_auditoria(self, _event):
        sel = self.tree_auditoria.selection()
        if not sel:
            return
        vals = self.tree_auditoria.item(sel[0], "values")
        anterior = formatear_json_legible(vals[5])
        nuevo = formatear_json_legible(vals[6])
        detalle = (
            f"Movimiento #{vals[0]} | {vals[1]} | Usuario: {vals[2]} | Tabla: {vals[3]} ({vals[4]})\n"
            f"--- DATOS ANTERIORES ---\n{anterior}\n"
            f"--- DATOS NUEVOS ---\n{nuevo}"
        )
        self.txt_detalle_audit.configure(state="normal")
        self.txt_detalle_audit.delete("1.0", "end")
        self.txt_detalle_audit.insert("1.0", detalle)
        self.txt_detalle_audit.configure(state="disabled")


# ======================================================================
# VENTANA PRINCIPAL DE LA APLICACIÓN
# ======================================================================
class BibliotecaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión de Biblioteca - Taller de Bases de Datos")

        ancho, alto = 1240, 740
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        ancho = min(ancho, sw - 40)
        alto = min(alto, sh - 80)
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(980, 620)
        self.configure(fg_color=COLOR_CREAM)
        configurar_estilo_treeview()

        self.vista_actual = None
        self.mostrar_login()

    def _cambiar_pantalla(self, nuevo_frame):
        if self.vista_actual is not None:
            self.vista_actual.destroy()
        self.vista_actual = nuevo_frame
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_login(self):
        self._cambiar_pantalla(LoginFrame(self, on_login_success=self.mostrar_principal))

    def mostrar_principal(self, sesion: SesionUsuario):
        self._cambiar_pantalla(MainFrame(self, sesion=sesion, on_logout=self.mostrar_login))