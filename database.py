import os
from urllib.parse import urlparse

import psycopg2


def conectar():
    try:
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            parsed = urlparse(database_url)
            conexion = psycopg2.connect(
                host=parsed.hostname or os.getenv("DB_HOST", "localhost"),
                database=parsed.path.lstrip("/") or os.getenv("DB_NAME", "refaccionaria_v2"),
                user=parsed.username or os.getenv("DB_USER", "postgres"),
                password=parsed.password or os.getenv("DB_PASSWORD", "Luisito2003"),
                port=parsed.port or os.getenv("DB_PORT", 5432),
                sslmode=os.getenv("DB_SSLMODE", "require"),
            )
        else:
            conexion = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "refaccionaria_v2"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "Luisito2003"),
                port=os.getenv("DB_PORT", 5432),
                sslmode=os.getenv("DB_SSLMODE", "disable"),
            )

        return conexion

    except Exception as e:
        print("Error al conectar:")
        print(e)
        return None
