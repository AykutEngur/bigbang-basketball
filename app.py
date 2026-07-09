"""
Big Bang Basketball - Flask web app
"""

import os
import uuid
import secrets
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, abort, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

import db
from mailer import send_welcome_email, send_team_created_email, send_join_request_email

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

try:
    db.init_db_if_needed()
except Exception as exc:
    print(f"[startup] DB hazirlanirken sorun olustu: {exc}")

MONTHS_TR = [
    (1, "Ocak"), (2, "Şubat"), (3, "Mart"), (4, "Nisan"),
    (5, "Mayıs"), (6, "Haziran"), (7, "Temmuz"), (8, "Ağustos"),
    (9, "Eylül"), (10, "Ekim"), (11, "Kasım"), (12, "Aralık"),
]

MIN_TEAM_SIZE = 6
JOIN_REQUEST_VALIDITY_HOURS = 24

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024

PHOTO_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads", "profile_photos")
TEAM_LOGO_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads", "team_logos")
os.makedirs(PHOTO_UPLOAD_DIR, exist_ok=True)
os.makedirs(TEAM_LOGO_UPLOAD_DIR, exist_ok=True)


def _allowed_photo(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS
    )


def _save_square_image(file_storage, save_dir, prefix):
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    unique_name = f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(save_dir, unique_name)
    image = Image.open(file_storage)
    image = image.convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((400, 400))
    image.save(save_path, quality=85, optimize=True)
    return unique_name


@app.context_processor
def inject_current_player():
    """Navbar avatari + okunmamis bildirim sayisi icin."""
    player_id = session.get("player_id")
    if not player_id:
        return {"current_player": None, "unread_count": 0}
    try:
        player = db.get_player_by_id(player_id)
        unread = db.get_unread_notification_count(player_id)
    except Exception:
        player = None
        unread = 0
    return {"current_player": player, "unread_count": unread}


def login_required_redirect():
    player_id = session.get("player_id")
    if not player_id:
        return None
    return db.get_player_by_id(player_id)


# ----------------------------------------------------------------------
# Home / Static pages
# ----------------------------------------------------------------------

@app.route("/")
def home():
    context = {
        "league_name": "Big Bang Basketball",
        "slogan": "Where legends are born.",
        "hashtag": "#BigBangBasketball",
        "instagram_handle": "@bigbang_basketball",
        "instagram_url": "https://www.instagram.com/bigbang_basketball",
        "stats": [
            {"number": "6", "label": "Takım"},
            {"number": "36+", "label": "Oyuncu"},
            {"number": "19", "label": "Toplam Maç"},
            {"number": "5", "label": "Hafta"},
        ],
    }
    return render_template("home.html", **context)


@app.route("/contract")
def contract():
    return render_template("contract.html")


@app.route("/federation")
def federation():
    return render_template("federation.html")


# ----------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    current_year = date.today().year
    years = list(range(current_year - 12, current_year - 60, -1))

    if request.method == "GET":
        return render_template(
            "register.html", error=None, form_data=None,
            months=MONTHS_TR, years=years,
        )

    form_data = {
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "dob_day": request.form.get("dob_day", ""),
        "dob_month": request.form.get("dob_month", ""),
        "dob_year": request.form.get("dob_year", ""),
        "contract_accepted": request.form.get("contract_accepted") == "on",
    }
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    def render_with_error(message):
        return render_template(
            "register.html", error=message, form_data=form_data,
            months=MONTHS_TR, years=years,
        )

    if not form_data["first_name"] or not form_data["last_name"]:
        return render_with_error("Ad ve soyad alanları zorunludur.")
    if not form_data["email"] or "@" not in form_data["email"]:
        return render_with_error("Geçerli bir e-posta adresi gir.")
    if len(password) < 6:
        return render_with_error("Şifre en az 6 karakter olmalı.")
    if password != password_confirm:
        return render_with_error("Şifreler birbiriyle eşleşmiyor.")
    if not (form_data["dob_day"] and form_data["dob_month"] and form_data["dob_year"]):
        return render_with_error("Doğum tarihini eksiksiz seç.")

    try:
        birth_date = date(
            int(form_data["dob_year"]), int(form_data["dob_month"]), int(form_data["dob_day"])
        )
    except ValueError:
        return render_with_error("Geçerli bir doğum tarihi seç.")

    if not form_data["contract_accepted"]:
        return render_with_error("Kayıt olabilmek için katılımcı sözleşmesini onaylaman gerekiyor.")

    try:
        if db.email_exists(form_data["email"]):
            return render_with_error("Bu e-posta adresi zaten kayıtlı. Giriş yapmayı dene.")
    except Exception as exc:
        print(f"[register] DB kontrol hatasi: {exc}")
        return render_with_error("Şu anda sunucuya bağlanılamıyor. Lütfen birazdan tekrar dene.")

    password_hash = generate_password_hash(password)
    try:
        player_id = db.create_player(
            first_name=form_data["first_name"], last_name=form_data["last_name"],
            email=form_data["email"], password_hash=password_hash,
            birth_date=birth_date, contract_accepted=True,
        )
    except Exception as exc:
        print(f"[register] DB kayit hatasi: {exc}")
        return render_with_error("Kayıt sırasında bir sorun oluştu. Lütfen tekrar dene.")

    session["player_id"] = player_id
    session["first_name"] = form_data["first_name"]
    #send_welcome_email(form_data["email"], form_data["first_name"])
    return render_template("register_success.html", first_name=form_data["first_name"])


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next", "")
    if request.method == "GET":
        return render_template("login.html", error=None, email=None, next_url=next_url)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    next_url = request.form.get("next_url", "")

    if not email or not password:
        return render_template(
            "login.html", error="E-posta ve şifre alanları zorunludur.",
            email=email, next_url=next_url,
        )

    try:
        player = db.get_player_by_email(email)
    except Exception as exc:
        print(f"[login] DB hatasi: {exc}")
        return render_template(
            "login.html", error="Şu anda sunucuya bağlanılamıyor.",
            email=email, next_url=next_url,
        )

    if not player or not check_password_hash(player["password_hash"], password):
        return render_template(
            "login.html", error="E-posta veya şifre yanlış.", email=email, next_url=next_url,
        )

    session["player_id"] = player["id"]
    session["first_name"] = player["first_name"]

    if next_url:
        return redirect(next_url)
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ----------------------------------------------------------------------
# Profile + photo upload
# ----------------------------------------------------------------------

@app.route("/profile")
def profile():
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("register"))
    player = db.get_player_by_id(player_id)
    if not player:
        session.clear()
        return redirect(url_for("register"))
    return render_template("profile.html", player=player)


@app.route("/profile/photo", methods=["POST"])
def upload_profile_photo():
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("register"))

    file = request.files.get("photo")
    if not file or file.filename == "":
        return redirect(url_for("profile"))

    if not _allowed_photo(file.filename):
        return render_template(
            "profile.html", player=db.get_player_by_id(player_id),
            photo_error="Yalnızca PNG, JPG veya WEBP formatında resim yükleyebilirsin.",
        )

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_PHOTO_SIZE_BYTES:
        return render_template(
            "profile.html", player=db.get_player_by_id(player_id),
            photo_error="Dosya boyutu 5 MB'ı geçemez.",
        )

    try:
        unique_name = _save_square_image(file, PHOTO_UPLOAD_DIR, f"player_{player_id}")
    except Exception as exc:
        print(f"[upload_profile_photo] Resim isleme hatasi: {exc}")
        return render_template(
            "profile.html", player=db.get_player_by_id(player_id),
            photo_error="Resim işlenirken bir sorun oluştu.",
        )

    try:
        current_player = db.get_player_by_id(player_id)
        old_photo = current_player.get("profile_photo") if current_player else None
        if old_photo:
            old_path = os.path.join(PHOTO_UPLOAD_DIR, old_photo)
            if os.path.exists(old_path):
                os.remove(old_path)
    except Exception:
        pass

    db.update_player_photo(player_id, unique_name)
    return redirect(url_for("profile"))


# ----------------------------------------------------------------------
# Mesajlarim / Bildirimler
# ----------------------------------------------------------------------

@app.route("/messages")
def messages():
    """
    Takim lideriyse: bekleyen katilma isteklerini gosterir + tum bildirimler.
    Takim uyesiyse: kendi gonderdigi bekleyen istekler + tum bildirimler.
    """
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("login", next="/messages"))

    player = db.get_player_by_id(player_id)
    if not player:
        session.clear()
        return redirect(url_for("register"))

    # Takim lideriyse bu takima gelen bekleyen istekler
    pending_requests = []
    my_team = None
    if player.get("team_id"):
        my_team = db.get_team_by_id(player["team_id"])
        if my_team and my_team.get("captain_id") == player_id:
            try:
                pending_requests = db.get_pending_requests_for_team(player["team_id"])
            except Exception as exc:
                print(f"[messages] pending_requests hatasi: {exc}")

    # Oyuncunun gonderdigi bekleyen istekler (geri cekme icin)
    my_sent_requests = []
    try:
        my_sent_requests = db.get_my_sent_requests(player_id)
    except Exception as exc:
        print(f"[messages] my_sent_requests hatasi: {exc}")

    # Tum bildirimler
    notifications = []
    try:
        notifications = db.get_notifications_for_player(player_id)
        db.mark_notifications_read(player_id)
    except Exception as exc:
        print(f"[messages] notifications hatasi: {exc}")

    return render_template(
        "messages.html",
        player=player,
        my_team=my_team,
        pending_requests=pending_requests,
        my_sent_requests=my_sent_requests,
        notifications=notifications,
    )


@app.route("/messages/decide/<int:request_id>/<decision>", methods=["POST"])
def decide_join_in_app(request_id, decision):
    """
    Takim lideri profil ici mesajlar sayfasindan isteği onaylar/reddeder.
    """
    if decision not in ("approve", "reject"):
        abort(404)

    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("login"))

    join_req = db.get_join_request_by_id(request_id)
    if not join_req or join_req["status"] != "pending":
        return redirect(url_for("messages"))

    # Sadece o takimin lideri karar verebilir
    my_team = db.get_team_by_id(join_req["team_id"])
    if not my_team or my_team.get("captain_id") != player_id:
        abort(403)

    if datetime.now() > join_req["expires_at"]:
        db.update_join_request_status(request_id, "expired")
        return redirect(url_for("messages"))

    if decision == "reject":
        db.update_join_request_status(request_id, "rejected")
        # Oyuncuya red bildirimi
        requester = db.get_player_by_id(join_req["player_id"])
        if requester:
            db.create_notification(
                player_id=join_req["player_id"],
                notif_type="join_request_rejected",
                message=f'"{my_team["name"]}" takımına katılma isteğin reddedildi.',
                related_join_request_id=request_id,
            )
    else:
        # Forma numarasi hala bos mu?
        if db.jersey_number_taken(join_req["team_id"], join_req["requested_jersey_number"]):
            return render_template(
                "messages.html",
                player=db.get_player_by_id(player_id),
                my_team=my_team,
                pending_requests=db.get_pending_requests_for_team(join_req["team_id"]),
                my_sent_requests=db.get_my_sent_requests(player_id),
                notifications=db.get_notifications_for_player(player_id),
                decision_error=f"#{join_req['requested_jersey_number']} forma numarası artık başka bir oyuncuda, bu isteği onaylayamazsın.",
            )
        db.add_player_to_team(
            join_req["player_id"], join_req["team_id"],
            join_req["requested_jersey_number"],
        )
        db.update_join_request_status(request_id, "approved")
        # Oyuncuya onay bildirimi
        db.create_notification(
            player_id=join_req["player_id"],
            notif_type="join_request_approved",
            message=f'"{my_team["name"]}" takımına katılma isteğin onaylandı! Artık takımın bir parçasısın.',
            related_join_request_id=request_id,
        )

    return redirect(url_for("messages"))


@app.route("/messages/cancel/<int:request_id>", methods=["POST"])
def cancel_join_request(request_id):
    """Oyuncu kendi gonderdigi bekleyen istegi geri ceker."""
    player_id = session.get("player_id")
    if not player_id:
        return redirect(url_for("login"))

    join_req = db.get_join_request_by_id(request_id)
    if not join_req:
        return redirect(url_for("messages"))

    # Sadece isteği gönderen iptal edebilir
    if join_req["player_id"] != player_id:
        abort(403)

    if join_req["status"] != "pending":
        return redirect(url_for("messages"))

    db.update_join_request_status(request_id, "rejected")  # "cancelled" yerine rejected kullanıyoruz

    # Takim liderine bildirim
    team = db.get_team_by_id(join_req["team_id"])
    if team and team.get("captain_id"):
        player = db.get_player_by_id(player_id)
        db.create_notification(
            player_id=team["captain_id"],
            notif_type="join_request_cancelled",
            message=f'{player["first_name"]} {player["last_name"]}, "{team["name"]}" takımına gönderdiği katılma isteğini geri çekti.',
            related_join_request_id=request_id,
        )

    return redirect(url_for("messages"))


# ----------------------------------------------------------------------
# Player pool
# ----------------------------------------------------------------------

@app.route("/player-pool")
def player_pool():
    try:
        players = db.get_all_players()
    except Exception as exc:
        print(f"[player_pool] DB hatasi: {exc}")
        players = []
    return render_template("player_pool.html", players=players)


# ----------------------------------------------------------------------
# Create team
# ----------------------------------------------------------------------

@app.route("/create-team", methods=["GET", "POST"])
def create_team():
    player = login_required_redirect()
    if not player:
        return render_template("create_team_auth_gate.html")

    if player.get("team_id"):
        return render_template(
            "create_team_already_in_team.html",
            team=db.get_team_by_id(player["team_id"]),
        )

    if request.method == "GET":
        return render_template("create_team.html", error=None, form_data=None)

    form_data = {
        "team_name": request.form.get("team_name", "").strip(),
        "jersey_number": request.form.get("jersey_number", "").strip(),
        "contract_accepted": request.form.get("contract_accepted") == "on",
    }

    def render_with_error(message):
        return render_template("create_team.html", error=message, form_data=form_data)

    if not form_data["team_name"]:
        return render_with_error("Takım ismi zorunludur.")
    if len(form_data["team_name"]) < 3:
        return render_with_error("Takım ismi en az 3 karakter olmalı.")
    if not form_data["jersey_number"].isdigit():
        return render_with_error("Geçerli bir forma numarası gir.")
    jersey_number = int(form_data["jersey_number"])
    if not (0 <= jersey_number <= 99):
        return render_with_error("Forma numarası 0-99 arasında olmalı.")
    if not form_data["contract_accepted"]:
        return render_with_error("Takım kurabilmek için kurallar ve uygunsuz içerik politikasını onaylaman gerekiyor.")

    try:
        if db.team_name_exists(form_data["team_name"]):
            return render_with_error("Bu takım ismi zaten kullanılıyor.")
    except Exception as exc:
        print(f"[create_team] DB kontrol hatasi: {exc}")
        return render_with_error("Şu anda sunucuya bağlanılamıyor.")

    logo_filename = None
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        if not _allowed_photo(logo_file.filename):
            return render_with_error("Logo yalnızca PNG, JPG veya WEBP formatında olabilir.")
        logo_file.seek(0, os.SEEK_END)
        logo_size = logo_file.tell()
        logo_file.seek(0)
        if logo_size > MAX_PHOTO_SIZE_BYTES:
            return render_with_error("Logo dosya boyutu 5 MB'ı geçemez.")
        try:
            logo_filename = _save_square_image(logo_file, TEAM_LOGO_UPLOAD_DIR, "team")
        except Exception as exc:
            print(f"[create_team] Logo isleme hatasi: {exc}")
            return render_with_error("Logo işlenirken bir sorun oluştu.")

    try:
        team_id = db.create_team(
            name=form_data["team_name"], captain_id=player["id"], logo_filename=logo_filename,
        )
        db.add_player_to_team(player["id"], team_id, jersey_number)
    except Exception as exc:
        print(f"[create_team] DB kayit hatasi: {exc}")
        return render_with_error("Takım kurulurken bir sorun oluştu.")

    #send_team_created_email(player["email"], player["first_name"], form_data["team_name"])
   # return render_template(
    #    "create_team_success.html", team_name=form_data["team_name"],
    #    min_team_size=MIN_TEAM_SIZE,
    #)


# ----------------------------------------------------------------------
# Join team
# ----------------------------------------------------------------------

@app.route("/join-team")
def join_team():
    try:
        teams = db.get_all_teams()
    except Exception as exc:
        print(f"[join_team] DB hatasi: {exc}")
        teams = []
    return render_template("join_team.html", teams=teams, min_team_size=MIN_TEAM_SIZE)


@app.route("/teams/<int:team_id>")
def team_detail(team_id):
    team = db.get_team_by_id(team_id)
    if not team:
        abort(404)

    members = db.get_team_members(team_id)
    captain = db.get_player_by_id(team["captain_id"]) if team["captain_id"] else None

    current_player_id = session.get("player_id")
    already_member = (
        current_player_id is not None
        and any(m["id"] == current_player_id for m in members)
    )
    has_pending = False
    if current_player_id and not already_member:
        try:
            has_pending = db.has_pending_request(current_player_id, team_id)
        except Exception:
            has_pending = False

    return render_template(
        "team_detail.html", team=team, members=members, captain=captain,
        min_team_size=MIN_TEAM_SIZE, already_member=already_member,
        has_pending=has_pending,
    )


@app.route("/teams/<int:team_id>/join", methods=["GET", "POST"])
def request_join_team(team_id):
    team = db.get_team_by_id(team_id)
    if not team:
        abort(404)

    player = login_required_redirect()
    if not player:
        return render_template("create_team_auth_gate.html", team=team, is_join_flow=True)

    if player.get("team_id"):
        return redirect(url_for("team_detail", team_id=team_id))

    if request.method == "GET":
        return render_template("join_team_request.html", team=team, error=None)

    jersey_number_raw = request.form.get("jersey_number", "").strip()
    if not jersey_number_raw.isdigit():
        return render_template("join_team_request.html", team=team, error="Geçerli bir forma numarası gir.")
    jersey_number = int(jersey_number_raw)
    if not (0 <= jersey_number <= 99):
        return render_template("join_team_request.html", team=team, error="Forma numarası 0-99 arasında olmalı.")

    try:
        if db.jersey_number_taken(team_id, jersey_number):
            return render_template(
                "join_team_request.html", team=team,
                error="Bu forma numarası takımda zaten kullanılıyor. Başka bir numara seç.",
            )
        if db.has_pending_request(player["id"], team_id):
            return render_template(
                "join_team_request.html", team=team,
                error="Bu takıma zaten bekleyen bir katılma isteğin var.",
            )
    except Exception as exc:
        print(f"[request_join_team] DB kontrol hatasi: {exc}")
        return render_template("join_team_request.html", team=team, error="Şu anda sunucuya bağlanılamıyor.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=JOIN_REQUEST_VALIDITY_HOURS)

    try:
        join_request_id = db.create_join_request(player["id"], team_id, token, jersey_number, expires_at)
    except Exception as exc:
        print(f"[request_join_team] DB kayit hatasi: {exc}")
        return render_template("join_team_request.html", team=team, error="İstek gönderilirken bir sorun oluştu.")

    captain = db.get_player_by_id(team["captain_id"]) if team["captain_id"] else None

    # In-app bildirim: takim liderine
    if captain:
        db.create_notification(
            player_id=captain["id"],
            notif_type="join_request_received",
            message=f'{player["first_name"]} {player["last_name"]}, "{team["name"]}" takımına katılmak için istek gönderdi. Talep ettiği forma numarası: #{jersey_number}',
            related_join_request_id=join_request_id,
        )

    # Mail de gönder (online olunca linke tıklanabilir, şimdilik bonus)
    if captain:
        approve_url = url_for("decide_join_request", token=token, decision="approve", _external=True)
        reject_url = url_for("decide_join_request", token=token, decision="reject", _external=True)
        #send_join_request_email(
           # captain["email"], captain["first_name"], player["first_name"], player["last_name"],
            #team["name"], jersey_number, approve_url, reject_url,
       # )

    return render_template("join_team_request_sent.html", team=team)


@app.route("/join-requests/<token>/<decision>")
def decide_join_request(token, decision):
    """Mail linkiyle onay/red (site online oldugunda kullanilir)."""
    if decision not in ("approve", "reject"):
        abort(404)

    join_request = db.get_join_request_by_token(token)
    if not join_request:
        return render_template("join_request_decision.html", outcome="not_found")
    if join_request["status"] != "pending":
        return render_template("join_request_decision.html", outcome="already_decided", join_request=join_request)
    if datetime.now() > join_request["expires_at"]:
        db.update_join_request_status(join_request["id"], "expired")
        return render_template("join_request_decision.html", outcome="expired")

    if decision == "reject":
        db.update_join_request_status(join_request["id"], "rejected")
        team = db.get_team_by_id(join_request["team_id"])
        db.create_notification(
            player_id=join_request["player_id"],
            notif_type="join_request_rejected",
            message=f'"{team["name"]}" takımına katılma isteğin reddedildi.',
            related_join_request_id=join_request["id"],
        )
        return render_template("join_request_decision.html", outcome="rejected")

    team_id = join_request["team_id"]
    player_id = join_request["player_id"]
    jersey_number = join_request["requested_jersey_number"]

    if db.jersey_number_taken(team_id, jersey_number):
        return render_template("join_request_decision.html", outcome="jersey_conflict")

    try:
        db.add_player_to_team(player_id, team_id, jersey_number)
        db.update_join_request_status(join_request["id"], "approved")
        team = db.get_team_by_id(team_id)
        db.create_notification(
            player_id=player_id,
            notif_type="join_request_approved",
            message=f'"{team["name"]}" takımına katılma isteğin onaylandı! Artık takımın bir parçasısın.',
            related_join_request_id=join_request["id"],
        )
    except Exception as exc:
        print(f"[decide_join_request] DB hatasi: {exc}")
        return render_template("join_request_decision.html", outcome="error")

    team = db.get_team_by_id(team_id)
    player = db.get_player_by_id(player_id)
    return render_template("join_request_decision.html", outcome="approved", team=team, player=player)


# ----------------------------------------------------------------------
# Placeholder routes
# ----------------------------------------------------------------------

PLACEHOLDER_PAGES = {
    "standings": "Puan Durumu",
    "fixtures": "Fikstür",
    "payment": "Ödeme",
}


@app.route("/<page_key>")
def placeholder(page_key):
    if page_key not in PLACEHOLDER_PAGES:
        return render_template("404.html"), 404
    return render_template("coming_soon.html", page_title=PLACEHOLDER_PAGES[page_key])


if __name__ == "__main__":
    app.run(debug=True)