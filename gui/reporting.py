import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from tkinter import messagebox
from core.database import (
    obtener_registros_hoy,
    obtener_todos_codificaciones,
    obtener_config_email
)

def generar_reporte_pdf(nombre_archivo):
    try:
        registros = obtener_registros_hoy()
        if not registros:
            raise ValueError("No hay registros para generar el reporte")
        
        lienzo_pdf = pdf_canvas.Canvas(nombre_archivo, pagesize=letter)
        fecha_str = datetime.now().date().isoformat()
        
        # Encabezado
        lienzo_pdf.setFont("Helvetica-Bold", 14)
        lienzo_pdf.drawString(50, 750, f"Reporte de Asistencia - {fecha_str}")
        
        # Configuración de contenido
        lienzo_pdf.setFont("Helvetica", 12)
        posicion_y = 720
        linea_altura = 15
        
        # Obtener todos los empleados con sus horarios
        empleados = obtener_todos_codificaciones()
        mapa_horarios = {emp[0]: (emp[3], emp[4]) for emp in empleados}  # ID: (hora_entrada, hora_salida)

        # Generar contenido
        for marca_tiempo, id_emp, accion in registros:
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

            # Escribir línea
            texto_linea = f"{marca_tiempo} — {nombre} — {accion.capitalize()} — {estado} — Horario: {hora_entrada}-{hora_salida}"
            lienzo_pdf.drawString(50, posicion_y, texto_linea)
            posicion_y -= linea_altura
            
            # Nueva página si se necesita
            if posicion_y < 50:
                lienzo_pdf.showPage()
                posicion_y = 750
                lienzo_pdf.setFont("Helvetica", 12)
        
        lienzo_pdf.save()
        return True
    
    except Exception as e:
        messagebox.showerror("Error en PDF", f"Error generando reporte: {str(e)}")
        return False

def enviar_reporte_email(nombre_archivo):
    try:
        config = obtener_config_email()
        if not all(config):
            raise ValueError("Configuración de email incompleta en la base de datos")
        
        servidor, puerto, usuario, contra, destinatario = config
        fecha_str = datetime.now().date().isoformat()
        
        # Crear mensaje
        mensaje = MIMEMultipart()
        mensaje['From'] = usuario
        mensaje['To'] = destinatario
        mensaje['Subject'] = f"Reporte Diario — {fecha_str}"
        mensaje.attach(MIMEText("Adjunto reporte de asistencia de hoy.", 'plain'))

        # Adjuntar PDF
        with open(nombre_archivo, 'rb') as f:
            adjunto = MIMEApplication(f.read(), Name=nombre_archivo)
        adjunto['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        mensaje.attach(adjunto)

        # Enviar correo
        with smtplib.SMTP(servidor, int(puerto)) as servidor_smtp:
            servidor_smtp.starttls()
            servidor_smtp.login(usuario, contra)
            servidor_smtp.send_message(mensaje)
        
        return True
    
    except Exception as e:
        messagebox.showerror("Error en Email", f"Error enviando reporte: {str(e)}")
        return False

def generar_y_enviar_reporte():
    try:
        fecha_str = datetime.now().date().isoformat()
        nombre_archivo = f"reporte_{fecha_str}.pdf"
        
        # Paso 1: Generar PDF
        if not generar_reporte_pdf(nombre_archivo):
            return
        
        # Paso 2: Enviar por email
        if not enviar_reporte_email(nombre_archivo):
            return
        
        messagebox.showinfo("Éxito", "Reporte generado y enviado correctamente")
    
    except Exception as e:
        messagebox.showerror("Error General", f"Error en proceso de reporte: {str(e)}")