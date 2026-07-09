"""
Big Bang Basketball - email gonderim yardimcisi
---------------------------------------------------
Gmail SMTP uzerinden, App Password ile mail gonderiyor.
Gercek kimlik bilgileri .env dosyasinda (bkz. .env.example),
bu dosya icinde hiçbir sifre hardcoded degil.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _send(to_email: str, subject: str, body: str) -> bool:
    username = os.environ.get("MAIL_USERNAME")
    app_password = os.environ.get("MAIL_APP_PASSWORD")
    sender_name = os.environ.get("MAIL_SENDER_NAME", "Big Bang Basketball")

    if not username or not app_password:
        print("[mail] MAIL_USERNAME / MAIL_APP_PASSWORD .env'de tanimli degil, mail atlandi.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{username}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(username, app_password)
            server.sendmail(username, to_email, msg.as_string())
        return True
    except Exception as exc:
        print(f"[mail] Gonderim basarisiz: {exc}")
        return False


def send_welcome_email(to_email: str, first_name: str) -> bool:
    """Kayit basarili olunca oyuncuya hos geldin maili gonderir."""
    subject = "Big Bang Basketball'a Hoş Geldin! 🏀"
    body = f"""Selam {first_name},

Big Bang Basketball ailesine hoş geldin! Kaydın başarıyla tamamlandı.

Sahada görüşmek üzere — Where legends are born.

Saygılarımla,
Aykut
Big Bang Basketball Başkanı
#BigBangBasketball
"""
    return _send(to_email, subject, body)


def send_team_created_email(to_email: str, leader_first_name: str, team_name: str) -> bool:
    """Takim basariyla kurulunca takim liderine bilgilendirme maili gonderir."""
    subject = f"\"{team_name}\" Takımın Kuruldu! 🏆"
    body = f"""Selam {leader_first_name},

"{team_name}" takımı başarıyla kuruldu ve sen takım lideri olarak atandın!

Artık oyuncu kabul etme ve takımdan çıkarma yetkisine sahipsin. Takımının
en az 6 oyuncuya ulaşması gerektiğini unutma — Oyuncu Havuzu sayfasından
free agent oyuncuları davet edebilir, ya da onların sana katılma isteği
göndermesini bekleyebilirsin.

Sahada görüşmek üzere — Where legends are born.

Saygılarımla,
Big Bang Basketball Federasyonu
#BigBangBasketball
"""
    return _send(to_email, subject, body)


def send_join_request_email(to_email: str, leader_first_name: str, player_first_name: str,
                             player_last_name: str, team_name: str, jersey_number: int,
                             approve_url: str, reject_url: str) -> bool:
    """
    Bir oyuncu takima katilma istegi gonderdiginde, takim liderine
    onay/red linkleri iceren mail gonderir. Link 24 saat gecerli.
    """
    subject = f"{team_name} - Yeni Katılma İsteği: {player_first_name} {player_last_name}"
    body = f"""Selam {leader_first_name},

{player_first_name} {player_last_name}, "{team_name}" takımına katılmak için
istek gönderdi. Talep ettiği forma numarası: {jersey_number}

Bu isteği onaylamak için:
{approve_url}

Reddetmek için:
{reject_url}

Bu link 24 saat içinde geçerlidir. Süre dolarsa istek otomatik olarak
geçersiz hale gelir ve oyuncu tekrar istek göndermesi gerekir.

Saygılarımla,
Big Bang Basketball Federasyonu
#BigBangBasketball
"""
    return _send(to_email, subject, body)