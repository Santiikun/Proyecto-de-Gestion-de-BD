import os
from flask import Flask, render_template, request, redirect, url_for, make_response, flash
import datetime
import pyodbc
import subprocess
from wtforms import SubmitField, SelectField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

UPLOAD_FOLDER = r'C:\\backups\\'  # Utilizar cadenas sin procesar (raw strings)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = '123456789'

# Configuración de la conexión a la base de datos
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SANTI;DATABASE=G_Hospital;UID=sa;PWD=123456')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        try:
            cursor = conn.cursor()
            cursor.execute(f"CREATE LOGIN {nombre_usuario} WITH PASSWORD = '{contraseña}', CHECK_POLICY = OFF")
            cursor.execute(f"CREATE USER {nombre_usuario} FOR LOGIN {nombre_usuario}")
            conn.commit()
            print(f"Usuario '{nombre_usuario}' creado exitosamente")
        except pyodbc.Error as error:
            print("Error al crear usuario:", error)
        finally:
            if cursor:
                cursor.close()
            return redirect(url_for('index'))
    return render_template('crear_usuario.html')

@app.route('/modificar_usuario', methods=['GET', 'POST'])
def modificar_usuario():
    cursor = None
    try:
        if request.method == 'POST':
            nuevo_nombre_usuario = request.form['nuevo_nombre_usuario'].strip()
            nombre_usuario_actual = request.form['nombre_usuario_actual'].strip()

            if nuevo_nombre_usuario and nombre_usuario_actual:
                cursor = conn.cursor()
                # Modificar el nombre de inicio de sesión
                cursor.execute(f"ALTER LOGIN {nombre_usuario_actual} WITH NAME = {nuevo_nombre_usuario}")
                # Modificar el nombre de usuario
                cursor.execute(f"ALTER USER {nombre_usuario_actual} WITH NAME = {nuevo_nombre_usuario}")
                conn.commit()
                print(f"Usuario '{nombre_usuario_actual}' modificado exitosamente a '{nuevo_nombre_usuario}'", 'success')
                return redirect(url_for('index'))
            else:
                print("Debes completar ambos campos para modificar un usuario.", 'error')
    except pyodbc.Error as error:
        print(f"Error al modificar usuario: {error}", 'error')
    finally:
        if cursor:
            cursor.close()
    return render_template('modificar_usuario.html')

@app.route('/eliminar_usuario', methods=['GET', 'POST'])
def eliminar_usuario():
    # Inicializar el cursor fuera del bloque try
    cursor = None
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        if conn:
            try:
                # Abrir el cursor aquí
                cursor = conn.cursor()
                # Primero revocar todos los permisos del usuario
                cursor.execute(f"REVOKE ALL FROM {nombre_usuario}")
                # Eliminar al usuario de la base de datos
                cursor.execute(f"DROP USER {nombre_usuario}")
                # Eliminar el login asociado al usuario
                cursor.execute(f"DROP LOGIN {nombre_usuario}")
                conn.commit()
                print(f"Usuario '{nombre_usuario}' eliminado exitosamente de toda la base de datos")
            except pyodbc.Error as error:
                print("Error al eliminar usuario:", error)
            finally:
                # No cerrar la conexión aquí
                if cursor:
                    cursor.close()
                # No cerrar la conexión aquí
                return redirect(url_for('index'))
    return render_template('eliminar_usuario.html')

@app.route('/crear_rol', methods=['GET', 'POST'])
def crear_rol():
    cursor = None
    try:
        if request.method == 'POST':
            nombre_rol = request.form['nombre_rol']
            if nombre_rol:
                cursor = conn.cursor()
                cursor.execute(f"CREATE ROLE {nombre_rol}")
                conn.commit()
                print(f"Rol '{nombre_rol}' creado con éxito")
                return redirect(url_for('index'))
            else:
                print("Debes proporcionar un nombre para el rol.")
    except pyodbc.Error as e:
        print(f"Error al crear el rol: {e}")
    finally:
        if cursor:
            cursor.close()
    return render_template('crear_rol.html')

@app.route('/asignar_rol', methods=['GET', 'POST'])
def asignar_rol():
    cursor = None
    try:
        if request.method == 'POST':
            nombre_rol = request.form['nombre_rol']
            nombre_usuario = request.form['nombre_usuario']
            if nombre_rol and nombre_usuario:
                cursor = conn.cursor()
                # Utilizar la sentencia GRANT para asignar el rol al usuario
                cursor.execute(f"ALTER ROLE {nombre_rol} ADD MEMBER {nombre_usuario}")
                conn.commit()
                print(f"Rol '{nombre_rol}' asignado al usuario '{nombre_usuario}' con éxito")
                return redirect(url_for('index'))
            else:
                print("Debes proporcionar un nombre de rol y un nombre de usuario.")
    except pyodbc.Error as e:
        print(f"Error al asignar el rol: {e}")
    finally:
        if cursor:
            cursor.close()
    return render_template('asignar_rol.html')

@app.route('/listar_usuarios', methods=['GET'])
def listar_usuarios():
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name AS UserName, 
                   dbname AS DefaultDatabase,
                   loginname AS LoginName 
            FROM sys.syslogins
            WHERE isntname = 0
            ORDER BY UserName;
        """)
        usuarios = cursor.fetchall()  # Obtener todos los resultados de la consulta
        return render_template('listar_usuarios.html', usuarios=usuarios)
    except pyodbc.Error as error:
        print("Error al obtener la lista de usuarios:", error)
        return "Error al obtener la lista de usuarios"
    finally:
        if cursor:
            cursor.close()

@app.route('/listar_roles')
def listar_roles():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM G_Hospital.sys.database_principals WHERE type_desc = 'DATABASE_ROLE' AND name != 'public' ORDER BY name")
        roles = cursor.fetchall()  # Obtener todos los resultados de la consulta
        return render_template('listar_roles.html', roles=roles)
    except pyodbc.Error as e:
        print(f"Error al obtener la lista de roles: {e}")
    finally:
        if cursor:
            cursor.close()
    return "Error al listar roles"

@app.route('/listar_entidades')
def listar_entidades():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_schema='dbo' AND table_type='BASE TABLE'")
        entidades = cursor.fetchall()
        return render_template('listar_entidades.html', entidades=entidades)
    except pyodbc.Error as e:
        print(f"Error al obtener la lista de entidades: {e}")
    return "Error al establecer conexión con la base de datos"



class EntidadForm(FlaskForm):
    entidad = SelectField('Nombre de la entidad', choices=[], validators=[DataRequired()])
    submit = SubmitField('Listar Atributos')

@app.route('/listar_atributos', methods=['GET', 'POST'])
def listar_atributos():
    form = EntidadForm()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_schema='dbo' AND table_type='BASE TABLE'")
        entidades = cursor.fetchall()
        form.entidad.choices = [(entidad[0], entidad[0]) for entidad in entidades]

        if form.validate_on_submit():
            entidad = form.entidad.data.strip()
            return redirect(url_for('listar_atributos_entidad', entidad=entidad))
    except pyodbc.Error as e:
        print(f"Error al obtener la lista de entidades: {e}")
    return render_template('listar_atributos.html', form=form)

@app.route('/listar_atributos/<entidad>')
def listar_atributos_entidad(entidad):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?", (entidad,))
        atributos = cursor.fetchall()
        return render_template('listar_atributos_entidad.html', entidad=entidad, atributos=atributos)
    except pyodbc.Error as e:
        print(f"Error al obtener la lista de atributos de la entidad '{entidad}': {e}")
    finally:
        if cursor:
            cursor.close()
    return f"Error al establecer conexión con la base de datos o entidad '{entidad}' no encontrada"



def crear_entidad_y_atributos(conn, nombre_entidad, atributos):
    try:
        with conn.cursor() as cursor:
            # Crear la tabla en la base de datos con un atributo id automático
            cursor.execute(f"CREATE TABLE {nombre_entidad} (id INT PRIMARY KEY IDENTITY(1,1));")

            # Agregar los atributos a la tabla
            for atributo in atributos:
                cursor.execute(f"ALTER TABLE {nombre_entidad} ADD {atributo} VARCHAR(255);")

        print(f"Tabla '{nombre_entidad}' creada con éxito junto con sus atributos.")
        return True
    except pyodbc.Error as e:
        print(f"Error al crear la tabla y sus atributos: {e}")
        return False

@app.route('/respaldar_bd', methods=['GET', 'POST'])
def respaldar_bd():
    if request.method == 'POST':
        nombre_bd = 'G_Hospital'
        ruta_respaldo = r'C:\\backups\\'  # Utilizar cadenas sin procesar (raw strings)
        if not os.path.exists(ruta_respaldo):
            os.makedirs(ruta_respaldo)  # Asegura que la carpeta existe
        nombre_archivo = nombre_bd + datetime.datetime.now().strftime("_%Y%m%d%H%M%S") + '.bak'
        ruta_completa = os.path.join(ruta_respaldo, nombre_archivo)
        
        print(f"Intentando guardar el respaldo en: {ruta_completa}")  # Diagnóstico
        cmd = [
            "sqlcmd",
            "-S", r".\SANTI",
            "-U", "sa",
            "-P", "123456",
            "-Q", f"BACKUP DATABASE [{nombre_bd}] TO DISK = '{ruta_completa}' WITH NOFORMAT, NOINIT;"
        ]
        try:
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
            return f'Respaldo realizado con éxito en {ruta_completa}'
        except subprocess.CalledProcessError as e:
            return f'Error al realizar el respaldo: {e.stderr}'
        
    return render_template('respaldar_bd.html')

@app.route('/restaurar_bd', methods=['GET', 'POST'])
def restaurar_bd():
    if request.method == 'POST':
        if 'restaurar' in request.form:
            archivo_bak = request.files['archivo_bak']
            if archivo_bak.filename == '':
                return 'Error: No se seleccionó ningún archivo para restaurar'

            ruta_archivo_bak = os.path.join(r'C:\\backups\\', archivo_bak.filename)  # Utilizar cadenas sin procesar (raw strings)
            archivo_bak.save(ruta_archivo_bak)

            # Obtener el nombre sugerido de la base de datos restaurada
            nombre_original_bd = 'G_Hospital'
            nombre_sugerido_bd = request.form.get('nombre_sugerido', nombre_original_bd)

            # Modificar el comando RESTORE DATABASE para especificar nuevas ubicaciones
            cmd = [
                "sqlcmd",
                "-S", r".\SANTI",
                "-U", "sa",
                "-P", "123456",
                "-Q", f"RESTORE DATABASE [{nombre_sugerido_bd}] FROM DISK = '{ruta_archivo_bak}' WITH REPLACE, MOVE 'G_Hospital' TO 'C:\\Program Files\\Microsoft SQL Server\\MSSQL16.SANTI\\MSSQL\\DATA\\{nombre_sugerido_bd}.mdf', MOVE 'G_Hospital_log' TO 'C:\\Program Files\\Microsoft SQL Server\\MSSQL16.SANTI\\MSSQL\\DATA\\{nombre_sugerido_bd}_log.ldf';"
            ]
            try:
                result = subprocess.run(cmd, check=True, text=True, capture_output=True)
                return f'Restauración realizada con éxito como {nombre_sugerido_bd}'
            except subprocess.CalledProcessError as e:
                return f'Error al realizar la restauración: {e.stderr}'
    return render_template('restaurar_bd.html')




@app.route('/crear_tabla', methods=['GET', 'POST'])
def crear_tabla():
    if request.method == 'POST':
        nombre_tabla = request.form['nombre_tabla']
        nombres_atributos = request.form.getlist('nombre_atributo[]')
        tipos_atributos = request.form.getlist('tipo_atributo[]')
        es_primary_keys = request.form.getlist('es_primary_key[]')

        columnas = []
        primary_keys = []
        for i in range(len(nombres_atributos)):
            columna = f"{nombres_atributos[i]} {tipos_atributos[i]}"
            if i < len(es_primary_keys) and es_primary_keys[i] == 'on':
                primary_keys.append(nombres_atributos[i])
            columnas.append(columna)

        if primary_keys:
            primary_keys_sql = ', '.join(primary_keys)
            columnas.append(f"PRIMARY KEY ({primary_keys_sql})")

        columnas_sql = ', '.join(columnas)
        sql_crear_tabla = f"CREATE TABLE {nombre_tabla} ({columnas_sql})"

        conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SANTI;DATABASE=G_Hospital;UID=sa;PWD=123456')
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(sql_crear_tabla)
                conn.commit()
                flash(f'Tabla "{nombre_tabla}" creada exitosamente.')
            except pyodbc.Error as e:
                flash(f'Error al crear la tabla: {e}')
            finally:
                cursor.close()
                conn.close()

        return redirect(url_for('crear_tabla'))

    return render_template('crear_tabla.html')





@app.route('/generar_pdf', methods=['GET', 'POST'])
def generar_pdf():
    cursor = conn.cursor()
    tablas = []  # Definir la variable tablas antes del bloque condicional

    if request.method == 'POST' and 'atributos_seleccionados' in request.form:
        # Segunda fase, generar PDF
        tabla = request.form['tabla_seleccionada']
        atributos_seleccionados = request.form.getlist('atributos_seleccionados')

        query = f"SELECT {', '.join(atributos_seleccionados)} FROM {tabla}"
        cursor.execute(query)
        data = cursor.fetchall()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Preparar los datos para la tabla
        data_for_table = [atributos_seleccionados]  # Encabezados de la tabla
        for row in data:
            data_for_table.append(list(row))

        # Crear la tabla
        table = Table(data_for_table)

        # Aplicar estilos a la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.aqua),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),

            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),

            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ])
        table.setStyle(style)

        # Construir el PDF
        elems = []

        # Agregar el título de la tabla
        styles = getSampleStyleSheet()
        title = Paragraph(f"<para align=center spaceb=3><font size=18><b>Datos de la tabla: {tabla}</b></font></para>", styles["BodyText"])
        elems.append(title)

        # Agregar espacio entre el título y la tabla
        elems.append(Spacer(1, 20))

        elems.append(table)
        doc.build(elems)
        pdf = buffer.getvalue()
        buffer.close()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=report.pdf'
        return response

    elif request.method == 'POST':
        # Primera fase, seleccionar atributos
        tabla_actual = request.form['tabla_seleccionada']
        query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabla_actual}'"
        cursor.execute(query)
        atributos = cursor.fetchall()
        cursor.close()
        return render_template('generar_pdf.html', tablas=tablas, atributos=atributos, tabla_actual=tabla_actual)

    # Obtener lista de tablas al cargar la página
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tablas = cursor.fetchall()
    cursor.close()  # Cerrar cursor después de utilizarlo
    return render_template('generar_pdf.html', tablas=tablas, atributos=None)

conn_str = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SANTI;DATABASE=G_Hospital;UID=sa;PWD=123456'

@app.route('/generar_procedimientos', methods=['GET', 'POST'])
def generar_procedimientos():
    if request.method == 'POST':
        conn = None
        cursor = None
        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sys.objects WHERE type = 'U'")
            table_names = [row.name for row in cursor.fetchall()]
            
            for table_name in table_names:
                # Obtener la columna de clave primaria
                cursor.execute(f"""
                SELECT TOP 1 COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
                AND TABLE_NAME = '{table_name}'
                """)
                primary_key_column = cursor.fetchone().COLUMN_NAME

                # Obtener columnas de la tabla
                cursor.execute(f"""
                SELECT c.name, t.name AS type_name, c.max_length, c.precision, c.scale
                FROM sys.columns c
                JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE c.object_id = OBJECT_ID('{table_name}')
                """)
                columns = cursor.fetchall()
                
                columns_list = []
                columns_list_params = []
                for column in columns:
                    col_name = column.name
                    col_type = column.type_name
                    col_length = column.max_length
                    col_precision = column.precision
                    col_scale = column.scale

                    if col_name != primary_key_column:
                        columns_list.append(f'[{col_name}]')
                        if col_type in ('varchar', 'nvarchar', 'char', 'nchar'):
                            columns_list_params.append(f'@{col_name} {col_type}({col_length})')
                        elif col_type in ('decimal', 'numeric'):
                            columns_list_params.append(f'@{col_name} {col_type}({col_precision}, {col_scale})')
                        else:
                            columns_list_params.append(f'@{col_name} {col_type}')
                
                # Añadir la columna de clave primaria al final de la lista de parámetros
                columns_list_params.append(f'@{primary_key_column} INT')

                columns_list_str = ', '.join(columns_list)
                columns_list_params_str = ', '.join(columns_list_params)

                # Generar procedimientos almacenados
                sp_statements = []
                
                # Procedimiento almacenado para INSERT
                sp_statements.append(f"""
                CREATE PROCEDURE [dbo].[Insertar{table_name}]
                    ({columns_list_params_str})
                AS
                BEGIN
                    INSERT INTO [{table_name}] ({columns_list_str}, [{primary_key_column}])
                    VALUES ({', '.join('@' + col.strip('[]') for col in columns_list)}, @{primary_key_column})
                END
                """)
                
                # Procedimiento almacenado para UPDATE
                update_set_clause = ', '.join(f'[{col.strip("[]")}] = @{col.strip("[]")}' for col in columns_list)
                sp_statements.append(f"""
                CREATE PROCEDURE [dbo].[Actualizar{table_name}]
                    ({columns_list_params_str})
                AS
                BEGIN
                    UPDATE [{table_name}]
                    SET {update_set_clause}
                    WHERE [{primary_key_column}] = @{primary_key_column}
                END
                """)
                
                # Procedimiento almacenado para DELETE
                sp_statements.append(f"""
                CREATE PROCEDURE [dbo].[Eliminar{table_name}]
                    @{primary_key_column} INT
                AS
                BEGIN
                    DELETE FROM [{table_name}]
                    WHERE [{primary_key_column}] = @{primary_key_column}
                END
                """)
                
                # Procedimiento almacenado para SELECT
                sp_statements.append(f"""
                CREATE PROCEDURE [dbo].[Seleccionar{table_name}]
                AS
                BEGIN
                    SELECT * FROM [{table_name}]
                END
                """)

                # Ejecutar los procedimientos almacenados
                for sp_statement in sp_statements:
                    cursor.execute(sp_statement)
                    conn.commit()

            return "Procedimientos almacenados generados con éxito"
        except pyodbc.Error as e:
            return f"Error al generar procedimientos almacenados: {e}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('generar_procedimientos.html')

@app.route('/eliminar_procedimientos', methods=['POST'])
def eliminar_procedimientos():
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Obtener el listado de procedimientos almacenados con los prefijos especificados
        cursor.execute("""
        SELECT name
        FROM sys.objects
        WHERE type = 'P' AND
              (
                  name LIKE 'Insertar%' OR
                  name LIKE 'Actualizar%' OR
                  name LIKE 'Eliminar%' OR
                  name LIKE 'Seleccionar%'
              )
        """)
        proc_names = [row.name for row in cursor.fetchall()]
        
        for proc_name in proc_names:
            # Generar el comando para eliminar el procedimiento almacenado
            cursor.execute(f"DROP PROCEDURE [{proc_name}]")
            conn.commit()
            print(f"Procedimiento eliminado: {proc_name}")

        return "Procedimientos almacenados eliminados con éxito"
    except pyodbc.Error as e:
        return f"Error al eliminar procedimientos almacenados: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
