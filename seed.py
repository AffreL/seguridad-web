from pathlib import Path
import sqlite3

import main


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"


def write_seed_images() -> None:
    return None


def now_at(day: str) -> str:
    return f"2026-04-{day} 10:00:00"


def get_or_create_user(conn: sqlite3.Connection, username: str, password: str, is_admin: int = 0) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO users (username, password, is_admin, balance, created_at) VALUES (?, ?, ?, 0, ?)",
        (username, password, is_admin, now_at("20")),
    )
    return int(cursor.lastrowid)


def get_or_create_petition(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    description: str,
    bank_alias: str,
    photo_path: str,
    goal_amount: float,
    created_at: str,
) -> int:
    row = conn.execute("SELECT id FROM petitions WHERE title = ?", (title,)).fetchone()
    if row:
        conn.execute(
            """
            UPDATE petitions
            SET user_id = ?, description = ?, bank_alias = ?, photo_path = ?, goal_amount = ?
            WHERE id = ?
            """,
            (user_id, description, bank_alias, photo_path, goal_amount, row["id"]),
        )
        return int(row["id"])
    cursor = conn.execute(
        """
        INSERT INTO petitions (user_id, title, description, bank_alias, photo_path, goal_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, description, bank_alias, photo_path, goal_amount, created_at),
    )
    return int(cursor.lastrowid)


def insert_once(
    conn: sqlite3.Connection,
    table: str,
    unique_where: str,
    unique_params: tuple,
    insert_sql: str,
    insert_params: tuple,
) -> None:
    exists = conn.execute(f"SELECT id FROM {table} WHERE {unique_where}", unique_params).fetchone()
    if not exists:
        conn.execute(insert_sql, insert_params)


def seed() -> None:
    main.init_db()
    write_seed_images()

    with main.db() as conn:
        admin_id = get_or_create_user(conn, "admin", "admin", 1)
        sofia_id = get_or_create_user(conn, "sofia", "sofia123")
        martin_id = get_or_create_user(conn, "martin", "martin123")
        lucia_id = get_or_create_user(conn, "lucia", "lucia123")
        diego_id = get_or_create_user(conn, "diego", "diego123")
        camila_id = get_or_create_user(conn, "camila", "camila123")

        seed_balances = {
            admin_id: 50000,
            sofia_id: 145000,
            martin_id: 93000,
            lucia_id: 118000,
            diego_id: 64000,
            camila_id: 87500,
        }
        for user_id, balance in seed_balances.items():
            conn.execute("UPDATE users SET balance = ? WHERE id = ?", (balance, user_id))
            insert_once(
                conn,
                "wallet_movements",
                "user_id = ? AND movement_type = ? AND detail = ?",
                (user_id, "carga inicial", f"Saldo inicial via alias {main.APP_DEPOSIT_ALIAS}"),
                "INSERT INTO wallet_movements (user_id, movement_type, amount, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, "carga inicial", balance, f"Saldo inicial via alias {main.APP_DEPOSIT_ALIAS}", now_at("20")),
            )

        perros_id = get_or_create_petition(
            conn,
            sofia_id,
            "Alimento y atencion para perros rescatados",
            "El refugio necesita alimento balanceado, pipetas, vacunas y fondos para reparar caniles. Hay perros adultos y cachorros esperando transito o adopcion.",
            "PATITAS.SUR.DONA",
            "/uploads/seed_perros.png",
            350000,
            now_at("21"),
        )
        riachuelo_id = get_or_create_petition(
            conn,
            martin_id,
            "Jornada comunitaria para limpiar el Riachuelo",
            "Vecinos y voluntarios organizan una limpieza de costa con bolsas, guantes, barbijos, traslado de residuos y agua para los equipos.",
            "RIACHUELO.LIMPIO.MP",
            "/uploads/seed_riachuelo.png",
            520000,
            now_at("22"),
        )
        comedor_id = get_or_create_petition(
            conn,
            lucia_id,
            "Insumos para el comedor del barrio",
            "Se busca cubrir arroz, fideos, verduras, garrafas y elementos de cocina para sostener 120 viandas semanales durante el mes.",
            "COMEDOR.BARRIO.AYUDA",
            "/uploads/seed_comedor.png",
            280000,
            now_at("23"),
        )

        signatures = [
            (perros_id, martin_id, "Martin"),
            (perros_id, lucia_id, "Lucia"),
            (perros_id, diego_id, "Diego"),
            (riachuelo_id, sofia_id, "Sofia"),
            (riachuelo_id, camila_id, "Camila"),
            (comedor_id, admin_id, "Admin"),
            (comedor_id, camila_id, "Camila"),
        ]
        for petition_id, user_id, signer_name in signatures:
            insert_once(
                conn,
                "signatures",
                "petition_id = ? AND user_id = ?",
                (petition_id, user_id),
                "INSERT INTO signatures (petition_id, user_id, signer_name, created_at) VALUES (?, ?, ?, ?)",
                (petition_id, user_id, signer_name, now_at("24")),
            )

        donations = [
            (perros_id, martin_id, 12000, "Martin", "Para alimento y vacunas."),
            (perros_id, diego_id, 8500, "Diego", "Gracias por el trabajo del refugio."),
            (riachuelo_id, camila_id, 18000, "Camila", "Sumo para bolsas y guantes."),
            (riachuelo_id, lucia_id, 9500, "Lucia", "Ojala se pueda repetir todos los meses."),
            (comedor_id, sofia_id, 15000, "Sofia", "Para la compra de verduras."),
        ]
        for petition_id, user_id, amount, donor_name, message in donations:
            insert_once(
                conn,
                "donations",
                "petition_id = ? AND user_id = ? AND amount = ?",
                (petition_id, user_id, amount),
                """
                INSERT INTO donations (petition_id, user_id, amount, donor_name, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (petition_id, user_id, amount, donor_name, message, now_at("25")),
            )

        comments = [
            (perros_id, martin_id, "Puedo pasar el sabado con una bolsa de alimento."),
            (perros_id, camila_id, "Tambien necesitan mantas o solo alimento?"),
            (perros_id, admin_id, "Actualicen si consiguen veterinaria para difundir."),
            (riachuelo_id, sofia_id, "Me anoto para la jornada de limpieza."),
            (riachuelo_id, diego_id, "Tengo guantes y bolsas para llevar."),
            (riachuelo_id, lucia_id, "Seria bueno sumar un punto de encuentro visible."),
            (comedor_id, martin_id, "Puedo ayudar con traslado de mercaderia."),
        ]
        for petition_id, user_id, body in comments:
            insert_once(
                conn,
                "comments",
                "petition_id = ? AND user_id = ? AND body = ?",
                (petition_id, user_id, body),
                "INSERT INTO comments (petition_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
                (petition_id, user_id, body, now_at("26")),
            )

    print("Seed cargado: usuarios, peticiones, firmas, donaciones y comentarios.")
    print("Usuarios de prueba: sofia/sofia123, martin/martin123, lucia/lucia123, diego/diego123, camila/camila123")


if __name__ == "__main__":
    seed()
