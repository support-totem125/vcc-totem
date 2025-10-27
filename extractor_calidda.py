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

def limpiar_mensaje_html(mensaje):
    """Limpiar tags HTML del mensaje"""
    if not mensaje:
        return ""
    
    # Remover tags HTML
    mensaje = re.sub(r'<br\s*/?>', '\n', mensaje)
    mensaje = re.sub(r'<[^>]+>', '', mensaje)
    return mensaje.strip()

def generar_mensaje_personalizado(estado, data=None, mensaje_error=None):
    """
    Generar mensaje personalizado según el resultado de la consulta
    
    Args:
        estado: 'success', 'sin_credito', 'sin_campana', 'no_califica', 'error'
        data: Datos del cliente (si existe)
        mensaje_error: Mensaje de error de la API
    
    Returns:
        Tupla (titulo, mensaje, tiene_oferta)
    """
    
    if estado == 'success' and data and data.get('tieneLineaCredito'):
        # Cliente CON línea de crédito - ÚNICA CONDICIÓN PARA OFERTA
        nombre = data.get('nombre', 'Cliente').split()[0]  # Primer nombre
        monto = data.get('lineaCredito', 0)
        fecha_carga = data.get('fechaCarga', '')
        fecha_vigencia = fecha_carga[:10] if fecha_carga else 'consultar'
        
        titulo = "🎉 ¡FELICITACIONES!"
        mensaje = f"""Hola {nombre},

¡Tenemos excelentes noticias para ti!

Tienes una línea de crédito APROBADA por:
💰 S/ {monto:,.2f}

Esta oferta está vigente desde: {fecha_vigencia}

Para activar tu crédito, comunícate con nosotros:
📞 01-614-9000 (opción 3)
⏰ Lunes a Viernes: 9:00 AM - 6:00 PM

¡Gracias por confiar en Calidda!"""
        
        return titulo, mensaje, True
    
    elif estado == 'success' and data and not data.get('tieneLineaCredito'):
        # Cliente registrado pero SIN línea de crédito
        nombre = data.get('nombre', 'Cliente').split()[0]
        segmentacion = data.get('segmentacionCliente', '')
        
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

¿Consultas? Llámanos al 01-614-9000 (opción 3)

¡Hasta luego!"""
        
        return titulo, mensaje, False
    
    elif estado == 'sin_campana' or (mensaje_error and 'campaña activa' in mensaje_error.lower()):
        # Cliente no tiene campaña activa
        titulo = "💬 MENSAJE IMPORTANTE"
        mensaje = """Hola Cliente,

Lo sentimos, por el momento no tienes una campaña activa.

📌 ¿Qué significa esto?
   Actualmente no cuentas con ofertas de crédito disponibles.

💡 ¿Qué puedes hacer?
   • Sigue usando el servicio de Calidda
   • Mantén tus pagos puntuales
   • Pronto podrías calificar para nuevas ofertas

Evaluamos constantemente a nuestros clientes para ofrecerles 
los mejores beneficios.

Para más información:
📞 01-614-9000 (opción 3)

¡Gracias por tu preferencia!
Hasta luego."""
        
        return titulo, mensaje, False
    
    elif estado == 'no_califica' or (mensaje_error and 'no califica' in mensaje_error.lower()):
        # Cliente no califica
        titulo = "📋 RESULTADO DE TU CONSULTA"
        mensaje = """Hola Cliente,

Gracias por tu consulta.

En este momento no calificas para una línea de crédito.

💡 Recomendaciones:
   • Mantén tus pagos al día
   • Evita retrasos en tus cuotas
   • Usa regularmente nuestro servicio

Trabajamos constantemente para ofrecerte mejores opciones.

Para más información comunícate con nosotros:
📞 01-614-9000 (opción 3)
⏰ Lunes a Viernes: 9:00 AM - 6:00 PM

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
   • La cuenta está bajo otro titular

Por favor verifica tu información o comunícate con nosotros:
📞 01-614-9000 (opción 3)

¡Gracias!"""
        
        return titulo, mensaje, False
    
    else:
        # Error genérico u otro caso
        titulo = "⚠️ INFORMACIÓN"
        mensaje_limpio = limpiar_mensaje_html(mensaje_error) if mensaje_error else ""
        
        mensaje = f"""Hola Cliente,

En este momento no podemos procesar tu consulta.

{f"Detalle: {mensaje_limpio}" if mensaje_limpio else ""}

Por favor intenta más tarde o comunícate con nosotros:
📞 01-614-9000 (opción 3)
⏰ Lunes a Viernes: 9:00 AM - 6:00 PM

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
        
        if 'campaña activa' in mensaje or 'campaña' in mensaje:
            return 'sin_campana'
        elif 'no califica' in mensaje:
            return 'no_califica'
        elif 'no encontrado' in mensaje or 'no existe' in mensaje:
            return 'dni_invalido'
        else:
            return 'error'
    
    else:
        return 'error'

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

def guardar_txt(dni, data, estado='success', mensaje_api=None):
    """Guardar resultado en archivo TXT con mensaje personalizado"""
    archivo = Path(OUTPUT_DIR) / f"{dni}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Determinar estado y generar mensaje
    estado_consulta = determinar_estado_consulta(data, estado, mensaje_api)
    titulo, mensaje_cliente, tiene_oferta = generar_mensaje_personalizado(
        estado_consulta, 
        data, 
        mensaje_api
    )
    
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            # Encabezado
            f.write("=" * 70 + "\n")
            f.write("CALIDDA - CONSULTA DE LÍNEA DE CRÉDITO\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Fecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DNI consultado: {dni}\n")
            f.write(f"Estado: {'✅ CON OFERTA' if tiene_oferta else '❌ SIN OFERTA'}\n")
            f.write("\n")
            
            # ========== MENSAJE PARA EL CLIENTE ==========
            f.write("=" * 70 + "\n")
            f.write(titulo + "\n")
            f.write("=" * 70 + "\n\n")
            f.write(mensaje_cliente)
            f.write("\n\n")
            
            # ========== DATOS TÉCNICOS (Solo si hay data) ==========
            if data:
                f.write("=" * 70 + "\n")
                f.write("📋 INFORMACIÓN TÉCNICA DEL CLIENTE\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"ID Cliente: {data.get('id', 'N/A')}\n")
                f.write(f"Nombre completo: {data.get('nombre', 'N/A')}\n")
                f.write(f"DNI: {data.get('numeroDocumento', dni)}\n")
                f.write(f"Segmentación: {data.get('segmentacionCliente', 'N/A')}\n\n")
                
                # ========== LÍNEA DE CRÉDITO (PRIORIDAD) ==========
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
                
                # ❌ CAMPOS ELIMINADOS: Campaña activa y Bono adicional
                # Ya no se muestran porque no son relevantes para la lógica
                
                # Contacto SAP
                if data.get('correoSAP') or data.get('numeroTelefonoSAP'):
                    f.write(f"\n{'-'*70}\n")
                    f.write("CONTACTO SAP\n")
                    f.write(f"{'-'*70}\n\n")
                    f.write(f"Email: {data.get('correoSAP', 'N/A')}\n")
                    f.write(f"Teléfono: {data.get('numeroTelefonoSAP', 'N/A')}\n")
                
                # Cuentas y direcciones
                if data.get('cuentasContrato'):
                    f.write(f"\n{'-'*70}\n")
                    f.write("CUENTAS Y DIRECCIONES\n")
                    f.write(f"{'-'*70}\n\n")
                    
                    for idx, cuenta in enumerate(data['cuentasContrato'], 1):
                        f.write(f"Cuenta {idx}:\n")
                        f.write(f"  ID: {cuenta.get('id', 'N/A')}\n")
                        f.write(f"  Cuenta corriente: {cuenta.get('cuentaCorriente', 'N/A')}\n")
                        f.write(f"  Dirección: {cuenta.get('direccion', 'N/A')}\n")
                        f.write(f"  Categoría: {cuenta.get('categoria', 'N/A')}\n")
                        f.write(f"  Ubigeo INEI: {cuenta.get('ubigeoInei', 'N/A')}\n")
                        f.write(f"  Estado: {'Activo' if cuenta.get('status') else 'Inactivo'}\n\n")
                
                # JSON completo (comentado - descomentar si necesitas debug)
                # f.write(f"\n{'='*70}\n")
                # f.write("DATOS COMPLETOS (JSON)\n")
                # f.write(f"{'='*70}\n\n")
                # f.write(json.dumps(data, indent=2, ensure_ascii=False))
            
            elif mensaje_api:
                # Si no hay data pero hay mensaje de error
                f.write("=" * 70 + "\n")
                f.write("📋 DETALLE TÉCNICO\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Mensaje del sistema:\n{limpiar_mensaje_html(mensaje_api)}\n")
            
            # Pie de página
            f.write("\n" + "=" * 70 + "\n")
            f.write("FIN DEL REPORTE\n")
            f.write("=" * 70 + "\n")
        
        logger.info(f"Archivo guardado: {archivo.name} - Tiene oferta: {tiene_oferta}")
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
        
        data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)
        consultas_sesion += 1
        
        if estado == 'success' and data:
            archivo = guardar_txt(dni, data, estado, mensaje_api)
            if archivo:
                exitosos += 1
                
                if data.get('tieneLineaCredito'):
                    con_credito += 1
                    monto = data.get('lineaCredito', 0)
                    print(f"   ✅ S/ {monto:,.2f} - {data.get('nombre', 'N/A')}")
                else:
                    print(f"   ✅ Sin línea - {data.get('nombre', 'N/A')}")
                
                print(f"   📄 {Path(archivo).name}")
        
        elif estado.startswith('invalid:'):
            # Guardar archivo incluso si no tiene oferta
            archivo = guardar_txt(dni, data, estado, mensaje_api)
            if archivo:
                print(f"   ℹ️  Sin oferta disponible")
                print(f"   📄 {Path(archivo).name}")
            errores += 1
        
        elif estado == 'expired':
            logger.warning("Sesión expirada - Reconectando...")
            session, id_aliado = login()
            if session:
                data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)
                if estado == 'success' and data:
                    guardar_txt(dni, data, estado, mensaje_api)
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
            # Guardar archivo con error
            archivo = guardar_txt(dni, data, estado, mensaje_api)
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

