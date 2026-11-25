import os, json, datetime, io, tempfile, cv2, requests, numpy as np
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "9035064383:AAH61Rzyg92Vu814MXEHQkxi2G7ZC1NgfZM"
ADMIN_ID = 6871060318
DEVELOPER_USERNAME = "ziocw"
DB_FILE = "db.json"

# Sightengine - كشف خفيف بالـ API فقط
SIGHT_USER = "453102091"
SIGHT_SECRET = "NRGuEH8hRmXPRgZFcsGedoYi4sRPXLNs"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "groups": {}, "assistants": [], "force_sub": None}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

# ============ الكشف الخفيف ============
def check_media_ai(file_bytes):
    try:
        r = requests.post("https://api.sightengine.com/1.0/transform.json",
            data={
                "concepts": "nudity,gore,face-minor,violence,child",
                "api_user": SIGHT_USER,
                "api_secret": SIGHT_SECRET
            },
            files={"media": file_bytes}, timeout=20)
        d = r.json()
        print("AI:", d)

        # قيم من الـ API
        minor = d.get("face-minor", {}).get("prob", 0)
        child = d.get("child", {}).get("prob", 0)
        nudity = d.get("nudity", {})
        sa = nudity.get("sexual_activity", 0)
        sd = nudity.get("sexual_display", 0)
        er = nudity.get("erotica", 0)
        gore = d.get("gore", {}).get("prob", 0)
        violence = d.get("violence", {}).get("prob", 0)

        # 1 - اطفال اباحي او معنف - اخطر شي، حذف فوري
        if (minor > 0.5 or child > 0.5) and (sa > 0.25 or sd > 0.25 or er > 0.25 or gore > 0.3):
            return True, "طفل - اباحي / معنف"
        if (minor > 0.6 or child > 0.6) and violence > 0.4:
            return True, "طفل - عنف"

        # 2 - اباحي
        if sa > 0.5:
            return True, "اباحي"
        if sd > 0.6:
            return True, "عرض جنسي"
        if er > 0.6:
            return True, "اباحي"

        # 3 - عنف / دم
        if gore > 0.55:
            return True, "عنف / دم"
        if violence > 0.6:
            return True, "عنف"

        return False, "clean"
    except Exception as e:
        print("AI Error:", e)
        return False, "error"

def check_video_ai(file_path, max_frames=8):
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return False, "cannot_open", 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    positions = list(range(0, total, int(fps) or 30))
    if total > 0:
        positions.append(total // 2)
        positions.append(max(0, total - 5))
    positions = sorted(set(positions))
    if len(positions) > max_frames:
        idxs = np.linspace(0, len(positions)-1, max_frames).astype(int)
        positions = [positions[i] for i in idxs]
    for i, pos in enumerate(positions):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if not ret: continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="JPEG", quality=80)
        is_bad, reason = check_media_ai(buf.getvalue())
        sec = pos / fps if fps else 0
        if is_bad:
            cap.release()
            return True, f"{reason} - الثانية {sec:.1f}", i+1
    cap.release()
    return False, "clean", 0

# ============ ادارة ============
async def is_admin_or_assistant(uid):
    return uid == ADMIN_ID or uid in db["assistants"]

def is_group_enabled(cid):
    g = db["groups"].get(str(cid))
    return True if not g else g.get("ai_enabled", True)

async def check_force_sub(uid, context):
    ch = db.get("force_sub")
    if not ch: return True
    try:
        m = await context.bot.get_chat_member(ch, uid)
        return m.status in ["member", "administrator", "creator"]
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    is_new = uid not in db["users"]
    db["users"][uid] = {"name": user.full_name, "username": user.username, "id": user.id}
    save_db(db)
    if is_new:
        try:
            await context.bot.send_message(ADMIN_ID, f"👤 مستخدم جديد\n• الاسم: {user.full_name}\n• اليوزر: @{user.username or 'لا يوجد'}\n• الايدي: `{user.id}`")
        except: pass
    if not await check_force_sub(user.id, context):
        ch = db["force_sub"]
        kb = [[InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{ch.replace('@','')}")],[InlineKeyboardButton("✅ تحققت", callback_data="check_sub")]]
        await update.message.reply_text("⚠️ اشترك بالقناة اولا", reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = [[InlineKeyboardButton("➕ اضفني لمجموعتك", url=f"https://t.me/{context.bot.username}?startgroup=new")],[InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{DEVELOPER_USERNAME}")]]
    if await is_admin_or_assistant(user.id):
        kb.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="panel")])
    kb.append([InlineKeyboardButton("🛡️ اضافة مشرف", callback_data="add_admin_menu")])
    await update.message.reply_text("هلا بيك 👋\n\n• بوت كشف خفيف\n• يكشف: اباحي - عنف - اطفال اباحي / معنف", reply_markup=InlineKeyboardMarkup(kb))

async def toggle_ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("❌ داخل المجموعة فقط"); return
    allowed = user.id == ADMIN_ID or user.id in db["assistants"]
    if not allowed:
        try:
            m = await context.bot.get_chat_member(chat.id, user.id)
            if m.status == "creator": allowed = True
        except: pass
    if not allowed:
        await update.message.reply_text("❌ للادمن فقط"); return
    gid = str(chat.id)
    if gid not in db["groups"]:
        db["groups"][gid] = {"title": chat.title, "owner_id": user.id, "ai_enabled": True}
    cmd = update.message.text.split()[0].lower()
    if cmd == "/on":
        db["groups"][gid]["ai_enabled"] = True; msg = "✅ تم تشغيل الكاشف"
    elif cmd == "/off":
        db["groups"][gid]["ai_enabled"] = False; msg = "⛔ تم اطفاء الكاشف"
    else:
        cur = db["groups"][gid].get("ai_enabled", True)
        db["groups"][gid]["ai_enabled"] = not cur
        msg = "✅ تم التشغيل" if not cur else "⛔ تم الاطفاء"
    save_db(db); await update.message.reply_text(msg)

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; user = q.from_user
    if not await is_admin_or_assistant(user.id):
        await q.answer("للادمن فقط", show_alert=True); return
    kb = [[InlineKeyboardButton("📊 الاحصائيات", callback_data="stats")],[InlineKeyboardButton("👥 المجموعات", callback_data="groups")]]
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("📢 الاشتراك الاجباري", callback_data="force_sub_menu")])
        kb.append([InlineKeyboardButton("➕ اضافة مساعد", callback_data="add_assistant")])
    kb.append([InlineKeyboardButton("🛡️ اضافة مشرف", callback_data="add_admin_menu")])
    await q.edit_message_text("⚙️ لوحة التحكم:", reply_markup=InlineKeyboardMarkup(kb))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; data = q.data; user = q.from_user
    if data == "panel": await panel(update, context); return
    if data == "check_sub":
        if await check_force_sub(user.id, context):
            await q.answer("تم التحقق ✅", show_alert=True); await q.message.delete(); await start(update, context)
        else: await q.answer("❌ لم تشترك بعد!", show_alert=True)
        return
    if data == "stats":
        await q.edit_message_text(f"📊 الاحصائيات:\n\n• المستخدمين: {len(db['users'])}\n• المجموعات: {len(db['groups'])}\n• المساعدين: {len(db['assistants'])}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]])); return
    if data == "groups":
        if not db["groups"]:
            await q.edit_message_text("لا توجد مجموعات", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]])); return
        kb = []
        for gid, info in db["groups"].items():
            st = "✅" if info.get("ai_enabled", True) else "⛔"
            kb.append([InlineKeyboardButton(f"{st} {info['title']}", callback_data="noop"), InlineKeyboardButton("تشغيل/اطفاء", callback_data=f"toggle_{gid}"), InlineKeyboardButton("🚪 مغادرة", callback_data=f"leave_{gid}")])
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="panel")])
        await q.edit_message_text("👥 المجموعات:", reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("toggle_"):
        gid = data.replace("toggle_", "")
        if gid in db["groups"]:
            cur = db["groups"][gid].get("ai_enabled", True); db["groups"][gid]["ai_enabled"] = not cur; save_db(db)
            await q.answer("تم التشغيل ✅" if not cur else "تم الاطفاء ⛔")
            q.data = "groups"; await callbacks(update, context)
        return
    if data.startswith("leave_"):
        gid = data.split("_")[1]
        try: await context.bot.leave_chat(int(gid))
        except: pass
        db["groups"].pop(gid, None); save_db(db); await q.answer("تمت المغادرة"); await panel(update, context); return
    if data == "force_sub_menu":
        await q.edit_message_text(f"📢 القناة الحالية: {db.get('force_sub') or 'لا توجد'}\n\nارسل يوزر القناة: @channel", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="panel")]]))
        context.user_data["waiting"] = "force_sub"; return
    if data == "add_assistant":
        if user.id != ADMIN_ID: await q.answer("للمالك فقط", show_alert=True); return
        await q.edit_message_text("ارسل يوزر او ايدي المساعد:"); context.user_data["waiting"] = "add_assistant"; return
    if data == "add_admin_menu":
        my = list(db["groups"].items()) if (user.id == ADMIN_ID or user.id in db["assistants"]) else [(g,i) for g,i in db["groups"].items() if i.get("owner_id")==user.id]
        if not my: await q.answer("ليس لديك مجموعة", show_alert=True); return
        kb = [[InlineKeyboardButton(f"🛡️ {info['title']}", callback_data=f"pick_group_{gid}")] for gid, info in my]
        await q.edit_message_text("اختر المجموعة:", reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("pick_group_"):
        context.user_data["target_group"] = data.split("_")[2]; context.user_data["waiting"] = "add_group_admin"
        await q.edit_message_text("ارسل يوزر المستخدم: @username"); return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; waiting = context.user_data.get("waiting"); text = update.message.text.strip()
    if not waiting: return
    if waiting == "force_sub" and user.id == ADMIN_ID:
        db["force_sub"] = None if text == "/off" else (text if text.startswith("@") else f"@{text}"); save_db(db); context.user_data["waiting"]=None; await update.message.reply_text(f"✅ تم التحديث: {db['force_sub']}"); return
    if waiting == "add_assistant" and user.id == ADMIN_ID:
        try:
            t = await context.bot.get_chat(text)
            if t.id not in db["assistants"]: db["assistants"].append(t.id); save_db(db)
            context.user_data["waiting"]=None; await update.message.reply_text(f"✅ تم اضافة المساعد: {t.full_name}")
        except: await update.message.reply_text("❌ لم اجد المستخدم")
        return
    if waiting == "add_group_admin":
        gid = context.user_data.get("target_group"); info = db["groups"].get(str(gid))
        if not (user.id==ADMIN_ID or user.id in db["assistants"] or (info and info.get("owner_id")==user.id)): await update.message.reply_text("❌ ليس لديك صلاحية"); return
        try:
            t = await context.bot.get_chat(text)
            await context.bot.promote_chat_member(int(gid), t.id, can_send_messages=True, can_delete_messages=True, can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False, can_pin_messages=False)
            context.user_data["waiting"]=None; await update.message.reply_text(f"✅ تم رفع {t.full_name} مشرف")
        except Exception as e: await update.message.reply_text(f"❌ فشل: {e}")
        return

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        if m.id == context.bot.id:
            chat = update.effective_chat; owner_id=None
            try:
                admins = await context.bot.get_chat_administrators(chat.id)
                for a in admins:
                    if a.status=="creator": owner_id=a.user.id
            except: pass
            db["groups"][str(chat.id)] = {"title": chat.title, "link": chat.invite_link or "خاص", "owner_id": owner_id, "ai_enabled": True}; save_db(db)

async def check_group_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    if msg.chat.type in ["group","supergroup"] and not is_group_enabled(msg.chat.id): return
    file_id=None; file_type="photo"
    if msg.photo: file_id=msg.photo[-1].file_id; file_type="photo"
    elif msg.sticker: file_id=msg.sticker.file_id; file_type="sticker"
    elif msg.animation: file_id=msg.animation.file_id; file_type="gif"
    elif msg.video: file_id=msg.video.file_id; file_type="video"
    elif msg.video_note: file_id=msg.video_note.file_id; file_type="video"
    elif msg.document and msg.document.mime_type and "video" in msg.document.mime_type: file_id=msg.document.file_id; file_type="video"
    if not file_id: return
    f = await context.bot.get_file(file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp: tmp_path=tmp.name
    await f.download_to_drive(tmp_path)
    is_bad=False; reason="clean"
    try:
        if file_type in ["video","gif"]:
            is_bad, reason, _ = check_video_ai(tmp_path, max_frames=8)
            if not is_bad:
                with open(tmp_path,"rb") as fh: is_bad, reason = check_media_ai(fh.read())
        else:
            with open(tmp_path,"rb") as fh: is_bad, reason = check_media_ai(fh.read())
    finally:
        try: os.remove(tmp_path)
        except: pass
    if msg.chat.type=="private":
        await msg.reply_text(f"🚨 ممنوع - {reason}" if is_bad else "✅ المحتوى نظيف"); return
    if not is_bad: return
    user=msg.from_user; chat=msg.chat
    try: await msg.delete()
    except: pass
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status=="administrator":
            await context.bot.promote_chat_member(chat.id, user.id, can_send_messages=False, can_delete_messages=False, can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False, can_pin_messages=False)
    except: pass
    try: await context.bot.restrict_chat_member(chat.id, user.id, ChatPermissions(can_send_messages=False))
    except: pass
    owner_id = db["groups"].get(str(chat.id), {}).get("owner_id")
    notif = f"🚨 تحذير\n• المستخدم: {user.full_name}\n• اليوزر: @{user.username or 'لا يوجد'}\n• الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n• المجموعة: {chat.title}\n• النوع: {file_type}\n• السبب: {reason}"
    if owner_id:
        try: await context.bot.send_message(owner_id, notif)
        except: pass
    try: await context.bot.send_message(ADMIN_ID, notif)
    except: pass
    try: await context.bot.send_message(chat.id, f"🚫 تم حذف محتوى ممنوع من {user.full_name}")
    except: pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["on","off","toggle"], toggle_ai_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Sticker.ALL | filters.ANIMATION | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO, check_group_media))
    print("Bot Running...")
    app.run_polling()
if __name__ == "__main__": main()
