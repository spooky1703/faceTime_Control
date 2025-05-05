import threading
from PIL import Image, ImageTk
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import cv2
from gui.admin_panels import (
    gestionar_empleados_gui, 
    configurar_correo_gui,  
    mostrar_registros_gui, 
    generar_y_enviar_reporte,
    limpiar_registros_gui  

)
from gui.recognition import registrar_empleado_gui, reconocer_empleado_gui, mostrar_animacion_bienvenida, streaming_reconocimiento
from core.config import CONTRASENA_ADMIN
from core.database import obtener_horario_empleado

class AplicacionPrincipal:
    def __init__(self, raiz):
        self.raiz = raiz
        self.stream_activo = False 
        self.raiz.attributes('-fullscreen', True)
        self.raiz.configure(bg='#255b79')  # Color principal cambiado
        self.raiz.bind("<Escape>", lambda e: self.raiz.destroy())
        
        self.estilo_botones = {
            'font': ('Helvetica', 18, 'bold'),
            'width': 35,
            'height': 2,
            'bd': 0,
            'highlightthickness': 0,
            'activebackground': '#3d6b88',
            'fg': 'black'  # Texto en blanco para mejor contraste
        }
        
        self.crear_menu_principal()
        self.crear_boton_salir()

    def crear_boton_salir(self):
        boton_salir = tk.Button(self.raiz, text="X", 
                              command=self.salir_aplicacion,
                              font=('Helvetica', 18, 'bold'),
                              bg='#ff4444', fg='black',
                              bd=0, highlightthickness=0)
        boton_salir.place(relx=0.98, rely=0.02, anchor='ne')

    def salir_aplicacion(self):
        if messagebox.askokcancel("Salir", "¿Está seguro de cerrar la aplicación?"):
            self.raiz.destroy()
            cv2.destroyAllWindows()
            os._exit(0)
    
    def crear_menu_principal(self):
        if hasattr(self, 'stream_activo'):
            self.detener_streaming() 
        self.limpiar_ventana()
        
        marco_principal = tk.Frame(self.raiz, bg='#255b79')
        marco_principal.place(relx=0.5, rely=0.5, anchor='center', width=1200, height=800)

        try:
            from PIL import Image, ImageTk
            script_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.abspath(os.path.join(script_dir, "..", "assets"))
            img_path = os.path.join(assets_dir, "fondoFinal.png")
            
            img_logo = Image.open(img_path)
            img_logo = img_logo.resize((1300, 550), Image.Resampling.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(img_logo)
            
            lbl_logo = tk.Label(marco_principal, 
                            image=self.logo_tk, 
                            bg='#255b79')
            lbl_logo.pack(pady=(40, 20))
            lbl_logo.image = self.logo_tk
            
        except Exception as e:
            print(f"Error cargando logo: {str(e)}")
            lbl_logo = tk.Label(marco_principal, 
                              text="FaceTime\nControl", 
                              font=('Helvetica', 36, 'bold'), 
                              fg='black', 
                              bg='#255b79')
            lbl_logo.pack(pady=(40, 20))

        marco_botones = tk.Frame(marco_principal, bg='#255b79')
        marco_botones.pack(pady=40)

        estilo_botones = {
            'font': ('Helvetica', 22, 'bold'),
            'width': 32,
            'height': 2,
            'bd': 0,
            'highlightthickness': 0,
            'activebackground': '#3d6b88',
            'fg': 'black'
        }

        btn_admin = tk.Button(marco_botones,
                            text="🔑 OPERACIONES DE ADMINISTRADOR",
                            command=self.acceso_administrador,
                            bg='#3498db',
                            **estilo_botones)
        btn_admin.pack(side=tk.LEFT, padx=25, pady=15)

        btn_trabajo = tk.Button(marco_botones,
                              text="👨💼 MODO TRABAJO",
                              command=self.modo_trabajo,
                              bg='#27ae60',
                              **estilo_botones)
        btn_trabajo.pack(side=tk.LEFT, padx=25, pady=15)

        self.crear_boton_salir()

    def acceso_administrador(self):
        contrasena = simpledialog.askstring("Acceso Administrador", "Contraseña:", show='*')
        if contrasena == CONTRASENA_ADMIN:
            self.crear_panel_admin()
        else:
            messagebox.showerror("Error", "Contraseña incorrecta")
    
    def crear_panel_admin(self):
        self.limpiar_ventana()
        marco_principal = tk.Frame(self.raiz, bg='#255b79')
        marco_principal.place(relx=0.5, rely=0.5, anchor='center')

        titulo = tk.Label(marco_principal, 
                        text="🔒 Panel de Administración", 
                        font=('Helvetica', 28, 'bold'), 
                        bg='#255b79', 
                        fg='white')
        titulo.pack(pady=40)

        marco_botones = tk.Frame(marco_principal, bg='#255b79')
        marco_botones.pack(pady=20)

        botones = [
        ("👥 Gestión de Empleados", gestionar_empleados_gui, '#3498db'),
        ("✉️ Configurar Email", configurar_correo_gui, '#8e44ad'),
        ("📋 Mostrar Registros", mostrar_registros_gui, '#16a085'),
        ("📤 Enviar Reporte Diario", generar_y_enviar_reporte, '#2ecc71'),
        ("⚠️ Limpiar Todos los Registros", limpiar_registros_gui, '#e74c3c')
        ]

        for texto, comando, color in botones:
            boton = tk.Button(marco_botones, 
                            text=texto, 
                            command=comando, 
                            bg=color,
                            **self.estilo_botones)
            boton.pack(pady=10)

        boton_salida = tk.Button(marco_principal, 
                               text="🔙 Volver al Menú Principal", 
                               command=self.crear_menu_principal, 
                               bg='#e74c3c',
                               **self.estilo_botones)
        boton_salida.pack(pady=30)

    def modo_trabajo(self):
        self.limpiar_ventana()
        marco_principal = tk.Frame(self.raiz, bg='#255b79')
        marco_principal.pack(fill=tk.BOTH, expand=True)
        
        self.marco_camara = tk.Label(marco_principal)
        self.marco_camara.pack(pady=20, padx=20)
        
        marco_botones = tk.Frame(marco_principal, bg='#255b79')
        marco_botones.pack(pady=10)
        
        btn_regresar = tk.Button(marco_principal, 
                           text="🏠 Menú Principal", 
                           command=self.crear_menu_principal,
                           bg='#3498db',
                           **self.estilo_botones)
        btn_regresar.pack(pady=10, side=tk.TOP, anchor=tk.NW)
        
        btn_iniciar = tk.Button(marco_botones, 
                            text="▶️ Iniciar Reconocimiento", 
                            command=self.iniciar_streaming,
                            bg='#27ae60',
                            **self.estilo_botones)
        btn_iniciar.pack(side=tk.LEFT, padx=10)
        
        btn_detener = tk.Button(marco_botones,
                            text="⏹ Detener Reconocimiento",
                            command=self.detener_streaming,
                            bg='#e74c3c',
                            **self.estilo_botones)
        btn_detener.pack(side=tk.LEFT, padx=10)

    def iniciar_streaming(self):
        if not self.stream_activo:
            self.stream_activo = True
            threading.Thread(target=streaming_reconocimiento, args=(self,), daemon=True).start()

    def detener_streaming(self):
        self.stream_activo = False

    def mostrar_selector_accion(self):
        ventana_emergente = tk.Toplevel(self.raiz)
        ventana_emergente.title("Selección de Acción")
        ventana_emergente.configure(bg='#255b79')
        ventana_emergente.attributes('-topmost', True)
        
        ancho_pantalla = self.raiz.winfo_screenwidth()
        alto_pantalla = self.raiz.winfo_screenheight()
        ancho_ventana = 600
        alto_ventana = 300
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)
        ventana_emergente.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        
        tk.Label(ventana_emergente, 
               text="Seleccione el tipo de registro:", 
               font=('Helvetica', 20, 'bold'), 
               bg='#255b79', 
               fg='white').pack(pady=20)
        
        marco_botones = tk.Frame(ventana_emergente, bg='#255b79')
        marco_botones.pack(pady=20)
        
        boton_entrada = tk.Button(marco_botones, 
                                text="🟢 ENTRADA", 
                                font=('Helvetica', 18), 
                                command=lambda: self.procesar_accion('entrada', ventana_emergente),
                                width=15, height=2, bg='#27ae60', fg='white')
        boton_entrada.pack(side=tk.LEFT, padx=20)
        
        boton_salida = tk.Button(marco_botones, 
                               text="🔴 SALIDA", 
                               font=('Helvetica', 18), 
                               command=lambda: self.procesar_accion('salida', ventana_emergente),
                               width=15, height=2, bg='#c0392b', fg='white')
        boton_salida.pack(side=tk.RIGHT, padx=20)
    
    def procesar_accion(self, accion, ventana):
        ventana.destroy()
        reconocer_empleado_gui(accion)
    
    def salir_modo_trabajo(self):
        contrasena = simpledialog.askstring("Salir del Modo Trabajo", 
                                         "Contraseña de Administrador:", show='*')
        if contrasena == CONTRASENA_ADMIN:
            self.crear_menu_principal()
        else:
            messagebox.showerror("Error", "Contraseña incorrecta")
    
    def limpiar_ventana(self):
        for widget in self.raiz.winfo_children():
            widget.destroy()

def main():
    root = tk.Tk()
    root.title("Control de Asistencia Facial")
    app = AplicacionPrincipal(root)
    root.mainloop()

if __name__ == "__main__":
    main()