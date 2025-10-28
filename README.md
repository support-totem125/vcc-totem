# Pasos

## 1. Instalar dependencias

pip install -r requirements.txt

## 2. Copiar plantilla de configuración

cp .env.example .env

## 3. Editar .env con tus credenciales

nano .env  # o usa tu editor favorito

## 4. Ejecutar

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
