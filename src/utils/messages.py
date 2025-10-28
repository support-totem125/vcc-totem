"""
Generación y manejo de mensajes personalizados
"""

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
        nombre = datos.get('nombre', 'Cliente')  # Nombre completo
        monto = datos.get('lineaCredito', 0)
        
        titulo = "🎉 ¡FELICITACIONES!"
        mensaje = f"""Hola {nombre},
¡Tenemos excelentes noticias para ti!
Tienes una línea de crédito APROBADA por:
💰 S/ {monto:,.2f}
¡Gracias por confiar en Calidda!"""
        
        return titulo, mensaje, True
    
    elif estado == 'success' and datos and not datos.get('tieneLineaCredito'):
        # Cliente registrado pero SIN línea de crédito
        nombre = datos.get('nombre', 'Cliente')
        
        titulo = "ℹ️ INFORMACIÓN DE TU CONSULTA"
        mensaje = f"""Hola {nombre},
En este momento no cuentas con una línea de crédito disponible.
Por favor, mantén tus pagos al día y continúa usando nuestro servicio.
¡Gracias por confiar en Calidda!"""
        
        return titulo, mensaje, False

    elif estado == 'dni_invalido' or (mensaje_error and 'no encontrado' in mensaje_error.lower()):
        # DNI no encontrado
        titulo = "⚠️ DNI NO ENCONTRADO"
        mensaje = """Lo sentimos,
No pudimos encontrar información asociada a este DNI en nuestro sistema.
Por favor, verifica el DNI e inténtalo nuevamente."""
        
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
        else:
            estado_dni = "⚠️ DNI VÁLIDO - SIN OFERTA"
    else:
        # DNI no encontrado o inválido
        estado_dni = "❌ DNI NO ENCONTRADO O INVÁLIDO"
    
    try:
        # Solo mostrar el mensaje personalizado
        print()
        print(titulo)
        print()
        print(mensaje_cliente)
        print()
        
        return True, estado_dni
        
    except Exception as e:
        return False, estado_dni