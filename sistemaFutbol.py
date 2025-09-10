import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import hashlib
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import time

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Gestión - Canchas de Fútbol",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de la base de datos MySQL
DB_CONFIG = {
    'host': 'bc1m00fbinftrdo7xahp-mysql.services.clever-cloud.com',
    'port': 3306,
    'user': 'uvv8ddfyy6im08il',
    'password': 'klx2DlrrUhqYk544pfWS',  # Por defecto XAMPP no tiene contraseña
    'database': 'bc1m00fbinftrdo7xahp',
    'charset': 'utf8mb4'
}

# Función para crear conexión a MySQL
def get_mysql_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None

# Función para crear la base de datos y tablas
def init_mysql_db():
    try:
        # Primero conectar sin especificar la base de datos
        config_without_db = DB_CONFIG.copy()
        del config_without_db['database']
        connection = mysql.connector.connect(**config_without_db)
        cursor = connection.cursor()

        # Crear base de datos si no existe
        cursor.execute("CREATE DATABASE IF NOT EXISTS bc1m00fbinftrdo7xahp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        connection.close()

        # Ahora conectar con la base de datos
        connection = get_mysql_connection()
        if not connection:
            return False

        cursor = connection.cursor()

        # Tabla de usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # Tabla de clientes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            dni VARCHAR(20) UNIQUE,
            nombre VARCHAR(100) NOT NULL,
            apellido VARCHAR(100),
            telefono VARCHAR(20),
            email VARCHAR(100),
            direccion TEXT,
            fecha_nacimiento DATE,
            equipo_favorito VARCHAR(100),
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dni (dni),
            INDEX idx_nombre (nombre)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # Tabla de canchas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS canchas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero VARCHAR(10) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            tipo ENUM('futbol5', 'futbol7', 'futbol11') NOT NULL,
            cesped ENUM('natural', 'sintetico') NOT NULL,
            techado BOOLEAN DEFAULT FALSE,
            iluminacion BOOLEAN DEFAULT TRUE,
            capacidad_jugadores INT NOT NULL,
            precio_hora_dia DECIMAL(10,2) NOT NULL,
            precio_hora_noche DECIMAL(10,2) NOT NULL,
            estado ENUM('disponible', 'mantenimiento', 'fuera_servicio') DEFAULT 'disponible',
            descripcion TEXT,
            imagen_url VARCHAR(255),
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_tipo (tipo),
            INDEX idx_estado (estado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # Tabla de reservas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cancha_id INT NOT NULL,
            cliente_id INT,
            cliente_nombre VARCHAR(200),
            fecha DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fin TIME NOT NULL,
            precio_total DECIMAL(10,2) NOT NULL,
            estado ENUM('pendiente', 'confirmada', 'en_curso', 'finalizada', 'cancelada') DEFAULT 'pendiente',
            metodo_pago ENUM('efectivo', 'tarjeta', 'transferencia') NOT NULL,
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cancha_id) REFERENCES canchas(id) ON DELETE CASCADE,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
            INDEX idx_fecha (fecha),
            INDEX idx_cancha (cancha_id),
            INDEX idx_estado (estado),
            UNIQUE KEY unique_reservation (cancha_id, fecha, hora_inicio, hora_fin)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # Tabla de mantenimiento
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mantenimiento (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cancha_id INT NOT NULL,
            tipo ENUM('preventivo', 'correctivo', 'limpieza') NOT NULL,
            descripcion TEXT NOT NULL,
            fecha_programada DATE NOT NULL,
            fecha_realizada DATE,
            responsable VARCHAR(100),
            costo DECIMAL(10,2),
            estado ENUM('programado', 'en_proceso', 'completado', 'cancelado') DEFAULT 'programado',
            observaciones TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cancha_id) REFERENCES canchas(id) ON DELETE CASCADE,
            INDEX idx_fecha (fecha_programada),
            INDEX idx_cancha (cancha_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        connection.commit()

        # Insertar datos de ejemplo
        insert_sample_data(cursor, connection)

        cursor.close()
        connection.close()
        return True

    except Error as e:
        st.error(f"Error inicializando base de datos MySQL: {e}")
        return False

# Función para insertar datos de ejemplo
def insert_sample_data(cursor, connection):
    try:
        # Insertar usuario admin por defecto
        cursor.execute('''
        INSERT IGNORE INTO usuarios (username, password, role, nombre, email)
        VALUES (%s, %s, %s, %s, %s)
        ''', ('admin', hashlib.md5('admin123'.encode()).hexdigest(), 'Administrador', 'Administrador', 'admin@futbol.com'))

        # Insertar usuario recepcionista
        cursor.execute('''
        INSERT IGNORE INTO usuarios (username, password, role, nombre, email)
        VALUES (%s, %s, %s, %s, %s)
        ''', ('recepcion', hashlib.md5('123456'.encode()).hexdigest(), 'Recepcionista', 'María Recepcionista', 'recepcion@futbol.com'))

        # Insertar clientes de ejemplo
        clientes = [
            ('12345678', 'Carlos', 'González', '555-0201', 'carlos@email.com', 'Av. Deportiva 456', '1990-06-15', 'Alianza Lima'),
            ('87654321', 'María', 'López', '555-0202', 'maria@email.com', 'Calle Fútbol 12', '1988-03-22', 'Universitario'),
            ('11223344', 'José', 'Martínez', '555-0203', 'jose@email.com', 'Jr. Pelota 78', '1985-11-08', 'Sporting Cristal'),
            ('44332211', 'Ana', 'Rodríguez', '555-0204', 'ana@email.com', 'Av. Champions 15', '1992-07-30', 'Real Madrid'),
            ('55667788', 'Pedro', 'Sánchez', '555-0205', 'pedro@email.com', 'Calle Mundial 8', '1987-12-12', 'Barcelona')
        ]

        for cliente in clientes:
            cursor.execute('''
            INSERT IGNORE INTO clientes (dni, nombre, apellido, telefono, email, direccion, fecha_nacimiento, equipo_favorito)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', cliente)

        # Insertar canchas de ejemplo
        canchas = [
            ('C1', 'Cancha Principal', 'futbol11', 'natural', True, True, 22, 80.00, 100.00, 'disponible', 'Cancha principal con césped natural e iluminación completa'),
            ('C2', 'Cancha Norte', 'futbol7', 'sintetico', False, True, 14, 50.00, 70.00, 'disponible', 'Cancha de fútbol 7 con césped sintético'),
            ('C3', 'Cancha Sur', 'futbol7', 'sintetico', False, True, 14, 50.00, 70.00, 'disponible', 'Cancha de fútbol 7 techada'),
            ('C4', 'Cancha Este', 'futbol5', 'sintetico', True, True, 10, 35.00, 45.00, 'disponible', 'Cancha de fútbol 5 techada ideal para torneos'),
            ('C5', 'Cancha Oeste', 'futbol5', 'sintetico', True, True, 10, 35.00, 45.00, 'mantenimiento', 'Cancha de fútbol 5 en mantenimiento'),
            ('C6', 'Mini Cancha', 'futbol5', 'sintetico', False, True, 10, 30.00, 40.00, 'disponible', 'Cancha pequeña ideal para niños')
        ]

        for cancha in canchas:
            cursor.execute('''
            INSERT IGNORE INTO canchas (numero, nombre, tipo, cesped, techado, iluminacion, capacidad_jugadores, 
                                       precio_hora_dia, precio_hora_noche, estado, descripcion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', cancha)

        # Insertar algunas reservas de ejemplo
        # Obtener IDs de canchas y clientes
        cursor.execute("SELECT id FROM canchas WHERE numero = 'C1'")
        cancha1_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM canchas WHERE numero = 'C2'")
        cancha2_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM clientes WHERE dni = '12345678'")
        cliente1_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM clientes WHERE dni = '87654321'")
        cliente2_id = cursor.fetchone()[0]

        # Reservas para hoy y mañana
        hoy = date.today()
        manana = hoy + timedelta(days=1)

        reservas_ejemplo = [
            (cancha1_id, cliente1_id, 'Carlos González', hoy, '18:00:00', '20:00:00', 200.00, 'confirmada', 'efectivo', 'Partido de empresa'),
            (cancha2_id, cliente2_id, 'María López', manana, '16:00:00', '17:00:00', 70.00, 'pendiente', 'tarjeta', 'Entrenamiento femenino'),
            (cancha1_id, None, 'Juan Pérez (sin registro)', hoy + timedelta(days=2), '20:00:00', '22:00:00', 200.00, 'confirmada', 'transferencia', 'Partido familiar')
        ]

        for reserva in reservas_ejemplo:
            cursor.execute('''
            INSERT IGNORE INTO reservas (cancha_id, cliente_id, cliente_nombre, fecha, hora_inicio, hora_fin, 
                                        precio_total, estado, metodo_pago, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', reserva)

        # Insertar mantenimiento programado
        mantenimiento_ejemplo = [
            (cancha1_id, 'preventivo', 'Mantenimiento mensual del césped natural', hoy + timedelta(days=7), None, 'Jardinero Principal', 150.00, 'programado', 'Incluye riego y fertilización'),
            (cancha2_id, 'limpieza', 'Limpieza profunda de vestuarios', hoy + timedelta(days=3), None, 'Equipo Limpieza', 80.00, 'programado', 'Desinfección completa')
        ]

        for mant in mantenimiento_ejemplo:
            cursor.execute('''
            INSERT IGNORE INTO mantenimiento (cancha_id, tipo, descripcion, fecha_programada, fecha_realizada, 
                                             responsable, costo, estado, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', mant)

        connection.commit()

    except Error as e:
        st.error(f"Error insertando datos de ejemplo: {e}")

# Funciones de autenticación
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def authenticate(username, password):
    connection = get_mysql_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, username, role, nombre FROM usuarios WHERE username = %s AND password = %s",
            (username, hash_password(password))
        )
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result
    except Error as e:
        st.error(f"Error en autenticación: {e}")
        return None

# Funciones para clientes
def get_clientes():
    connection = get_mysql_connection()
    if not connection:
        return pd.DataFrame()

    try:
        query = '''
        SELECT * FROM clientes 
        WHERE activo = TRUE 
        ORDER BY nombre, apellido
        '''
        df = pd.read_sql(query, connection)
        connection.close()
        return df
    except Error as e:
        st.error(f"Error obteniendo clientes: {e}")
        return pd.DataFrame()

def add_cliente(dni, nombre, apellido, telefono, email, direccion, fecha_nacimiento, equipo_favorito):
    connection = get_mysql_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute('''
        INSERT INTO clientes (dni, nombre, apellido, telefono, email, direccion, fecha_nacimiento, equipo_favorito)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (dni, nombre, apellido, telefono, email, direccion, fecha_nacimiento, equipo_favorito))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error agregando cliente: {e}")
        if connection:
            connection.close()
        return False

def buscar_cliente_por_dni(dni):
    connection = get_mysql_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id, dni, nombre, apellido, telefono, email, direccion, equipo_favorito
        FROM clientes 
        WHERE dni = %s AND activo = TRUE
        ''', (dni,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return {
                'id': result[0],
                'dni': result[1],
                'nombre': result[2],
                'apellido': result[3],
                'telefono': result[4],
                'email': result[5],
                'direccion': result[6],
                'equipo_favorito': result[7]
            }
        return None
    except Error as e:
        st.error(f"Error buscando cliente: {e}")
        return None

# Funciones para canchas
def get_canchas():
    connection = get_mysql_connection()
    if not connection:
        return pd.DataFrame()

    try:
        query = '''
        SELECT * FROM canchas 
        WHERE activo = TRUE 
        ORDER BY numero
        '''
        df = pd.read_sql(query, connection)
        connection.close()
        return df
    except Error as e:
        st.error(f"Error obteniendo canchas: {e}")
        return pd.DataFrame()

def get_canchas_disponibles():
    connection = get_mysql_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id, numero, nombre, tipo, precio_hora_dia, precio_hora_noche 
        FROM canchas 
        WHERE activo = TRUE AND estado = 'disponible'
        ORDER BY numero
        ''')
        canchas = cursor.fetchall()
        cursor.close()
        connection.close()
        return canchas
    except Error as e:
        st.error(f"Error obteniendo canchas disponibles: {e}")
        return []

# Función para verificar disponibilidad
def verificar_disponibilidad(cancha_id, fecha, hora_inicio, hora_fin, reserva_id=None):
    connection = get_mysql_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        query = '''
        SELECT COUNT(*) FROM reservas 
        WHERE cancha_id = %s AND fecha = %s 
        AND estado != 'cancelada'
        AND (
            (hora_inicio < %s AND hora_fin > %s) OR
            (hora_inicio < %s AND hora_fin > %s) OR
            (hora_inicio >= %s AND hora_fin <= %s)
        )
        '''
        params = [cancha_id, fecha, hora_fin, hora_inicio, hora_inicio, hora_inicio, hora_inicio, hora_fin]

        # Si es una edición, excluir la reserva actual
        if reserva_id:
            query += " AND id != %s"
            params.append(reserva_id)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        cursor.close()
        connection.close()

        return count == 0
    except Error as e:
        st.error(f"Error verificando disponibilidad: {e}")
        return False

# Función para crear reserva
def crear_reserva(cancha_id, cliente_info, fecha, hora_inicio, hora_fin, metodo_pago, observaciones):
    connection = get_mysql_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()

        # Calcular precio
        cursor.execute("SELECT precio_hora_dia, precio_hora_noche FROM canchas WHERE id = %s", (cancha_id,))
        precios = cursor.fetchone()

        # Determinar si es horario diurno o nocturno (antes de 18:00 es día)
        hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()
        precio_por_hora = precios[0] if hora_inicio_dt < datetime.strptime('18:00', '%H:%M').time() else precios[1]

        # Calcular horas
        inicio = datetime.strptime(hora_inicio, '%H:%M')
        fin = datetime.strptime(hora_fin, '%H:%M')
        horas = (fin - inicio).seconds / 3600
        precio_total = precio_por_hora * horas

        # Insertar reserva
        cliente_id = cliente_info['id'] if cliente_info else None
        cliente_nombre = f"{cliente_info['nombre']} {cliente_info['apellido']}" if cliente_info else None

        cursor.execute('''
        INSERT INTO reservas (cancha_id, cliente_id, cliente_nombre, fecha, hora_inicio, hora_fin, 
                             precio_total, metodo_pago, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (cancha_id, cliente_id, cliente_nombre, fecha, hora_inicio, hora_fin, precio_total, metodo_pago, observaciones))

        reserva_id = cursor.lastrowid
        connection.commit()
        cursor.close()
        connection.close()
        return reserva_id

    except Error as e:
        st.error(f"Error creando reserva: {e}")
        if connection:
            connection.close()
        return None

# Función para obtener reservas
def get_reservas(fecha_inicio=None, fecha_fin=None, estado=None):
    connection = get_mysql_connection()
    if not connection:
        return pd.DataFrame()

    try:
        query = '''
        SELECT r.*, c.numero as cancha_numero, c.nombre as cancha_nombre 
        FROM reservas r
        JOIN canchas c ON r.cancha_id = c.id
        WHERE 1=1
        '''
        params = []

        if fecha_inicio:
            query += " AND r.fecha >= %s"
            params.append(fecha_inicio)

        if fecha_fin:
            query += " AND r.fecha <= %s"
            params.append(fecha_fin)

        if estado:
            query += " AND r.estado = %s"
            params.append(estado)

        query += " ORDER BY r.fecha DESC, r.hora_inicio"

        df = pd.read_sql(query, connection, params=params)
        connection.close()
        return df
    except Error as e:
        st.error(f"Error obteniendo reservas: {e}")
        return pd.DataFrame()

# Función para actualizar estado de reserva
def actualizar_estado_reserva(reserva_id, nuevo_estado):
    connection = get_mysql_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE reservas SET estado = %s WHERE id = %s", (nuevo_estado, reserva_id))
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error actualizando estado de reserva: {e}")
        return False

# Función para verificar conexión MySQL
def test_mysql_connection():
    try:
        connection = get_mysql_connection()
        if connection and connection.is_connected():
            connection.close()
            return True
        return False
    except:
        return False

# Inicializar base de datos MySQL
@st.cache_resource
def initialize_database():
    return init_mysql_db()

# Inicializar session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'cliente_actual' not in st.session_state:
    st.session_state.cliente_actual = None
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False

# Verificar y inicializar base de datos
if not st.session_state.db_initialized:
    st.info("🔄 Inicializando conexión con MySQL...")
    if test_mysql_connection():
        if initialize_database():
            st.session_state.db_initialized = True
            st.success("✅ Base de datos MySQL inicializada correctamente")
            st.info("ℹ️ Datos de ejemplo insertados. Usuario: admin, Contraseña: admin123")
        else:
            st.error("❌ Error inicializando la base de datos")
            st.stop()
    else:
        st.error("❌ No se pudo conectar a MySQL. Verifica que XAMPP esté ejecutándose.")
        st.info("📋 Asegúrate de que:")
        st.write("- XAMPP esté instalado y ejecutándose")
        st.write("- El servicio MySQL esté activo")
        st.write("- La configuración de DB_CONFIG sea correcta")
        st.stop()

# Login
if not st.session_state.logged_in:
    st.title("⚽ Sistema de Gestión - Canchas de Fútbol")
    st.subheader("Iniciar Sesión")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Usuario", value="admin")
            password = st.text_input("Contraseña", type="password", value="admin123")
            login_button = st.form_submit_button("Ingresar")

            if login_button:
                user = authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = {
                        'id': user[0],
                        'username': user[1],
                        'role': user[2],
                        'nombre': user[3]
                    }
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")

    st.info("👤 Usuarios disponibles:")
    st.write("- **admin** / admin123 (Administrador)")
    st.write("- **recepcion** / 123456 (Recepcionista)")

else:
    # Sidebar con información del usuario
    with st.sidebar:
        st.title("⚽ Canchas Fútbol")
        st.write(f"**Usuario:** {st.session_state.user_info['nombre']}")
        st.write(f"**Rol:** {st.session_state.user_info['role']}")

        # Estado de conexión
        if test_mysql_connection():
            st.success("🟢 MySQL Conectado")
        else:
            st.error("🔴 MySQL Desconectado")

        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.cliente_actual = None
            st.rerun()

        st.markdown("---")

        # Menú principal
        menu_options = ["📊 Dashboard", "📅 Reservas", "👥 Clientes",
                        "🏟️ Canchas", "📈 Reportes", "⚙️ Configuración"]
        selected_menu = st.selectbox("Menú", menu_options)

    # Dashboard
    if selected_menu == "📊 Dashboard":
        st.title("📊 Dashboard")

        col1, col2, col3, col4 = st.columns(4)

        # Métricas principales
        connection = get_mysql_connection()
        if connection:
            try:
                # Total canchas
                canchas_count = pd.read_sql("SELECT COUNT(*) as count FROM canchas WHERE activo = TRUE", connection).iloc[0]['count']

                # Reservas hoy
                reservas_hoy = pd.read_sql(
                    "SELECT COUNT(*) as count FROM reservas WHERE fecha = CURDATE()",
                    connection
                ).iloc[0]['count']

                # Ingresos del mes
                ingresos_mes = pd.read_sql(
                    "SELECT COALESCE(SUM(precio_total), 0) as total FROM reservas WHERE MONTH(fecha) = MONTH(CURDATE()) AND YEAR(fecha) = YEAR(CURDATE()) AND estado != 'cancelada'",
                    connection
                ).iloc[0]['total']

                # Clientes registrados
                clientes_count = pd.read_sql(
                    "SELECT COUNT(*) as count FROM clientes WHERE activo = TRUE",
                    connection
                ).iloc[0]['count']

                with col1:
                    st.metric("Canchas Activas", canchas_count)
                with col2:
                    st.metric("Reservas Hoy", reservas_hoy)
                with col3:
                    st.metric("Ingresos Mes", f"${ingresos_mes:,.2f}")
                with col4:
                    st.metric("Clientes", clientes_count)

                # Gráficos
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Reservas por Día (Última Semana)")
                    reservas_semana = pd.read_sql('''
                    SELECT DATE(fecha) as fecha, COUNT(*) as total
                    FROM reservas 
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    AND estado != 'cancelada'
                    GROUP BY DATE(fecha)
                    ORDER BY fecha
                    ''', connection)

                    if not reservas_semana.empty:
                        reservas_semana['fecha_str'] = pd.to_datetime(reservas_semana['fecha']).dt.strftime('%Y-%m-%d')
                        fig = px.bar(
                            reservas_semana,
                            x='fecha_str',
                            y='total',
                            title="Reservas por Día",
                            labels={'fecha_str': 'Fecha', 'total': 'Cantidad'},
                            color='total',
                            color_continuous_scale='Blues'
                        )
                        fig.update_layout(xaxis_tickangle=-45, showlegend=False, height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos de reservas para mostrar")

                with col2:
                    st.subheader("Canchas Más Reservadas")
                    canchas_populares = pd.read_sql('''
                    SELECT c.nombre as cancha, COUNT(r.id) as reservas
                    FROM canchas c
                    LEFT JOIN reservas r ON c.id = r.cancha_id AND r.estado != 'cancelada'
                    WHERE c.activo = TRUE
                    GROUP BY c.id, c.nombre
                    ORDER BY reservas DESC
                    LIMIT 5
                    ''', connection)

                    if not canchas_populares.empty and canchas_populares['reservas'].sum() > 0:
                        fig = px.pie(
                            canchas_populares,
                            values='reservas',
                            names='cancha',
                            title="Distribución de Reservas",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos de reservas por cancha")

                connection.close()

            except Error as e:
                st.error(f"Error obteniendo métricas: {e}")

    # Reservas
    elif selected_menu == "📅 Reservas":
        st.title("📅 Gestión de Reservas")

        tab1, tab2, tab3 = st.tabs(["Nueva Reserva", "Lista de Reservas", "Calendario"])

        with tab1:
            st.subheader("Nueva Reserva")

            col1, col2 = st.columns([1, 1])

            with col1:
                # Sección de cliente
                st.subheader("👤 Cliente")
                col_cliente1, col_cliente2 = st.columns([2, 1])

                with col_cliente1:
                    dni_buscar = st.text_input("🔍 Buscar cliente por DNI",
                                               value="", placeholder="Ingrese DNI")

                with col_cliente2:
                    if st.button("🔍 Buscar", key="buscar_cliente_reserva"):
                        if dni_buscar:
                            cliente = buscar_cliente_por_dni(dni_buscar)
                            if cliente:
                                st.session_state.cliente_actual = cliente
                                st.success(f"Cliente encontrado: {cliente['nombre']} {cliente['apellido']}")
                            else:
                                st.warning("Cliente no encontrado")
                                st.session_state.cliente_actual = None
                        else:
                            st.session_state.cliente_actual = None

                # Mostrar información del cliente seleccionado
                if st.session_state.cliente_actual:
                    st.info(f"**Cliente:** {st.session_state.cliente_actual['nombre']} {st.session_state.cliente_actual['apellido']} "
                            f"(DNI: {st.session_state.cliente_actual['dni']})")
                    if st.button("❌ Quitar cliente", key="quitar_cliente_reserva"):
                        st.session_state.cliente_actual = None
                        st.rerun()

                # Datos de la reserva
                st.subheader("📋 Datos de la Reserva")
                canchas_disponibles = get_canchas_disponibles()

                if canchas_disponibles:
                    cancha_options = [f"{cancha[1]} - {cancha[2]} ({cancha[3]}) - ${cancha[4]}/h día - ${cancha[5]}/h noche"
                                      for cancha in canchas_disponibles]
                    cancha_selected = st.selectbox("Seleccionar Cancha", cancha_options)
                    cancha_id = canchas_disponibles[cancha_options.index(cancha_selected)][0]

                    col_fecha, col_inicio, col_fin = st.columns(3)
                    with col_fecha:
                        fecha_reserva = st.date_input("Fecha", min_value=date.today())
                    with col_inicio:
                        hora_inicio = st.time_input("Hora Inicio", value=datetime.strptime("16:00", "%H:%M").time())
                    with col_fin:
                        hora_fin = st.time_input("Hora Fin", value=datetime.strptime("18:00", "%H:%M").time())

                    metodo_pago = st.selectbox("Método de Pago", ["efectivo", "tarjeta", "transferencia"])
                    observaciones = st.text_area("Observaciones", placeholder="Información adicional sobre la reserva")

                    if st.button("💾 Crear Reserva"):
                        if hora_fin > hora_inicio:
                            if verificar_disponibilidad(cancha_id, fecha_reserva, hora_inicio.strftime('%H:%M'), hora_fin.strftime('%H:%M')):
                                reserva_id = crear_reserva(
                                    cancha_id,
                                    st.session_state.cliente_actual,
                                    fecha_reserva,
                                    hora_inicio.strftime('%H:%M'),
                                    hora_fin.strftime('%H:%M'),
                                    metodo_pago,
                                    observaciones
                                )
                                if reserva_id:
                                    st.success(f"✅ Reserva creada exitosamente. ID: {reserva_id}")
                                    st.session_state.cliente_actual = None
                                    st.rerun()
                                else:
                                    st.error("❌ Error creando la reserva")
                            else:
                                st.error("❌ La cancha no está disponible en ese horario")
                        else:
                            st.error("❌ La hora de fin debe ser mayor a la hora de inicio")
                else:
                    st.warning("No hay canchas disponibles")

        with tab2:
            st.subheader("Lista de Reservas")

            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha_filtro_inicio = st.date_input("Fecha Inicio", value=date.today())
            with col2:
                fecha_filtro_fin = st.date_input("Fecha Fin", value=date.today() + timedelta(days=7))
            with col3:
                estado_filtro = st.selectbox("Estado", ["Todos", "pendiente", "confirmada", "en_curso", "finalizada", "cancelada"])

            # Obtener reservas
            estado_query = None if estado_filtro == "Todos" else estado_filtro
            df_reservas = get_reservas(fecha_filtro_inicio, fecha_filtro_fin, estado_query)

            if not df_reservas.empty:
                st.write(f"**Total de reservas:** {len(df_reservas)}")

                # Mostrar reservas
                for idx, reserva in df_reservas.iterrows():
                    with st.expander(f"Reserva #{reserva['id']} - {reserva['cancha_nombre']} - {reserva['fecha']} - ${reserva['precio_total']:,.2f}"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.write(f"**Cliente:** {reserva['cliente_nombre'] if reserva['cliente_nombre'] else 'Sin registro'}")
                            st.write(f"**Cancha:** {reserva['cancha_numero']} - {reserva['cancha_nombre']}")
                            st.write(f"**Horario:** {reserva['hora_inicio']} - {reserva['hora_fin']}")

                        with col2:
                            st.write(f"**Fecha:** {reserva['fecha']}")
                            st.write(f"**Estado:** {reserva['estado'].title()}")
                            st.write(f"**Pago:** {reserva['metodo_pago'].title()}")

                        with col3:
                            st.write(f"**Total:** ${reserva['precio_total']:,.2f}")
                            if reserva['observaciones']:
                                st.write(f"**Observaciones:** {reserva['observaciones']}")

                        # Botones para cambiar estado
                        if reserva['estado'] == 'pendiente':
                            col_btn1, col_btn2, col_btn3 = st.columns(3)
                            with col_btn1:
                                if st.button("✅ Confirmar", key=f"conf_{reserva['id']}"):
                                    if actualizar_estado_reserva(reserva['id'], 'confirmada'):
                                        st.success("Reserva confirmada")
                                        st.rerun()
                            with col_btn2:
                                if st.button("❌ Cancelar", key=f"canc_{reserva['id']}"):
                                    if actualizar_estado_reserva(reserva['id'], 'cancelada'):
                                        st.success("Reserva cancelada")
                                        st.rerun()

                        elif reserva['estado'] == 'confirmada':
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("🎮 En Curso", key=f"curso_{reserva['id']}"):
                                    if actualizar_estado_reserva(reserva['id'], 'en_curso'):
                                        st.success("Partido iniciado")
                                        st.rerun()

                        elif reserva['estado'] == 'en_curso':
                            if st.button("🏁 Finalizar", key=f"fin_{reserva['id']}"):
                                if actualizar_estado_reserva(reserva['id'], 'finalizada'):
                                    st.success("Partido finalizado")
                                    st.rerun()
            else:
                st.info("No se encontraron reservas en el período seleccionado")

        with tab3:
            st.subheader("📅 Calendario de Reservas")

            # Controles de navegación
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

            # Inicializar fecha actual si no existe
            if 'calendar_date' not in st.session_state:
                st.session_state.calendar_date = date.today()

            current_date = st.session_state.calendar_date

            with col1:
                if st.button("← Anterior"):
                    if current_date.month == 1:
                        st.session_state.calendar_date = current_date.replace(year=current_date.year-1, month=12)
                    else:
                        st.session_state.calendar_date = current_date.replace(month=current_date.month-1)
                    st.rerun()

            with col2:
                if st.button("Hoy"):
                    st.session_state.calendar_date = date.today()
                    st.rerun()

            with col3:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                st.markdown(f"### {meses[current_date.month-1]} {current_date.year}")

            with col4:
                if st.button("Siguiente →"):
                    if current_date.month == 12:
                        st.session_state.calendar_date = current_date.replace(year=current_date.year+1, month=1)
                    else:
                        st.session_state.calendar_date = current_date.replace(month=current_date.month+1)
                    st.rerun()

            with col5:
                # Filtro de cancha
                canchas_disponibles = get_canchas_disponibles()
                canchas_options = ["Todas"] + [f"{c[2]}" for c in canchas_disponibles]
                cancha_filter = st.selectbox("Cancha:", canchas_options, key="calendar_filter")

            # Obtener datos de reservas del mes actual
            primer_dia_mes = current_date.replace(day=1)
            if current_date.month == 12:
                ultimo_dia_mes = current_date.replace(year=current_date.year+1, month=1, day=1) - timedelta(days=1)
            else:
                ultimo_dia_mes = current_date.replace(month=current_date.month+1, day=1) - timedelta(days=1)

            # Obtener reservas del mes
            connection = get_mysql_connection()
            reservas_mes = pd.DataFrame()

            if connection:
                try:
                    query = '''
                    SELECT r.*, c.numero as cancha_numero, c.nombre as cancha_nombre 
                    FROM reservas r
                    JOIN canchas c ON r.cancha_id = c.id
                    WHERE r.fecha >= %s AND r.fecha <= %s
                    AND r.estado != 'cancelada'
                    '''
                    params = [primer_dia_mes, ultimo_dia_mes]

                    # Filtrar por cancha si se seleccionó una específica
                    if cancha_filter != "Todas":
                        query += " AND c.nombre = %s"
                        params.append(cancha_filter)

                    query += " ORDER BY r.fecha, r.hora_inicio"

                    reservas_mes = pd.read_sql(query, connection, params=params)
                    connection.close()
                except Error as e:
                    st.error(f"Error obteniendo reservas: {e}")

            # Crear calendario usando Streamlit nativo
            import calendar
            cal = calendar.monthcalendar(current_date.year, current_date.month)

            # Encabezado de días de la semana
            dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            cols_header = st.columns(7)
            for i, dia in enumerate(dias_semana):
                with cols_header[i]:
                    st.markdown(f"**{dia}**")

            st.markdown("---")

            # Crear calendario día por día
            for semana in cal:
                cols = st.columns(7)
                for i, dia in enumerate(semana):
                    with cols[i]:
                        if dia == 0:
                            # Día vacío
                            st.markdown("<br>", unsafe_allow_html=True)
                        else:
                            # Crear fecha para este día
                            fecha_dia = date(current_date.year, current_date.month, dia)

                            # Contar reservas para este día
                            if not reservas_mes.empty:
                                reservas_dia = reservas_mes[pd.to_datetime(reservas_mes['fecha']).dt.date == fecha_dia]
                                num_reservas = len(reservas_dia)
                            else:
                                num_reservas = 0

                            # Determinar estilo según reservas y si es hoy
                            if fecha_dia == date.today():
                                if num_reservas == 0:
                                    st.markdown(f"🔵 **{dia}**")
                                elif num_reservas <= 2:
                                    st.markdown(f"🟢 **{dia}** ({num_reservas})")
                                elif num_reservas <= 4:
                                    st.markdown(f"🟡 **{dia}** ({num_reservas})")
                                else:
                                    st.markdown(f"🔴 **{dia}** ({num_reservas})")
                            else:
                                if num_reservas == 0:
                                    st.markdown(f"{dia}")
                                elif num_reservas <= 2:
                                    st.markdown(f"🟢 {dia} ({num_reservas})")
                                elif num_reservas <= 4:
                                    st.markdown(f"🟡 {dia} ({num_reservas})")
                                else:
                                    st.markdown(f"🔴 {dia} ({num_reservas})")

                            # Botón para seleccionar día si tiene reservas
                            if num_reservas > 0:
                                if st.button("📋", key=f"select_day_{dia}", help=f"Ver reservas del {dia}"):
                                    st.session_state.selected_date = fecha_dia

            # Leyenda
            st.markdown("---")
            st.markdown("**Leyenda:**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("🟢 1-2 reservas")
            with col2:
                st.markdown("🟡 3-4 reservas")
            with col3:
                st.markdown("🔴 5+ reservas")
            with col4:
                st.markdown("🔵 Día actual")

            # Mostrar detalles del día seleccionado
            if 'selected_date' in st.session_state:
                selected_date = st.session_state.selected_date
                st.markdown("---")
                st.markdown(f"### 📅 Reservas del {selected_date.strftime('%d/%m/%Y')}")

                # Obtener reservas del día seleccionado
                connection = get_mysql_connection()
                if connection:
                    try:
                        query = '''
                        SELECT r.*, c.numero as cancha_numero, c.nombre as cancha_nombre 
                        FROM reservas r
                        JOIN canchas c ON r.cancha_id = c.id
                        WHERE r.fecha = %s
                        ORDER BY r.hora_inicio
                        '''
                        reservas_dia = pd.read_sql(query, connection, params=[selected_date])
                        connection.close()

                        if not reservas_dia.empty:
                            for idx, reserva in reservas_dia.iterrows():
                                # Contenedor para cada reserva
                                with st.container():
                                    # Información principal de la reserva
                                    col1, col2, col3 = st.columns([2, 1, 1])

                                    with col1:
                                        # Color según estado
                                        estado_emoji = {
                                            'pendiente': '🟡',
                                            'confirmada': '🟢',
                                            'en_curso': '🔵',
                                            'finalizada': '⚫',
                                            'cancelada': '🔴'
                                        }
                                        emoji = estado_emoji.get(reserva['estado'], '⚪')

                                        st.markdown(f"""
                                        **{emoji} {reserva['hora_inicio']} - {reserva['hora_fin']}**  
                                        🏟️ {reserva['cancha_nombre']} ({reserva['cancha_numero']})  
                                        👤 {reserva['cliente_nombre'] if reserva['cliente_nombre'] else 'Sin registro'}
                                        """)

                                    with col2:
                                        st.markdown(f"""
                                        **💰 Total:**  
                                        ${reserva['precio_total']:,.2f}
                                        
                                        **💳 Pago:**  
                                        {reserva['metodo_pago'].title()}
                                        """)

                                    with col3:
                                        st.markdown(f"""
                                        **Estado:**  
                                        {reserva['estado'].replace('_', ' ').title()}
                                        """)

                                    # Observaciones si existen
                                    if reserva['observaciones']:
                                        st.info(f"📝 **Observaciones:** {reserva['observaciones']}")

                                    # Botones de acción
                                    if reserva['estado'] in ['pendiente', 'confirmada', 'en_curso']:
                                        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)

                                        if reserva['estado'] == 'pendiente':
                                            with col_btn1:
                                                if st.button("✅ Confirmar", key=f"conf_cal_{reserva['id']}"):
                                                    if actualizar_estado_reserva(reserva['id'], 'confirmada'):
                                                        st.success("Reserva confirmada")
                                                        st.rerun()
                                            with col_btn2:
                                                if st.button("❌ Cancelar", key=f"canc_cal_{reserva['id']}"):
                                                    if actualizar_estado_reserva(reserva['id'], 'cancelada'):
                                                        st.success("Reserva cancelada")
                                                        st.rerun()

                                        elif reserva['estado'] == 'confirmada':
                                            with col_btn1:
                                                if st.button("🎮 Iniciar", key=f"start_cal_{reserva['id']}"):
                                                    if actualizar_estado_reserva(reserva['id'], 'en_curso'):
                                                        st.success("Partido iniciado")
                                                        st.rerun()
                                            with col_btn2:
                                                if st.button("❌ Cancelar", key=f"canc2_cal_{reserva['id']}"):
                                                    if actualizar_estado_reserva(reserva['id'], 'cancelada'):
                                                        st.success("Reserva cancelada")
                                                        st.rerun()

                                        elif reserva['estado'] == 'en_curso':
                                            with col_btn1:
                                                if st.button("🏁 Finalizar", key=f"fin_cal_{reserva['id']}"):
                                                    if actualizar_estado_reserva(reserva['id'], 'finalizada'):
                                                        st.success("Partido finalizado")
                                                        st.rerun()

                                    st.markdown("---")
                        else:
                            st.info(f"No hay reservas para el {selected_date.strftime('%d/%m/%Y')}")

                    except Error as e:
                        st.error(f"Error obteniendo reservas del día: {e}")

            # Resumen del mes al final
            if not reservas_mes.empty:
                st.markdown("---")
                st.markdown("### 📊 Resumen del Mes")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_reservas = len(reservas_mes)
                    st.metric("Total Reservas", total_reservas)

                with col2:
                    if 'precio_total' in reservas_mes.columns:
                        ingresos_mes = reservas_mes['precio_total'].sum()
                        st.metric("Ingresos", f"${ingresos_mes:,.2f}")

                with col3:
                    if 'cancha_nombre' in reservas_mes.columns:
                        cancha_popular = reservas_mes['cancha_nombre'].mode()
                        if not cancha_popular.empty:
                            st.metric("Cancha Popular", cancha_popular.iloc[0])

                with col4:
                    reservas_confirmadas = len(reservas_mes[reservas_mes['estado'] == 'confirmada'])
                    st.metric("Confirmadas", reservas_confirmadas)

    # Clientes
    elif selected_menu == "👥 Clientes":
        st.title("👥 Gestión de Clientes")

        tab1, tab2 = st.tabs(["Lista de Clientes", "Agregar Cliente"])

        with tab1:
            st.subheader("Lista de Clientes")
            df_clientes = get_clientes()

            if not df_clientes.empty:
                # Filtro de búsqueda
                search_cliente = st.text_input("🔍 Buscar cliente", placeholder="Nombre, apellido o DNI")

                if search_cliente:
                    df_filtered = df_clientes[
                        df_clientes['nombre'].str.contains(search_cliente, case=False, na=False) |
                        df_clientes['apellido'].str.contains(search_cliente, case=False, na=False) |
                        df_clientes['dni'].str.contains(search_cliente, case=False, na=False)
                        ]
                else:
                    df_filtered = df_clientes

                # Mostrar tabla de clientes
                if not df_filtered.empty:
                    columns_to_show = ['dni', 'nombre', 'apellido', 'telefono', 'email', 'equipo_favorito']
                    st.dataframe(
                        df_filtered[columns_to_show],
                        use_container_width=True,
                        column_config={
                            "dni": "DNI",
                            "nombre": "Nombre",
                            "apellido": "Apellido",
                            "telefono": "Teléfono",
                            "email": "Email",
                            "equipo_favorito": "Equipo Favorito"
                        }
                    )
                else:
                    st.info("No se encontraron clientes con ese criterio")

                # Estadísticas
                st.subheader("📊 Estadísticas")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Clientes", len(df_clientes))

                with col2:
                    # Clientes con reservas
                    connection = get_mysql_connection()
                    if connection:
                        clientes_con_reservas = pd.read_sql('''
                        SELECT COUNT(DISTINCT cliente_id) as count 
                        FROM reservas 
                        WHERE cliente_id IS NOT NULL
                        ''', connection).iloc[0]['count']
                        connection.close()
                        st.metric("Con Reservas", clientes_con_reservas)

                with col3:
                    # Equipo más popular
                    if 'equipo_favorito' in df_clientes.columns:
                        equipo_popular = df_clientes['equipo_favorito'].mode()
                        if not equipo_popular.empty:
                            st.metric("Equipo Popular", equipo_popular.iloc[0])
            else:
                st.info("No hay clientes registrados")

        with tab2:
            st.subheader("Agregar Nuevo Cliente")

            with st.form("cliente_form"):
                col1, col2 = st.columns(2)

                with col1:
                    dni = st.text_input("DNI*", placeholder="12345678")
                    nombre = st.text_input("Nombre*", placeholder="Juan")
                    apellido = st.text_input("Apellido", placeholder="Pérez")
                    telefono = st.text_input("Teléfono", placeholder="555-0123")

                with col2:
                    email = st.text_input("Email", placeholder="cliente@email.com")
                    direccion = st.text_area("Dirección", placeholder="Av. Principal #123")
                    fecha_nacimiento = st.date_input("Fecha de Nacimiento",
                                                     value=None, min_value=date(1900, 1, 1))
                    equipo_favorito = st.text_input("Equipo Favorito", placeholder="Alianza Lima")

                if st.form_submit_button("💾 Guardar Cliente"):
                    if dni and nombre:
                        if add_cliente(dni, nombre, apellido, telefono, email, direccion, fecha_nacimiento, equipo_favorito):
                            st.success("✅ Cliente agregado exitosamente")
                            st.rerun()
                        else:
                            st.error("❌ Error: El DNI ya existe o hubo un problema")
                    else:
                        st.error("❌ DNI y Nombre son obligatorios")

    # Canchas
    elif selected_menu == "🏟️ Canchas":
        st.title("🏟️ Gestión de Canchas")

        df_canchas = get_canchas()

        if not df_canchas.empty:
            st.subheader("Lista de Canchas")

            # Mostrar canchas en cards
            for idx, cancha in df_canchas.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**{cancha['nombre']}** ({cancha['numero']})")
                        st.write(f"Tipo: {cancha['tipo'].replace('futbol', 'Fútbol ')}")
                        st.write(f"Césped: {cancha['cesped'].title()}")
                        caracteristicas = []
                        if cancha['techado']:
                            caracteristicas.append("Techada")
                        if cancha['iluminacion']:
                            caracteristicas.append("Iluminada")
                        if caracteristicas:
                            st.write(f"Características: {', '.join(caracteristicas)}")

                    with col2:
                        estado_color = {"disponible": "🟢", "mantenimiento": "🟡", "fuera_servicio": "🔴"}
                        st.write(f"Estado: {estado_color.get(cancha['estado'], '⚪')} {cancha['estado'].replace('_', ' ').title()}")
                        st.write(f"Capacidad: {cancha['capacidad_jugadores']} jugadores")
                        st.write(f"Precio día: ${cancha['precio_hora_dia']:,.2f}/hora")
                        st.write(f"Precio noche: ${cancha['precio_hora_noche']:,.2f}/hora")

                    with col3:
                        # Botones de acción según rol
                        if st.session_state.user_info['role'] == 'Administrador':
                            if cancha['estado'] == 'disponible':
                                if st.button("🔧 Mantenimiento", key=f"mant_{cancha['id']}"):
                                    # Aquí iría la lógica para cambiar a mantenimiento
                                    pass
                            elif cancha['estado'] == 'mantenimiento':
                                if st.button("✅ Disponible", key=f"disp_{cancha['id']}"):
                                    # Aquí iría la lógica para cambiar a disponible
                                    pass

                    if cancha['descripcion']:
                        st.write(f"*{cancha['descripcion']}*")

                    st.markdown("---")

            # Estadísticas de canchas
            st.subheader("📊 Estadísticas de Canchas")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_canchas = len(df_canchas)
                st.metric("Total Canchas", total_canchas)

            with col2:
                disponibles = len(df_canchas[df_canchas['estado'] == 'disponible'])
                st.metric("Disponibles", disponibles)

            with col3:
                en_mantenimiento = len(df_canchas[df_canchas['estado'] == 'mantenimiento'])
                st.metric("En Mantenimiento", en_mantenimiento)

            # Gráfico de distribución por tipo
            if not df_canchas.empty:
                tipo_dist = df_canchas['tipo'].value_counts()
                fig = px.pie(
                    values=tipo_dist.values,
                    names=[f"Fútbol {name.replace('futbol', '')}" for name in tipo_dist.index],
                    title="Distribución de Canchas por Tipo"
                )
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No hay canchas registradas")

    # Reportes
    elif selected_menu == "📈 Reportes":
        st.title("📈 Reportes y Análisis")

        tab1, tab2 = st.tabs(["Reportes de Ingresos", "Reportes de Ocupación"])

        with tab1:
            st.subheader("Reportes de Ingresos")

            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha Inicio", date.today().replace(day=1))
            with col2:
                fecha_fin = st.date_input("Fecha Fin", date.today())

            connection = get_mysql_connection()
            if connection:
                try:
                    # Ingresos por período
                    ingresos_periodo = pd.read_sql('''
                    SELECT DATE(fecha) as fecha, SUM(precio_total) as total_ingresos, COUNT(*) as num_reservas
                    FROM reservas 
                    WHERE DATE(fecha) BETWEEN %s AND %s AND estado != 'cancelada'
                    GROUP BY DATE(fecha)
                    ORDER BY fecha
                    ''', connection, params=(fecha_inicio, fecha_fin))

                    if not ingresos_periodo.empty:
                        total_ingresos = ingresos_periodo['total_ingresos'].sum()
                        total_reservas = ingresos_periodo['num_reservas'].sum()

                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Ingresos Totales", f"${total_ingresos:,.2f}")
                        with col2:
                            st.metric("Total Reservas", int(total_reservas))

                        # Gráfico de ingresos
                        ingresos_periodo['fecha_str'] = ingresos_periodo['fecha'].astype(str)
                        fig = px.line(
                            ingresos_periodo,
                            x='fecha_str',
                            y='total_ingresos',
                            title="Evolución de Ingresos",
                            labels={'fecha_str': 'Fecha', 'total_ingresos': 'Ingresos ($)'},
                            markers=True
                        )
                        fig.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig, use_container_width=True)

                        # Ingresos por cancha
                        ingresos_cancha = pd.read_sql('''
                        SELECT c.nombre as cancha, SUM(r.precio_total) as ingresos, COUNT(r.id) as reservas
                        FROM reservas r
                        JOIN canchas c ON r.cancha_id = c.id
                        WHERE DATE(r.fecha) BETWEEN %s AND %s AND r.estado != 'cancelada'
                        GROUP BY c.id, c.nombre
                        ORDER BY ingresos DESC
                        ''', connection, params=(fecha_inicio, fecha_fin))

                        if not ingresos_cancha.empty:
                            st.subheader("Ingresos por Cancha")
                            fig = px.bar(
                                ingresos_cancha,
                                x='ingresos',
                                y='cancha',
                                orientation='h',
                                title="Ingresos por Cancha",
                                labels={'ingresos': 'Ingresos ($)', 'cancha': 'Cancha'},
                                color='ingresos'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos de ingresos para el período seleccionado")

                    connection.close()

                except Error as e:
                    st.error(f"Error generando reporte de ingresos: {e}")

        with tab2:
            st.subheader("Reportes de Ocupación")

            connection = get_mysql_connection()
            if connection:
                try:
                    # Ocupación por hora del día
                    ocupacion_hora = pd.read_sql('''
                    SELECT HOUR(hora_inicio) as hora, COUNT(*) as reservas
                    FROM reservas 
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND estado != 'cancelada'
                    GROUP BY HOUR(hora_inicio)
                    ORDER BY hora
                    ''', connection)

                    if not ocupacion_hora.empty:
                        st.subheader("Ocupación por Hora (Últimos 30 días)")
                        ocupacion_hora['hora_str'] = ocupacion_hora['hora'].apply(lambda x: f"{x}:00")
                        fig = px.bar(
                            ocupacion_hora,
                            x='hora_str',
                            y='reservas',
                            title="Reservas por Hora del Día",
                            labels={'hora_str': 'Hora', 'reservas': 'Cantidad de Reservas'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Ocupación por día de la semana
                    ocupacion_dia = pd.read_sql('''
                    SELECT DAYNAME(fecha) as dia_semana, COUNT(*) as reservas
                    FROM reservas 
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND estado != 'cancelada'
                    GROUP BY DAYOFWEEK(fecha), DAYNAME(fecha)
                    ORDER BY DAYOFWEEK(fecha)
                    ''', connection)

                    if not ocupacion_dia.empty:
                        st.subheader("Ocupación por Día de la Semana")
                        fig = px.bar(
                            ocupacion_dia,
                            x='dia_semana',
                            y='reservas',
                            title="Reservas por Día de la Semana",
                            labels={'dia_semana': 'Día', 'reservas': 'Cantidad de Reservas'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    connection.close()

                except Error as e:
                    st.error(f"Error generando reporte de ocupación: {e}")

    # Configuración
    elif selected_menu == "⚙️ Configuración":
        st.title("⚙️ Configuración del Sistema")

        if st.session_state.user_info['role'] == 'Administrador':
            tab1, tab2 = st.tabs(["Información General", "Base de Datos"])

            with tab1:
                st.subheader("Información del Complejo")

                with st.form("config_form"):
                    complejo_nombre = st.text_input("Nombre del Complejo", value="Complejo Deportivo San Martín")
                    complejo_direccion = st.text_area("Dirección")
                    complejo_telefono = st.text_input("Teléfono")
                    complejo_email = st.text_input("Email")

                    if st.form_submit_button("Guardar Configuración"):
                        st.success("Configuración guardada exitosamente")

            with tab2:
                st.subheader("Estado de la Base de Datos")

                if test_mysql_connection():
                    st.success("Conexión MySQL: Activa")

                    connection = get_mysql_connection()
                    if connection:
                        try:
                            cursor = connection.cursor()
                            cursor.execute("SELECT VERSION() as version")
                            mysql_version = cursor.fetchone()[0]
                            st.info(f"Versión MySQL: {mysql_version}")
                            st.info(f"Base de datos: {DB_CONFIG['database']}")
                            cursor.close()
                            connection.close()
                        except Error as e:
                            st.error(f"Error obteniendo información de BD: {e}")
                else:
                    st.error("Conexión MySQL: Inactiva")
        else:
            st.warning("Solo los administradores pueden acceder a la configuración")

    # Footer
    st.markdown("---")
    st.markdown("**Sistema de Gestión de Canchas de Fútbol** - Desarrollado con Streamlit y MySQL")



