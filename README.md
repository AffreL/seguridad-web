# Demo de Donaciones Vulnerable

Aplicacion FastAPI educativa que renderiza HTML directo, pensada para practicar pruebas de vulnerabilidades web en un entorno local.

## Ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Abrir: http://127.0.0.1:8000

## Datos de ejemplo

```bash
python seed.py
```

El seed crea usuarios, peticiones, firmas, donaciones y comentarios. Incluye ejemplos para perros rescatados y limpieza del Riachuelo.
Tambien carga saldos ficticios en la billetera interna de cada usuario.

## Billetera interna

La app usa dinero simulado dentro de SQLite. Para cargar saldo, entrar a `Mi perfil` y usar el alias de la app:

```text
DONACIONES.APP
```

Desde el perfil tambien se puede retirar saldo indicando un alias propio. Las donaciones se descuentan del saldo del donante y se acreditan al creador de la publicacion.

Usuario administrador inicial:

- Usuario: `admin`
- Password: `admin`

> No usar en produccion. La app evita protecciones habituales a proposito para que sea facil inspeccionar y probar.
