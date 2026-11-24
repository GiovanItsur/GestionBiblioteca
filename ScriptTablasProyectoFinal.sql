CREATE DATABASE biblioteca_db;

USE biblioteca_db;

CREATE TABLE usuarios (
    id_usuario 		INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    username 		VARCHAR(50) NOT NULL UNIQUE,
    password_hash 	VARCHAR(255) NOT NULL,
    rol 			ENUM('ADMIN', 'OPERADOR', 'CONSULTA') NOT NULL DEFAULT 'CONSULTA',
    activo 			TINYINT(1) NOT NULL DEFAULT 1,
    fecha_creacion 	DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categorias (
    id_categoria 	INT AUTO_INCREMENT PRIMARY KEY,
    nombre 			VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE autores (
    id_autor 		INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE libros (
    id_libro 			INT AUTO_INCREMENT PRIMARY KEY,
    isbn 				VARCHAR(20) NOT NULL UNIQUE,
    titulo 				VARCHAR(200) NOT NULL,
    id_autor 			INT NOT NULL,
    id_categoria 		INT NOT NULL,
    editorial 			VARCHAR(100) NOT NULL,
    anio_publicacion 	SMALLINT NOT NULL,
    CONSTRAINT chk_anio_publicacion CHECK (anio_publicacion BETWEEN 1450 AND 2100),
    CONSTRAINT fk_libros_autor FOREIGN KEY (id_autor) REFERENCES autores(id_autor),
    CONSTRAINT fk_libros_categoria FOREIGN KEY (id_categoria) REFERENCES categorias(id_categoria)
);

CREATE TABLE ejemplares (
    id_ejemplar 		INT AUTO_INCREMENT PRIMARY KEY,
    id_libro 		INT NOT NULL,
    codigo_barras	VARCHAR(50) NOT NULL UNIQUE,
    ubicacion 		VARCHAR(80) NOT NULL DEFAULT 'Estantería General',
    estado 			ENUM('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'BAJA') NOT NULL DEFAULT 'DISPONIBLE',
    fecha_alta 		DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ejemplares_libro FOREIGN KEY (id_libro) REFERENCES libros(id_libro)
);

CREATE TABLE lectores (
    id_lector 			INT AUTO_INCREMENT PRIMARY KEY,
    matricula 			VARCHAR(30) NOT NULL UNIQUE,
    nombre_completo 	VARCHAR(120) NOT NULL,
    correo 				VARCHAR(120) NOT NULL UNIQUE,
    telefono 			VARCHAR(20),
    tipo 				ENUM('ALUMNO', 'DOCENTE', 'EXTERNO') NOT NULL DEFAULT 'ALUMNO',
    activo 				TINYINT(1) NOT NULL DEFAULT 1
);


CREATE TABLE prestamos (
    id_prestamo 			INT AUTO_INCREMENT PRIMARY KEY,
    id_ejemplar 			INT NOT NULL,
    id_lector 				INT NOT NULL,
    id_usuario_registro 	INT NOT NULL,
    fecha_prestamo 			DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_limite 			DATETIME NOT NULL,
    fecha_devolucion 		DATETIME NULL,
    estado 					ENUM('ACTIVO', 'DEVUELTO', 'VENCIDO') NOT NULL DEFAULT 'ACTIVO',
    observaciones 			VARCHAR(255) NULL,
    CONSTRAINT fk_prestamos_ejemplar FOREIGN KEY (id_ejemplar) REFERENCES ejemplares(id_ejemplar),
    CONSTRAINT fk_prestamos_lector FOREIGN KEY (id_lector) REFERENCES lectores(id_lector),
    CONSTRAINT fk_prestamos_usuario FOREIGN KEY (id_usuario_registro) REFERENCES usuarios(id_usuario)
);


CREATE TABLE auditoria (
    id_movimiento 			BIGINT AUTO_INCREMENT PRIMARY KEY,
    tabla_afectada 			VARCHAR(60) NOT NULL,
    tipo_operacion 			ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    fecha_hora 				DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_responsable 	VARCHAR(100) NOT NULL,
    datos_anteriores 		JSON NULL,
    datos_nuevos 			JSON NULL
);


