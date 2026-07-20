from database import conectar

conexion = conectar()

if conexion:
    print("✅ Conexión exitosa a PostgreSQL")
    conexion.close()
else:
    print("❌ No se pudo conectar")
