# Big Bang Basketball — Website (v0.2: home + register + profile)

Stack: **Flask** (Python) + **HTML/CSS/JS** (Jinja2 templating) + **MySQL**

## Kurulum

```bash
cd bigbang_site
pip install -r requirements.txt
```

MySQL sunucunun çalışıyor olması gerekiyor (yerelde XAMPP/MAMP, Docker,
veya doğrudan kurulu `mysql`/`mariadb-server`).

`.env.example` dosyasını `.env` olarak kopyala ve kendi bilgilerinle doldur:

```bash
cp .env.example .env
```

`.env` içine girmen gerekenler:

- `SECRET_KEY` — Flask session'larını imzalamak için rastgele uzun bir string.
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — MySQL bağlantı bilgilerin.
- `MAIL_USERNAME` — `aykengur@gmail.com`
- `MAIL_APP_PASSWORD` — **Gmail normal şifresi DEĞİL.** Gmail hesabında
  2 adımlı doğrulamayı açtıktan sonra
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
  adresinden "Mail" için oluşturulan 16 haneli uygulama şifresi.

`.env` dosyası `.gitignore`'da, asla repoya gitmeyecek.

Veritabanı tabloları ilk çalıştırmada otomatik oluşturuluyor
(`db.init_db_if_needed()`, `schema.sql`'i okuyup uyguluyor). İstersen
elle de çalıştırabilirsin:

```bash
mysql -u root -p < schema.sql
```

## Çalıştırma

```bash
python app.py
```

Sonra **http://127.0.0.1:5000** adresine git.

## Şu an ne var

### Sayfalar
- **`/`** — ana sayfa (hero, istatistikler, hızlı linkler, turnuva formatı, Instagram).
- **`/register`** — kayıt formu: ad, soyad, email, şifre (+ tekrar), gün/ay/yıl
  doğum tarihi, ve sözleşme onay kutucuğu. Sözleşme linki yeni sekmede
  `/contract` sayfasını açar.
- **`/contract`** — katılımcı sözleşmesi: amaç (kâr amacı gütmeme), 2+ maç
  kaçırma tazminatı kuralı, sportmenlik maddesi, katılım bedeli, kişisel
  veri kullanımı.
- **`/profile`** — giriş yapmış oyuncunun bilgileri (ad, email, doğum tarihi,
  takım — şimdilik "henüz katılmadı", forma no — "henüz atanmadı"). Giriş
  yapılmamışsa otomatik `/register`'a yönlendirir.
- **`/logout`** — session'ı temizler, ana sayfaya döner.

### Kayıt akışı (uçtan uca)

1. Form gönderilir → sunucu tarafında validasyon (zorunlu alanlar, email
   formatı, şifre uzunluğu/eşleşmesi, geçerli tarih, sözleşme onayı).
2. Email zaten kayıtlı mı kontrol edilir (MySQL `UNIQUE` + ön kontrol).
3. Şifre **hash'lenerek** (`werkzeug.security.generate_password_hash`,
   asla düz metin) `players` tablosuna yazılır.
4. Flask **session** açılır (`session['player_id']`) — kullanıcı otomatik
   "giriş yapmış" olur.
5. `aykengur@gmail.com` adresinden (Gmail SMTP + App Password) oyuncuya
   hoş geldin maili gönderilir. Mail gönderimi başarısız olsa da kayıt
   işlemi geri alınmaz, sadece konsola log yazılır.
6. Kullanıcı başarı sayfasına yönlendirilir, oradan profiline geçer.
7. **Navbar'daki "Kayıt Ol" yazısı artık "Profilim" olur** (session kontrolü
   `base.html` içinde `session.get('player_id')` ile yapılıyor).

### Dosya yapısı

```
bigbang_site/
├── app.py              # Flask route'ları (home, register, contract, profile, logout, placeholder)
├── db.py                # MySQL bağlantısı + players tablosu sorguları
├── mailer.py            # Gmail SMTP üzerinden hoş geldin maili
├── schema.sql           # players, teams, matches, payments tabloları
├── requirements.txt
├── .env.example         # kopyalanıp .env yapılacak örnek ayar dosyası
├── .gitignore           # .env, __pycache__ vb. hariç tutuluyor
├── templates/
│   ├── base.html        # navbar (session-aware) + footer
│   ├── home.html
│   ├── register.html
│   ├── register_success.html
│   ├── contract.html
│   ├── profile.html
│   ├── coming_soon.html
│   └── 404.html
└── static/
    ├── css/style.css    # form-card, checkbox-group, contract-box stilleri eklendi
    ├── js/main.js
    └── img/logo.png
```

Navigasyondaki şu linkler hâlâ placeholder (`coming_soon.html`'e düşüyor):
`/create-team`, `/join-team`, `/player-pool`, `/fixtures`, `/payment`.

## Sıradaki adımlar (önerilen sıra)

1. `payment` — katılım bedeli ödeme akışı (Stripe entegrasyonu,
   shopatpartyhouse.com'daki gibi), `payments` tablosuna kayıt.
2. `create-team` / `join-team` — takım oluşturma ve katılma mantığı,
   `teams` tablosu ile `players.team_id` güncellemesi.
3. `player-pool` — takımı olmayan (`is_free_agent = TRUE`) oyuncuların listesi.
4. `fixtures` — maç takvimi + skorlar (`matches` tablosundan).
5. `profile` sayfasının takım adı, forma no ve istatistiklerle
   zenginleştirilmesi.
6. Giriş yapma (`/login`) sayfası — şu an sadece kayıt sırasında otomatik
   session açılıyor, ayrı bir login akışı henüz yok.

## Güvenlik notları

- Şifreler asla düz metin saklanmıyor, `werkzeug.security` ile hash'leniyor.
- `.env` dosyası git'e girmiyor — gerçek DB ve mail kimlik bilgileri
  sadece sunucunda/yerelinde duruyor.
- `SECRET_KEY` production'a çıkmadan önce `.env.example`'daki placeholder'dan
  değiştirilmeli.

## Renk paleti

| Renk | Hex |
|---|---|
| Lacivert | `#0C2340` |
| Turuncu | `#F58426` |
| Beyaz | `#FFFFFF` |
| Açık gri (arka plan) | `#F4F6F9` |

## Slogan

**"Where legends are born."**
