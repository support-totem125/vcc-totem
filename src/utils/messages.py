"""
Generación y manejo de mensajes personalizados
"""

import textwrap

def generar_mensaje_personalizado(estado, datos=None, mensaje_error=None):
    """
    Generar mensaje personalizado según el resultado de la consulta
    
    Args:
        estado: 'success', 'error'
        datos: Datos del cliente (si existe)
        mensaje_error: Mensaje de error de la API
    
    Returns:
        Tupla (mensaje_completo, tiene_oferta)
    """
    
    if estado == 'success' and datos and datos.get('tieneLineaCredito'):
        # Cliente CON línea de crédito - ÚNICA CONDICIÓN PARA OFERTA
        nombre = datos.get('nombre', 'Cliente')
        monto = datos.get('lineaCredito', 0)
        
        mensaje_completo = textwrap.dedent(f"""
            🎉 ¡FELICITACIONES!
            Hola {nombre},
            ¡Tenemos excelentes noticias para ti!
            Tienes una línea de crédito APROBADA por:
            💰 S/ {monto:,.2f}
            ¡Gracias por confiar en Calidda!
        """).strip()
        
        return mensaje_completo, True
    
    elif estado == 'success' and datos and not datos.get('tieneLineaCredito'):
        # Cliente registrado pero SIN línea de crédito
        nombre = datos.get('nombre', 'Cliente')
        
        mensaje_completo = textwrap.dedent(f"""
            ℹ️ INFORMACIÓN DE TU CONSULTA
            Hola {nombre},
            En este momento no cuentas con una línea de crédito disponible.
            Por favor, mantén tus pagos al día y continúa usando nuestro servicio.
            ¡Gracias por confiar en Calidda!
        """).strip()
        
        return mensaje_completo, False

    elif estado == 'dni_invalido' or (mensaje_error and ('no encontrado' in mensaje_error.lower() or 'no califica' in mensaje_error.lower() or 'no tiene campaña' in mensaje_error.lower())):
        # DNI no encontrado o sin campaña activa
        mensaje_completo = textwrap.dedent("""
            ℹ️ INFORMACIÓN DE TU CONSULTA
            Lo sentimos,
            Por el momento no tienes una campaña activa.
            - Sigue usando el servicio se Calidda
            - Mantente al día con tus recibos.
            Gracias!
        """).strip()
        
        return mensaje_completo, False
    
    else:
        # Error genérico u otro caso (incluyendo timeout)
        mensaje_completo = textwrap.dedent("""
            ⚠️ INFORMACIÓN
            Hola Cliente,
            En este momento no podemos procesar tu consulta.
            ¡Gracias por tu comprensión!
        """).strip()
        
        return mensaje_completo, False

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

def mostrar_resultado(dni, data, estado='success', mensaje_api=None):
    """Mostrar resultado en consola con mensaje personalizado"""
    
    # Determinar estado y generar mensaje
    estado_consulta = determinar_estado_consulta(data, estado, mensaje_api)
    mensaje_completo, tiene_oferta = generar_mensaje_personalizado(
        estado_consulta, 
        data, 
        mensaje_api
    )
    
    # ========== DETERMINAR ESTADO DEL DNI ==========
    if data and data.get('id'):
        # DNI existe en el sistema (tiene ID de cliente)
        if data.get('tieneLineaCredito'):
            estado_dni = "✅ DNI VÁLIDO - CON OFERTA"
        else:
            estado_dni = "⚠️ DNI VÁLIDO - SIN OFERTA"
    else:
        # DNI no encontrado o inválido
        estado_dni = "❌ DNI NO ENCONTRADO O INVÁLIDO"
    
    try:
        # Mostrar el mensaje personalizado completo
        print()
        print(mensaje_completo)
        print()
        
        return True, estado_dni, tiene_oferta  # ← Retornando tiene_oferta también
        
    except Exception as e:
        return False, estado_dni, False  # ← Agregado False para tiene_oferta en caso de error

