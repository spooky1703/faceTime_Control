import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import re
import sqlite3
from datetime import datetime, timedelta
from core.database import (
    obtener_empleados_con_horarios, actualizar_empleado, eliminar_empleado,
    obtener_horario_empleado, obtener_registros_hoy, obtener_todos_codificaciones
)
from core.config import RUTA_BD, CONTRASENA_ADMIN
from gui.reporting import generar_y_enviar_reporte
from gui.recognition import registrar_empleado_gui

def gestionar_empleados_gui():
    def actualizar_lista():
        lista_empleados.delete(0, tk.END)
        empleados = obtener_empleados_con_horarios()  
        for emp in empleados:
            # Formato: ID - Nombre (Horario: HH:MM a HH:MM)
            lista_empleados.insert(tk.END, f"{emp[0]} - {emp[1]} (Entrada: {emp[2]}, Salida: {emp[3]})")
        lbl_contador.config(text=f"Empleados registrados: {len(empleados)}")

    def editar_seleccionado():
        seleccion = lista_empleados.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Selecciona un empleado primero")
            return
            
        entry_text = lista_empleados.get(seleccion[0])
        emp_id = entry_text.split(" - ")[0]
        
        # Obtener datos actuales desde la BD
        conexion = sqlite3.connect(RUTA_BD)
        c = conexion.cursor()
        c.execute("SELECT name, hora_entrada, hora_salida FROM employees WHERE id = ?", (emp_id,))
        nombre_actual, hora_entrada_act, hora_salida_act = c.fetchone()
        conexion.close
        
        # Diálogo de edición
        nuevo_nombre = simpledialog.askstring("Editar empleado", "Nuevo nombre:", initialvalue=nombre_actual)
        nueva_entrada = simpledialog.askstring("Horario", "Hora entrada (HH:MM):", initialvalue=hora_entrada_act)
        nueva_salida = simpledialog.askstring("Horario", "Hora salida (HH:MM):", initialvalue=hora_salida_act)
        
        # Validaciones
        if not all([re.match(r"^\d{2}:\d{2}$", h) for h in [nueva_entrada, nueva_salida]]):
            messagebox.showerror("Error", "Formato de hora inválido")
            return
            
        # Actualizar en BD
        try:
            actualizar_empleado(emp_id, nuevo_nombre, nueva_entrada, nueva_salida)
            actualizar_lista()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_seleccionado():
        seleccion = lista_empleados.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Selecciona un empleado primero")
            return
            
        # Extraer ID del formato del listbox
        entry_text = lista_empleados.get(seleccion[0])
        emp_id = entry_text.split(" - ")[0]
        
        # Obtener nombre real desde la BD
        conexion = sqlite3.connect(RUTA_BD)
        c = conexion.cursor()
        c.execute("SELECT name FROM employees WHERE id = ?", (emp_id,))
        nombre = c.fetchone()[0]
        conexion.close()

        if messagebox.askyesno("Confirmar", f"¿Eliminar a {nombre} permanentemente?"):
            if eliminar_empleado(emp_id):
                actualizar_lista()
                messagebox.showinfo("Éxito", "Empleado eliminado")
            else:
                messagebox.showerror("Error", "No se pudo eliminar")


  
    ventana = tk.Toplevel()
    ventana.title("Gestión de Empleados")
    ventana.geometry("500x400")
    
    marco_principal = tk.Frame(ventana, padx=20, pady=20)
    marco_principal.pack(fill=tk.BOTH, expand=True)
    
    lbl_titulo = tk.Label(marco_principal, text="Lista de Empleados Registrados",
                        font=('Helvetica', 14, 'bold'))
    lbl_titulo.pack(pady=5)
    
    lbl_contador = tk.Label(marco_principal, text="Cargando...")
    lbl_contador.pack()
    
    marco_lista = tk.Frame(marco_principal)
    marco_lista.pack(fill=tk.BOTH, expand=True, pady=10)
    
    lista_empleados = tk.Listbox(marco_lista, font=('Helvetica', 12))
    scroll = tk.Scrollbar(marco_lista, orient=tk.VERTICAL)
    lista_empleados.config(yscrollcommand=scroll.set)
    scroll.config(command=lista_empleados.yview)
    
    lista_empleados.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    marco_botones = tk.Frame(marco_principal)
    marco_botones.pack(pady=10)
    
    btn_registrar = tk.Button(marco_botones, 
                            text="➕ Nuevo Empleado", 
                            command=registrar_empleado_gui,
                            bg='#2ecc71', width=15)
    btn_registrar.pack(side=tk.LEFT, padx=5)
    
    btn_editar = tk.Button(marco_botones, text="✏️ Editar", command=editar_seleccionado,
                         bg='#f39c12', width=15)
    btn_editar.pack(side=tk.LEFT, padx=5)
    
    btn_eliminar = tk.Button(marco_botones, text="🗑️ Eliminar", command=eliminar_seleccionado,
                           bg='#e74c3c', width=15)
    btn_eliminar.pack(side=tk.LEFT, padx=5)
    
    btn_actualizar = tk.Button(marco_principal, text="🔄 Actualizar Lista", 
                             command=actualizar_lista, bg='#3498db')
    btn_actualizar.pack(pady=10)
    
    actualizar_lista()

def configurar_correo_gui():
    servidor_smtp = simpledialog.askstring("Email", "SMTP server: (ej: smtp.gmail.com)")
    puerto_smtp = simpledialog.askinteger("Email", "SMTP port: (ej: 587)")
    usuario = simpledialog.askstring("Email", "Usuario: (tu correo)")
    contrasena = simpledialog.askstring("Email", "Contraseña:", show='*')
    destinatario = simpledialog.askstring("Email", "Destinatario:")
    
    from core.database import establecer_config_email  # <-- Agregar este import
    establecer_config_email(servidor_smtp, puerto_smtp, usuario, contrasena, destinatario)
    
    messagebox.showinfo("Email", "Configuración de correo guardada.")

def mostrar_registros_gui():
    conexion = sqlite3.connect(RUTA_BD)
    c = conexion.cursor()
    c.execute("SELECT timestamp, employee_id, action FROM logs ORDER BY timestamp DESC;")
    filas = c.fetchall()
    conexion.close()

    # Obtener todos los empleados con sus horarios
    empleados = obtener_todos_codificaciones()
    mapa_horarios = {emp[0]: (emp[3], emp[4]) for emp in empleados}  # ID: (hora_entrada, hora_salida)

    ventana = tk.Toplevel()
    ventana.title("Historial de Registros")
    columnas = ("timestamp", "nombre", "accion", "estado", "horario")
    arbol = ttk.Treeview(ventana, columns=columnas, show='headings')
    
    # Configurar columnas
    for col in columnas:
        arbol.heading(col, text=col.capitalize())
    
    arbol.pack(fill=tk.BOTH, expand=True)

    for marca_tiempo, id_emp, accion in filas:
        nombre = next((emp[1] for emp in empleados if emp[0] == id_emp), "Desconocido")
        tiempo = datetime.fromisoformat(marca_tiempo).time()
        
        # Obtener horario del empleado
        hora_entrada, hora_salida = mapa_horarios.get(id_emp, ('09:00', '18:00'))
        hora_entrada_obj = datetime.strptime(hora_entrada, "%H:%M").time()
        hora_salida_obj = datetime.strptime(hora_salida, "%H:%M").time()
        
        # Determinar estado
        if accion == 'entrada':
            estado = 'A tiempo' if tiempo <= hora_entrada_obj else 'Tarde'
        else:
            margen_tardanza = datetime.combine(datetime.today(), hora_salida_obj) + timedelta(minutes=5)
            hora_limite = margen_tardanza.time()
            
            if tiempo < hora_salida_obj:
                estado = 'Temprano'
            elif tiempo > hora_limite:
                estado = 'Tarde'
            else:
                estado = 'A tiempo'

        arbol.insert("", tk.END, values=(
            marca_tiempo, 
            nombre, 
            accion, 
            estado,
            f"{hora_entrada} - {hora_salida}"
        ))

def limpiar_registros_gui():
    # Verificar contraseña
    contrasena = simpledialog.askstring("Confirmación", "Contraseña de administrador:", show='*')
    if contrasena != CONTRASENA_ADMIN:
        messagebox.showerror("Error", "Contraseña incorrecta")
        return
    
    if messagebox.askyesno("Confirmar", "¿Borrar TODOS los registros de asistencia?\nEsta acción es irreversible"):
        conexion = sqlite3.connect(RUTA_BD)
        c = conexion.cursor()
        c.execute("DELETE FROM logs;")
        conexion.commit()
        conexion.close()
        messagebox.showinfo("Éxito", "Registros eliminados completamente")

botones = [
    ("👥 Gestión de Empleados", gestionar_empleados_gui, '#3498db'),
    ("✉️ Configurar Email", configurar_correo_gui, '#8e44ad'),
    ("📋 Mostrar Registros", mostrar_registros_gui, '#16a085'),
    ("📤 Enviar Reporte Diario", generar_y_enviar_reporte, '#2ecc71'),
    ("⚠️ Limpiar Todos los Registros", limpiar_registros_gui, '#e74c3c')
]