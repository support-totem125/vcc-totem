#!/usr/bin/env python3
"""
FastAPI wrapper que expone /query y utiliza los módulos internos de src
para hacer una sola consulta por DNI y devolver un mensaje amigable para Chatwoot.
"""
import os
import sys
from typing import Optional

# Asegurar que /app/src esté en el path cuando el contenedor working_dir es /app
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Importar funciones internas
try:
    from api.auth import login
    from api.client import consultar_dni
    from utils.messages import generar_mensaje_personalizado, determinar_estado_consulta
except Exception as e:
    raise

app = FastAPI(title="Calidda API", version="1.0")

class DNIRequest(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8)

class QueryResponse(BaseModel):
    success: bool
    dni: str
    client_title: Optional[str] = None
    client_message: Optional[str] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None
    return_code: int

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/query', response_model=QueryResponse)
def query_dni(body: DNIRequest):
    dni = body.dni.strip()
    if not dni or not dni.isdigit() or len(dni) != 8:
        raise HTTPException(status_code=400, detail='DNI inválido')

    # Iniciar sesión
    session, id_aliado = login()
    if not session:
        raise HTTPException(status_code=500, detail='No se pudo iniciar sesión en Calidda')

    data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)

    # Generar mensaje al cliente usando utilidades internas
    estado_consulta = determinar_estado_consulta(data, estado, mensaje_api)
    title, message, _ = generar_mensaje_personalizado(estado_consulta, data, mensaje_api)

    # Retornar un JSON conciso para n8n/Chatwoot
    resp = QueryResponse(
        success=(estado == 'success' and data is not None),
        dni=dni,
        client_title=title,
        client_message=message,
        raw_output=None,
        error=mensaje_api if mensaje_api else None,
        return_code=0 if estado == 'success' else 1
    )

    return resp

if __name__ == '__main__':
    uvicorn.run('api_wrapper:app', host='0.0.0.0', port=5000, log_level='info')
