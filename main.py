from datetime import datetime
from pathlib import Path
import secrets
import sqlite3
from typing import Optional

from fastapi import Cookie, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "donaciones.db"
APP_DEPOSIT_ALIAS = "DONACIONES.APP"

UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Demo Donaciones Vulnerable")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS petitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                bank_alias TEXT NOT NULL,
                photo_path TEXT,
                goal_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                petition_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                signer_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(petition_id) REFERENCES petitions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                petition_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                donor_name TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(petition_id) REFERENCES petitions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                petition_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(petition_id) REFERENCES petitions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS wallet_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                amount REAL NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                destination_alias TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "balance" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN balance REAL NOT NULL DEFAULT 0")
        admin = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (username, password, is_admin, balance, created_at) VALUES (?, ?, ?, ?, ?)",
                ("admin", "admin", 1, 0, now()),
            )


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def query_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute(sql, params).fetchone()


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with db() as conn:
        return conn.execute(sql, params).fetchall()


def current_user(session: Optional[str]) -> Optional[sqlite3.Row]:
    if not session:
        return None
    return query_one(
        """
        SELECT users.*
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (session,),
    )


def layout(title: str, body: str, user: Optional[sqlite3.Row] = None) -> HTMLResponse:
    admin_link = '<a href="/admin">Admin</a>' if user and user["is_admin"] else ""
    auth = (
        f'<span>Hola, <b>{user["username"]}</b> · ${user["balance"]:.2f}</span><a href="/profile">Mi perfil</a><a href="/logout">Salir</a>{admin_link}'
        if user
        else '<a href="/login">Entrar</a><a href="/register">Crear usuario</a>'
    )
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{title}</title>
            <style>
                :root {{
                    color-scheme: light;
                    font-family: Arial, Helvetica, sans-serif;
                    background: #f5f7fb;
                    color: #172033;
                }}
                body {{ margin: 0; }}
                header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 16px;
                    padding: 18px 28px;
                    background: #ffffff;
                    border-bottom: 1px solid #dbe1ea;
                    position: sticky;
                    top: 0;
                    z-index: 2;
                }}
                nav {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
                a {{ color: #1f5fbf; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                main {{ max-width: 1100px; margin: 0 auto; padding: 28px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }}
                .card {{
                    background: #ffffff;
                    border: 1px solid #dbe1ea;
                    border-radius: 8px;
                    padding: 18px;
                    box-shadow: 0 8px 24px rgba(23, 32, 51, 0.05);
                }}
                .hero {{
                    display: grid;
                    grid-template-columns: minmax(0, 1.1fr) minmax(260px, .9fr);
                    gap: 24px;
                    align-items: start;
                }}
                img.cover {{ width: 100%; max-height: 420px; object-fit: cover; border-radius: 8px; border: 1px solid #dbe1ea; }}
                form {{ display: grid; gap: 12px; }}
                input, textarea, select, button {{
                    font: inherit;
                    border-radius: 6px;
                    border: 1px solid #b9c3d3;
                    padding: 10px 12px;
                }}
                textarea {{ min-height: 120px; resize: vertical; }}
                button {{
                    background: #1f5fbf;
                    color: #ffffff;
                    border-color: #1f5fbf;
                    cursor: pointer;
                    font-weight: 700;
                }}
                button.secondary {{ background: #ffffff; color: #1f5fbf; }}
                .button-link {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border: 1px solid #b9c3d3;
                    border-radius: 6px;
                    padding: 10px 12px;
                    background: #ffffff;
                    color: #1f5fbf;
                }}
                .filters {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
                    gap: 12px;
                    align-items: end;
                }}
                .muted {{ color: #61708a; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }}
                .metric strong {{ display: block; font-size: 32px; }}
                table {{ width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 8px; overflow: hidden; }}
                th, td {{ text-align: left; border-bottom: 1px solid #dbe1ea; padding: 12px; vertical-align: top; }}
                @media (max-width: 760px) {{
                    header {{ align-items: flex-start; flex-direction: column; }}
                    main {{ padding: 18px; }}
                    .hero {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <header>
                <a href="/"><strong>Donaciones Comunitarias</strong></a>
                <nav>
                    <a href="/petitions/new">Crear peticion</a>
                    {auth}
                </nav>
            </header>
            <main>{body}</main>
        </body>
        </html>
        """
    )


def require_user(session: Optional[str]) -> Optional[sqlite3.Row]:
    return current_user(session)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    user = current_user(session)
    petitions = query_all(
        """
        SELECT p.*,
            u.username,
            (SELECT COUNT(*) FROM signatures s WHERE s.petition_id = p.id) AS signatures,
            (SELECT COUNT(*) FROM comments c WHERE c.petition_id = p.id) AS comments,
            (SELECT COALESCE(SUM(d.amount), 0) FROM donations d WHERE d.petition_id = p.id) AS donated
        FROM petitions p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.id DESC
        """
    )
    cards = "".join(
        f"""
        <article class="card">
            {'<img class="cover" src="' + p["photo_path"] + '" alt="Foto de la peticion">' if p["photo_path"] else ""}
            <h2><a href="/petitions/{p["id"]}">{p["title"]}</a></h2>
            <p class="muted">Creada por {p["username"]} el {p["created_at"]}</p>
            <p>{p["description"][:220]}</p>
            <p><b>Firmas:</b> {p["signatures"]} · <b>Comentarios:</b> {p["comments"]} · <b>Donado:</b> ${p["donated"]:.2f}</p>
        </article>
        """
        for p in petitions
    )
    body = f"""
    <section class="card">
        <h1>Pedidos de donacion</h1>
        <p class="muted">Publica una causa, recibe donaciones dentro de la app y deja que otros firmen y comenten.</p>
    </section>
    <section class="grid" style="margin-top: 18px;">{cards or '<p class="muted">Todavia no hay peticiones.</p>'}</section>
    """
    return layout("Donaciones", body, user)


@app.get("/register", response_class=HTMLResponse)
def register_form(session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    return layout(
        "Crear usuario",
        """
        <section class="card">
            <h1>Crear usuario</h1>
            <form method="post" action="/register">
                <input name="username" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Password" required>
                <button>Crear cuenta</button>
            </form>
        </section>
        """,
        current_user(session),
    )


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)) -> RedirectResponse:
    with db() as conn:
        conn.execute(
            "INSERT INTO users (username, password, is_admin, balance, created_at) VALUES (?, ?, 0, 0, ?)",
            (username, password, now()),
        )
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    return layout(
        "Entrar",
        """
        <section class="card">
            <h1>Entrar</h1>
            <form method="post" action="/login">
                <input name="username" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Password" required>
                <button>Entrar</button>
            </form>
        </section>
        """,
        current_user(session),
    )


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)) -> RedirectResponse:
    user = query_one("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    if not user:
        return RedirectResponse("/login", status_code=303)
    token = secrets.token_hex(16)
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], now()),
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session", token)
    return response


@app.get("/logout")
def logout(session: Optional[str] = Cookie(default=None)) -> RedirectResponse:
    if session:
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (session,))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/profile", response_class=HTMLResponse)
def profile(session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    user = require_user(session)
    if not user:
        return layout("Perfil", '<section class="card"><p>Necesitas entrar para ver tu perfil.</p></section>')
    movements = query_all(
        "SELECT * FROM wallet_movements WHERE user_id = ? ORDER BY id DESC LIMIT 30",
        (user["id"],),
    )
    withdrawals = query_all(
        "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user["id"],),
    )
    body = f"""
    <section class="card">
        <h1>Mi perfil</h1>
        <div class="stats">
            <div class="metric"><strong>${user["balance"]:.2f}</strong><span>Saldo disponible</span></div>
            <div class="metric"><strong>{APP_DEPOSIT_ALIAS}</strong><span>Alias de carga de la app</span></div>
        </div>
    </section>
    <section class="grid" style="margin-top: 18px;">
        <form class="card" method="post" action="/wallet/deposit">
            <h2>Cargar saldo</h2>
            <p class="muted">Para esta demo, ingresar el alias de la app acredita saldo inmediatamente.</p>
            <input name="app_alias" value="{APP_DEPOSIT_ALIAS}" placeholder="Alias de la app" required>
            <input name="amount" type="number" min="1" step="0.01" placeholder="Monto" required>
            <button>Cargar saldo</button>
        </form>
        <form class="card" method="post" action="/wallet/withdraw">
            <h2>Retirar saldo</h2>
            <input name="destination_alias" placeholder="Tu alias de destino" required>
            <input name="amount" type="number" min="1" step="0.01" placeholder="Monto" required>
            <button>Retirar</button>
        </form>
    </section>
    <section class="card" style="margin-top: 18px;">
        <h2>Movimientos</h2>
        <table>
            <tr><th>Fecha</th><th>Tipo</th><th>Monto</th><th>Detalle</th></tr>
            {''.join(f'<tr><td>{m["created_at"]}</td><td>{m["movement_type"]}</td><td>${m["amount"]:.2f}</td><td>{m["detail"] or ""}</td></tr>' for m in movements) or '<tr><td colspan="4" class="muted">Todavia no hay movimientos.</td></tr>'}
        </table>
    </section>
    <section class="card" style="margin-top: 18px;">
        <h2>Retiros recientes</h2>
        <table>
            <tr><th>Fecha</th><th>Alias destino</th><th>Monto</th></tr>
            {''.join(f'<tr><td>{w["created_at"]}</td><td>{w["destination_alias"]}</td><td>${w["amount"]:.2f}</td></tr>' for w in withdrawals) or '<tr><td colspan="3" class="muted">Todavia no hay retiros.</td></tr>'}
        </table>
    </section>
    """
    return layout("Perfil", body, user)


@app.post("/wallet/deposit")
def deposit(
    session: Optional[str] = Cookie(default=None),
    app_alias: str = Form(...),
    amount: float = Form(...),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if amount <= 0:
        return RedirectResponse("/profile", status_code=303)
    if app_alias != APP_DEPOSIT_ALIAS:
        return RedirectResponse("/profile", status_code=303)
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user["id"]))
        conn.execute(
            "INSERT INTO wallet_movements (user_id, movement_type, amount, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], "carga", amount, f"Carga desde alias {APP_DEPOSIT_ALIAS}", now()),
        )
    return RedirectResponse("/profile", status_code=303)


@app.post("/wallet/withdraw")
def withdraw(
    session: Optional[str] = Cookie(default=None),
    destination_alias: str = Form(...),
    amount: float = Form(...),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if amount <= 0 or amount > float(user["balance"]):
        return RedirectResponse("/profile", status_code=303)
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user["id"]))
        conn.execute(
            "INSERT INTO withdrawals (user_id, amount, destination_alias, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], amount, destination_alias, now()),
        )
        conn.execute(
            "INSERT INTO wallet_movements (user_id, movement_type, amount, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], "retiro", -amount, f"Retiro hacia {destination_alias}", now()),
        )
    return RedirectResponse("/profile", status_code=303)


@app.get("/petitions/new", response_class=HTMLResponse)
def new_petition_form(session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    user = require_user(session)
    if not user:
        return layout("Login requerido", '<section class="card"><p>Necesitas entrar para crear una peticion.</p></section>')
    return layout(
        "Nueva peticion",
        """
        <section class="card">
            <h1>Nueva peticion</h1>
            <form method="post" action="/petitions" enctype="multipart/form-data">
                <input name="title" placeholder="Titulo" required>
                <textarea name="description" placeholder="Descripcion de la causa" required></textarea>
                <input name="goal_amount" type="number" min="0" step="0.01" placeholder="Objetivo de recaudacion" value="0">
                <input name="photo" type="file" accept="image/*">
                <button>Publicar</button>
            </form>
        </section>
        """,
        user,
    )


@app.post("/petitions")
async def create_petition(
    session: Optional[str] = Cookie(default=None),
    title: str = Form(...),
    description: str = Form(...),
    goal_amount: float = Form(0),
    photo: Optional[UploadFile] = File(default=None),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)

    photo_path = None
    if photo and photo.filename:
        target = UPLOAD_DIR / f"{secrets.token_hex(6)}_{photo.filename}"
        target.write_bytes(await photo.read())
        photo_path = f"/uploads/{target.name}"

    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO petitions (user_id, title, description, bank_alias, photo_path, goal_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user["id"], title, description, "", photo_path, goal_amount, now()),
        )
        petition_id = cursor.lastrowid
    return RedirectResponse(f"/petitions/{petition_id}", status_code=303)


@app.get("/petitions/{petition_id}", response_class=HTMLResponse)
def petition_detail(petition_id: int, session: Optional[str] = Cookie(default=None)) -> HTMLResponse:
    user = current_user(session)
    petition = query_one(
        """
        SELECT p.*, u.username
        FROM petitions p
        JOIN users u ON u.id = p.user_id
        WHERE p.id = ?
        """,
        (petition_id,),
    )
    if not petition:
        return layout("No encontrada", '<section class="card"><h1>Peticion no encontrada</h1></section>', user)

    signatures = query_all("SELECT * FROM signatures WHERE petition_id = ? ORDER BY id DESC", (petition_id,))
    donations = query_all("SELECT * FROM donations WHERE petition_id = ? ORDER BY id DESC", (petition_id,))
    comments = query_all(
        """
        SELECT c.*, u.username
        FROM comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.petition_id = ?
        ORDER BY c.id DESC
        """,
        (petition_id,),
    )
    donated = sum(float(d["amount"]) for d in donations)
    auth_forms = (
        f"""
        <div class="grid">
            <form class="card" method="post" action="/petitions/{petition_id}/sign">
                <h3>Firmar</h3>
                <input name="signer_name" placeholder="Nombre para mostrar" value="{user["username"]}" required>
                <button>Firmar peticion</button>
            </form>
            <form class="card" method="post" action="/petitions/{petition_id}/donate">
                <h3>Donar desde mi saldo</h3>
                <p class="muted">Saldo disponible: ${user["balance"]:.2f}</p>
                <input name="amount" type="number" min="1" step="0.01" placeholder="Monto" required>
                <input name="message" placeholder="Mensaje opcional">
                <button>Donar</button>
            </form>
            <form class="card" method="post" action="/petitions/{petition_id}/comments">
                <h3>Comentar</h3>
                <textarea name="body" placeholder="Comentario" required></textarea>
                <button>Publicar comentario</button>
            </form>
        </div>
        """
        if user
        else '<section class="card"><p><a href="/login">Entra</a> para firmar, donar o comentar.</p></section>'
    )
    body = f"""
    <section class="hero">
        <div>
            {'<img class="cover" src="' + petition["photo_path"] + '" alt="Foto de la peticion">' if petition["photo_path"] else ""}
            <h1>{petition["title"]}</h1>
            <p class="muted">Creada por {petition["username"]} el {petition["created_at"]}</p>
            <p>{petition["description"]}</p>
        </div>
        <aside class="card">
            <h2>Donaciones en la app</h2>
            <p><b>Objetivo:</b> ${petition["goal_amount"]:.2f}</p>
            <p><b>Recaudado registrado:</b> ${donated:.2f}</p>
            <p><b>Creador:</b> {petition["username"]}</p>
            <p><b>Firmas:</b> {len(signatures)}</p>
        </aside>
    </section>
    <section style="margin-top: 18px;">{auth_forms}</section>
    <section class="grid" style="margin-top: 18px;">
        <div class="card">
            <h2>Firmas</h2>
            {''.join(f'<p>{s["signer_name"]} <span class="muted">{s["created_at"]}</span></p>' for s in signatures) or '<p class="muted">Sin firmas todavia.</p>'}
        </div>
        <div class="card">
            <h2>Donaciones</h2>
            {''.join(f'<p><b>${d["amount"]:.2f}</b> de {d["donor_name"]}<br><span class="muted">{d["message"] or ""}</span></p>' for d in donations) or '<p class="muted">Sin donaciones registradas.</p>'}
        </div>
        <div class="card">
            <h2>Comentarios</h2>
            {''.join(f'<p><b>{c["username"]}</b>: {c["body"]}<br><span class="muted">{c["created_at"]}</span></p>' for c in comments) or '<p class="muted">Sin comentarios todavia.</p>'}
        </div>
    </section>
    """
    return layout(petition["title"], body, user)


@app.post("/petitions/{petition_id}/sign")
def sign_petition(
    petition_id: int,
    session: Optional[str] = Cookie(default=None),
    signer_name: str = Form(...),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with db() as conn:
        conn.execute(
            "INSERT INTO signatures (petition_id, user_id, signer_name, created_at) VALUES (?, ?, ?, ?)",
            (petition_id, user["id"], signer_name, now()),
        )
    return RedirectResponse(f"/petitions/{petition_id}", status_code=303)


@app.post("/petitions/{petition_id}/donate")
def donate(
    petition_id: int,
    session: Optional[str] = Cookie(default=None),
    amount: float = Form(...),
    message: str = Form(""),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    petition = query_one("SELECT * FROM petitions WHERE id = ?", (petition_id,))
    if not petition or amount <= 0 or amount > float(user["balance"]):
        return RedirectResponse(f"/petitions/{petition_id}", status_code=303)
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user["id"]))
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, petition["user_id"]))
        conn.execute(
            """
            INSERT INTO donations (petition_id, user_id, amount, donor_name, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (petition_id, user["id"], amount, user["username"], message, now()),
        )
        conn.execute(
            "INSERT INTO wallet_movements (user_id, movement_type, amount, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], "donacion enviada", -amount, f"Donacion a peticion #{petition_id}", now()),
        )
        conn.execute(
            "INSERT INTO wallet_movements (user_id, movement_type, amount, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (petition["user_id"], "donacion recibida", amount, f"Donacion recibida en peticion #{petition_id}", now()),
        )
    return RedirectResponse(f"/petitions/{petition_id}", status_code=303)


@app.post("/petitions/{petition_id}/comments")
def comment(
    petition_id: int,
    session: Optional[str] = Cookie(default=None),
    body: str = Form(...),
) -> RedirectResponse:
    user = require_user(session)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with db() as conn:
        conn.execute(
            "INSERT INTO comments (petition_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
            (petition_id, user["id"], body, now()),
        )
    return RedirectResponse(f"/petitions/{petition_id}", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin(
    session: Optional[str] = Cookie(default=None),
    q: str = "",
    date_from: str = "",
    date_to: str = "",
    sort: str = "donated_desc",
    user_role: str = "all",
) -> HTMLResponse:
    user = require_user(session)
    if not user:
        return layout("Admin", '<section class="card"><p>Necesitas entrar como admin.</p></section>')
    if not user["is_admin"]:
        return layout("Admin", '<section class="card"><p>No tenes permisos de administrador.</p></section>', user)

    totals = query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS users,
            (SELECT COUNT(*) FROM petitions) AS petitions,
            (SELECT COUNT(*) FROM signatures) AS signatures,
            (SELECT COUNT(*) FROM comments) AS comments,
            (SELECT COUNT(*) FROM donations) AS donations,
            (SELECT COALESCE(SUM(amount), 0) FROM donations) AS donated,
            (SELECT COALESCE(SUM(balance), 0) FROM users) AS app_balance,
            (SELECT COUNT(*) FROM withdrawals) AS withdrawals,
            (SELECT COALESCE(SUM(amount), 0) FROM withdrawals) AS withdrawn
        """
    )
    petition_filters = []
    petition_params = []
    if q:
        petition_filters.append("(p.title LIKE ? OR p.description LIKE ? OR u.username LIKE ?)")
        like_q = f"%{q}%"
        petition_params.extend([like_q, like_q, like_q])
    if date_from:
        petition_filters.append("p.created_at >= ?")
        petition_params.append(f"{date_from} 00:00:00")
    if date_to:
        petition_filters.append("p.created_at <= ?")
        petition_params.append(f"{date_to} 23:59:59")
    petition_where = f"WHERE {' AND '.join(petition_filters)}" if petition_filters else ""
    petition_order_options = {
        "donated_desc": "donated DESC, signatures DESC",
        "signatures_desc": "signatures DESC, donated DESC",
        "comments_desc": "comments DESC, donated DESC",
        "newest": "p.id DESC",
        "oldest": "p.id ASC",
        "goal_desc": "p.goal_amount DESC",
    }
    petition_order = petition_order_options.get(sort, petition_order_options["donated_desc"])
    top_petitions = query_all(
        f"""
        SELECT p.id, p.title, u.username,
            (SELECT COUNT(*) FROM signatures s WHERE s.petition_id = p.id) AS signatures,
            (SELECT COUNT(*) FROM comments c WHERE c.petition_id = p.id) AS comments,
            (SELECT COALESCE(SUM(d.amount), 0) FROM donations d WHERE d.petition_id = p.id) AS donated,
            p.goal_amount,
            p.created_at
        FROM petitions p
        JOIN users u ON u.id = p.user_id
        {petition_where}
        ORDER BY {petition_order}
        LIMIT 20
        """,
        tuple(petition_params),
    )

    user_filters = []
    user_params = []
    if q:
        user_filters.append("username LIKE ?")
        user_params.append(f"%{q}%")
    if user_role == "admins":
        user_filters.append("is_admin = 1")
    elif user_role == "regular":
        user_filters.append("is_admin = 0")
    user_where = f"WHERE {' AND '.join(user_filters)}" if user_filters else ""
    users = query_all(
        f"SELECT id, username, is_admin, balance, created_at FROM users {user_where} ORDER BY id DESC LIMIT 30",
        tuple(user_params),
    )

    filtered_petitions = query_one(
        f"SELECT COUNT(*) AS total FROM petitions p JOIN users u ON u.id = p.user_id {petition_where}",
        tuple(petition_params),
    )
    filtered_users = query_one(f"SELECT COUNT(*) AS total FROM users {user_where}", tuple(user_params))
    selected_sort = {
        "donated_desc": "",
        "signatures_desc": "",
        "comments_desc": "",
        "newest": "",
        "oldest": "",
        "goal_desc": "",
    }
    selected_sort[sort if sort in selected_sort else "donated_desc"] = "selected"
    selected_role = {"all": "", "admins": "", "regular": ""}
    selected_role[user_role if user_role in selected_role else "all"] = "selected"
    body = f"""
    <section class="card">
        <h1>Panel administrador</h1>
        <div class="stats">
            <div class="metric"><strong>{totals["users"]}</strong><span>Usuarios</span></div>
            <div class="metric"><strong>{totals["petitions"]}</strong><span>Peticiones</span></div>
            <div class="metric"><strong>{totals["signatures"]}</strong><span>Firmas</span></div>
            <div class="metric"><strong>{totals["donations"]}</strong><span>Donaciones</span></div>
            <div class="metric"><strong>${totals["donated"]:.2f}</strong><span>Total registrado</span></div>
            <div class="metric"><strong>{totals["comments"]}</strong><span>Comentarios</span></div>
            <div class="metric"><strong>${totals["app_balance"]:.2f}</strong><span>Saldo en app</span></div>
            <div class="metric"><strong>${totals["withdrawn"]:.2f}</strong><span>Retirado</span></div>
        </div>
    </section>
    <section class="card" style="margin-top: 18px;">
        <h2>Filtros</h2>
        <form method="get" action="/admin" class="filters">
            <label>
                <span class="muted">Buscar</span>
                <input name="q" value="{q}" placeholder="Titulo, descripcion, usuario">
            </label>
            <label>
                <span class="muted">Desde</span>
                <input name="date_from" type="date" value="{date_from}">
            </label>
            <label>
                <span class="muted">Hasta</span>
                <input name="date_to" type="date" value="{date_to}">
            </label>
            <label>
                <span class="muted">Ordenar peticiones</span>
                <select name="sort">
                    <option value="donated_desc" {selected_sort["donated_desc"]}>Mas donado</option>
                    <option value="signatures_desc" {selected_sort["signatures_desc"]}>Mas firmas</option>
                    <option value="comments_desc" {selected_sort["comments_desc"]}>Mas comentarios</option>
                    <option value="newest" {selected_sort["newest"]}>Mas nuevas</option>
                    <option value="oldest" {selected_sort["oldest"]}>Mas antiguas</option>
                    <option value="goal_desc" {selected_sort["goal_desc"]}>Mayor objetivo</option>
                </select>
            </label>
            <label>
                <span class="muted">Usuarios</span>
                <select name="user_role">
                    <option value="all" {selected_role["all"]}>Todos</option>
                    <option value="admins" {selected_role["admins"]}>Admins</option>
                    <option value="regular" {selected_role["regular"]}>No admins</option>
                </select>
            </label>
            <button>Aplicar filtros</button>
            <a class="button-link" href="/admin">Limpiar</a>
        </form>
        <p class="muted">Resultados: {filtered_petitions["total"]} peticiones y {filtered_users["total"]} usuarios.</p>
    </section>
    <section class="card" style="margin-top: 18px;">
        <h2>Peticiones filtradas</h2>
        <table>
            <tr><th>ID</th><th>Titulo</th><th>Creador</th><th>Firmas</th><th>Comentarios</th><th>Objetivo</th><th>Donado</th><th>Creada</th></tr>
            {''.join(f'<tr><td>{p["id"]}</td><td><a href="/petitions/{p["id"]}">{p["title"]}</a></td><td>{p["username"]}</td><td>{p["signatures"]}</td><td>{p["comments"]}</td><td>${p["goal_amount"]:.2f}</td><td>${p["donated"]:.2f}</td><td>{p["created_at"]}</td></tr>' for p in top_petitions) or '<tr><td colspan="8" class="muted">No hay peticiones para estos filtros.</td></tr>'}
        </table>
    </section>
    <section class="card" style="margin-top: 18px;">
        <h2>Usuarios filtrados</h2>
        <table>
            <tr><th>ID</th><th>Usuario</th><th>Admin</th><th>Saldo</th><th>Creado</th></tr>
            {''.join(f'<tr><td>{u["id"]}</td><td>{u["username"]}</td><td>{u["is_admin"]}</td><td>${u["balance"]:.2f}</td><td>{u["created_at"]}</td></tr>' for u in users) or '<tr><td colspan="5" class="muted">No hay usuarios para estos filtros.</td></tr>'}
        </table>
    </section>
    """
    return layout("Admin", body, user)
