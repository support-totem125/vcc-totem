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
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import time
import threading

# Importar funciones internas
try:
    from api.auth import login
    from api.client import consultar_dni
    from utils.messages import generar_mensaje_personalizado, determinar_estado_consulta
except Exception as e:
    raise

app = FastAPI(title="Calidda API", version="1.0")

# Session cache to avoid logging in on every request when running as a long-lived
# FastAPI process. The CLI (`src/main.py`) already keeps a session for the duration
# of the process. For the wrapper we keep a module-level cached session and refresh
# it after SESSION_TTL seconds or when login fails.
SESSION_TTL = int(os.environ.get("CALIDDA_SESSION_TTL", 60 * 60))  # 1 hour by default
_session_lock = threading.Lock()
_session_cache = {
    "session": None,
    "id_aliado": None,
    "ts": 0,
}


def get_session(force: bool = False):
    """Return a logged-in requests.Session and id_aliado. Re-login when needed.

    force: if True, forces a fresh login.
    """
    now = time.time()
    # Fast path: valid session
    sess = _session_cache.get("session")
    if not force and sess and (now - _session_cache.get("ts", 0) < SESSION_TTL):
        return sess, _session_cache.get("id_aliado")

    # Acquire lock to perform a single login across threads
    with _session_lock:
        # Check again after acquiring lock
        sess = _session_cache.get("session")
        if (
            not force
            and sess
            and (time.time() - _session_cache.get("ts", 0) < SESSION_TTL)
        ):
            return sess, _session_cache.get("id_aliado")

        # Perform login
        s, id_aliado = login()
        if not s:
            # keep old session if exists but mark ts to 0 so next call will retry
            _session_cache["ts"] = 0
            raise RuntimeError("No se pudo iniciar sesión en Calidda")

        _session_cache["session"] = s
        _session_cache["id_aliado"] = id_aliado
        _session_cache["ts"] = time.time()
        return s, id_aliado


class DNIRequest(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8)


class QueryResponse(BaseModel):
    success: bool
    dni: str
    client_message: Optional[str] = None
    # Versión compacta (una sola línea) adecuada para plataformas que no manejan bien saltos
    # client_message_compact: Optional[str] = None
    # Versión HTML donde los saltos de línea se convierten en <br/> para Chatwoot u otros clientes
    # client_message_html: Optional[str] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None
    return_code: int
    tiene_oferta: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query_dni(body: DNIRequest):
    dni = body.dni.strip()
    if not dni or not dni.isdigit() or len(dni) != 8:
        raise HTTPException(status_code=400, detail="DNI inválido")

    # Obtener sesión (usa cache para no login en cada request)
    try:
        session, id_aliado = get_session()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        data, estado, mensaje_api = consultar_dni(session, dni, id_aliado)
    except Exception as e:
        # Invalidate cached session on unexpected errors so next request re-logins
        _session_cache["ts"] = 0
        raise HTTPException(status_code=500, detail=f"Error consultando DNI: {e}")

    # Generar mensaje al cliente usando utilidades internas
    estado_consulta = determinar_estado_consulta(data, estado, mensaje_api)
    mensaje_completo, tiene_oferta = generar_mensaje_personalizado(
        estado_consulta, data, mensaje_api
    )

    # Formatear versiones alternativas del mensaje
    # compact: eliminar saltos de línea y colapsar espacios
    compact = " ".join(mensaje_completo.split()) if mensaje_completo else None
    # html: reemplazar saltos de línea por <br/> (preserva texto)
    html = mensaje_completo.replace("\n", "<br/>") if mensaje_completo else None

    # Retornar un JSON conciso para n8n/Chatwoot
    resp = QueryResponse(
        success=(estado == "success" and data is not None),
        dni=dni,
        client_message=mensaje_completo,
        client_message_compact=compact,
        client_message_html=html,
        raw_output=None,
        error=mensaje_api if mensaje_api else None,
        return_code=0 if estado == "success" else 1,
        tiene_oferta=tiene_oferta,
    )

    return resp


if __name__ == "__main__":
    uvicorn.run("api_wrapper:app", host="0.0.0.0", port=5000, log_level="info")
