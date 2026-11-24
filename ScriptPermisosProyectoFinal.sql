CREATE ROLE 'rol_bib_admin', 'rol_bib_operador', 'rol_bib_consulta';

-- Permisos de Administrador
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON biblioteca_db.* TO 'rol_bib_admin';

-- Permisos de Operador
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.libros TO 'rol_bib_operador';
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.ejemplares TO 'rol_bib_operador';
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.autores TO 'rol_bib_operador';
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.categorias TO 'rol_bib_operador';
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.lectores TO 'rol_bib_operador';
GRANT SELECT, INSERT, UPDATE ON biblioteca_db.prestamos TO 'rol_bib_operador';
GRANT SELECT ON biblioteca_db.vw_reporte_libros_mas_solicitados TO 'rol_bib_operador';
GRANT SELECT ON biblioteca_db.vw_reporte_lectores_vencidos TO 'rol_bib_operador';
GRANT EXECUTE ON biblioteca_db.* TO 'rol_bib_operador';

-- Permisos de Consulta
GRANT SELECT ON biblioteca_db.libros TO 'rol_bib_consulta';
GRANT SELECT ON biblioteca_db.ejemplares TO 'rol_bib_consulta';
GRANT SELECT ON biblioteca_db.autores TO 'rol_bib_consulta';
GRANT SELECT ON biblioteca_db.categorias TO 'rol_bib_consulta';
GRANT SELECT ON biblioteca_db.vw_reporte_libros_mas_solicitados TO 'rol_bib_consulta';
GRANT SELECT ON biblioteca_db.vw_reporte_lectores_vencidos TO 'rol_bib_consulta';
GRANT EXECUTE ON PROCEDURE biblioteca_db.sp_consultar_ejemplar_por_codigo TO 'rol_bib_consulta';

-- Usuarios de base de datos 
CREATE USER 'bib_admin'@'%' IDENTIFIED BY 'BibAdmin';
CREATE USER 'bib_operador'@'%' IDENTIFIED BY 'BibOper';
CREATE USER 'bib_consulta'@'%' IDENTIFIED BY 'BibCons';

GRANT 'rol_bib_admin' TO 'bib_admin'@'%';
GRANT 'rol_bib_operador' TO 'bib_operador'@'%';
GRANT 'rol_bib_consulta' TO 'bib_consulta'@'%';

SET DEFAULT ROLE ALL TO 'bib_admin'@'%', 'bib_operador'@'%', 'bib_consulta'@'%';