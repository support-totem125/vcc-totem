"""
Funciones de consulta de clientes en la API de Calidda
"""

import logging
import requests
from config import CONSULTA_API, TIMEOUT, QUICK_TIMEOUT

logger = logging.getLogger(__name__)

def consultar_dni(session, dni, id_aliado):
    """Consultar línea de crédito por DNI"""
    params = {
        'numeroDocumento': dni,
        'tipoDocumento': 'PE2',
        'idAliado': id_aliado,
        'canal': 'FNB'
    }
    
    try:
        print(f"\nConsultando... (tiempo máximo de espera: {TIMEOUT} segundos)")
        print("Por favor espere mientras se procesa su solicitud...")
        
        # Primera consulta rápida para verificar si el DNI existe
        try:
            response = session.get(CONSULTA_API, params=params, timeout=30)
            
            # Si la respuesta es rápida y el DNI no existe, retornamos inmediatamente
            if response.status_code == 200:
                data = response.json()
                if data is None:
                    logger.error(f"Respuesta vacía de la API para DNI {dni}")
                    return None, 'error', 'Error en la respuesta de la API'
                    
                mensaje = data.get('message', '')
                if mensaje:  # Solo procesar si hay mensaje
                    mensaje = mensaje.lower()
                    if not data.get('valid') and ('no encontrado' in mensaje or 'no existe' in mensaje):
                        logger.info(f"DNI {dni} no encontrado (respuesta rápida)")
                        return None, f'invalid: {data.get("message")}', data.get('message')
                    
        except requests.exceptions.Timeout:
            # Si la consulta rápida falla por timeout, continuamos con la consulta normal
            logger.debug(f"Timeout en consulta rápida para DNI {dni}, intentando consulta completa")
        
        # Si no es una respuesta rápida de DNI no encontrado, hacemos la consulta completa
        response = session.get(CONSULTA_API, params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            if data is None:
                logger.error(f"Respuesta vacía de la API para DNI {dni}")
                return None, 'error', 'Error en la respuesta de la API'
            
            if data.get('valid'):
                if 'data' not in data:
                    logger.error(f"Respuesta sin campo 'data' para DNI {dni}")
                    return None, 'error', 'Error en el formato de la respuesta'
                return data['data'], 'success', None
            else:
                mensaje = data.get('message', 'Sin mensaje')
                logger.info(f"DNI {dni} inválido: {mensaje}")
                return None, f'invalid: {mensaje}', mensaje
        
        elif response.status_code == 401:
            return None, 'expired', 'Sesión expirada'
        elif response.status_code == 403:
            return None, 'blocked', 'Acceso bloqueado'
        elif response.status_code == 429:
            return None, 'rate_limit', 'Demasiadas consultas'
        else:
            return None, f'error_{response.status_code}', f'Error HTTP {response.status_code}'
            
    except requests.exceptions.Timeout:
        logger.error(f"Tiempo de espera agotado ({TIMEOUT} segundos) consultando DNI {dni}")
        return None, 'timeout', f'La consulta excedió el tiempo máximo de espera de {TIMEOUT} segundos. Por favor, inténtelo nuevamente.'
    except Exception as e:
        logger.error(f"Error consultando DNI {dni}: {e}")
        return None, f'exception: {str(e)}', str(e)