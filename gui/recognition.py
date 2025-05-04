import re
import cv2
import pickle
import numpy as np
import sqlite3
from tkinter import simpledialog, messagebox
from deepface import DeepFace
from datetime import datetime
from PIL import Image, ImageTk
import tkinter as tk
from core.database import (
    agregar_empleado, 
    obtener_todos_codificaciones, 
    registrar_asistencia, 
    obtener_ultima_accion  
)
from core.config import SALTAR_DETECCION_VIVACIDAD

def detectar_parpadeo(marco_rgb):
    try:
        caras = DeepFace.extract_faces(
            img_path=marco_rgb,
            detector_backend='mediapipe',
            enforce_detection=False
        )
    except Exception:
        return False

    if not caras:
        return False

    puntos_referencia = caras[0].get('landmarks', {})
    ojo_izquierdo = puntos_referencia.get('left_eye', [])
    ojo_derecho = puntos_referencia.get('right_eye', [])
    if len(ojo_izquierdo) < 6 or len(ojo_derecho) < 6:
        return False

    def calcular_rao(puntos_ojo):
        pts = np.array([(p['x'], p['y']) for p in puntos_ojo])
        p1, p2, p3, p4, p5, p6 = pts
        vertical1 = np.linalg.norm(p2 - p6)
        vertical2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        return (vertical1 + vertical2) / (2.0 * horizontal) if horizontal > 0 else 0.0

    rao_promedio = (calcular_rao(ojo_izquierdo) + calcular_rao(ojo_derecho)) / 2.0
    return rao_promedio < 0.21

def streaming_reconocimiento(app):
    captura = cv2.VideoCapture(0)
    datos = obtener_todos_codificaciones()
    
    if not datos:
        messagebox.showinfo("Info", "No hay empleados registrados.")
        return
    
    ids, nombres, codificaciones, horas_entrada, horas_salida = zip(*datos)
    
    while getattr(app, 'stream_activo', True):
        ret, marco = captura.read()
        if not ret: 
            continue
        
        marco_pequeno = cv2.resize(marco, (0,0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(marco_pequeno, cv2.COLOR_BGR2RGB)
        
        try:
            # Detectar solo 1 rostro por frame
            representaciones = DeepFace.represent(
                rgb,
                model_name='Facenet',
                detector_backend='mediapipe',
                enforce_detection=False,
                align=False
            )
            
            if not representaciones:
                continue
                
            # Tomar solo el rostro con mayor confianza
            rep = max(representaciones, key=lambda x: x['face_confidence'])
            
            facial_area = rep['facial_area']
            x = facial_area['x'] * 4  # x4 por el resize 0.25
            y = facial_area['y'] * 4
            w = facial_area['w'] * 4
            h = facial_area['h'] * 4
            
            embedding = np.array(rep['embedding'], dtype=np.float32)
            embedding /= np.linalg.norm(embedding)  # Normalización L2
            
            # Calcular similaridad con todos
            similaridades = [np.dot(embedding, cod) for cod in codificaciones]
            indice = np.argmax(similaridades)
            similaridad_max = similaridades[indice]
            
            if similaridad_max > 0.65:  # Umbral aumentado para Facenet
                id_empleado = ids[indice]
                nombre = nombres[indice]
                hora_entrada = horas_entrada[indice]
                hora_salida = horas_salida[indice]
                
                ahora = datetime.now()
                hora_salida_obj = datetime.strptime(hora_salida, "%H:%M").time()
                hora_actual = ahora.time()
                
                # Determinar acción
                accion = 'salida' if hora_actual >= hora_salida_obj else 'entrada'
                
                # Registrar solo 1 vez por detección
                if registrar_asistencia(id_empleado, accion):
                    texto = f"{nombre} | {accion.upper()} | Registrado"
                else:
                    texto = f"{nombre} | {accion.upper()} | No registrado"
                
                cv2.rectangle(marco, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(marco, texto, (x, y-10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        except Exception as e:
            print(f"Error en reconocimiento: {str(e)}")
            continue

        # Actualizar interfaz
        img = cv2.cvtColor(marco, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        app.marco_camara.config(image=imgtk)
        app.marco_camara.image = imgtk

    captura.release()

def registrar_empleado_gui():
    nombre = simpledialog.askstring("Registrar Empleado", "Nombre del empleado:")
    if not nombre:
        return
    
    # Validar formato de hora
    while True:
        hora_entrada = simpledialog.askstring("Horario", "Hora entrada (HH:MM):", initialvalue="09:00")
        hora_salida = simpledialog.askstring("Horario", "Hora salida (HH:MM):", initialvalue="18:00")
        
        if re.match(r"^\d{2}:\d{2}$", hora_entrada) and re.match(r"^\d{2}:\d{2}$", hora_salida):
            break
        messagebox.showerror("Error", "Formato inválido. Use HH:MM")
    
    # Capturar rostro
    captura = cv2.VideoCapture(0)
    messagebox.showinfo("Registrar", "Presiona 's' para capturar foto. 'q' para cancelar.")
    
    registro_exitoso = False
    while True:
        ret, marco = captura.read()
        if not ret:
            continue
        
        cv2.imshow("Registrar - presiona 's' o 'q'", marco)
        tecla = cv2.waitKey(1) & 0xFF
        
        if tecla == ord('s'):
            try:
                rgb = cv2.cvtColor(marco, cv2.COLOR_BGR2RGB)
                representacion = DeepFace.represent(
                    rgb,
                    model_name='Facenet',
                    detector_backend='mediapipe',
                    enforce_detection=False
                )[0]

                # Convertir a numpy array y verificar tamaño
                embedding = np.array(representacion['embedding'], dtype=np.float32)
                
                if embedding.shape != (128,):  # Facenet debe generar 128 elementos
                    raise ValueError(f"Dimensión incorrecta: {embedding.shape}")

                # Serializar CORRECTAMENTE
                bytes_codificacion = pickle.dumps(embedding.tobytes())  # <--- ¡Cambio clave!

                agregar_empleado(nombre, bytes_codificacion, hora_entrada, hora_salida)
                messagebox.showinfo("Registrado", f"Empleado '{nombre}' registrado con éxito.")
                break

            except Exception as e:
                messagebox.showerror("Error", f"Falló el registro: {str(e)}")
                break
                    
        elif tecla == ord('q'):
            break
    
    captura.release()
    cv2.destroyAllWindows()

def reconocer_empleado_gui(accion=None):
    if not accion:
        accion = simpledialog.askstring("Registro", "Tipo de registro ('entrada' o 'salida'):")
    
    if accion not in ('entrada', 'salida'):
        messagebox.showerror("Error", "Acción no válida.")
        return

    datos = obtener_todos_codificaciones()
    if not datos:
        messagebox.showinfo("Info", "No hay empleados registrados.")
        return
    ids, nombres, codificaciones = zip(*datos)

    captura = cv2.VideoCapture(0)
    messagebox.showinfo("Reconocimiento", f"Registro de {accion}. Presiona 'q' para cancelar.")
    while True:
        ret, marco = captura.read()
        if not ret:
            continue
        reducido = cv2.resize(marco, (0,0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(reducido, cv2.COLOR_BGR2RGB)

        try:
            representaciones = DeepFace.represent(
                rgb,
                model_name='Facenet',
                detector_backend='mediapipe',
                enforce_detection=False
            )
        except ValueError:
            representaciones = []

        for rep in representaciones:
            cod_actual = np.array(rep['embedding'], dtype=np.float32)
            distancias = [1 - np.dot(cod_actual, cod)/(np.linalg.norm(cod_actual)*np.linalg.norm(cod)) for cod in codificaciones]
            indice = int(np.argmin(distancias))
            if distancias[indice] < 0.4:
                id_empleado, nombre = ids[indice], nombres[indice]
                ultima_accion = obtener_ultima_accion(id_empleado)
                if ultima_accion == accion:
                    messagebox.showwarning("Aviso", f"Ya marcaste '{accion}' anteriormente.")
                    break
                registrar_asistencia(id_empleado, accion)
                mostrar_animacion_bienvenida(nombre, marco)
                captura.release()
                cv2.destroyAllWindows()
                return

        cv2.imshow("Reconocimiento - presiona 'q'", marco)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    captura.release()
    cv2.destroyAllWindows()

def mostrar_animacion_bienvenida(nombre, marco):
    ventana = tk.Toplevel()
    ventana.overrideredirect(True)
    imagen = cv2.cvtColor(marco, cv2.COLOR_BGR2RGB)
    h, w, _ = imagen.shape
    imagen = cv2.resize(imagen, (w*2, h*2), interpolation=cv2.INTER_LINEAR)
    pil_imagen = ImageTk.PhotoImage(Image.fromarray(imagen))
    etiqueta = tk.Label(ventana, image=pil_imagen)
    etiqueta.image = pil_imagen
    etiqueta.pack()
    mensaje = tk.Label(ventana, text=f"¡Bienvenido, {nombre}!", font=('Helvetica', 20, 'bold'),
                   bg='black', fg='white')
    mensaje.pack(fill='x')
    ventana.after(2000, ventana.destroy)