# Bot Welcome & Auto-Reply Telegram

Bot sederhana yang otomatis:
1. Menyapa anggota baru saat mereka masuk ke grup.
2. Membalas dengan pesan/link promo setiap orang yang chat pribadi (DM) ke bot.

## Langkah Setup

1. **Buat bot di Telegram**
   - Chat `@BotFather` di Telegram
   - Ketik `/newbot`, ikuti instruksinya
   - Salin TOKEN yang diberikan (contoh: `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxx`)

2. **Install dependensi**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set token bot**
   ```bash
   export BOT_TOKEN="token_kamu_di_sini"
   ```
   Atau edit langsung variabel `BOT_TOKEN` di `bot.py`.

4. **Tambahkan bot ke grup**
   - Undang bot ke grupmu
   - Jadikan bot sebagai **admin** grup

5. **Matikan privacy mode** (WAJIB, kalau tidak bot tidak akan mendeteksi member baru)
   - Chat `@BotFather` → `/setprivacy` → pilih bot kamu → `Disable`

6. **Jalankan bot**
   ```bash
   python bot.py
   ```

## Kustomisasi Pesan

- **Pesan sambutan grup**: edit variabel `WELCOME_MESSAGE` di `bot.py`. Bisa pakai:
  - `{name}` → nama member baru
  - `{group}` → nama grup
- **Pesan balasan DM**: edit variabel `DM_REPLY_MESSAGE` di `bot.py`. Bisa pakai:
  - `{name}` → nama orang yang chat

## Catatan

- Bot ini pakai polling (terus menerus cek update), cocok untuk dijalankan di VPS/server pribadi atau service seperti Railway/Render.
- Jangan taruh token bot langsung di kode kalau mau upload ke GitHub — pakai environment variable.
