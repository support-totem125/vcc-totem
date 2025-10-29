# vcc-totem — Integración Calidda (wrapper y utilidades)

Este repositorio contiene el código usado por el servicio "vcc-totem" (wrapper HTTP y utilidades) que consulta la API de Calidda y genera mensajes listos para enviar a Chatwoot vía n8n.

## Contenido principal

- `api_wrapper.py` — FastAPI wrapper que expone endpoints HTTP para consultar DNI y devolver el mensaje formateado.
- `src/` — Código original del proyecto (login, cliente API, formateadores y script CLI).
- `requirements.txt` — Dependencias Python.

## Requisitos

- Python 3.11+
- Pip
- (Opcional) Docker y docker-compose si prefieres ejecutar el servicio en contenedores.

## Instalación rápida (entorno local)

1. Crear y activar un virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Copiar la plantilla de configuración y editar variables:

```bash
cp .env.example .env
# editar .env con tus credenciales (API, usuario, etc.)
nano .env
```

4. Probar el script CLI (opcional):

```bash
python src/main.py
```

Nota: el enfoque recomendado para integración con n8n es no ejecutar el CLI directamente desde n8n sino usar `api_wrapper.py` (FastAPI) que importa y reutiliza la lógica del proyecto.

## Ejecutar el wrapper FastAPI (desarrollo)

```bash
# desde el directorio vcc-totem
python api_wrapper.py
# o usando uvicorn directamente
uvicorn api_wrapper:app --host 0.0.0.0 --port 5000
```

Endpoints importantes

- `GET /health` — salud del servicio (retorna `{"status":"ok"}`).
- `POST /query` — body: `{"dni":"<8 dígitos>"}`. Retorna JSON con campos útiles para n8n/Chatwoot:
	- `client_message` — mensaje con saltos de línea
	- `client_message_compact` — mensaje en una sola línea (ideal para canales que no soportan saltos)
	- `client_message_html` — versión HTML (salto = `<br/>`) para sistemas que aceptan HTML

Ejemplo:

```bash
curl -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{"dni":"72364276"}'
```

## Ejecución con Docker (docker-compose)

Este proyecto suele montarse dentro del servicio `calidda-api` en `docker-compose.yaml` del repo padre. Asegúrate de montar el directorio en el contenedor y exponer el puerto 5000.

## Integración con n8n y Chatwoot

- En n8n, reemplaza el nodo "Execute Command" por un nodo HTTP Request que haga POST a `http://calidda-api:5000/query` (o `http://localhost:5000` si llamas desde host). Body JSON: `{"dni":"{{ $json.dni }}"}`.
- Para enviar mensajes a Chatwoot usa un nodo HTTP Request con los headers:
	- `api_access_token: <TU_TOKEN_CHATWOOT>`
	- `Content-Type: application/json`

Body (ejemplo usando la respuesta del wrapper):

```json
{
	"content": "{{$json.client_message_html}}",
	"message_type": 1
}
```

Nota: en algunas instalaciones Chatwoot acepta token vía header `api_access_token` (en vez de `Authorization: Bearer`). En tu entorno comprobamos que `api_access_token` funciona.

## Actualizar el subproyecto

- Usa el script `scripts/update-vcc-totem.sh`. El script ahora hace `git fetch --all` y preferirá traer cambios desde el remote `upstream` si existe. Los logs se escriben en `logs/vcc-totem-updates.log`.
- Si prefieres hacerlo manualmente:

```bash
cd vcc-totem
git fetch upstream
git merge upstream/main
```

## Errores comunes y soluciones rápidas

- "can't open file '/app/main.py'": ocurre si un contenedor intenta ejecutar `main.py` en la raíz; el script real está en `src/main.py`. Actualiza scripts para usar `src/main.py` o usa `api_wrapper.py`.
- 401 Unauthorized al POST a Chatwoot: prueba enviar el token con header `api_access_token: <token>` (en vez de Authorization) y verifica que el token pertenece a un usuario con acceso a la cuenta/inbox objetivo.

## Logs

- Wrapper y scripts generan logs en `logs/`.

## Contribuciones

- Haz fork y PR. Si conviertes `vcc-totem` en submódulo del repo padre asegúrate de actualizar `.gitmodules`.

## Contacto

- Si necesitas ayuda con la integración n8n → Chatwoot o con la generación de tokens, añade un issue o contacta al mantenedor del repo.

---
Archivo original: `src/` mantiene la implementación del CLI y utilidades; `api_wrapper.py` contiene la versión recomendada para uso en producción con n8n.
