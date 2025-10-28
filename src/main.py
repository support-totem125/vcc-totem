#!/usr/bin/env python3
"""
Consulta líneas de crédito en portal Calidda usando credenciales de FNB
"""

import logging
import random
import time
from pathlib import Path

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config import (
    DELAY_MIN, DELAY_MAX, MAX_CONSULTAS_POR_SESION,
    LOG_FILE, LOG_LEVEL, DNIS_FILE, mostrar_config
)
from api.auth import login
from api.client import consultar_dni
from utils.messages import mostrar_resultado

# ========== CONFIGURAR LOGGING ==========
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Función principal"""
    print("\n")
    print("🚀 EXTRACTOR DE LÍNEAS DE CRÉDITO - CALIDDA")
    print("   Versión segura con credenciales en .env")
    print()
    
    # Mostrar configuración
    mostrar_config()
    
    # Login inicial
    print("=" * 70)
    print("🔐 INICIANDO SESIÓN")
    print("=" * 70)
    print()
    
    session, id_aliado = login()
    
    if not session:
        logger.error("No se pudo iniciar sesión")
        return
    
    print(f"\n✅ Sesión iniciada correctamente\n")
    consultas_sesion = 0
    
    # Bucle principal de consultas
    while True:
        dni = input("\nIngrese el DNI a consultar (o 'q' para salir): ").strip()
        
        if dni.lower() == 'q':
            print("\n✅ Programa finalizado")
            return
            
        # Validar que sea un DNI válido (8 dígitos)
        if not dni.isdigit() or len(dni) != 8:
            print("❌ DNI inválido. Debe contener 8 dígitos numéricos")
            continue
    
        # Reconectar si es necesario
        if consultas_sesion >= MAX_CONSULTAS_POR_SESION:
            logger.info("Reconectando...")
            time.sleep(random.uniform(10, 20))
            session, id_aliado = login()
            if not session:
                logger.error("Error al reconectar")
                continue
            consultas_sesion = 0
        
        print("\n" + "=" * 70)
        print("📋 PROCESANDO CONSULTA")
        print("=" * 70)
        print(f"\nConsultando DNI: {dni}")
        
        data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)
        consultas_sesion += 1
        
        # ========== CASO 1: DNI VÁLIDO CON DATOS ==========
        if estado == 'success' and data and data.get('id'):
            mostrar_resultado(dni, data, estado, mensaje_api)
        
        # ========== CASO 2: DNI NO VÁLIDO O SIN DATOS ==========
        elif estado.startswith('invalid:'):
            mostrar_resultado(dni, data, estado, mensaje_api)
        
        # ========== CASO 3: SESIÓN EXPIRADA ==========
        elif estado == 'expired':
            logger.warning("Sesión expirada - Reconectando...")
            print("⚠️ Sesión expirada - Reconectando...")
            session, id_aliado = login()
            if session:
                data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)
                mostrar_resultado(dni, data, estado, mensaje_api)
        
        # ========== CASO 4: RATE LIMIT ==========
        elif estado == 'rate_limit':
            logger.warning("RATE LIMIT - Esperando 60 segundos...")
            print(f"⚠️ RATE LIMIT - Esperando 60s...")
            time.sleep(60)
            continue
        
        # ========== CASO 5: BLOQUEADO ==========
        elif estado == 'blocked':
            logger.error("ACCESO BLOQUEADO")
            print("🚨 ACCESO BLOQUEADO")
            print("El programa se cerrará...")
            return
        
        # ========== CASO 6: TIMEOUT ==========
        elif estado == 'timeout':
            print(f"\n❌ Error: {mensaje_api}")
            print("Por favor, inténtelo nuevamente.")
        
        # Delay entre consultas
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"\nEsperando {delay:.1f}s antes de la siguiente consulta...")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        logger.warning("Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        logger.exception("Error fatal en ejecución")
