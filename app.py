from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import conectar
from functools import wraps

app = Flask(__name__)

app.secret_key = "refaccionaria2026"

# ===============================
# DECORADORES DE SEGURIDAD
# ===============================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if "id_usuario" not in session:
            flash("Debes iniciar sesión.", "warning")
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if "id_usuario" not in session:
            flash("Debes iniciar sesión.", "warning")
            return redirect(url_for("login"))

        if session.get("rol") != "ADMIN":
            flash("No tienes permisos para acceder a esta sección.", "danger")
            return redirect(url_for("dashboard_cajero"))

        return f(*args, **kwargs)

    return decorated


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        conexion = conectar()

        if conexion:

            cursor = conexion.cursor()

            cursor.execute("""
                SELECT
                    id_usuario,
                    usuario,
                    rol
                FROM usuarios
                WHERE usuario = %s
                AND password = %s
                AND activo = TRUE
            """, (usuario, password))

            resultado = cursor.fetchone()

            cursor.close()
            conexion.close()

            if resultado:

                session["id_usuario"] = resultado[0]
                session["usuario"] = resultado[1]
                session["rol"] = resultado[2]

                flash(f"Bienvenido {usuario}", "success")

                if session["rol"] == "ADMIN":
                    return redirect(url_for("dashboard_admin"))

                elif session["rol"] == "CAJERO":
                    return redirect(url_for("dashboard_cajero"))

            else:
                flash("Usuario o contraseña incorrectos", "danger")
                return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard_admin")
@admin_required
def dashboard_admin():

    return render_template("dashboard_admin.html")


@app.route("/dashboard_cajero")
@login_required
def dashboard_cajero():

    return render_template("dashboard_cajero.html")


@app.route("/cajero")
@login_required
def cajero():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT

        p.id_producto,
        p.codigo,
        p.nombre,
        p.stock,
        p.precio_venta::numeric,

        u.pasillo,
        u.estante,
        u.nivel

    FROM productos p

    LEFT JOIN ubicaciones u
        ON p.id_ubicacion = u.id_ubicacion

    WHERE p.activo = TRUE

    ORDER BY p.nombre

""")

    productos = cursor.fetchall()

    cursor.close()
    conexion.close()

    if "carrito" not in session:
        session["carrito"] = []

    total = sum(item["subtotal"] for item in session["carrito"])

    return render_template(
        "cajero.html",
        productos=productos,
        carrito=session["carrito"],
        total=total
    )




@app.route("/productos", methods=["GET", "POST"])
@admin_required
def productos():

    if "id_usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":

        codigo = request.form["codigo"]
        codigo_oem = request.form["codigo_oem"]
        nombre = request.form["nombre"]
        marca_refaccion = request.form["marca_refaccion"]

        id_categoria = request.form["id_categoria"]
        id_ubicacion = request.form["id_ubicacion"]

        precio_compra = request.form["precio_compra"]
        precio_venta = request.form["precio_venta"]

        stock = request.form["stock"]
        stock_minimo = request.form["stock_minimo"]

        cursor.execute("""
            INSERT INTO productos
            (
                codigo,
                codigo_oem,
                nombre,
                marca_refaccion,
                id_categoria,
                id_ubicacion,
                precio_compra,
                precio_venta,
                stock,
                stock_minimo
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            codigo,
            codigo_oem,
            nombre,
            marca_refaccion,
            id_categoria,
            id_ubicacion,
            precio_compra,
            precio_venta,
            stock,
            stock_minimo
        ))

        conexion.commit()

        flash("Producto registrado correctamente", "success")

        return redirect(url_for("productos"))

    cursor.execute("""
        SELECT *
        FROM categorias
        ORDER BY nombre
    """)
    categorias = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM ubicaciones
        ORDER BY id_ubicacion
    """)
    ubicaciones = cursor.fetchall()

    cursor.execute("""
    SELECT
        p.id_producto,
        p.codigo,
        p.nombre,
        p.marca_refaccion,
        c.nombre AS categoria,
        CONCAT(
            u.pasillo, '-',
            u.estante, '-',
            u.nivel
        ) AS ubicacion,
        p.precio_venta,
        p.stock

    FROM productos p

    LEFT JOIN categorias c
        ON p.id_categoria = c.id_categoria

    LEFT JOIN ubicaciones u
        ON p.id_ubicacion = u.id_ubicacion

    WHERE p.activo = TRUE

    ORDER BY p.id_producto
""")

    productos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "productos.html",
        categorias=categorias,
        ubicaciones=ubicaciones,
        productos=productos
    )




@app.route("/editar_producto/<int:id_producto>", methods=["GET", "POST"])
@admin_required
def editar_producto(id_producto):

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":

        nombre = request.form["nombre"]
        marca_refaccion = request.form["marca_refaccion"]
        precio_venta = request.form["precio_venta"]
        stock = request.form["stock"]

        cursor.execute("""
            UPDATE productos
            SET
                nombre = %s,
                marca_refaccion = %s,
                precio_venta = %s,
                stock = %s
            WHERE id_producto = %s
        """,
        (
            nombre,
            marca_refaccion,
            precio_venta,
            stock,
            id_producto
        ))

        conexion.commit()

        flash("Producto actualizado correctamente", "success")

        cursor.close()
        conexion.close()

        return redirect(url_for("productos"))

    cursor.execute("""
        SELECT *
        FROM productos
        WHERE id_producto = %s
    """, (id_producto,))

    producto = cursor.fetchone()

    cursor.close()
    conexion.close()

    return render_template(
        "editar_producto.html",
        producto=producto
    )





@app.route("/eliminar_producto/<int:id>")
@admin_required
def eliminar_producto(id):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM productos
        WHERE id_producto = %s
    """, (id,))

    conexion.commit()

    flash("Producto eliminado correctamente.", "success")

    cursor.close()
    conexion.close()

    return redirect(url_for("productos"))


@app.route("/compatibilidades", methods=["GET", "POST"])
@admin_required
def compatibilidades():

    conexion = conectar()
    cursor = conexion.cursor()

    # ================= REGISTRAR COMPATIBILIDAD =================

    if request.method == "POST":

        id_producto = request.form["id_producto"]
        id_modelo = request.form["id_modelo"]
        anio_inicio = request.form["anio_inicio"]
        anio_fin = request.form["anio_fin"]

        # Validar que el año inicial no sea mayor al final
        if int(anio_inicio) > int(anio_fin):

            flash(
                "El año de inicio no puede ser mayor que el año final.",
                "warning"
            )

            cursor.close()
            conexion.close()

            return redirect(url_for("compatibilidades"))

        # Registrar compatibilidad
        cursor.execute("""
            INSERT INTO compatibilidades
            (
                id_producto,
                id_modelo,
                anio_inicio,
                anio_fin
            )
            VALUES
            (%s, %s, %s, %s)
        """,
        (
            id_producto,
            id_modelo,
            anio_inicio,
            anio_fin
        ))

        conexion.commit()

        flash(
            "Compatibilidad registrada correctamente.",
            "success"
        )

        cursor.close()
        conexion.close()

        return redirect(url_for("compatibilidades"))

    # ================= PRODUCTOS =================

    cursor.execute("""
        SELECT
            id_producto,
            codigo,
            nombre
        FROM productos
        WHERE activo = TRUE
        ORDER BY nombre
    """)
    productos = cursor.fetchall()

    # ================= MODELOS =================

    cursor.execute("""
        SELECT *
        FROM modelos
        ORDER BY nombre
    """)
    modelos = cursor.fetchall()

    # ================= COMPATIBILIDADES =================

    cursor.execute("""
        SELECT
            c.id_compatibilidad,
            p.nombre,
            m.nombre,
            c.anio_inicio,
            c.anio_fin

        FROM compatibilidades c

        INNER JOIN productos p
            ON c.id_producto = p.id_producto

        INNER JOIN modelos m
            ON c.id_modelo = m.id_modelo

        ORDER BY c.id_compatibilidad
    """)
    compatibilidades_lista = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "compatibilidades.html",
        productos=productos,
        modelos=modelos,
        compatibilidades=compatibilidades_lista
    )


@app.route("/editar_compatibilidad/<int:id_compatibilidad>", methods=["POST"])
@admin_required
def editar_compatibilidad(id_compatibilidad):

    conexion = conectar()
    cursor = conexion.cursor()

    anio_inicio = request.form["anio_inicio"]
    anio_fin = request.form["anio_fin"]

    # Validación
    if int(anio_inicio) > int(anio_fin):

        flash(
            "El año de inicio no puede ser mayor al año final.",
            "warning"
        )

        cursor.close()
        conexion.close()

        return redirect(url_for("compatibilidades"))

    cursor.execute("""
        UPDATE compatibilidades
        SET
            anio_inicio = %s,
            anio_fin = %s
        WHERE id_compatibilidad = %s
    """,
    (
        anio_inicio,
        anio_fin,
        id_compatibilidad
    ))

    conexion.commit()

    cursor.close()
    conexion.close()

    flash(
        "Compatibilidad actualizada correctamente.",
        "success"
    )

    return redirect(url_for("compatibilidades"))


@app.route("/eliminar_compatibilidad/<int:id_compatibilidad>")
@admin_required
def eliminar_compatibilidad(id_compatibilidad):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM compatibilidades
        WHERE id_compatibilidad = %s
    """, (id_compatibilidad,))

    conexion.commit()

    cursor.close()
    conexion.close()

    flash(
        "Compatibilidad eliminada correctamente.",
        "success"
    )

    return redirect(url_for("compatibilidades"))




@app.route("/buscar", methods=["GET", "POST"])
def buscar():

    conexion = conectar()
    cursor = conexion.cursor()

    resultados = []

    # ================= BUSCAR COMPATIBILIDADES =================

    if request.method == "POST":

        id_modelo = request.form["id_modelo"]
        anio = request.form["anio"]

        cursor.execute("""
            SELECT
                p.codigo,
                p.nombre,
                p.marca_refaccion,
                c.anio_inicio,
                c.anio_fin,
                p.stock,
                p.precio_venta,
                p.id_producto

            FROM compatibilidades c

            INNER JOIN productos p
                ON c.id_producto = p.id_producto

            WHERE c.id_modelo = %s
            AND %s BETWEEN c.anio_inicio AND c.anio_fin
            AND p.activo = TRUE

            ORDER BY p.nombre
        """, (id_modelo, anio))

        resultados = cursor.fetchall()

        # Si no hay resultados
        if len(resultados) == 0:

            flash(
                "No se encontraron refacciones compatibles para el modelo y año seleccionados.",
                "warning"
            )

    # ================= MARCAS =================

    cursor.execute("""
        SELECT *
        FROM marcas
        ORDER BY nombre
    """)
    marcas = cursor.fetchall()

    # ================= MODELOS =================

    cursor.execute("""
        SELECT *
        FROM modelos
        ORDER BY nombre
    """)
    modelos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "buscar.html",
        marcas=marcas,
        modelos=modelos,
        resultados=resultados
    )


@app.route("/api/compatibilidad")
def api_compatibilidad():

    id_modelo = request.args.get("id_modelo")
    anio = request.args.get("anio")


    conexion = conectar()
    cursor = conexion.cursor()


    if anio:

        cursor.execute("""
            SELECT
                p.codigo,
                p.nombre,
                p.marca_refaccion,
                c.anio_inicio,
                c.anio_fin,
                p.stock,
                p.precio_venta,
                p.id_producto

            FROM compatibilidades c

            INNER JOIN productos p
                ON c.id_producto = p.id_producto


            WHERE c.id_modelo = %s

            AND %s BETWEEN c.anio_inicio
            AND c.anio_fin

            AND p.activo = TRUE

            ORDER BY p.nombre

        """,
        (
            id_modelo,
            anio
        ))


    else:

        cursor.execute("""
            SELECT
                p.codigo,
                p.nombre,
                p.marca_refaccion,
                c.anio_inicio,
                c.anio_fin,
                p.stock,
                p.precio_venta,
                p.id_producto


            FROM compatibilidades c


            INNER JOIN productos p
                ON c.id_producto = p.id_producto


            WHERE c.id_modelo = %s

            AND p.activo = TRUE


            ORDER BY p.nombre

        """,
        (
            id_modelo,
        ))



    resultados = cursor.fetchall()


    cursor.close()
    conexion.close()



    return jsonify([

        {
            "codigo": r[0],
            "nombre": r[1],
            "marca": r[2],
            "anio_inicio": r[3],
            "anio_fin": r[4],
            "stock": r[5],
            "precio": float(r[6]),
            "id_producto": r[7]
        }

        for r in resultados

    ])


@app.route("/ventas", methods=["GET", "POST"])
def ventas():

    if "id_usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar()
    cursor = conexion.cursor()

    mensaje = ""

    if request.method == "POST":

        id_producto = request.form["id_producto"]
        cantidad = int(request.form["cantidad"])

        cursor.execute("""
            SELECT nombre, precio_venta, stock
            FROM productos
            WHERE id_producto = %s
        """, (id_producto,))

        producto = cursor.fetchone()

        if producto:

            nombre = producto[0]
            precio = float(producto[1])
            stock = int(producto[2])

            if cantidad <= stock:

                subtotal = precio * cantidad

                cursor.execute("""
    		INSERT INTO ventas
    		(id_usuario, total)
    		VALUES (%s, %s)
    		RETURNING id_venta
		""", (session["id_usuario"], subtotal))

                id_venta = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO detalle_ventas
                    (
                        id_venta,
                        id_producto,
                        cantidad,
                        precio_unitario,
                        subtotal
                    )
                    VALUES
                    (%s,%s,%s,%s,%s)
                """,
                (
                    id_venta,
                    id_producto,
                    cantidad,
                    precio,
                    subtotal
                ))

                cursor.execute("""
                    UPDATE productos
                    SET stock = stock - %s
                    WHERE id_producto = %s
                """,
                (
                    cantidad,
                    id_producto
                ))

                conexion.commit()

                mensaje = f"Venta registrada. Total: ${subtotal}"

            else:

                mensaje = "Stock insuficiente"

    cursor.execute("""
        SELECT
            id_producto,
            codigo,
            nombre,
            precio_venta,
            stock
        FROM productos
        WHERE activo = TRUE
        ORDER BY nombre
    """)

    productos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "ventas.html",
        productos=productos,
        mensaje=mensaje
    )





@app.route("/carrito")
def carrito():

    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if "carrito" not in session:
        session["carrito"] = []

    total = 0

    for item in session["carrito"]:
        total += item["subtotal"]

    return render_template(
        "carrito.html",
        carrito=session["carrito"],
        total=total
    )





@app.route("/agregar_carrito/<int:id_producto>")
def agregar_carrito(id_producto):

    if "id_usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            id_producto,
            nombre,
            precio_venta
        FROM productos
        WHERE id_producto = %s
    """, (id_producto,))

    producto = cursor.fetchone()

    cursor.close()
    conexion.close()

    if "carrito" not in session:
        session["carrito"] = []

    item = {
        "id_producto": producto[0],
        "nombre": producto[1],
        "precio": float(producto[2]),
        "cantidad": 1,
        "subtotal": float(producto[2])
    }

    session["carrito"].append(item)
    session.modified = True

    return redirect(url_for("carrito"))





@app.route("/eliminar_carrito/<int:indice>")
def eliminar_carrito(indice):

    if "carrito" in session:

        carrito = session["carrito"]

        if 0 <= indice < len(carrito):
            carrito.pop(indice)

        session["carrito"] = carrito
        session.modified = True

    return redirect(url_for("carrito"))





@app.route("/finalizar_venta")
def finalizar_venta():

    if "carrito" not in session:
        return redirect(url_for("carrito"))

    carrito = session["carrito"]

    if len(carrito) == 0:
        return redirect(url_for("carrito"))

    conexion = conectar()
    cursor = conexion.cursor()

    total = 0

    for item in carrito:
        total += item["subtotal"]

    # Usuario ADMIN temporal
    id_usuario = session["id_usuario"]

    cursor.execute("""
        INSERT INTO ventas
        (
            id_usuario,
            total
        )
        VALUES
        (%s, %s)
        RETURNING id_venta
    """,
    (
        id_usuario,
        total
    ))

    id_venta = cursor.fetchone()[0]

    for item in carrito:

        cursor.execute("""
            INSERT INTO detalle_ventas
            (
                id_venta,
                id_producto,
                cantidad,
                precio_unitario,
                subtotal
            )
            VALUES
            (%s,%s,%s,%s,%s)
        """,
        (
            id_venta,
            item["id_producto"],
            item["cantidad"],
            item["precio"],
            item["subtotal"]
        ))

        cursor.execute("""
            UPDATE productos
            SET stock = stock - %s
            WHERE id_producto = %s
        """,
        (
            item["cantidad"],
            item["id_producto"]
        ))

    conexion.commit()

    cursor.close()
    conexion.close()

    session["carrito"] = []
    session.modified = True

    return redirect(url_for("carrito"))




@app.route("/historial_ventas")
def historial_ventas():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            v.id_venta,
            u.nombre,
            v.fecha,
            v.total

        FROM ventas v

        INNER JOIN usuarios u
            ON v.id_usuario = u.id_usuario

        ORDER BY v.id_venta DESC
    """)

    ventas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "historial_ventas.html",
        ventas=ventas
    )




@app.route("/detalle_venta/<int:id_venta>")
def detalle_venta(id_venta):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            p.codigo,
            p.nombre,
            dv.cantidad,
            dv.precio_unitario,
            dv.subtotal

        FROM detalle_ventas dv

        INNER JOIN productos p
            ON dv.id_producto = p.id_producto

        WHERE dv.id_venta = %s
    """, (id_venta,))

    detalles = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "detalle_venta.html",
        detalles=detalles,
        id_venta=id_venta
    )




@app.route("/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios():

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":

        nombre = request.form["nombre"]
        usuario = request.form["usuario"]
        password = request.form["password"]
        rol = request.form["rol"]

        cursor.execute("""
            INSERT INTO usuarios
            (
                nombre,
                usuario,
                password,
                rol
            )
            VALUES
            (%s,%s,%s,%s)
        """,
        (
            nombre,
            usuario,
            password,
            rol
        ))

        conexion.commit()

        return redirect(url_for("usuarios"))

    cursor.execute("""
        SELECT
            id_usuario,
            nombre,
            usuario,
            rol,
            activo
        FROM usuarios
        ORDER BY id_usuario
    """)

    usuarios_lista = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "usuarios.html",
        usuarios=usuarios_lista
    )


@app.route("/editar_usuario/<int:id_usuario>", methods=["POST"])
@admin_required
def editar_usuario(id_usuario):

    conexion = conectar()
    cursor = conexion.cursor()

    nombre = request.form["nombre"]
    usuario = request.form["usuario"]
    rol = request.form["rol"]

    cursor.execute("""
        UPDATE usuarios
        SET
            nombre = %s,
            usuario = %s,
            rol = %s
        WHERE id_usuario = %s
    """, (
        nombre,
        usuario,
        rol,
        id_usuario
    ))

    conexion.commit()

    cursor.close()
    conexion.close()

    flash("Usuario actualizado correctamente.", "success")

    return redirect(url_for("usuarios"))


@app.route("/eliminar_usuario/<int:id_usuario>")
@admin_required
def eliminar_usuario(id_usuario):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET activo = FALSE
        WHERE id_usuario = %s
    """, (id_usuario,))

    conexion.commit()

    cursor.close()
    conexion.close()

    flash("Usuario desactivado correctamente.", "success")

    return redirect(url_for("usuarios"))



@app.route("/vehiculos")
@admin_required
def vehiculos():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT 
            m.id_modelo,
            ma.nombre AS marca,
            m.nombre AS modelo
        FROM modelos m
        JOIN marcas ma ON m.id_marca = ma.id_marca
        ORDER BY ma.nombre, m.nombre;
    """)

    vehiculos_lista = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "vehiculos.html",
        vehiculos=vehiculos_lista
    )





@app.route("/buscar_global")
def buscar_global():

    texto = request.args.get("q")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT 
            p.id_producto,
            p.nombre,
            p.marca_refaccion,
            p.precio_venta,
            p.stock,

            STRING_AGG(DISTINCT m.nombre, ', ') AS modelos,
            MIN(c.anio_inicio) AS anio_min,
            MAX(c.anio_fin) AS anio_max

        FROM productos p

        LEFT JOIN compatibilidades c 
            ON p.id_producto = c.id_producto

        LEFT JOIN modelos m 
            ON c.id_modelo = m.id_modelo

        WHERE 
            p.nombre ILIKE %s
            OR p.codigo ILIKE %s
            OR p.codigo_oem ILIKE %s

        GROUP BY 
            p.id_producto,
            p.nombre,
            p.marca_refaccion,
            p.precio_venta,
            p.stock

        ORDER BY p.nombre
    """, (
        f"%{texto}%",
        f"%{texto}%",
        f"%{texto}%"
    ))

    resultados = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "buscar_global.html",
        texto=texto,
        resultados=resultados
    )





@app.route("/api/buscar")
def api_buscar():

    q = request.args.get("q", "")

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            id_producto,
            nombre,
            codigo,
            precio_venta,
            stock
        FROM productos
        WHERE nombre ILIKE %s
           OR codigo ILIKE %s
           OR codigo_oem ILIKE %s
        LIMIT 8
    """, (
        f"%{q}%",
        f"%{q}%",
        f"%{q}%"
    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "productos": [
            {
                "id": r[0],
                "nombre": r[1],
                "codigo": r[2],
                "precio": r[3],
                "stock": r[4]
            }
            for r in rows
        ]
    }



@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
