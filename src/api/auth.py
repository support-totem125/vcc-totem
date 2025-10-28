"""
Funciones de autenticación con la API de Calidda
"""

import jwt
import requests
import logging

from src.config import (
    USUARIO, PASSWORD, LOGIN_API, TIMEOUT
)

logger = logging.getLogger(__name__)

def login():
    """Login a la API de Calidda"""
    http_session = requests.Session()
    
    http_session.headers.update({
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'es-419,es;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://appweb.calidda.com.pe',
        'referer': 'https://appweb.calidda.com.pe/WebFNB/login',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    logger.info("Iniciando sesión...")
    
    payload = {
        "usuario": USUARIO,
        "password": PASSWORD,
        "captcha": "exitoso",
        "Latitud": "",
        "Longitud": ""
    }
    
    try:
        response = http_session.post(LOGIN_API, json=payload, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get('valid'):
                logger.error(f"Login inválido: {data.get('message')}")
                return None, None
            
            auth_data = data.get('data', {})
            token = auth_data.get('authToken')
            
            if not token:
                logger.error("No se encontró authToken en respuesta")
                return None, None
            
            # Decodificar token
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            id_aliado = decoded.get('commercialAllyId')
            user_id = decoded.get('id')
            
            logger.info(f"Login exitoso - User ID: {user_id}, ID Aliado: {id_aliado}")
            
            # Configurar headers
            http_session.headers.update({
                'authorization': f'Bearer {token}',
                'referer': 'https://appweb.calidda.com.pe/WebFNB/consulta-credito'
            })
            
            return http_session, id_aliado
        
        else:
            logger.error(f"Error en login: Status {response.status_code}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return None, None