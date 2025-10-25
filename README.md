# Pasos

## 1. Instalar dependencias

pip install -r requirements.txt

## 2. Copiar plantilla de configuración

cp .env.example .env

## 3. Editar .env con tus credenciales

nano .env  # o usa tu editor favorito

## 4. Crear lista de DNIs (En Linux)

```bash
echo "12345678" >> lista_dnis.txt
echo "23456789" >> lista_dnis.txt
```

o

- Puedes crear el archivo "lista_dnis.txt" manualmente e ingresar los numeros

```txt
12345678
23456789
```

## 5. Ejecutar

python extractor_calidda.py

## Estructura

```md
script-calidda-usuarios/
├── .env                          # Credenciales (NO subir a Git)
├── .env.example                  # Ejemplo de configuración
├── .gitignore                    # Ignorar archivos sensibles
├── extractor_calidda.py          # Script principal
├── config.py                     # Carga de configuración
├── lista_dnis.txt                # Lista de DNIs a procesar
├── requirements.txt              # Dependencias
└── consultas_credito/            # Carpeta de resultados
    ├── 12345678_20251025_143022.txt
    └── ...
```
