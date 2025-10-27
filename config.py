#!/usr/bin/env python3
"""
Configuración del extractor - Carga desde .env
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno desde .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Verificar que existe el archivo .env
if not env_path.exists():
    raise FileNotFoundError(
        "❌ Archivo .env no encontrado.\n"
        "   Copia .env.example a .env y configura tus credenciales:\n"
        "   cp .env.example .env"
    )

# ========== CREDENCIALES ==========
USUARIO = os.getenv('CALIDDA_USUARIO')
PASSWORD = os.getenv('CALIDDA_PASSWORD')

if not USUARIO or not PASSWORD:
    raise ValueError(
        "❌ Credenciales no configuradas.\n"
        "   Verifica que CALIDDA_USUARIO y CALIDDA_PASSWORD estén en .env"
    )

# ========== URLs ==========
BASE_URL = os.getenv('BASE_URL', 'https://appweb.calidda.com.pe')
LOGIN_API = BASE_URL + os.getenv('LOGIN_API', '/FNB_Services/api/Seguridad/autenticar')
CONSULTA_API = BASE_URL + os.getenv('CONSULTA_API', '/FNB_Services/api/financiamiento/lineaCredito')

# ========== CONFIGURACIÓN DE SEGURIDAD ==========
DELAY_MIN = float(os.getenv('DELAY_MIN', '10'))
DELAY_MAX = float(os.getenv('DELAY_MAX', '207'))
TIMEOUT = int(os.getenv('TIMEOUT', '60'))
MAX_CONSULTAS_POR_SESION = int(os.getenv('MAX_CONSULTAS_POR_SESION', '50'))

# ========== DIRECTORIOS ==========
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'consultas_credito')
DNIS_FILE = os.getenv('DNIS_FILE', 'lista_dnis.txt')

# ========== LOGGING ==========
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'extractor.log')

# ========== VALIDACIÓN ==========
def validar_configuracion():
    """Validar que la configuración es correcta"""
    errores = []
    
    if not USUARIO:
        errores.append("CALIDDA_USUARIO no configurado")
    
    if not PASSWORD:
        errores.append("CALIDDA_PASSWORD no configurado")
    
    if DELAY_MIN > DELAY_MAX:
        errores.append("DELAY_MIN no puede ser mayor que DELAY_MAX")
    
    if TIMEOUT < 5:
        errores.append("TIMEOUT debe ser al menos 5 segundos")
    
    if errores:
        raise ValueError(
            "❌ Errores de configuración:\n" +
            "\n".join(f"   - {e}" for e in errores)
        )
    
    return True

# Validar al importar
validar_configuracion()

# Función para mostrar configuración (sin credenciales)
def mostrar_config():
    """Mostrar configuración actual (sin credenciales)"""
    print("=" * 70)
    print("⚙️  CONFIGURACIÓN")
    print("=" * 70)
    print(f"Usuario: {USUARIO}")
    print(f"Password: {'*' * len(PASSWORD or '')}")
    print(f"\nBase URL: {BASE_URL}")
    print(f"Login API: {LOGIN_API}")
    print(f"Consulta API: {CONSULTA_API}")
    print(f"\nDelay: {DELAY_MIN}-{DELAY_MAX} segundos")
    print(f"Timeout: {TIMEOUT} segundos")
    print(f"Max consultas/sesión: {MAX_CONSULTAS_POR_SESION}")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"DNIs file: {DNIS_FILE}")
    print(f"Log file: {LOG_FILE}")
    print("=" * 70)
    print()

