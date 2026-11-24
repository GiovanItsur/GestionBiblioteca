USE biblioteca_db;

DELIMITER //

CREATE FUNCTION fn_calcular_dias_retraso(p_id_prestamo INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_fecha_limite DATETIME;
    DECLARE v_fecha_devolucion DATETIME;
    DECLARE v_dias INT DEFAULT 0;

    SELECT fecha_limite, fecha_devolucion
    INTO v_fecha_limite, v_fecha_devolucion
    FROM prestamos
    WHERE id_prestamo = p_id_prestamo;

    IF v_fecha_limite IS NULL THEN
        RETURN 0;
    END IF;

    SET v_dias = DATEDIFF(COALESCE(DATE(v_fecha_devolucion), CURDATE()), DATE(v_fecha_limite));
    RETURN IF(v_dias > 0, v_dias, 0);
END //

CREATE FUNCTION fn_contar_ejemplares_disponibles(p_id_libro INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*) INTO v_total
    FROM ejemplares
    WHERE id_libro = p_id_libro AND estado = 'DISPONIBLE';
    RETURN v_total;
END //



CREATE FUNCTION fn_ejemplar_disponible(p_codigo_barras VARCHAR(50))
RETURNS TINYINT(1)
READS SQL DATA
BEGIN
    DECLARE v_disponible TINYINT(1) DEFAULT 0;
    SELECT IF(estado = 'DISPONIBLE', 1, 0)
    INTO v_disponible
    FROM ejemplares
    WHERE codigo_barras = TRIM(p_codigo_barras)
    LIMIT 1;
    RETURN IFNULL(v_disponible, 0);
END //


CREATE TRIGGER trg_validar_codigo_barras
BEFORE INSERT ON ejemplares
FOR EACH ROW
BEGIN
    SET NEW.codigo_barras = TRIM(NEW.codigo_barras);
    IF NEW.codigo_barras = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El código de barras no puede estar vacío.';
    END IF;
END //

-- Impide prestar un ejemplar no disponible o a un lector inactivo


CREATE TRIGGER trg_validar_prestamo_disponible
BEFORE INSERT ON prestamos
FOR EACH ROW
BEGIN
    DECLARE v_estado_ejemplar VARCHAR(20);
    DECLARE v_lector_activo TINYINT(1);

    SELECT estado INTO v_estado_ejemplar
    FROM ejemplares
    WHERE id_ejemplar = NEW.id_ejemplar;

    IF v_estado_ejemplar IS NULL OR v_estado_ejemplar <> 'DISPONIBLE' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El ejemplar no está disponible para préstamo.';
    END IF;

    SELECT activo INTO v_lector_activo
    FROM lectores
    WHERE id_lector = NEW.id_lector;

    IF v_lector_activo IS NULL OR v_lector_activo = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El lector se encuentra inactivo o no existe.';
    END IF;
END //

-- Impide devolver dos veces el mismo préstamo o usar fecha de devolución inválida
CREATE TRIGGER trg_validar_devolucion
BEFORE UPDATE ON prestamos
FOR EACH ROW
BEGIN
    IF OLD.estado = 'DEVUELTO' AND NEW.estado = 'DEVUELTO' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Este préstamo ya fue devuelto anteriormente.';
    END IF;

    IF NEW.fecha_devolucion IS NOT NULL AND NEW.fecha_devolucion < OLD.fecha_prestamo THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: La fecha de devolución no puede ser anterior al préstamo.';
    END IF;
END //


CREATE TRIGGER trg_audit_ejemplares_update
AFTER UPDATE ON ejemplares
FOR EACH ROW
BEGIN
    INSERT INTO auditoria (tabla_afectada, tipo_operacion, usuario_responsable, datos_anteriores, datos_nuevos)
    VALUES (
        'ejemplares',
        'UPDATE',
        COALESCE(@app_usuario, USER()),
        JSON_OBJECT('id_ejemplar', OLD.id_ejemplar, 'codigo_barras', OLD.codigo_barras, 'estado', OLD.estado, 'ubicacion', OLD.ubicacion),
        JSON_OBJECT('id_ejemplar', NEW.id_ejemplar, 'codigo_barras', NEW.codigo_barras, 'estado', NEW.estado, 'ubicacion', NEW.ubicacion)
    );
END //

CREATE TRIGGER trg_audit_ejemplares_delete
AFTER DELETE ON ejemplares
FOR EACH ROW
BEGIN
    INSERT INTO auditoria (tabla_afectada, tipo_operacion, usuario_responsable, datos_anteriores, datos_nuevos)
    VALUES (
        'ejemplares',
        'DELETE',
        COALESCE(@app_usuario, USER()),
        JSON_OBJECT('id_ejemplar', OLD.id_ejemplar, 'codigo_barras', OLD.codigo_barras, 'estado', OLD.estado, 'ubicacion', OLD.ubicacion),
        NULL
    );
END //

CREATE TRIGGER trg_audit_prestamos_insert
AFTER INSERT ON prestamos
FOR EACH ROW
BEGIN
    INSERT INTO auditoria (tabla_afectada, tipo_operacion, usuario_responsable, datos_anteriores, datos_nuevos)
    VALUES (
        'prestamos',
        'INSERT',
        COALESCE(@app_usuario, USER()),
        NULL,
        JSON_OBJECT('id_prestamo', NEW.id_prestamo, 'id_ejemplar', NEW.id_ejemplar, 'id_lector', NEW.id_lector, 'estado', NEW.estado, 'fecha_limite', NEW.fecha_limite)
    );
END //

CREATE TRIGGER trg_audit_prestamos_update
AFTER UPDATE ON prestamos
FOR EACH ROW
BEGIN
    INSERT INTO auditoria (tabla_afectada, tipo_operacion, usuario_responsable, datos_anteriores, datos_nuevos)
    VALUES (
        'prestamos',
        'UPDATE',
        COALESCE(@app_usuario, USER()),
        JSON_OBJECT('id_prestamo', OLD.id_prestamo, 'estado', OLD.estado, 'fecha_devolucion', OLD.fecha_devolucion),
        JSON_OBJECT('id_prestamo', NEW.id_prestamo, 'estado', NEW.estado, 'fecha_devolucion', NEW.fecha_devolucion)
    );
END //


CREATE PROCEDURE sp_consultar_ejemplar_por_codigo(
    IN p_codigo_barras VARCHAR(50),
    OUT p_disponible TINYINT(1)
)
BEGIN
    SET p_disponible = fn_ejemplar_disponible(p_codigo_barras);

    SELECT
        e.id_ejemplar,
        e.codigo_barras,
        e.ubicacion,
        e.estado AS estado_ejemplar,
        l.id_libro,
        l.isbn,
        l.titulo,
        a.nombre_completo AS autor,
        c.nombre AS categoria,
        l.editorial,
        l.anio_publicacion,
        fn_contar_ejemplares_disponibles(l.id_libro) AS copias_disponibles_titulo
    FROM ejemplares e
    INNER JOIN libros l ON e.id_libro = l.id_libro
    INNER JOIN autores a ON l.id_autor = a.id_autor
    INNER JOIN categorias c ON l.id_categoria = c.id_categoria
    WHERE e.codigo_barras = TRIM(p_codigo_barras);
END //

-- Registrar préstamo con TRANSACCIÓN explícita
CREATE PROCEDURE sp_registrar_prestamo(
    IN p_codigo_barras VARCHAR(50),
    IN p_matricula_lector VARCHAR(30),
    IN p_id_usuario INT,
    IN p_dias_prestamo INT,
    OUT p_id_prestamo INT,
    OUT p_mensaje VARCHAR(255)
)
BEGIN
    DECLARE v_id_ejemplar INT;
    DECLARE v_id_lector INT;
    DECLARE v_err_msg TEXT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_err_msg = MESSAGE_TEXT;
        ROLLBACK;
        SET p_id_prestamo = NULL;
        SET p_mensaje = CONCAT('Transacción cancelada: ', v_err_msg);
    END;

    SET p_id_prestamo = NULL;

    IF p_dias_prestamo IS NULL OR p_dias_prestamo <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Los días de préstamo deben ser mayores a cero.';
    END IF;

    START TRANSACTION;

    SELECT id_ejemplar INTO v_id_ejemplar
    FROM ejemplares
    WHERE codigo_barras = TRIM(p_codigo_barras)
    FOR UPDATE;

    IF v_id_ejemplar IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Código de barras no encontrado.';
    END IF;

    SELECT id_lector INTO v_id_lector
    FROM lectores
    WHERE matricula = TRIM(p_matricula_lector);

    IF v_id_lector IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Matrícula de lector no encontrada.';
    END IF;

    INSERT INTO prestamos (id_ejemplar, id_lector, id_usuario_registro, fecha_prestamo, fecha_limite, estado)
    VALUES (v_id_ejemplar, v_id_lector, p_id_usuario, NOW(), DATE_ADD(NOW(), INTERVAL p_dias_prestamo DAY), 'ACTIVO');

    SET p_id_prestamo = LAST_INSERT_ID();

    UPDATE ejemplares
    SET estado = 'PRESTADO'
    WHERE id_ejemplar = v_id_ejemplar;

    COMMIT;
    SET p_mensaje = 'Préstamo registrado correctamente.';
END //

-- Registrar devolución con TRANSACCIÓN explícita
CREATE PROCEDURE sp_registrar_devolucion(
    IN p_codigo_barras VARCHAR(50),
    IN p_observaciones VARCHAR(255),
    OUT p_dias_retraso INT,
    OUT p_mensaje VARCHAR(255)
)
BEGIN
    DECLARE v_id_ejemplar INT;
    DECLARE v_id_prestamo INT;
    DECLARE v_err_msg TEXT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_err_msg = MESSAGE_TEXT;
        ROLLBACK;
        SET p_dias_retraso = 0;
        SET p_mensaje = CONCAT('Transacción cancelada: ', v_err_msg);
    END;

    SET p_dias_retraso = 0;

    START TRANSACTION;

    SELECT id_ejemplar INTO v_id_ejemplar
    FROM ejemplares
    WHERE codigo_barras = TRIM(p_codigo_barras)
    FOR UPDATE;

    IF v_id_ejemplar IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Código de barras no encontrado.';
    END IF;

    SELECT id_prestamo INTO v_id_prestamo
    FROM prestamos
    WHERE id_ejemplar = v_id_ejemplar AND estado IN ('ACTIVO', 'VENCIDO')
    ORDER BY fecha_prestamo DESC
    LIMIT 1
    FOR UPDATE;

    IF v_id_prestamo IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No existe un préstamo activo para este ejemplar.';
    END IF;

    UPDATE prestamos
    SET fecha_devolucion = NOW(),
        estado = 'DEVUELTO',
        observaciones = p_observaciones
    WHERE id_prestamo = v_id_prestamo;

    UPDATE ejemplares
    SET estado = 'DISPONIBLE'
    WHERE id_ejemplar = v_id_ejemplar;

    SET p_dias_retraso = fn_calcular_dias_retraso(v_id_prestamo);

    COMMIT;
    SET p_mensaje = IF(p_dias_retraso > 0,
        CONCAT('Devolución registrada con ', p_dias_retraso, ' día(s) de retraso.'),
        'Devolución registrada a tiempo.');
END //

CREATE PROCEDURE sp_registrar_ejemplar_completo(
    IN p_isbn VARCHAR(20),
    IN p_titulo VARCHAR(200),
    IN p_id_autor INT,
    IN p_id_categoria INT,
    IN p_editorial VARCHAR(100),
    IN p_anio SMALLINT,
    IN p_codigo_barras VARCHAR(50),
    IN p_ubicacion VARCHAR(80),
    OUT p_id_ejemplar INT,
    OUT p_mensaje VARCHAR(255)
)
BEGIN
    DECLARE v_id_libro INT;
    DECLARE v_err_msg TEXT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_err_msg = MESSAGE_TEXT;
        ROLLBACK;
        SET p_id_ejemplar = NULL;
        SET p_mensaje = CONCAT('Error al registrar ejemplar: ', v_err_msg);
    END;

    START TRANSACTION;

    SELECT id_libro INTO v_id_libro FROM libros WHERE isbn = TRIM(p_isbn) LIMIT 1;

    IF v_id_libro IS NULL THEN
        INSERT INTO libros (isbn, titulo, id_autor, id_categoria, editorial, anio_publicacion)
        VALUES (TRIM(p_isbn), p_titulo, p_id_autor, p_id_categoria, p_editorial, p_anio);
        SET v_id_libro = LAST_INSERT_ID();
    END IF;

    INSERT INTO ejemplares (id_libro, codigo_barras, ubicacion, estado)
    VALUES (v_id_libro, TRIM(p_codigo_barras), p_ubicacion, 'DISPONIBLE');

    SET p_id_ejemplar = LAST_INSERT_ID();

    COMMIT;
    SET p_mensaje = 'Ejemplar registrado correctamente.';
END //

DELIMITER ;

-- vissta con los libros más solicitados
CREATE OR REPLACE VIEW vw_reporte_libros_mas_solicitados AS
SELECT
    DENSE_RANK() OVER (ORDER BY COUNT(p.id_prestamo) DESC) AS ranking,
    l.isbn,
    l.titulo,
    a.nombre_completo AS autor,
    c.nombre AS categoria,
    COUNT(p.id_prestamo) AS total_prestamos,
    COUNT(DISTINCT e.id_ejemplar) AS ejemplares_usados,
    fn_contar_ejemplares_disponibles(l.id_libro) AS disponibles_actualmente
FROM libros l
INNER JOIN autores a ON l.id_autor = a.id_autor
INNER JOIN categorias c ON l.id_categoria = c.id_categoria
INNER JOIN ejemplares e ON l.id_libro = e.id_libro
INNER JOIN prestamos p ON e.id_ejemplar = p.id_ejemplar
GROUP BY l.id_libro, l.isbn, l.titulo, a.nombre_completo, c.nombre
HAVING COUNT(p.id_prestamo) >= 1
ORDER BY total_prestamos DESC, l.titulo ASC;

-- vista para lectores con préstamos vencidos 
CREATE OR REPLACE VIEW vw_reporte_lectores_vencidos AS
WITH prestamos_vencidos AS (
    SELECT
        p.id_prestamo,
        p.id_lector,
        p.id_ejemplar,
        p.fecha_prestamo,
        p.fecha_limite,
        fn_calcular_dias_retraso(p.id_prestamo) AS dias_retraso
    FROM prestamos p
    WHERE p.estado IN ('ACTIVO', 'VENCIDO')
      AND p.fecha_devolucion IS NULL
      AND p.fecha_limite < NOW()
)
SELECT
    lec.matricula,
    lec.nombre_completo AS lector,
    lec.tipo,
    lec.correo,
    COUNT(pv.id_prestamo) AS prestamos_vencidos,
    MAX(pv.dias_retraso) AS max_dias_retraso,
    GROUP_CONCAT(CONCAT(l.titulo, ' [', e.codigo_barras, ']') SEPARATOR '; ') AS libros_pendientes
FROM lectores lec
INNER JOIN prestamos_vencidos pv ON lec.id_lector = pv.id_lector
INNER JOIN ejemplares e ON pv.id_ejemplar = e.id_ejemplar
INNER JOIN libros l ON e.id_libro = l.id_libro
WHERE EXISTS (
    SELECT 1
    FROM prestamos p2
    WHERE p2.id_lector = lec.id_lector
      AND p2.fecha_devolucion IS NULL
      AND p2.fecha_limite < NOW()
)
GROUP BY lec.id_lector, lec.matricula, lec.nombre_completo, lec.tipo, lec.correo
ORDER BY max_dias_retraso DESC;

