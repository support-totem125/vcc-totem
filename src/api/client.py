"""
Funciones de consulta de clientes en la API de Calidda
"""

import logging
import requests
from src.config import CONSULTA_API, TIMEOUT

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
        
        response = session.get(CONSULTA_API, params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('valid'):
                return data['data'], 'success', None
            else:
                mensaje = data.get('message', 'Sin mensaje')
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