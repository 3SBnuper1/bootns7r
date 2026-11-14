from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button
from pyrogram.errors import PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid, UserNotParticipant, ChatWriteForbidden
import os
os.system("pip install pyrolistener")
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop
from datetime import datetime, timedelta
from pytz import timezone
import json

# ===== بياناتك هنا داخل الملف =====
API_ID = 9661697
API_HASH = "4ae76784fdfecd5df142004955bb8393"
BOT_TOKEN = "9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8"
OWNER = 5723475089
# ===================================

app = Client("autoPost", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
loop = get_event_loop()
listener = Listener(client=app)

def write(fp, data):
    with open(fp, "w") as f: json.dump(data, f, indent=2)
def read(fp, default):
    if not os.path.exists(fp): write(fp, default)
    with open(fp) as f: return json.load(f)

users_db = "users.json"
channels_db = "channels.json"
users = read(users_db, {})
channels = read(channels_db, [])

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"vip": False, "accounts": {}, "current": None, "mode": "separate"}
    if "accounts" not in users[uid]: users[uid]["accounts"] = {}
    if "mode" not in users[uid]: users[uid]["mode"] = "separate"
    return users[uid]

def get_acc(uid):
    u = get_user(uid)
    cur = u.get("current")
    if not cur or cur not in u["accounts"]: return None, None, u
    return cur, u["accounts"][cur], u

def get_mode(uid):
    return get_user(uid).get("mode", "separate")

def get_groups_for_posting(uid, acc_id):
    u = get_user(uid)
    if get_mode(uid) == "all":
        all_groups = []
        for a in u["accounts"].values():
            for g in a.get("groups", []):
                if g not in all_groups: all_groups.append(g)
        return all_groups
    return u["accounts"][acc_id].get("groups", [])

def home_markup():
    return Markup([
        [Button("- حساباتي -", callback_data="myAccounts")],
        [Button("- حسابك -", callback_data="account")],
        [Button("- السوبرات الحاليه -", callback_data="currentSupers"), Button("- إضافة سوبر -", callback_data="newSuper")],
        [Button("- تعيين المدة بين كل نشر -", callback_data="waitTime"), Button("- تعيين كليشة النشر -", callback_data="newCaption")],
        [Button("- ايقاف النشر -", callback_data="stopPosting"), Button("- بدء النشر -", callback_data="startPosting")],
        [Button("🚀 تشغيل الكل بنفس الوقت", callback_data="startAll")],
        [Button("🛑 ايقاف الكل", callback_data="stopAll")],
        [Button("🔀 وضع النشر: كلمن وحده / الكل بكل الكروبات", callback_data="changeMode")],
    ])

async def subscription(message: Message):
    for channel in channels:
        try: await app.get_chat_member(channel, message.from_user.id)
        except UserNotParticipant: return channel
    return True

@app.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    uid = message.from_user.id
    sub = await subscription(message)
    u = get_user(uid)
    if uid == OWNER: u["vip"] = True
    if isinstance(sub, str):
        return await message.reply(f"- عليك الاشتراك بقناة البوت اولا\n- القناه: @{sub}\n- اشترك ثم ارسل /start")
    if not u["vip"]:
        return await message.reply(f"لا يمكنك استخدام البوت تواصل مع [المطور](tg://openmessage?user_id={OWNER}) لتفعيل الاشتراك")
    await message.reply(f"- مرحبا بك عزيزي {message.from_user.first_name} في بوت النشر التلقائي\n\n- اختار حساب من - حساباتي - حتى تتحكم بيه وحده\n- تحكم في البوت من الازرار التاليه:", reply_markup=home_markup())

@app.on_callback_query(filters.regex(r"^toHome$"))
async def toHome(_, cb: CallbackQuery):
    await cb.message.edit_text("- القائمة الرئيسية:", reply_markup=home_markup())

# ===== الحسابات =====
@app.on_callback_query(filters.regex(r"^myAccounts$"))
async def myAccounts(_, cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    btns = []
    for acc_id, acc in u["accounts"].items():
        status = "🟢 شغال" if acc.get("posting") else "🔴 واقف"
        btns.append([Button(f"{acc.get('name', acc_id)} - {status}", callback_data=f"selectAcc {acc_id}")])
    btns.append([Button("- اضافة حساب جديد -", callback_data="login")])
    btns.append([Button("- الرئيسية -", callback_data="toHome")])
    await cb.message.edit_text("حساباتك:\nاضغط على حساب حتى تتحكم بيه وحده", reply_markup=Markup(btns))

@app.on_callback_query(filters.regex(r"^selectAcc "))
async def selectAcc(_, cb: CallbackQuery):
    acc_id = cb.data.split()[1]
    u = get_user(cb.from_user.id)
    u["current"] = acc_id
    write(users_db, users)
    acc = u["accounts"][acc_id]
    await cb.message.edit_text(f"تم اختيار الحساب: {acc.get('name', acc_id)}\nالسوبرات: {len(acc.get('groups', []))}\nالكليشة: {acc.get('caption', 'مو مضبوطة')}\nالانتظار: {acc.get('waitTime', 60)} ثانية", reply_markup=home_markup())

@app.on_callback_query(filters.regex(r"^account$"))
async def account(_, cb: CallbackQuery):
    await cb.message.edit_text("- استخدم الازرار للتحكم بحسابك:", reply_markup=Markup([
        [Button("- تسجيل حساب جديد -", callback_data="login"), Button("- تغيير الحساب الحالي -", callback_data="myAccounts")],
        [Button("- العوده -", callback_data="toHome")]
    ]))

@app.on_callback_query(filters.regex(r"^(login)$"))
async def login(_, cb: CallbackQuery):
    uid = cb.from_user.id
    await cb.message.delete()
    try:
        ask = await listener.listen(from_id=uid, chat_id=uid, text="- أرسل رقم الهاتف الخاص بك:\n- يمكنك ارسال /cancel لإلغاء التسجيل.", reply_markup=ForceReply(selective=True, placeholder="+9647700000"), timeout=30)
    except exceptions.TimeOut:
        return await app.send_message(uid, "- نفد وقت استلام رقم الهاتف")
    if ask.text == "/cancel": return await ask.reply("- تم إلغاء العمليه.")
    create_task(registration(ask))

async def registration(message: Message):
    uid = message.from_user.id
    number = message.text
    lmsg = await message.reply("- جارٍ تسجيل الدخول إلى حسابك")
    client = Client("registration", in_memory=True, api_id=API_ID, api_hash=API_HASH)
    await client.connect()
    try: p_code_hash = await client.send_code(number)
    except PhoneNumberInvalid: return await lmsg.edit_text("- رقم الهاتف خاطئ")
    try:
        code = await listener.listen(from_id=uid, chat_id=uid, text="- تم ارسال كود إلى خاصك قم بإرساله.", timeout=120, reply_markup=ForceReply(selective=True, placeholder="1 2 3 4 5"))
    except exceptions.TimeOut: return await lmsg.reply("- نفذ وقت استلام الكود.")
    try: await client.sign_in(number, p_code_hash.phone_code_hash, code.text.replace(" ", ""))
    except PhoneCodeInvalid: return await code.reply("- كود خاطئ")
    except PhoneCodeExpired: return await code.reply("- الكود منتهي")
    except SessionPasswordNeeded:
        try: password = await listener.listen(from_id=uid, chat_id=uid, text="- ادخل كلمة مرور التحقق بخطوتين.", reply_markup=ForceReply(selective=True), timeout=180)
        except exceptions.TimeOut: return await lmsg.reply("- نفذ وقت كلمة المرور")
        try: await client.check_password(password.text)
        except PasswordHashInvalid: return await password.reply("- كلمة مرور خاطئه")
    session = await client.export_session_string()
    me = await client.get_me()
    await client.disconnect()
    u = get_user(uid)
    acc_id = str(me.id)
    u["accounts"][acc_id] = {"session": session, "name": f"{me.first_name} ({me.id})", "groups": [], "caption": "", "waitTime": 60, "posting": False}
    u["current"] = acc_id
    write(users_db, users)
    await app.send_message(uid, "- تم تسجيل الدخول، وهذا الحساب صار الحالي.\n- الان كل شي تسويه راح يطبق على هذا الحساب فقط.", reply_markup=Markup([[Button("الصفحه الرئيسيه", callback_data="toHome")]]))

# ===== السوبرات + فحص موجود بالكروب =====
@app.on_callback_query(filters.regex(r"^newSuper$"))
async def newSuper(_, cb: CallbackQuery):
    uid = cb.from_user.id
    acc_id, acc, u = get_acc(uid)
    if not acc: return await cb.answer("اختار حساب اولاً من - حساباتي -", show_alert=True)
    await cb.message.delete()
    try: ask = await listener.listen(from_id=uid, chat_id=uid, text=f"- ارسل رابط السوبر لإضافته للحساب {acc.get('name')} فقط.\n- يمكنك ارسال /cancel للالغاء.", reply_markup=ForceReply(selective=True), timeout=60)
    except exceptions.TimeOut: return await app.send_message(uid, "نفذ وقت استلام الرابط")
    if ask.text == "/cancel": return await ask.reply("- تم إلغاء العمليه")
    try: chat = await app.get_chat(ask.text if "+" in ask.text else ask.text.split("/")[-1])
    except Exception: return await ask.reply("- لم يتم ايجاد السوبر.")
    if chat.id in acc.get("groups", []):
        return await ask.reply(f"- ⚠️ هذا الحساب موجود بهذا الكروب already\n- الكروب: {chat.title}\n- الحساب: {acc.get('name')}", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))
    try:
        client = Client(f"check_{acc_id}", api_id=API_ID, api_hash=API_HASH, session_string=acc["session"])
        await client.start()
        try:
            await client.get_chat_member(chat.id, "me")
            is_member = True
        except UserNotParticipant: is_member = False
        except Exception: is_member = False
        await client.stop()
        if is_member:
            return await ask.reply(f"- ⚠️ يابه تره هذا الحساب موجود بهذا الكروب\n- الكروب: {chat.title}\n- الحساب: {acc.get('name')}\n\nتبقى تريد اضيفه لقائمة النشر لو لا؟", reply_markup=Markup([[Button("✅ اي ضيفه", callback_data=f"forceAdd {chat.id}")],[Button("❌ لا تلغيه", callback_data="toHome")]]))
    except Exception: pass
    acc["groups"].append(chat.id)
    write(users_db, users)
    await ask.reply(f"- تمت اضافة السوبر الى الحساب {acc.get('name')} فقط.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^forceAdd "))
async def force_add(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    group = int(cb.data.split()[1])
    if group not in acc["groups"]:
        acc["groups"].append(group)
        write(users_db, users)
    await cb.message.edit_text("- تمت اضافته لقائمة النشر رغم انه موجود بالكروب.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^currentSupers$"))
async def currentSupers(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    if not acc: return await cb.answer("اختار حساب اولاً", show_alert=True)
    if not acc.get("groups"): return await cb.answer("- لم يتم إضافة اي سوبر لهذا الحساب", show_alert=True)
    markup = []
    for group in acc["groups"]:
        try: title = (await app.get_chat(group)).title
        except: title = str(group)
        markup.append([Button(title, callback_data="none"), Button("🗑", callback_data=f"delSuper {group}")])
    markup.append([Button("- الصفحه الرئيسيه -", callback_data="toHome")])
    await cb.message.edit_text(f"- سوبرات الحساب: {acc.get('name')}", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^delSuper"))
async def delSuper(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    group = int(cb.data.split()[1])
    if group in acc["groups"]: acc["groups"].remove(group)
    write(users_db, users)
    await cb.answer("- تم حذف السوبر من هذا الحساب فقط", show_alert=True)

# ===== كليشة خاصة بكل حساب =====
@app.on_callback_query(filters.regex(r"^newCaption$"))
async def newCaption(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    if not acc: return await cb.answer("اختار حساب اولاً", show_alert=True)
    await cb.message.delete()
    try: ask = await listener.listen(from_id=cb.from_user.id, chat_id=cb.from_user.id, text=f"ارسل الكليشة الجديدة للحساب: {acc.get('name')}\nهاي الكليشة راح تنشر بهذا الحساب فقط.", reply_markup=ForceReply(selective=True), timeout=120)
    except exceptions.TimeOut: return await app.send_message(cb.from_user.id, "- انتهى الوقت")
    acc["caption"] = ask.text
    write(users_db, users)
    await ask.reply(f"تم حفظ الكليشة للحساب {acc.get('name')} فقط ✅\n\nنصها:\n{ask.text}", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^waitTime$"))
async def waitTime(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    if not acc: return await cb.answer("اختار حساب اولاً", show_alert=True)
    await cb.message.delete()
    try: ask = await listener.listen(from_id=cb.from_user.id, chat_id=cb.from_user.id, text="- ارسل مدة الانتظار بالثواني لهذا الحساب فقط.", reply_markup=ForceReply(selective=True), timeout=120)
    except exceptions.TimeOut: return await app.send_message(cb.from_user.id, "- انتهى الوقت")
    try: acc["waitTime"] = int(ask.text)
    except: return await ask.reply("- الرقم غلط")
    write(users_db, users)
    await ask.reply("- تم تعيين مدة الانتظار لهذا الحساب فقط.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

# ===== وضع النشر =====
@app.on_callback_query(filters.regex(r"^changeMode$"))
async def change_mode(_, cb: CallbackQuery):
    current = get_mode(cb.from_user.id)
    await cb.message.edit_text(f"وضع النشر الحالي: {'🔀 الكل بكل الكروبات' if current == 'all' else '👤 كلمن وحده'}\n\nاختار الوضع اللي تريده:", reply_markup=Markup([
        [Button("👤 كلمن وحده - كل حساب بسوبراته", callback_data="setMode separate")],
        [Button("🔀 الكل بكل الكروبات - كل حساب بكل الكروبات", callback_data="setMode all")],
        [Button("- الصفحه الرئيسيه -", callback_data="toHome")]
    ]))

@app.on_callback_query(filters.regex(r"^setMode "))
async def set_mode(_, cb: CallbackQuery):
    mode = cb.data.split()[1]
    u = get_user(cb.from_user.id)
    u["mode"] = mode
    write(users_db, users)
    await cb.answer("تم تفعيل وضع: الكل بكل الكروبات ✅" if mode == "all" else "تم تفعيل وضع: كلمن وحده ✅", show_alert=True)
    await cb.message.edit_text("- تم تغيير الوضع بنجاح", reply_markup=home_markup())

# ===== النشر =====
@app.on_callback_query(filters.regex(r"^startPosting$"))
async def startPosting(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    if not acc: return await cb.answer("اختار حساب اولاً", show_alert=True)
    if acc.get("posting"): return await cb.answer("هذا الحساب ينشر already", show_alert=True)
    if not acc.get("groups"): return await cb.answer("ضيف سوبر لهذا الحساب اولاً", show_alert=True)
    acc["posting"] = True
    write(users_db, users)
    create_task(posting(cb.from_user.id, acc_id))
    await cb.message.edit_text("- بدأت عملية النشر لهذا الحساب فقط", reply_markup=Markup([[Button("- إيقاف النشر -", callback_data="stopPosting"), Button("- عوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^stopPosting$"))
async def stopPosting(_, cb: CallbackQuery):
    acc_id, acc, u = get_acc(cb.from_user.id)
    if not acc: return await cb.answer("اختار حساب اولاً", show_alert=True)
    acc["posting"] = False
    write(users_db, users)
    await cb.message.edit_text("- تم ايقاف النشر لهذا الحساب فقط", reply_markup=Markup([[Button("- بدء النشر -", callback_data="startPosting"), Button("- عوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^startAll$"))
async def start_all(_, cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    started = 0
    delay_between = 10
    current_delay = 0
    for acc_id, acc in u["accounts"].items():
        if acc.get("posting"): continue
        if not acc.get("groups") or not acc.get("caption"): continue
        acc["posting"] = True
        create_task(posting_delayed(cb.from_user.id, acc_id, current_delay))
        current_delay += delay_between
        started += 1
    write(users_db, users)
    await cb.answer(f"تم تشغيل {started} حساب ✅\nراح يبدون واحد ورا الثاني كل {delay_between} ثانية", show_alert=True)

@app.on_callback_query(filters.regex(r"^stopAll$"))
async def stop_all(_, cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    stopped = 0
    for acc_id, acc in u["accounts"].items():
        if acc.get("posting"):
            acc["posting"] = False
            stopped += 1
    write(users_db, users)
    await cb.answer(f"تم ايقاف {stopped} حساب", show_alert=True)

async def posting_delayed(user_id, acc_id, delay):
    if delay > 0:
        await sleep(delay)
        u = get_user(user_id)
        if acc_id not in u["accounts"] or not u["accounts"][acc_id].get("posting"):
            return
    await posting(user_id, acc_id)

async def posting(user_id, acc_id):
    u = get_user(user_id)
    acc = u["accounts"][acc_id]
    client = Client(f"acc_{acc_id}", api_id=API_ID, api_hash=API_HASH, session_string=acc["session"])
    await client.start()
    try:
        while acc.get("posting"):
            caption = acc.get("caption")
            if not caption:
                acc["posting"] = False
                write(users_db, users)
                await app.send_message(user_id, f"- توقف النشر للحساب {acc.get('name')} لان ماكو كليشة")
                break
            groups_to_post = get_groups_for_posting(user_id, acc_id)
            for group in list(groups_to_post):
                try: await client.send_message(group, caption)
                except ChatWriteForbidden:
                    try:
                        await client.join_chat(group)
                        await client.send_message(group, caption)
                    except Exception as e2:
                        await app.send_message(user_id, str(e2))
                except Exception as e:
                    try:
                        chat = await client.join_chat(group)
                        await client.send_message(chat.id, caption)
                    except Exception as e2:
                        await app.send_message(user_id, str(e2))
            await sleep(acc.get("waitTime", 60))
    finally:
        await client.stop()

_timezone = timezone("Asia/Baghdad")
def timeCalc(limit):
    start = datetime.now(_timezone)
    end = start + timedelta(days=limit)
    return {"current_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d"), "endTime": end.strftime("%H:%M"), "hours": limit*24, "minutes": limit*24*60}

async def main():
    await app.start()
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(main())
