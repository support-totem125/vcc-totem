#!/usr/bin/env python3
"""
Extractor de Líneas de Crédito - Calidda
Versión segura con credenciales en .env
"""

import requests
import json
from datetime import datetime
import time
import random
import os
import logging
from pathlib import Path

# Importar configuración desde config.py
try:
    from config import (
        USUARIO, PASSWORD, LOGIN_API, CONSULTA_API,
        DELAY_MIN, DELAY_MAX, TIMEOUT, MAX_CONSULTAS_POR_SESION,
        OUTPUT_DIR, DNIS_FILE, LOG_FILE, LOG_LEVEL,
        mostrar_config
    )
except ImportError as e:
    print(f"❌ Error importando configuración: {e}")
    print("   Asegúrate de tener config.py y .env configurados")
    exit(1)

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

# ========== FUNCIONES ==========

def crear_directorio():
    """Crear directorio de salida"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

def login():
    """Login a la API de Calidda"""
    session = requests.Session()
    
    session.headers.update({
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
        response = session.post(LOGIN_API, json=payload, timeout=TIMEOUT)
        
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
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            id_aliado = decoded.get('commercialAllyId')
            user_id = decoded.get('id')
            
            logger.info(f"Login exitoso - User ID: {user_id}, ID Aliado: {id_aliado}")
            
            # Configurar headers
            session.headers.update({
                'authorization': f'Bearer {token}',
                'referer': 'https://appweb.calidda.com.pe/WebFNB/consulta-credito'
            })
            
            return session, id_aliado
        
        else:
            logger.error(f"Error en login: Status {response.status_code}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return None, None

def consultar_dni(session, dni, id_aliado):
    """Consultar línea de crédito por DNI"""
    params = {
        'numeroDocumento': dni,
        'tipoDocumento': 'PE2',
        'idAliado': id_aliado,
        'canal': 'FNB'
    }
    
    try:
        response = session.get(CONSULTA_API, params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('valid'):
                return data['data'], 'success'
            else:
                return None, f"invalid: {data.get('message', 'Sin mensaje')}"
        
        elif response.status_code == 401:
            return None, 'expired'
        elif response.status_code == 403:
            return None, 'blocked'
        elif response.status_code == 429:
            return None, 'rate_limit'
        else:
            return None, f'error_{response.status_code}'
            
    except Exception as e:
        logger.error(f"Error consultando DNI {dni}: {e}")
        return None, f'exception: {str(e)}'

def guardar_txt(dni, data):
    """Guardar resultado en archivo TXT"""
    archivo = Path(OUTPUT_DIR) / f"{dni}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("CONSULTA LÍNEA DE CRÉDITO - CALIDDA\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DNI: {dni}\n\n")
            
            if data:
                f.write("-" * 70 + "\n")
                f.write("INFORMACIÓN DEL CLIENTE\n")
                f.write("-" * 70 + "\n\n")
                
                f.write(f"ID: {data.get('id', 'N/A')}\n")
                f.write(f"Nombre: {data.get('nombre', 'N/A')}\n")
                f.write(f"DNI: {data.get('numeroDocumento', dni)}\n")
                f.write(f"Segmentación: {data.get('segmentacionCliente', 'N/A')}\n\n")
                
                f.write("-" * 70 + "\n")
                f.write("LÍNEA DE CRÉDITO\n")
                f.write("-" * 70 + "\n\n")
                
                tiene_credito = data.get('tieneLineaCredito', False)
                f.write(f"Tiene línea de crédito: {'SÍ' if tiene_credito else 'NO'}\n")
                
                if tiene_credito:
                    linea = data.get('lineaCredito', 0)
                    f.write(f"Monto disponible: S/ {linea:,.2f}\n")
                    f.write(f"Fecha de carga: {data.get('fechaCarga', 'N/A')}\n")
                    f.write(f"ID Consulta: {data.get('idConsulta', 'N/A')}\n")
                
                f.write(f"\nCampaña activa: {'SÍ' if data.get('activeCampaign', False) else 'NO'}\n")
                f.write(f"Bono adicional: S/ {data.get('additionalBonus', 0):,.2f}\n")
                
                # Contacto
                if data.get('correoSAP') or data.get('numeroTelefonoSAP'):
                    f.write(f"\n{'-'*70}\n")
                    f.write("CONTACTO SAP\n")
                    f.write(f"{'-'*70}\n\n")
                    f.write(f"Email: {data.get('correoSAP', 'N/A')}\n")
                    f.write(f"Teléfono: {data.get('numeroTelefonoSAP', 'N/A')}\n")
                
                # Cuentas
                if data.get('cuentasContrato'):
                    f.write(f"\n{'-'*70}\n")
                    f.write("CUENTAS Y DIRECCIONES\n")
                    f.write(f"{'-'*70}\n\n")
                    
                    for idx, cuenta in enumerate(data['cuentasContrato'], 1):
                        f.write(f"Cuenta {idx}:\n")
                        f.write(f"  Cuenta corriente: {cuenta.get('cuentaCorriente', 'N/A')}\n")
                        f.write(f"  Dirección: {cuenta.get('direccion', 'N/A')}\n")
                        f.write(f"  Categoría: {cuenta.get('categoria', 'N/A')}\n")
                        f.write(f"  Ubigeo: {cuenta.get('ubigeoInei', 'N/A')}\n\n")
                
                # JSON completo
                f.write(f"\n{'='*70}\n")
                f.write("DATOS COMPLETOS (JSON)\n")
                f.write(f"{'='*70}\n\n")
                f.write(json.dumps(data, indent=2, ensure_ascii=False))
            
            else:
                f.write("⚠️ NO SE ENCONTRARON DATOS\n")
            
            f.write(f"\n\n{'='*70}\n")
            f.write("FIN DEL REPORTE\n")
            f.write(f"{'='*70}\n")
        
        logger.info(f"Archivo guardado: {archivo.name}")
        return str(archivo)
        
    except Exception as e:
        logger.error(f"Error guardando archivo: {e}")
        return None

def leer_dnis_archivo(archivo=None):
    """Leer DNIs desde archivo TXT"""
    if archivo is None:
        archivo = DNIS_FILE
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            dnis = []
            for linea in f:
                dni = ''.join(filter(str.isdigit, linea.strip()))
                if dni and len(dni) == 8:
                    dnis.append(dni)
            
            logger.info(f"Leídos {len(dnis)} DNIs desde {archivo}")
            return dnis
            
    except FileNotFoundError:
        logger.warning(f"Archivo {archivo} no encontrado")
        return []

def main():
    """Función principal"""
    print("\n")
    print("🚀 EXTRACTOR DE LÍNEAS DE CRÉDITO - CALIDDA")
    print("   Versión segura con credenciales en .env")
    print()
    
    # Mostrar configuración
    mostrar_config()
    
    # Crear directorio de salida
    crear_directorio()
    
    # Leer DNIs desde archivo
    dnis = leer_dnis_archivo()
    
    if not dnis:
        logger.error("No hay DNIs para procesar")
        print("\n💡 Crea un archivo lista_dnis.txt con un DNI por línea")
        return
    
    # Login
    print("=" * 70)
    print("🔐 INICIANDO SESIÓN")
    print("=" * 70)
    print()
    
    session, id_aliado = login()
    
    if not session:
        logger.error("No se pudo iniciar sesión")
        return
    
    print(f"\n✅ Sesión iniciada correctamente\n")
    
    # Procesar DNIs
    print("=" * 70)
    print(f"📋 PROCESANDO {len(dnis)} DNI(S)")
    print("=" * 70)
    print()
    
    exitosos = 0
    con_credito = 0
    errores = 0
    consultas_sesion = 0
    
    for i, dni in enumerate(dnis, 1):
        # Reconectar si es necesario
        if consultas_sesion >= MAX_CONSULTAS_POR_SESION:
            logger.info(f"Reconectando después de {consultas_sesion} consultas...")
            time.sleep(random.uniform(10, 20))
            session, id_aliado = login()
            if not session:
                logger.error("Error al reconectar")
                break
            consultas_sesion = 0
        
        print(f"[{i}/{len(dnis)}] DNI: {dni}")
        
        data, estado = consultar_dni(session, dni, id_aliado)
        consultas_sesion += 1
        
        if estado == 'success' and data:
            archivo = guardar_txt(dni, data)
            if archivo:
                exitosos += 1
                
                if data.get('tieneLineaCredito'):
                    con_credito += 1
                    monto = data.get('lineaCredito', 0)
                    print(f"   ✅ S/ {monto:,.2f} - {data.get('nombre', 'N/A')}")
                else:
                    print(f"   ✅ Sin línea - {data.get('nombre', 'N/A')}")
                
                print(f"   📄 {Path(archivo).name}")
        
        elif estado == 'expired':
            logger.warning("Sesión expirada - Reconectando...")
            session, id_aliado = login()
            if session:
                data, estado = consultar_dni(session, dni, id_aliado)
                if estado == 'success' and data:
                    guardar_txt(dni, data)
                    exitosos += 1
        
        elif estado == 'rate_limit':
            logger.warning("RATE LIMIT - Esperando 60 segundos...")
            print(f"   ⚠️ RATE LIMIT - Esperando 60s...")
            time.sleep(60)
        
        elif estado == 'blocked':
            logger.error("ACCESO BLOQUEADO")
            print(f"   🚨 BLOQUEADO")
            errores += 1
            break
        
        else:
            logger.error(f"Error en DNI {dni}: {estado}")
            print(f"   ❌ Error: {estado}")
            errores += 1
        
        # Delay entre consultas
        if i < len(dnis):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            logger.debug(f"Esperando {delay:.1f}s")
            print(f"   ⏳ {delay:.1f}s...\n")
            time.sleep(delay)
    
    # Resumen final
    print("=" * 70)
    print("📊 RESUMEN FINAL")
    print("=" * 70)
    print(f"Total procesados: {len(dnis)}")
    print(f"Exitosos: {exitosos}")
    if exitosos > 0:
        porcentaje = (con_credito/exitosos*100)
        print(f"  └─ Con línea de crédito: {con_credito} ({porcentaje:.1f}%)")
        print(f"  └─ Sin línea de crédito: {exitosos - con_credito}")
    print(f"Errores: {errores}")
    print(f"\n📁 Archivos: {OUTPUT_DIR}/")
    print(f"📋 Log: {LOG_FILE}")
    print("✅ Proceso completado\n")
    
    logger.info(f"Proceso completado: {exitosos}/{len(dnis)} exitosos")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        logger.warning("Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        logger.exception("Error fatal en ejecución")

