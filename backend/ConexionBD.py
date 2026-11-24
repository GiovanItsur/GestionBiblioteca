import mysql.connector

DB_CONFIG = {

    "host": "tbdiuhg.mysql.database.azure.com",
    "port": 3306,
    "user": "Admin",
    "password": "12345root#",
    "database": "biblioteca_db",
    "autocommit": True,
    "ssl_disabled": False,
    "ssl_verify_cert": False,
}

def get_connection(app_username: str | None = None):
    """Abre conexión SSL hacia Azure MySQL y fija @app_usuario para auditoría."""
    conn = mysql.connector.connect(**DB_CONFIG)
    if app_username:
        with conn.cursor() as cur:
            cur.execute("SET @app_usuario = %s", (app_username,))
    return conn


if __name__ == "__main__":
    try:
        cn = get_connection("prueba_conexion")
        print("Conexión exitosa a Azure MySQL:", cn.is_connected())
        cn.close()
    except Exception as e:
        print("Error al conectar a Azure MySQL:", e)