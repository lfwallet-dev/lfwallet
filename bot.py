"""
Bot Telegram - Auto Welcome, Auto Reply DM & Force-Join Gate
====================================
Bot ini akan otomatis:
1. Menyapa setiap anggota baru yang bergabung ke grup Telegram kamu.
2. Membalas dengan link promo setiap orang yang chat pribadi (DM) ke bot —
   TAPI mengecek dulu apakah orang tersebut sudah join semua grup/channel
   yang diwajibkan (lihat REQUIRED_CHANNELS di bawah).

Library yang dipakai: python-telegram-bot (versi 20+)
Install dulu dengan:
    pip install python-telegram-bot --upgrade

Cara pakai:
1. Buat bot baru lewat @BotFather di Telegram, lalu salin TOKEN-nya.
2. Isi TOKEN di bawah (variabel BOT_TOKEN) atau lewat environment variable.
3. Tambahkan bot ke grup kamu, jadikan admin (minimal punya izin baca pesan).
4. Matikan privacy mode bot lewat @BotFather -> /setprivacy -> Disable,
   supaya bot bisa mendeteksi event anggota baru masuk.
5. PENTING untuk fitur force-join: tambahkan bot sebagai ADMIN di SETIAP
   grup/channel yang ada di REQUIRED_CHANNELS. Kalau bot bukan admin di
   sana, Telegram akan menolak permintaan cek keanggotaan, dan bot akan
   selalu menganggap user belum join channel tersebut.
6. Jalankan: python bot.py
"""

import logging
import os
from telegram import Update, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ------------------------------------------------------------------
# KONFIGURASI
# ------------------------------------------------------------------

# Cara paling aman: set token lewat environment variable.
# export BOT_TOKEN="123456:ABC-DEF..."
BOT_TOKEN = os.environ.get("BOT_TOKEN", "MASUKKAN_TOKEN_BOT_DI_SINI")

# Customize the welcome message here.
# {name} is automatically replaced with the new member's name.
# {group} is automatically replaced with the group's name.
WELCOME_MESSAGE = (
    "👋 Welcome, {name}!\n\n"
    "Thanks for joining {group}.\n"
    "Check the pinned message for info & group rules 🙏\n\n"
    "🚨 LF Wallet Airdrop is LIVE\n"
    "500 $LW. Up to 1,200 $LW per referral."
)

# Text + URL for the buttons attached to the welcome & DM messages.
MENU_BUTTON_1_TEXT = "🚀 LF Wallet"
MENU_BUTTON_1_URL = "https://t.me/LFWallet_AirdropBot?start=ref8994710600"

MENU_BUTTON_2_TEXT = "🐶 DoggieZen"
MENU_BUTTON_2_URL = "https://t.me/doggiezenbot/DoggieZen?startapp=4UQKTU8"

# Message automatically sent when someone sends a private message (DM) to the bot.
DM_REPLY_MESSAGE = (
    "👋 Hi {name}!\n\n"
    "🚨 LF Wallet Airdrop is LIVE\n\n"
    "500 $LW.\n"
    "Up to 1,200 $LW per referral.\n\n"
    "Tap the button below 👇"
)

# Grup/channel yang WAJIB di-join dulu sebelum bot membalas dengan link menu.
# "username" harus tanpa @ dan tanpa https://t.me/ (dipakai untuk cek keanggotaan).
# PENTING: bot harus dijadikan ADMIN di setiap grup/channel ini, kalau tidak
# Telegram tidak akan mengizinkan bot mengecek status keanggotaan.
REQUIRED_CHANNELS = [
    {"name": "LF Wallets", "username": "LFWallets"},
    {"name": "LF Wallet Airdrop", "username": "LFWalletAirdrop"},
    {"name": "LF Wallet Airdrop 2", "username": "LF_WalletAirdrop"},
]

# Pesan yang dikirim kalau user BELUM join semua grup/channel di atas.
NOT_JOINED_MESSAGE = (
    "🔒 Please join all the groups/channels below first, then tap "
    "\"✅ I've Joined\" to continue."
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# HANDLER
# ------------------------------------------------------------------

def extract_status_change(chat_member_update: ChatMemberUpdated):
    """Mengecek apakah update ini benar-benar 'member baru masuk'."""
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in ("member", "administrator", "creator") or (
        old_status == "restricted" and old_is_member is True
    )
    is_member = new_status in ("member", "administrator", "creator") or (
        new_status == "restricted" and new_is_member is True
    )

    return was_member, is_member


def build_menu_keyboard():
    """Membuat keyboard dengan dua tombol menu link (LF Wallet & DoggieZen)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(MENU_BUTTON_1_TEXT, url=MENU_BUTTON_1_URL)],
            [InlineKeyboardButton(MENU_BUTTON_2_TEXT, url=MENU_BUTTON_2_URL)],
        ]
    )


async def get_not_joined_channels(bot, user_id: int):
    """Mengecek satu-satu channel di REQUIRED_CHANNELS, kembalikan yang BELUM di-join."""
    not_joined = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel['username']}", user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(channel)
        except TelegramError as e:
            # Kalau bot bukan admin di channel tsb, Telegram akan menolak pengecekan.
            logger.warning(
                f"Tidak bisa mengecek member di @{channel['username']}: {e}. "
                "Pastikan bot sudah jadi admin di channel/grup tersebut."
            )
            not_joined.append(channel)
    return not_joined


def build_join_keyboard(not_joined_channels):
    """Membuat keyboard berisi tombol join tiap channel + tombol cek ulang."""
    buttons = [
        [InlineKeyboardButton(f"➕ Join {c['name']}", url=f"https://t.me/{c['username']}")]
        for c in not_joined_channels
    ]
    buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_join")])
    return InlineKeyboardMarkup(buttons)


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil setiap ada perubahan status member di grup."""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result

    # Hanya kirim sambutan kalau sebelumnya BUKAN member, sekarang JADI member
    if not was_member and is_member:
        member = update.chat_member.new_chat_member.user
        chat = update.chat_member.chat

        name = member.full_name or member.first_name or "Sobat"
        text = WELCOME_MESSAGE.format(name=name, group=chat.title or "grup ini")

        await context.bot.send_message(
            chat_id=chat.id, text=text, reply_markup=build_menu_keyboard()
        )
        logger.info(f"Menyapa member baru: {name} di grup {chat.title}")


async def reply_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil setiap ada orang mengirim pesan pribadi (DM) ke bot."""
    user = update.effective_user
    name = user.full_name or user.first_name or "Sobat"

    not_joined = await get_not_joined_channels(context.bot, user.id)
    if not_joined:
        await update.message.reply_text(
            NOT_JOINED_MESSAGE, reply_markup=build_join_keyboard(not_joined)
        )
        logger.info(f"{name} ({user.id}) belum join semua grup, diminta join dulu.")
        return

    text = DM_REPLY_MESSAGE.format(name=name)
    await update.message.reply_text(text, reply_markup=build_menu_keyboard())
    logger.info(f"Membalas DM dari: {name} ({user.id})")


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil saat user menekan tombol '✅ I've Joined'."""
    query = update.callback_query
    user = query.from_user
    name = user.full_name or user.first_name or "Sobat"

    await query.answer()  # menghilangkan loading spinner di tombol

    not_joined = await get_not_joined_channels(context.bot, user.id)
    if not_joined:
        await query.answer(
            "❌ You haven't joined all groups/channels yet.", show_alert=True
        )
        await query.edit_message_reply_markup(reply_markup=build_join_keyboard(not_joined))
        return

    text = DM_REPLY_MESSAGE.format(name=name)
    await query.edit_message_text(text, reply_markup=build_menu_keyboard())
    logger.info(f"{name} ({user.id}) sudah join semua grup, menu link dikirim.")


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    if BOT_TOKEN == "MASUKKAN_TOKEN_BOT_DI_SINI":
        print("⚠️  Token bot belum diisi. Set environment variable BOT_TOKEN")
        print('    atau edit langsung variabel BOT_TOKEN di file ini.')
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # ChatMemberHandler mendeteksi perubahan status member (masuk/keluar/dipromosikan, dll)
    app.add_handler(
        ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER)
    )

    # Membalas otomatis saat orang pertama kali menekan tombol "Start" (perintah /start)
    app.add_handler(CommandHandler("start", reply_dm))

    # Membalas otomatis setiap pesan yang dikirim langsung (private chat) ke bot
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, reply_dm)
    )

    # Menangani tombol "✅ I've Joined" untuk cek ulang keanggotaan grup
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))

    print("🤖 Bot berjalan... tekan Ctrl+C untuk berhenti.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
