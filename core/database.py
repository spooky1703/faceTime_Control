#hasta aqui funciona
import sqlite3
from datetime import datetime, timedelta
import pickle
import numpy as np
import re
from tkinter import messagebox
from core.config import RUTA_BD

def inicializar_bd():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            encoding BLOB NOT NULL,
            hora_entrada TEXT NOT NULL DEFAULT '09:00',
            hora_salida TEXT NOT NULL DEFAULT '18:00'
        );''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            timestamp TEXT NOT NULL,
            employee_id INTEGER,
            action TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS config_email (
            servidor_smtp TEXT,
            puerto_smtp INTEGER,
            usuario TEXT,
            contrasena TEXT,
            destinatario TEXT
        );''')
    
    conexion.commit()
    conexion.close()

def agregar_empleado(nombre, bytes_codificacion, hora_entrada='09:00', hora_salida='18:00'):
    if not re.match(r"^\d{2}:\d{2}$", hora_entrada) or not re.match(r"^\d{2}:\d{2}$", hora_salida):
        raise ValueError("Formato de hora inválido (Use HH:MM)")
    
    # Verificar integridad de los bytes
    try:
        bytes_embedding = pickle.loads(bytes_codificacion)
        embedding = np.frombuffer(bytes_embedding, dtype=np.float32)

        if embedding.size != 128:
            raise ValueError("Codificación facial corrupta")
    except Exception as e:
        raise ValueError(f"Error en codificación: {str(e)}")
    
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    try:
        c.execute('''INSERT INTO employees (name, encoding, hora_entrada, hora_salida) 
                   VALUES (?, ?, ?, ?);''', 
                   (nombre, bytes_codificacion, hora_entrada, hora_salida))
        conexion.commit()
    except sqlite3.IntegrityError:
        raise ValueError("El empleado ya existe")
    finally:
        conexion.close()
        
def obtener_todos_codificaciones():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("SELECT id, name, encoding, hora_entrada, hora_salida FROM employees;")
    filas = c.fetchall()
    conexion.close()

    empleados = []
    for fila in filas:
        id_emp, nombre, codificacion, h_entrada, h_salida = fila
        
        # Cargar correctamente los bytes
        bytes_embedding = pickle.loads(codificacion)
        embedding = np.frombuffer(bytes_embedding, dtype=np.float32)
        
        if embedding.shape != (128,):
            continue  # Omitir datos corruptos
        
        embedding = embedding / np.linalg.norm(embedding)  # Normalizar
        empleados.append((id_emp, nombre, embedding, h_entrada, h_salida))
    
    return empleados

def obtener_horario_empleado(id_empleado):
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("SELECT hora_entrada, hora_salida FROM employees WHERE id = ?;", (id_empleado,))
    resultado = c.fetchone()
    conexion.close()
    return resultado if resultado else ('09:00', '18:00')

def registrar_asistencia(id_empleado, accion):
    ahora = datetime.now()
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    
    try:
        hora_entrada, hora_salida = obtener_horario_empleado(id_empleado)
        hora_salida_obj = datetime.strptime(hora_salida, "%H:%M").time()
        hora_actual = ahora.time()
        
        # Validar salida sin popups
        if accion == "salida" and hora_actual < hora_salida_obj:
            return False  # Solo retorna False sin mostrar error
        
        # Lógica anti-duplicados
        c.execute('''SELECT action, timestamp FROM logs 
                   WHERE employee_id = ? 
                   ORDER BY timestamp DESC LIMIT 1''', (id_empleado,))
        ultimo = c.fetchone()
        
        if ultimo:
            ultima_accion, ultimo_tiempo = ultimo
            ultimo_tiempo = datetime.fromisoformat(ultimo_tiempo)
            if (ahora - ultimo_tiempo).seconds < 300 and ultima_accion == accion:
                return False
        
        # Insertar registro
        marca_tiempo = ahora.isoformat(timespec='seconds')
        c.execute('''INSERT INTO logs (timestamp, employee_id, action) 
                   VALUES (?, ?, ?)''', (marca_tiempo, id_empleado, accion))
        conexion.commit()
        return True
        
    except Exception as e:
        print(f"Error registrando: {str(e)}")
        return False
    finally:
        conexion.close()

def obtener_empleados_con_horarios():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("SELECT id, name, hora_entrada, hora_salida FROM employees ORDER BY name;")
    empleados = c.fetchall()
    conexion.close()
    return empleados

def actualizar_empleado(id_empleado, nuevo_nombre, nueva_entrada, nueva_salida):
    if not re.match(r"^\d{2}:\d{2}$", nueva_entrada) or not re.match(r"^\d{2}:\d{2}$", nueva_salida):
        raise ValueError("Formato de hora inválido")
    
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    try:
        c.execute('''UPDATE employees 
                   SET name = ?, hora_entrada = ?, hora_salida = ?
                   WHERE id = ?''', 
                   (nuevo_nombre, nueva_entrada, nueva_salida, id_empleado))
        conexion.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conexion.close()

def eliminar_empleado(id_empleado):
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("DELETE FROM employees WHERE id = ?;", (id_empleado,))
    conexion.commit()
    filas_afectadas = c.rowcount
    conexion.close()
    return filas_afectadas > 0

def obtener_registros_hoy():
    hoy = datetime.now().date().isoformat()
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("SELECT timestamp, employee_id, action FROM logs WHERE DATE(timestamp) = ? ORDER BY timestamp;", (hoy,))
    filas = c.fetchall()
    conexion.close()
    return filas

def limpiar_registros():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("DELETE FROM logs;")
    conexion.commit()
    conexion.close()

def obtener_config_email():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS config_email (
        servidor_smtp TEXT,
        puerto_smtp INTEGER,
        usuario TEXT,
        contrasena TEXT,
        destinatario TEXT
    );''')
    
    c.execute("SELECT servidor_smtp, puerto_smtp, usuario, contrasena, destinatario FROM config_email LIMIT 1;")
    config = c.fetchone()
    conexion.close()
    return config if config else (None, None, None, None, None)

def establecer_config_email(servidor, puerto, usuario, contra, destinatario):
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("DELETE FROM config_email;")
    c.execute('''INSERT INTO config_email (servidor_smtp, puerto_smtp, usuario, contrasena, destinatario)
               VALUES (?, ?, ?, ?, ?)''', (servidor, puerto, usuario, contra, destinatario))
    conexion.commit()
    conexion.close()

def obtener_ultima_accion(id_empleado):
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute('''SELECT action FROM logs 
               WHERE employee_id = ? 
               ORDER BY timestamp DESC LIMIT 1''', (id_empleado,))
    resultado = c.fetchone()
    conexion.close()
    return resultado[0] if resultado else None