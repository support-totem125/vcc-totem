# Pasos

## 1. Crear entorno virtual

.\venv\Scripts\activate

## 2. Instalar dependencias

pip install -r requirements.txt

## 3. Copiar plantilla de configuración

cp .env.example .env

## 4. Editar .env con tus credenciales

nano .env  # o usa tu editor favorito

## 5. Ejecutar

python extractor_calidda.py

## Estructura

```md
script-calidda-usuarios/
├── .env                          # Credenciales (NO subir a Git)
├── .env.example                  # Ejemplo de configuración
├── .gitignore                    # Ignorar archivos sensibles
├── main.py                       # Script principal
├── config.py                     # Carga de configuración
├── requirements.txt              # Dependencias
```
