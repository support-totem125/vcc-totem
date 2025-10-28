"""
Utilidades de formateo y procesamiento de texto
"""

import re
from unidecode import unidecode

def procesar_direccion(direccion):
    """Procesa y formatea la dirección asegurando que termine en LIMA"""
    if not direccion:
        return "N/A"
    
    try:
        # Primero intentamos normalizar caracteres especiales a sus equivalentes ASCII
        direccion_norm = unidecode(direccion)

        # Verificar si termina en LIMA
        partes = direccion_norm.strip().split()
        if partes and partes[-1].upper() != 'LIMA':
            # Si es un ubigeo de Lima (15) y no termina en LIMA, agregarlo
            direccion_norm = f"{direccion_norm} LIMA"
        
        return direccion_norm
        
    except Exception as e:
        return direccion  # Devolver la dirección original en caso de error

def limpiar_mensaje_html(mensaje):
    """Limpiar tags HTML del mensaje"""
    if not mensaje:
        return ""
    
    # Remover tags HTML
    mensaje = re.sub(r'<br\s*/?>', '\n', mensaje)
    mensaje = re.sub(r'<[^>]+>', '', mensaje)
    return mensaje.strip()