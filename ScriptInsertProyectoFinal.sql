USE biblioteca_db;

SET @app_usuario = 'sistema_seed';

INSERT INTO usuarios (nombre_completo, username, password_hash, rol, activo) VALUES
('Administrador General', 'admin', 'PENDIENTE_BCRYPT', 'ADMIN', 1),
('Bibliotecario Turno Matutino', 'operador', 'PENDIENTE_BCRYPT', 'OPERADOR', 1),
('Usuario Consulta', 'consulta', 'PENDIENTE_BCRYPT', 'CONSULTA', 1);

INSERT INTO categorias (nombre) VALUES
('Novela Histórica'),
('Literatura Juvenil'),
('Suspenso'),
('Poesía');

INSERT INTO autores (nombre_completo) VALUES
('Antonio Velasco Piña'),
('Judith Kerr'),
('Jürgen Banscherus'),
('Margarito Ledesma (Leobino Zavala)');

INSERT INTO libros (isbn, titulo, id_autor, id_categoria, editorial, anio_publicacion) VALUES
('9789684230071', 'Tlacaelel: El azteca entre los aztecas', 1, 1, 'Editorial Jus', 1979),
('9788434585805', 'Cuando Hitler robó el Conejo Rosa', 2, 2, 'Salvat Alfaguara', 1986),
('9786074714210', 'El aviso', 3, 3, 'Ediciones SM (Gran Angular)', 2009),
('9786079392192', 'Poesías', 4, 4, 'Instituto Estatal de la Cultura de Guanajuato', 2014);

INSERT INTO ejemplares (id_libro, codigo_barras, ubicacion, estado) VALUES
(1, '9789684230071', 'Pasillo A - Historia de México', 'DISPONIBLE'),
(2, '9788434585805', 'Pasillo B - Biblioteca Juvenil', 'DISPONIBLE'),
(3, '9786074714210', 'Pasillo B - Suspenso Juvenil', 'DISPONIBLE'),
(4, '9786079392192', 'Pasillo C - Clásicos de Guanajuato', 'DISPONIBLE');

INSERT INTO lectores (matricula, nombre_completo, correo, telefono, tipo) VALUES
('ISC2026001', 'Carlos Mendoza López', 'carlos.mendoza@uni.edu.mx', '4451001122', 'ALUMNO'),
('ISC2026002', 'Ana Sofía Ramírez', 'ana.ramirez@uni.edu.mx', '4451003344', 'ALUMNO'),
('DOC2026010', 'Mtro. Luis Herrera', 'luis.herrera@uni.edu.mx', '4451005566', 'DOCENTE');

INSERT INTO prestamos (id_ejemplar, id_lector, id_usuario_registro, fecha_prestamo, fecha_limite, fecha_devolucion, estado)
VALUES (1, 1, 1, DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_SUB(NOW(), INTERVAL 13 DAY), DATE_SUB(NOW(), INTERVAL 14 DAY), 'DEVUELTO');


INSERT INTO prestamos (id_ejemplar, id_lector, id_usuario_registro, fecha_prestamo, fecha_limite, estado)
VALUES (2, 1, 2, DATE_SUB(NOW(), INTERVAL 15 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY), 'ACTIVO');
UPDATE ejemplares SET estado = 'PRESTADO' WHERE id_ejemplar = 2;


INSERT INTO prestamos (id_ejemplar, id_lector, id_usuario_registro, fecha_prestamo, fecha_limite, estado)
VALUES (3, 2, 2, DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY), 'ACTIVO');
UPDATE ejemplares SET estado = 'PRESTADO' WHERE id_ejemplar = 3;

USE biblioteca_db;
UPDATE usuarios SET password_hash = SHA2('Admin123!', 256) WHERE username = 'admin';
UPDATE usuarios SET password_hash = SHA2('Operador123!', 256) WHERE username = 'operador';
UPDATE usuarios SET password_hash = SHA2('Consulta123!', 256) WHERE username = 'consulta';
