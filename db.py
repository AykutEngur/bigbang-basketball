"""
Big Bang Basketball - veritabani yardimci fonksiyonlari
"""

import os
import mysql.connector


def _connection_kwargs(include_database=True):
    kwargs = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }
    if include_database:
        kwargs["database"] = os.environ.get("DB_NAME", "bigbang_basketball")
    return kwargs


def get_connection():
    return mysql.connector.connect(**_connection_kwargs())


def ensure_database_exists():
    db_name = os.environ.get("DB_NAME", "bigbang_basketball")
    conn = mysql.connector.connect(**_connection_kwargs(include_database=False))
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {db_name} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci"
        )
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Players
# ----------------------------------------------------------------------

def email_exists(email: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM players WHERE email = %s", (email,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def create_player(first_name, last_name, email, password_hash, birth_date,
                   contract_accepted=True):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO players
                (first_name, last_name, email, password_hash, birth_date,
                 contract_accepted, contract_accepted_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (first_name, last_name, email, password_hash, birth_date,
             contract_accepted),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_player_by_email(email: str):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM players WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_player_by_id(player_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT p.*, t.name AS team_name, t.logo AS team_logo
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.id = %s
            """,
            (player_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def update_player_photo(player_id: int, filename: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE players SET profile_photo = %s WHERE id = %s",
            (filename, player_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_players():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT p.id, p.first_name, p.last_name, p.profile_photo,
                   p.jersey_number, p.is_free_agent, p.points_total,
                   p.created_at, t.name AS team_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            ORDER BY p.created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def jersey_number_taken(team_id: int, jersey_number: int, exclude_player_id=None) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if exclude_player_id:
            cursor.execute(
                "SELECT id FROM players WHERE team_id = %s AND jersey_number = %s AND id != %s",
                (team_id, jersey_number, exclude_player_id),
            )
        else:
            cursor.execute(
                "SELECT id FROM players WHERE team_id = %s AND jersey_number = %s",
                (team_id, jersey_number),
            )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def add_player_to_team(player_id: int, team_id: int, jersey_number: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE players
            SET team_id = %s, jersey_number = %s, is_free_agent = FALSE
            WHERE id = %s
            """,
            (team_id, jersey_number, player_id),
        )
        conn.commit()
    finally:
        conn.close()


def ban_player(player_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET is_banned = TRUE WHERE id = %s", (player_id,))
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Teams
# ----------------------------------------------------------------------

def team_name_exists(name: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM teams WHERE name = %s", (name,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def create_team(name: str, captain_id: int, logo_filename=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO teams (name, logo, captain_id, leader_contract_accepted)
            VALUES (%s, %s, %s, TRUE)
            """,
            (name, logo_filename, captain_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_team_by_id(team_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_all_teams():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT t.*, COUNT(p.id) AS player_count
            FROM teams t
            LEFT JOIN players p ON p.team_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_team_members(team_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, first_name, last_name, profile_photo, jersey_number, points_total
            FROM players
            WHERE team_id = %s
            ORDER BY jersey_number ASC
            """,
            (team_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Join requests
# ----------------------------------------------------------------------

def create_join_request(player_id: int, team_id: int, token: str,
                         requested_jersey_number: int, expires_at):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO join_requests
                (player_id, team_id, token, requested_jersey_number, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (player_id, team_id, token, requested_jersey_number, expires_at),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def has_pending_request(player_id: int, team_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM join_requests
            WHERE player_id = %s AND team_id = %s AND status = 'pending'
            """,
            (player_id, team_id),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_join_request_by_token(token: str):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM join_requests WHERE token = %s", (token,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_join_request_by_id(request_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM join_requests WHERE id = %s", (request_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_pending_requests_for_team(team_id: int):
    """Takim liderinin inbox'i icin: takima gelen bekleyen istekler."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT jr.*,
                   p.first_name, p.last_name, p.profile_photo, p.points_total
            FROM join_requests jr
            JOIN players p ON jr.player_id = p.id
            WHERE jr.team_id = %s AND jr.status = 'pending'
            ORDER BY jr.created_at DESC
            """,
            (team_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_my_sent_requests(player_id: int):
    """Oyuncunun gonderdigi tum bekleyen istekler (geri cekebilmesi icin)."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT jr.*, t.name AS team_name, t.logo AS team_logo
            FROM join_requests jr
            JOIN teams t ON jr.team_id = t.id
            WHERE jr.player_id = %s AND jr.status = 'pending'
            ORDER BY jr.created_at DESC
            """,
            (player_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def update_join_request_status(request_id: int, status: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE join_requests SET status = %s, decided_at = NOW() WHERE id = %s",
            (status, request_id),
        )
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------

def create_notification(player_id: int, notif_type: str, message: str,
                          related_join_request_id=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notifications
                (player_id, type, message, related_join_request_id)
            VALUES (%s, %s, %s, %s)
            """,
            (player_id, notif_type, message, related_join_request_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_notifications_for_player(player_id: int):
    """Oyuncunun tum bildirimlerini (okunmus + okunmamis) getirir, yeniden eskiye."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT n.*, jr.requested_jersey_number, jr.player_id AS req_player_id,
                   t.name AS team_name, t.id AS team_id,
                   p.first_name AS req_first_name, p.last_name AS req_last_name,
                   p.profile_photo AS req_photo
            FROM notifications n
            LEFT JOIN join_requests jr ON n.related_join_request_id = jr.id
            LEFT JOIN teams t ON jr.team_id = t.id
            LEFT JOIN players p ON jr.player_id = p.id
            WHERE n.player_id = %s
            ORDER BY n.created_at DESC
            LIMIT 50
            """,
            (player_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_unread_notification_count(player_id: int) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE player_id = %s AND is_read = FALSE",
            (player_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def mark_notifications_read(player_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read = TRUE WHERE player_id = %s",
            (player_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# DB init
# ----------------------------------------------------------------------

def init_db_if_needed():
    ensure_database_exists()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE 'players'")
        if cursor.fetchone() is None:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                raw = f.read()
            cleaned_lines = [
                line for line in raw.splitlines()
                if not line.strip().startswith("--")
            ]
            cleaned_sql = "\n".join(cleaned_lines)
            statements = cleaned_sql.split(";")
            for statement in statements:
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            conn.commit()
    finally:
        conn.close()