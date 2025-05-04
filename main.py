import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from tkinter import Tk
from core.database import inicializar_bd
from gui.main_window import AplicacionPrincipal

def main():
    inicializar_bd()
    root = Tk()
    root.title("Control de Asistencia Facial")
    
    try:
        if os.name == 'nt':
            root.iconbitmap("assets/logo_windows.ico")
        else:
            from tkinter import PhotoImage
            icono = PhotoImage(file="assets/logo_mac.png")
            root.iconphoto(True, icono)
    except Exception as e:
        print(f"[Aviso] No se pudo cargar el ícono: {e}")

    root.configure(bg='#2c3e50')
    root.attributes('-fullscreen', True)
    
    app = AplicacionPrincipal(root)
    root.mainloop()

if __name__ == "__main__":
    main()