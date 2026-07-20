import psycopg2

def conectar():
    try:
        conexion = psycopg2.connect(
            host="localhost",
            database="refaccionaria_v2",
            user="postgres",
            password="Luisito2003"
        )

        return conexion

    except Exception as e:
        print("Error al conectar:")
        print(e)
        return None
