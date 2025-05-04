import smtplib
import os
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

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generar_reporte_pdf(nombre_archivo):
    try:
        registros = obtener_registros_hoy()
        if not registros:
            raise ValueError("No hay registros para generar el reporte")
        
        # Configuración inicial
        pdf = pdf_canvas.Canvas(nombre_archivo, pagesize=letter)
        ancho, alto = letter
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        estilo_encabezado = ParagraphStyle(
            'Encabezado',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=1,
            spaceAfter=20,
            textColor=colors.HexColor('#2c3e50')
        )
        
        estilo_titulo_columna = ParagraphStyle(
            'TituloColumna',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=1
        )
        
        # Encabezado del documento
        encabezado = Paragraph("Reporte de Asistencia Diaria", estilo_encabezado)
        
        # Contenido de la tabla
        empleados = obtener_todos_codificaciones()
        mapa_horarios = {emp[0]: (emp[3], emp[4]) for emp in empleados}
        
        # Crear datos para la tabla
        datos = [
            [
                Paragraph('<b>Fecha/Hora</b>', estilo_titulo_columna),
                Paragraph('<b>Empleado</b>', estilo_titulo_columna),
                Paragraph('<b>Tipo</b>', estilo_titulo_columna),
                Paragraph('<b>Estado</b>', estilo_titulo_columna),
                Paragraph('<b>Horario</b>', estilo_titulo_columna)
            ]
        ]
        
        for marca_tiempo, id_emp, accion in registros:
            nombre = next((emp[1] for emp in empleados if emp[0] == id_emp), "Desconocido")
            tiempo = datetime.fromisoformat(marca_tiempo)
            hora_entrada, hora_salida = mapa_horarios.get(id_emp, ('09:00', '18:00'))
            
            # Formatear fecha y hora
            fecha_formateada = tiempo.strftime("%d/%m/%Y %H:%M")
            
            # Determinar estado con colores
            hora_entrada_obj = datetime.strptime(hora_entrada, "%H:%M").time()
            hora_salida_obj = datetime.strptime(hora_salida, "%H:%M").time()
            
            if accion == 'entrada':
                estado = 'Tarde' if tiempo.time() > hora_entrada_obj else 'A tiempo'
                color_estado = colors.red if estado == 'Tarde' else colors.green
            else:
                margen = datetime.combine(tiempo.date(), hora_salida_obj) + timedelta(minutes=5)
                estado = 'A tiempo' if margen.time() >= tiempo.time() >= hora_salida_obj else 'Temprano' if tiempo.time() < hora_salida_obj else 'Tarde'
                color_estado = colors.orange if estado == 'Temprano' else colors.green if estado == 'A tiempo' else colors.red
            
            datos.append([
                fecha_formateada,
                nombre,
                accion.capitalize(),
                Paragraph(f'<font color="{color_estado}">{estado}</font>', styles['Normal']),
                f"{hora_entrada} - {hora_salida}"
            ])
        
        # Crear tabla
        tabla = Table(datos, colWidths=[100, 120, 60, 80, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        # Construir PDF
        elementos = [encabezado, Spacer(1, 12), tabla]
        tabla.wrapOn(pdf, ancho - 100, alto)
        tabla.drawOn(pdf, 50, alto - 250)
        
        # Pie de página
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawRightString(ancho - 50, 30, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        pdf.save()
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
        
        if not os.path.exists(nombre_archivo):
            raise FileNotFoundError(f"Archivo no encontrado: {nombre_archivo}")

        mensaje = MIMEMultipart()
        mensaje['From'] = usuario
        mensaje['To'] = destinatario
        mensaje['Subject'] = f"Reporte Diario — {fecha_str}"
        mensaje.attach(MIMEText("Adjunto reporte de asistencia de hoy.", 'plain'))

        with open(nombre_archivo, 'rb') as f:
            adjunto = MIMEApplication(f.read(), Name=os.path.basename(nombre_archivo))
        
        adjunto['Content-Disposition'] = f'attachment; filename="{os.path.basename(nombre_archivo)}"'
        mensaje.attach(adjunto)

        with smtplib.SMTP(servidor, int(puerto)) as servidor_smtp:
            servidor_smtp.starttls()
            servidor_smtp.login(usuario, contra)
            servidor_smtp.send_message(mensaje)
        
        return True
    
    except Exception as e:
        messagebox.showerror("Error en Email", f"Error enviando reporte: {str(e)}\nRuta: {nombre_archivo}")
        return False

def generar_y_enviar_reporte():
    try:
        backup_dir = "backup"
        os.makedirs(backup_dir, exist_ok=True)
        
        fecha_str = datetime.now().date().isoformat()
        nombre_archivo = os.path.join(backup_dir, f"reporte_{fecha_str}.pdf")
        
        if not generar_reporte_pdf(nombre_archivo):
            return False
        
        if not enviar_reporte_email(nombre_archivo):
            return False
        
        messagebox.showinfo("Éxito", "Reporte generado y enviado correctamente")
        return True
    
    except Exception as e:
        messagebox.showerror("Error General", f"Error en proceso de reporte: {str(e)}")
        return False