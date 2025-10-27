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
import re
from unidecode import unidecode

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
        logger.warning(f"Error procesando dirección: {e}")
        return direccion  # Devolver la dirección original en caso de error

def crear_directorio():
    """Crear directorio de salida"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

def limpiar_mensaje_html(mensaje):
    """Limpiar tags HTML del mensaje"""
    if not mensaje:
        return ""
    
    # Remover tags HTML
    mensaje = re.sub(r'<br\s*/?>', '\n', mensaje)
    mensaje = re.sub(r'<[^>]+>', '', mensaje)
    return mensaje.strip()

def generar_mensaje_personalizado(estado, datos=None, mensaje_error=None):
    """
    Generar mensaje personalizado según el resultado de la consulta
    
    Args:
        estado: 'success', 'error'
        datos: Datos del cliente (si existe)
        mensaje_error: Mensaje de error de la API
    
    Returns:
        Tupla (titulo, mensaje, tiene_oferta)
    """
    
    if estado == 'success' and datos and datos.get('tieneLineaCredito'):
        # Cliente CON línea de crédito - ÚNICA CONDICIÓN PARA OFERTA
        nombre = datos.get('nombre', 'Cliente').split()[0]  # Primer nombre
        monto = datos.get('lineaCredito', 0)
        fecha_carga = datos.get('fechaCarga', '')
        fecha_vigencia = fecha_carga[:10] if fecha_carga else 'consultar'
        
        titulo = "🎉 ¡FELICITACIONES!"
        mensaje = f"""Hola {nombre},
¡Tenemos excelentes noticias para ti!
Tienes una línea de crédito APROBADA por:
💰 S/ {monto:,.2f}
Esta oferta está vigente desde: {fecha_vigencia}
¡Gracias por confiar en Calidda!"""
        
        return titulo, mensaje, True
    
    elif estado == 'success' and datos and not datos.get('tieneLineaCredito'):
        # Cliente registrado pero SIN línea de crédito
        nombre = datos.get('nombre', 'Cliente').split()[0]
        segmentacion = datos.get('segmentacionCliente', '')
        
        titulo = "ℹ️ INFORMACIÓN DE TU CONSULTA"
        mensaje = f"""Hola {nombre},
Gracias por tu interés en nuestros servicios de crédito.
En este momento no cuentas con una línea de crédito disponible.
📋 Estado: {segmentacion}
💡 ¿Cómo puedo calificar?
   • Mantén tus pagos al día
   • Continúa usando nuestro servicio regularmente
   • Evaluamos periódicamente a nuestros clientes
Sigue usando el servicio de Calidda y muy pronto podrías calificar 
para una oferta crediticia.
¡Hasta luego!"""
        
        return titulo, mensaje, False

    elif estado == 'dni_invalido' or (mensaje_error and 'no encontrado' in mensaje_error.lower()):
        # DNI no encontrado
        titulo = "⚠️ DNI NO ENCONTRADO"
        mensaje = """Lo sentimos,
No pudimos encontrar información asociada a este DNI en nuestro sistema.
Posibles razones:
   • El DNI no está registrado como cliente de Calidda
   • Existe un error en el número ingresado
Por favor, verifica el DNI e inténtalo nuevamente.

¡Gracias!"""
        
        return titulo, mensaje, False
    
    else:
        # Error genérico u otro caso
        titulo = "⚠️ INFORMACIÓN"
        
        mensaje = f"""Hola Cliente,
En este momento no podemos procesar tu consulta.
¡Gracias por tu comprensión!"""
        
        return titulo, mensaje, False

def determinar_estado_consulta(data, estado, mensaje_api):
    """Determinar el estado de la consulta para mensaje personalizado"""
    
    if estado == 'success' and data:
        if data.get('tieneLineaCredito'):
            return 'success'
        else:
            return 'sin_credito'
    
    elif estado.startswith('invalid:'):
        mensaje = estado.split('invalid:', 1)[1].strip().lower()
        
        if 'no encontrado' in mensaje or 'no existe' in mensaje:
            return 'dni_invalido'
        else:
            return 'error'
    
    else:
        return 'error'

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
            import jwt
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
            
    except Exception as e:
        logger.error(f"Error consultando DNI {dni}: {e}")
        return None, f'exception: {str(e)}', str(e)

def mostrar_resultado(dni, data, estado='success', mensaje_api=None):
    """Mostrar resultado en consola con mensaje personalizado"""
    
    # Determinar estado y generar mensaje
    estado_consulta = determinar_estado_consulta(data, estado, mensaje_api)
    titulo, mensaje_cliente, tiene_oferta = generar_mensaje_personalizado(
        estado_consulta, 
        data, 
        mensaje_api
    )
    
    # ========== DETERMINAR ESTADO DEL DNI ==========
    if data and data.get('id'):
        # DNI existe en el sistema (tiene ID de cliente)
        if data.get('tieneLineaCredito'):
            estado_dni = "✅ DNI VÁLIDO - CON OFERTA"
            icono_estado = "✅"
        else:
            estado_dni = "⚠️ DNI VÁLIDO - SIN OFERTA"
            icono_estado = "⚠️"
    else:
        # DNI no encontrado o inválido
        estado_dni = "❌ DNI NO ENCONTRADO O INVÁLIDO"
        icono_estado = "❌"
    
    try:
        # Encabezado
        print("=" * 70)
        print("CALIDDA - CONSULTA DE LÍNEA DE CRÉDITO")
        print("=" * 70)
        print()
        print(f"Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"DNI consultado: {dni}")
        print(f"Estado: {estado_dni}")
        
        # Solo verificar LIMA si el DNI es válido (tiene ID de cliente)
        if data and data.get('id'):
            es_de_lima = False
            if data.get('cuentasContrato'):
                for cuenta in data['cuentasContrato']:
                    direccion = cuenta.get('direccion', '').strip()
                    if direccion.upper().endswith('LIMA'):
                        es_de_lima = True
                        break
            
            print(f"{'ES DE LIMA' if es_de_lima else 'NO ES DE LIMA'}")
        
        print()
        
        # ========== MENSAJE PARA EL CLIENTE ==========
        print("=" * 70)
        print(titulo)
        print("=" * 70)
        print()
        print(mensaje_cliente)
        print()
            
            # ========== DATOS TÉCNICOS (Solo si hay data) ==========
        if data:
            print("=" * 70)
            print("📋 INFORMACIÓN TÉCNICA DEL CLIENTE")
            print("=" * 70)
            print()
            
            print(f"ID Cliente: {data.get('id', 'N/A')}")
            print(f"Nombre completo: {data.get('nombre', 'N/A')}")
            print(f"DNI: {data.get('numeroDocumento', dni)}")
            print(f"Segmentación: {data.get('segmentacionCliente', 'N/A')}")
            print()
            
            # ========== LÍNEA DE CRÉDITO (PRIORIDAD) ==========
            print("-" * 70)
            print("LÍNEA DE CRÉDITO")
            print("-" * 70)
            print()
            
            tiene_credito = data.get('tieneLineaCredito', False)
            print(f"Tiene línea de crédito: {'SÍ' if tiene_credito else 'NO'}")
            
            if tiene_credito:
                linea = data.get('lineaCredito', 0)
                print(f"Monto disponible: S/ {linea:,.2f}")
                print(f"Fecha de carga: {data.get('fechaCarga', 'N/A')}")
                print(f"ID Consulta: {data.get('idConsulta', 'N/A')}")
            
            # Contacto SAP
            if data.get('correoSAP') or data.get('numeroTelefonoSAP'):
                print("\n" + "-" * 70)
                print("CONTACTO SAP")
                print("-" * 70)
                print()
                print(f"Email: {data.get('correoSAP', 'N/A')}")
                print(f"Teléfono: {data.get('numeroTelefonoSAP', 'N/A')}")
            
            # Cuentas y direcciones
            if data.get('cuentasContrato'):
                print("\n" + "-" * 70)
                print("CUENTAS Y DIRECCIONES")
                print("-" * 70)
                print()
                
                for idx, cuenta in enumerate(data['cuentasContrato'], 1):
                    print(f"Cuenta {idx}:")
                    print(f"  ID: {cuenta.get('id', 'N/A')}")
                    print(f"  Cuenta corriente: {cuenta.get('cuentaCorriente', 'N/A')}")
                    print(f"  Dirección: {procesar_direccion(cuenta.get('direccion', 'N/A'))}")
                    print(f"  Categoría: {cuenta.get('categoria', 'N/A')}")
                    print(f"  Ubigeo INEI: {cuenta.get('ubigeoInei', 'N/A')}")
                    print(f"  Estado: {'Activo' if cuenta.get('status') else 'Inactivo'}")
                    print()
        
        elif mensaje_api:
            # Si no hay data pero hay mensaje de error
            print("=" * 70)
            print("📋 DETALLE TÉCNICO")
            print("=" * 70)
            print()
            print(f"Mensaje del sistema:\n{limpiar_mensaje_html(mensaje_api)}")
        
        # Pie de página
        print("\n" + "=" * 70)
        print("FIN DEL REPORTE")
        print("=" * 70)
        
        logger.info(f"Consulta completada - Estado: {estado_dni}")
        return True
        
    except Exception as e:
        logger.error(f"Error mostrando resultado: {e}")
        return False

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
        
        # ========== CASO 6: OTROS ERRORES ==========
        else:
            logger.error(f"Error en DNI {dni}: {estado}")
            print(f"❌ Error técnico: {estado}")
            mostrar_resultado(dni, data, estado, mensaje_api)
        
        # Delay entre consultas
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"\nEsperando {delay:.1f}s antes de la siguiente consulta...")
    
    print("\n✅ Consulta completada\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        logger.warning("Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        logger.exception("Error fatal en ejecución")
