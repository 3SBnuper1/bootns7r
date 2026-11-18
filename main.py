import asyncio, json, os, random
from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button, ChatMemberUpdated
from pyrogram.errors import PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid, UserNotParticipant, FloodWait, UserDeactivated, AuthKeyUnregistered, SessionRevoked, UserIsBlocked
from datetime import datetime as dt, timedelta
from pytz import timezone

# ===== الاعدادات =====
app = Client("autoPost", api_id=9661697, api_hash="4ae76784fdfecd5df142004955bb8393", bot_token="9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8")
loop = asyncio.get_event_loop()
owner = 5723475089
DEV = "@i999l9"
_timezone = timezone("Asia/Baghdad")

# ===== Listener بديل بدون pyrolistener =====
waiting = {}
class TimeOut(Exception): pass
async def wait_input(uid, text, timeout=60, reply_markup=None):
    await app.send_message(uid, text, reply_markup=reply_markup)
    fut = loop.create_future()
    waiting[uid] = fut
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeOut()
    finally:
        waiting.pop(uid, None)

@app.on_message(filters.private & ~filters.command(["start","admin"]), group=-1)
async def _on_wait(_, message: Message):
    uid = message.from_user.id
    if uid in waiting and not waiting[uid].done():
        waiting[uid].set_result(message)
        message.stop_propagation()

# ===== قاعدة البيانات =====
def write(fp, data):
    with open(fp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
def read(fp):
    if not os.path.exists(fp):
        write(fp, {"users":{},"accounts":{},"groups":{},"channels":{},"vip":{},"settings":{},"blocked":{},"force_stopped":[],"subscribed":[],"referrals":{},"blocked_users":[],"stats_per_user":{},"last_report_date":None})
    with open(fp, encoding="utf-8") as f: return json.load(f)
db = read("data.json")
for _k,_v in {"channels":{},"blocked_users":[],"stats_per_user":{},"last_report_date":None}.items():
    if _k not in db: db[_k]=_v
def save(): write("data.json", db)

def get_settings(uid):
    uid=str(uid)
    if uid not in db["settings"]:
        db["settings"][uid]={"caption":"اهلا بكم 🔥","captions":["اهلا بكم 🔥"],"caption_mode":"single","delay":60,"delay_min":60,"delay_max":120,"media_enabled":False,"protect_enabled":True,"report_enabled":True,"random_enabled":False,"stealth_enabled":False,"media_file":None,"forced_channel":None,"last_post_accs":[],"last_post_groups":[]}
        save()
    return db["settings"][uid]

def get_forced():
    ch=db["settings"].get(str(owner),{}).get("forced_channel")
    if not ch: return None
    if str(ch).startswith("-100"): return str(ch)
    return "@"+str(ch).replace("@","").strip()
def is_admin(uid): return uid==owner
def is_vip(uid):
    if is_admin(uid): return True
    v=db["vip"].get(str(uid))
    if not v: return False
    if v.get("expire")=="lifetime": return True
    try:
        if dt.now()>dt.fromisoformat(v["expire"]):
            del db["vip"][str(uid)]; save(); return False
        return True
    except: return False
def vip_left(uid):
    v=db["vip"].get(str(uid))
    if not v: return None
    if v.get("expire")=="lifetime": return "مدى الحياة"
    exp=dt.fromisoformat(v["expire"]); return f"{(exp-dt.now()).days} يوم - {exp.strftime('%Y-%m-%d')}"
def is_force(acc): return acc in db.get("force_stopped",[])
def force_acc(acc):
    if acc not in db["force_stopped"]: db["force_stopped"].append(acc); save()
def unforce_acc(acc):
    if acc in db["force_stopped"]: db["force_stopped"].remove(acc); save(); return True
    return False
def bkey(a,g): return f"{a}__{g}"
def is_blocked(a,g): return bkey(a,g) in db.get("blocked",{})
def t(v): return "✅ مفعل" if v else "❌ معطل"
def is_cancel(text): return text and text.strip().lower() in ["/cancel","cancel","الغاء"]

def mainMarkup(uid):
    r=[[Button("- 📁 الحسابات -", callback_data="accounts")],[Button("- 🚀 النشر -", callback_data="posting"), Button("- 👥 المجموعات -", callback_data="groups")],[Button("- 👥 احالتي 🎁 -", callback_data="myRef"), Button("- 🥷 التخفي -", callback_data="stealthInfo")],[Button("- ℹ️ معلومات حول البوت -", callback_data="aboutBot")]]
    if is_admin(uid): r.append([Button("- 📊 احصائيات -", callback_data="statics"), Button("- 👑 VIP -", callback_data="vipAdmin")])
    r.append([Button("- 👑 اشتراكي -", callback_data="checkMyVip"), Button("- 🔍 فحص -", callback_data="checkAcc")])
    return Markup(r)
refMarkup = Markup([[Button("- احالتي 🎁 -", callback_data="myRef")],[Button("- ℹ️ معلومات حول البوت -", callback_data="aboutBot")]])
backMarkup = Markup([[Button("- العوده -", callback_data="toHome")]])
toHomeMarkup = Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]])

posting_tasks = {}
account_clients = {}
stats_today = {"count":0}
stealth_counter = {}

# ===== اشعار اشتراك + حظر =====
async def get_forced_total():
    ch=get_forced()
    if not ch: return 0
    try: return await app.get_chat_members_count(ch)
    except:
        try:
            chat=await app.get_chat(ch)
            return getattr(chat,"members_count",0) or 0
        except: return 0

async def notify_subscribed(uid, first_name, username):
    if str(uid) in db.get("subscribed",[]): return
    db.setdefault("subscribed",[]).append(str(uid)); save()
    total=await get_forced_total()
    try: await app.send_message(owner, f"✅ واحد اشترك بالقناة الاجبارية\n\n🆔 {uid}\n👤 الاسم: {first_name or ''}\n🔗 اليوزر: @{username or 'ماكو'}\n📊 عدد المشتركين الكلي بالقناة: {total}\n📊 عدد مستخدمين البوت: {len(db['users'])}")
    except: pass

async def notify_blocked(uid, first_name, username):
    if str(uid) in db.get("blocked_users",[]): return
    db.setdefault("blocked_users",[]).append(str(uid)); save()
    if str(uid) in db.get("subscribed",[]): db["subscribed"].remove(str(uid)); save()
    blocked_count=len(db.get("blocked_users",[])); remaining=len(db["users"])-blocked_count
    try: await app.send_message(owner, f"🚫 واحد حظر البوت\n\n🆔 {uid}\n👤 الاسم: {first_name or ''}\n🔗 اليوزر: @{username or 'ماكو'}\n\n📊 اللي حظروا البوت: {blocked_count}\n📊 المستخدمين الباقين: {remaining}")
    except: pass

@app.on_chat_member_updated()
async def on_my_chat_member(_, update: ChatMemberUpdated):
    try:
        if update.chat.type.value=="private" or str(update.chat.type)=="private":
            new_status=update.new_chat_member.status.value if hasattr(update.new_chat_member.status,"value") else str(update.new_chat_member.status)
            if new_status in ["kicked","left"] and update.from_user.id!=owner:
                await notify_blocked(update.from_user.id, update.from_user.first_name or "", update.from_user.username or "")
    except: pass

# ===== نسخة احتياطية كل نص ساعة =====
async def backup_loop():
    while True:
        await asyncio.sleep(1800)
        try:
            if os.path.exists("data.json"):
                now=_timezone.localize(dt.now()).strftime("%Y-%m-%d %H:%M")
                await app.send_document(owner, "data.json", caption=f"💾 نسخة احتياطية\n🕒 {now}\n👥 المستخدمين: {len(db['users'])}\n📁 الحسابات: {len(db['accounts'])}\n👥 المجموعات: {len(db['groups'])}\n📢 القنوات: {len(db.get('channels',{}))}")
        except Exception as e: print(f"خطأ نسخة: {e}")

# ===== اذاعة =====
async def do_broadcast(target, message: Message):
    sent=0; failed=0; blocked_now=[]
    targets=[]
    if target=="users": targets=[int(k) for k in db["users"].keys() if k not in db.get("blocked_users",[])]
    elif target=="groups": targets=[int(k) for k in db["groups"].keys()]
    elif target=="channels": targets=[int(k) for k in db.get("channels",{}).keys()]
    elif target=="all": targets=[int(k) for k in db["users"].keys() if k not in db.get("blocked_users",[])] + [int(k) for k in db["groups"].keys()] + [int(k) for k in db.get("channels",{}).keys()]
    for tid in targets:
        try:
            if message.photo: await app.send_photo(tid, message.photo.file_id, caption=message.caption or "")
            elif message.video: await app.send_video(tid, message.video.file_id, caption=message.caption or "")
            elif message.text: await app.send_message(tid, message.text)
            else: await message.copy(tid)
            sent+=1
        except UserIsBlocked:
            failed+=1
            if str(tid) not in db.get("blocked_users",[]) and tid>0: blocked_now.append(tid)
        except: failed+=1
        await asyncio.sleep(0.05)
    for tid in blocked_now: await notify_blocked(tid, db["users"].get(str(tid),{}).get("name",""), db["users"].get(str(tid),{}).get("username",""))
    return sent, failed

async def get_user_client(acc_key):
    if acc_key in account_clients:
        try: await account_clients[acc_key].get_me(); return account_clients[acc_key]
        except: pass
    acc=db["accounts"].get(acc_key)
    if not acc: return None
    c=Client(acc_key, api_id=app.api_id, api_hash=app.api_hash, session_string=acc["session"], in_memory=True)
    await c.start(); account_clients[acc_key]=c; return c

async def subscription(message):
    uid=message.from_user.id; ch=get_forced()
    if not ch or is_admin(uid): return True
    try: await app.get_chat_member(ch, uid); return True
    except UserNotParticipant: return ch
    except: return True

# ===== START =====
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    uid=message.from_user.id
    ref=None
    if len(message.command)>1 and message.command[1].startswith("ref_"): ref=message.command[1].replace("ref_","")
    is_new=str(uid) not in db["users"]
    db["users"][str(uid)]={"name":message.from_user.first_name or "","username":message.from_user.username or "","id":uid}; save()
    if is_new:
        try: await app.send_message(owner,f"👤 مستخدم جديد دخل البوت\n\n🆔 {uid}\n👤 الاسم: {message.from_user.first_name or ''}\n🔗 اليوزر: @{message.from_user.username or 'ماكو'}\n📊 العدد الكلي: {len(db['users'])}")
        except: pass
    if is_new and ref and ref!=str(uid) and ref in db["users"]:
        db.setdefault("referrals",{})
        if ref not in db["referrals"]: db["referrals"][ref]={"invited":[],"rewarded":False}
        if uid not in db["referrals"][ref]["invited"]:
            db["referrals"][ref]["invited"].append(uid); save()
            cnt=len(db["referrals"][ref]["invited"])
            try: await app.send_message(int(ref), f"👥 احالة جديدة! صار عندك {cnt}/3")
            except: pass
            if cnt>=3 and not db["referrals"][ref].get("rewarded"):
                db["referrals"][ref]={"invited":[],"rewarded":False}
                old=db["vip"].get(ref)
                if old and old.get("expire")!="lifetime":
                    try: exp=dt.fromisoformat(old["expire"])+timedelta(days=1)
                    except: exp=dt.now()+timedelta(days=1)
                else: exp=dt.now()+timedelta(days=1)
                db["vip"][ref]={"expire":exp.isoformat(),"notified":False}; save()
                try: await app.send_message(int(ref), "🎁 مبروك! جبت 3 احالات، حصلت يوم VIP مجاني 👑")
                except: pass
    sub=await subscription(message)
    if isinstance(sub, str):
        return await message.reply(f"- اشترك بقناة البوت اولاً:\n{sub}\nبعدها ارسل /start")
    await notify_subscribed(uid, message.from_user.first_name or "", message.from_user.username or "")
    if not is_vip(uid):
        return await message.reply(f"❌ غير مشترك VIP\nراسل المطور: {DEV}\n\n🎁 او جيب 3 اشخاص من رابطك وتاخذ يوم VIP مجاني!", reply_markup=refMarkup)
    await message.reply("- مرحبا بك في بوت النشر التلقائي", reply_markup=mainMarkup(uid))

@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    await notify_subscribed(uid, callback.from_user.first_name or "", callback.from_user.username or "")
    await callback.message.edit_text("- مرحبا بك في بوت النشر التلقائي", reply_markup=mainMarkup(uid))

@app.on_callback_query(filters.regex(r"^(aboutBot)$"))
async def aboutBot(_: Client, callback: CallbackQuery):
    txt="""ℹ️ معلومات حول البوت

🚀 النشر: تضيف حسابات + مجموعات + كليشة (وحدة او عدة)
البوت ينشر تلقائياً بكل المجموعات

🛡️ الحماية:
- حلقة وحدة: سوبر ورا سوبر، مو 6 بنفس الثانية
- انتظار 5-15 ثانية بين كل سوبر
- تأخير عشوائي بين كل دورة
- ايقاف تلقائي اذا انطرد او انحظر
- ايقاف اجباري طوارئ

🥷 التخفي: النشرة 1 و 2 عادي، النشرة 3 رد على رسالة موجودة
👥 الاحالة: كل 3 = يوم VIP مجاني
"""
    back=Markup([[Button("- العوده -", callback_data="toHome")]]) if is_vip(callback.from_user.id) else refMarkup
    await callback.message.edit_text(txt, reply_markup=back)

@app.on_callback_query(filters.regex(r"^(myRef)$"))
async def myRef(_: Client, callback: CallbackQuery):
    uid=str(callback.from_user.id); me=await app.get_me()
    link=f"https://t.me/{me.username}?start=ref_{uid}"
    cnt=len(db.get("referrals",{}).get(uid,{"invited":[]}).get("invited",[]))
    back=Markup([[Button("- العوده -", callback_data="toHome")]]) if is_vip(int(uid)) else refMarkup
    await callback.message.edit_text(f"👥 نظام الاحالة 🎁\n\n🔗 رابطك:\n{link}\n\n👥 جبت: {cnt}/3\n🎁 كل 3 تاخذ يوم VIP مجاني!", reply_markup=back)

@app.on_callback_query(filters.regex(r"^(stealthInfo)$"))
async def stealthInfo(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    s=get_settings(uid); cur=s["stealth_enabled"]
    txt=f"🥷 وضع التخفي\n\nاذا شغلته:\nالنشر 1 و 2: عادي\nالنشر 3: رد على رسالة موجودة بنفس نص النشر\n\nالحالة: {'✅ شغال' if cur else '❌ مطفي'}"
    btn=Button("❌ طفي التخفي", callback_data="toggleStealth") if cur else Button("✅ شغل التخفي", callback_data="toggleStealth")
    await callback.message.edit_text(txt, reply_markup=Markup([[btn],[Button("- العوده -", callback_data="toHome")]]))

# ===== الحسابات =====
@app.on_callback_query(filters.regex(r"^(accounts)$"))
async def accountsMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid or is_admin(uid)]
    txt="📁 الحسابات\n\n" + ("\n".join([f"{v.get('phone',k)} {'⛔ ايقاف' if is_force(k) else ''}" for k,v in accs]) if accs else "لا توجد حسابات")
    markup=[]
    for k,v in accs: markup.append([Button(v.get('phone',k), callback_data="noop"), Button("🗑 حذف", callback_data=f"delAcc_{k}")])
    markup.append([Button("- ➕ اضافة -", callback_data="addAcc")]); markup.append([Button("- العوده -", callback_data="toHome")])
    await callback.message.edit_text(txt, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addAcc)$"))
async def addAcc(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    await callback.message.delete()
    try: ask=await wait_input(uid, "- أرسل رقم الهاتف:\nيمكنك ارسال /cancel للالغاء.", timeout=60, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- نفد الوقت", reply_markup=backMarkup)
    if ask.text=="/cancel": return await ask.reply("- تم الالغاء.")
    asyncio.create_task(registration(ask))

async def registration(message: Message):
    uid=message.from_user.id; number=message.text
    lmsg=await message.reply("- جارٍ تسجيل الدخول...")
    reMarkup=Markup([[Button("- إعادة المحاوله -", callback_data="addAcc"), Button("- العوده -", callback_data="toHome")]])
    client=Client("registration", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    try: p_code=await client.send_code(number)
    except PhoneNumberInvalid: return await lmsg.edit_text("- رقم خاطئ", reply_markup=reMarkup)
    try: code=await wait_input(uid, "- تم ارسال كود لخاصك، ارسله هنا.", timeout=120, reply_markup=ForceReply(selective=True))
    except TimeOut: return await lmsg.reply("- نفد وقت الكود.", reply_markup=reMarkup)
    try: await client.sign_in(number, p_code.phone_code_hash, code.text.replace(" ",""))
    except PhoneCodeInvalid: return await code.reply("- كود خاطئ.", reply_markup=reMarkup)
    except PhoneCodeExpired: return await code.reply("- الكود منتهي.", reply_markup=reMarkup)
    except SessionPasswordNeeded:
        try: password=await wait_input(uid, "- ادخل كلمة مرور التحقق بخطوتين.", timeout=180, reply_markup=ForceReply(selective=True))
        except TimeOut: return await lmsg.reply("- نفد وقت كلمة المرور.", reply_markup=reMarkup)
        try: await client.check_password(password.text)
        except PasswordHashInvalid: return await password.reply("- كلمة مرور خاطئه.", reply_markup=reMarkup)
    session=await client.export_session_string(); await client.disconnect()
    key=f"acc_{int(dt.now().timestamp())}_{random.randint(100,999)}"
    db["accounts"][key]={"owner":uid,"session":session,"phone":number,"status":"🟢 موجود"}; save()
    await app.send_message(uid, f"تم اضافة ✅ {number}\n\nهل تريد انضمام الحساب للمجموعات؟", reply_markup=Markup([[Button("✅ اي نعم", callback_data=f"joinPrompt_{key}")],[Button("❌ لا، بعدين", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(delAcc_)"))
async def delAcc(_: Client, callback: CallbackQuery):
    k=callback.data.replace("delAcc_","")
    if k in account_clients:
        try: await account_clients[k].stop()
        except: pass
        del account_clients[k]
    db["accounts"].pop(k,None); save()
    await callback.message.edit_text("تم حذف الحساب ✅", reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(joinPrompt_)"))
async def joinPrompt(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; key=callback.data.replace("joinPrompt_","")
    grps=[(k,v) for k,v in db["groups"].items() if v.get("owner")==uid or is_admin(uid)]
    if not grps: return await callback.message.edit_text("⚠️ ماكو مجموعات محفوظة", reply_markup=backMarkup)
    markup=[[Button(f"➕ انضمام | {g.get('title',gid)[:30]}", callback_data=f"doJoin_{key}_{gid}")] for gid,g in grps]
    markup.append([Button("✅ تم", callback_data="toHome")])
    await callback.message.edit_text("📋 اختر المجموعات:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(doJoin_)"))
async def doJoin(_: Client, callback: CallbackQuery):
    try: _,key,gid=callback.data.split("_",2)
    except: return await callback.answer("خطأ", show_alert=True)
    acc=db["accounts"].get(key)
    if not acc: return await callback.answer("الحساب مو موجود", show_alert=True)
    g=db["groups"].get(gid); link=g.get("link") if isinstance(g,dict) else g
    try:
        client=await get_user_client(key)
        try: await client.join_chat(link if link else int(gid))
        except Exception as e:
            if "already" not in str(e).lower() and "participant" not in str(e).lower(): raise e
        await callback.answer("تم الانضمام ✅")
    except Exception as ex: await callback.answer(f"فشل: {ex}", show_alert=True)

# ===== المجموعات =====
@app.on_callback_query(filters.regex(r"^(groups)$"))
async def groupsMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid or is_admin(uid)]
    txt="👥 المجموعات\n\n" + ("\n".join([v.get('title',k) for k,v in grps]) if grps else "لا توجد مجموعات")
    markup=[]
    for k,v in grps: markup.append([Button(v.get('title',k)[:30], callback_data="noop"), Button("🚪 حذف + مغادرة", callback_data=f"delGrp_{k}")])
    markup.append([Button("- ➕ اضافة مجموعة -", callback_data="addGrpChooseAcc")]); markup.append([Button("- العوده -", callback_data="toHome")])
    await callback.message.edit_text(txt, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addGrpChooseAcc)$"))
async def addGrpChooseAcc(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    if not accs: return await callback.message.edit_text("اضف حساب اولا", reply_markup=backMarkup)
    markup=[[Button("كل الحسابات", callback_data="addGrp_all")]]
    for k in accs: markup.append([Button(db["accounts"][k].get("phone",k), callback_data=f"addGrpAcc_{k}")])
    markup.append([Button("- العوده -", callback_data="toHome")])
    await callback.message.edit_text("اختر الحساب:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addGrpAcc_|addGrp_all)"))
async def addGrpAsk(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    await callback.message.delete()
    try: ask=await wait_input(uid, "- ارسل رابط السوبر / القناة لإضافته.\n- يمكنك ارسال /cancel للالغاء.", timeout=60, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("نفد وقت الرابط", reply_markup=backMarkup)
    if ask.text=="/cancel": return await ask.reply("- تم الالغاء.")
    asyncio.create_task(add_group_logic(ask, callback.data))

async def add_group_logic(message, chosen):
    uid=message.from_user.id; link=message.text.strip()
    if chosen.startswith("addGrpAcc_"):
        ak=chosen.replace("addGrpAcc_","")
        if ak not in db["accounts"] or db["accounts"][ak]["owner"]!=uid: return await message.reply("الحساب مو موجود")
        accs=[(ak, db["accounts"][ak])]; mode_txt=f"للحساب {db['accounts'][ak].get('phone')}"
    else:
        accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid]; mode_txt="لجميع الحسابات"
    await message.reply(f"جاري دخول {mode_txt} ... ⏳")
    joined=0; skipped=0; failed=""; gid_final=None; title_final=link; is_channel=False
    for ak,acc in accs:
        try:
            client=await get_user_client(ak)
            try: chat=await client.join_chat(link)
            except Exception as e:
                if "already" in str(e).lower() or "participant" in str(e).lower():
                    skipped+=1
                    try: chat=await client.get_chat(link)
                    except: continue
                else: failed+=f"\n{acc.get('phone')}: {e}"; continue
            gid_final=str(chat.id); title_final=chat.title or link; joined+=1
            if str(chat.type).lower().find("channel")!=-1: is_channel=True
        except Exception as ex: failed+=f"\n{acc.get('phone')}: {ex}"
    if not gid_final: return await message.reply(f"❌ فشل\n{failed}", reply_markup=mainMarkup(uid))
    if is_channel: db.setdefault("channels",{})[gid_final]={"owner":uid,"title":title_final,"link":link}
    else: db["groups"][gid_final]={"owner":uid,"title":title_final,"link":link}
    save()
    await message.reply(f"تم ✅ ({mode_txt})\n✅ دخل: {joined}\n⏭️ موجود: {skipped}\n🆔 {gid_final}\n{failed}", reply_markup=mainMarkup(uid))

@app.on_callback_query(filters.regex(r"^(delGrp_)"))
async def delGrpAsk(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; grp_id=callback.data.replace("delGrp_","")
    title=db["groups"].get(grp_id,{}).get("title",grp_id)[:30]
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    markup=[[Button("🚪 مغادرة بكل الحسابات", callback_data=f"leaveGrp_{grp_id}__ALL")]]
    for k in accs: markup.append([Button(f"🚪 مغادرة {db['accounts'][k].get('phone',k)}", callback_data=f"leaveGrp_{grp_id}__{k}")])
    markup.append([Button("🗑 حذف من البوت فقط", callback_data=f"delOnly_{grp_id}")]); markup.append([Button("🔙 رجوع", callback_data="groups")])
    await callback.message.edit_text(f"🚪 حذف:\n{title}\nالحساب يغادر فعلاً؟", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(leaveGrp_)"))
async def leaveGrp(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; rest=callback.data.replace("leaveGrp_",""); grp_id,acc_part=rest.split("__",1) if "__" in rest else (rest,"ALL")
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
    title=db["groups"].get(grp_id,{}).get("title",grp_id); ok=0; fail=0
    for a in accs:
        try:
            client=await get_user_client(a)
            stop_post(uid,a,grp_id); await client.leave_chat(int(grp_id)); ok+=1
        except: fail+=1
    db["groups"].pop(grp_id,None); db.get("channels",{}).pop(grp_id,None); save()
    await callback.message.edit_text(f"تم ✅\n🚪 غادر: {ok}\n❌ فشل: {fail}\n{title}", reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(delOnly_)"))
async def delOnly(_: Client, callback: CallbackQuery):
    grp_id=callback.data.replace("delOnly_",""); db["groups"].pop(grp_id,None); db.get("channels",{}).pop(grp_id,None); save()
    await callback.message.edit_text("تم حذف من البوت فقط ✅", reply_markup=backMarkup)

# ===== النشر =====
@app.on_callback_query(filters.regex(r"^(posting)$"))
async def postingMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if not is_vip(uid): return await callback.answer("- انتهى اشتراكك.", show_alert=True)
    markup=Markup([[Button("- ▶️ بدء -", callback_data="startPost"), Button("- ⏹️ ايقاف -", callback_data="stopPost")],[Button("- 📝 الكليشة -", callback_data="setCaption")],[Button("- ⏱️ المدة -", callback_data="setDelay")],[Button("- ⚙️ اعدادات -", callback_data="autoSettings")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text("🚀 النشر", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(setCaption)$"))
async def setCaption(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; s=get_settings(uid)
    markup=Markup([[Button("- 📝 كليشة وحدة -", callback_data="captionSingle")],[Button("- 📝 عدة كلايش -", callback_data="captionMulti")],[Button("- 📋 عرض الكلايش -", callback_data="captionShow")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text(f"📝 الكليشة\n\nالوضع: {'عدة كلايش' if s.get('caption_mode')=='multi' else 'كليشة وحدة'}\nعدد الكلايش: {len(s.get('captions',[]))}", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(captionSingle)$"))
async def captionSingle(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; await callback.message.delete()
    try: ask=await wait_input(uid, "📝 دز الكليشة الوحدة:", timeout=120, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- انتهى الوقت.")
    s=get_settings(uid); s["caption"]=ask.text; s["captions"]=[ask.text]; s["caption_mode"]="single"; save()
    await ask.reply(f"✅ تم حفظ كليشة وحدة:\n{ask.text}", reply_markup=toHomeMarkup)

@app.on_callback_query(filters.regex(r"^(captionMulti)$"))
async def captionMulti(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; await callback.message.delete()
    try: ask=await wait_input(uid, "📝 دز عدة كلايش، كل كليشة بسطر:\nاهلا بكم 🔥\nعرض اليوم خصم 50%", timeout=120, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- انتهى الوقت.")
    lines=[l.strip() for l in (ask.text or "").split("\n") if l.strip()]
    if len(lines)<2: return await ask.reply("⚠️ لازم تدز كليشتين على الاقل، كل وحدة بسطر")
    s=get_settings(uid); s["captions"]=lines; s["caption"]=lines[0]; s["caption_mode"]="multi"; save()
    await ask.reply("✅ تم حفظ عدة كلايش:\n\n"+"\n".join([f"{i}. {c}" for i,c in enumerate(lines,1)])+"\n\n🎲 كل نشرة راح يختار وحدة عشوائياً", reply_markup=toHomeMarkup)

@app.on_callback_query(filters.regex(r"^(captionShow)$"))
async def captionShow(_: Client, callback: CallbackQuery):
    s=get_settings(callback.from_user.id); caps=s.get("captions",[])
    txt="📋 الكلايش الحالية:\n\n"+"\n".join([f"{i}. {c}" for i,c in enumerate(caps,1)]) if caps else "ماكو كلايش"
    await callback.message.edit_text(txt, reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(setDelay)$"))
async def setDelay(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; s=get_settings(uid); await callback.message.delete()
    try: ask=await wait_input(uid, "ارسل المدة بالثواني." if not s["random_enabled"] else "ارسل هكذا: 60-120", timeout=60, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- انتهى الوقت.")
    if s["random_enabled"]:
        try: a,b=ask.text.split("-"); s["delay_min"]=int(a); s["delay_max"]=int(b); save(); await ask.reply(f"تم: {a}-{b} 🎲", reply_markup=toHomeMarkup)
        except: await ask.reply("ارسل 60-120")
    else:
        try: d=int(ask.text); s["delay"]=d if d>=30 else 30; save(); await ask.reply(f"تم: {s['delay']} ثانية ✅", reply_markup=toHomeMarkup)
        except: await ask.reply("ارسل رقم")

# ===== الاعدادات =====
@app.on_callback_query(filters.regex(r"^(autoSettings)$"))
async def autoSettings(_: Client, callback: CallbackQuery):
    s=get_settings(callback.from_user.id)
    markup=Markup([[Button(f"🖼️ صور: {t(s['media_enabled'])}", callback_data="toggleMedia")],[Button(f"🛡️ حماية: {t(s['protect_enabled'])}", callback_data="toggleProtect")],[Button(f"📊 تقرير: {t(s['report_enabled'])}", callback_data="toggleReport")],[Button(f"🎲 عشوائي: {t(s['random_enabled'])}", callback_data="toggleRandom")],[Button(f"🥷 تخفي: {t(s['stealth_enabled'])}", callback_data="toggleStealth")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text("⚙️ اعدادات", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(toggleMedia|toggleProtect|toggleReport|toggleRandom|toggleStealth)$"))
async def toggleSetting(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; s=get_settings(uid)
    key={"toggleMedia":"media_enabled","toggleProtect":"protect_enabled","toggleReport":"report_enabled","toggleRandom":"random_enabled","toggleStealth":"stealth_enabled"}[callback.data]
    s[key]=not s[key]; save()
    if key=="media_enabled" and s[key]:
        await callback.message.delete()
        try: ask=await wait_input(uid, "ارسل الصورة:", timeout=60, reply_markup=ForceReply(selective=True))
        except TimeOut: return await callback.message.reply("- انتهى الوقت.")
        if ask.photo or ask.video:
            path=f"media_{uid}.jpg"; await ask.download(path); s["media_file"]=path; save()
            await ask.reply("تم حفظ الصورة ✅", reply_markup=toHomeMarkup)
        else: await ask.reply("ارسل صورة")
        return
    await callback.answer(f"{'تم التشغيل ✅' if s[key] else 'تم الاطفاء ❌'}", show_alert=True)
    await autoSettings(_, callback)

# ===== ايقاف / تشغيل =====
@app.on_callback_query(filters.regex(r"^(stopPost)$"))
async def stopPostMenu(_: Client, callback: CallbackQuery):
    markup=Markup([[Button("- ⏹️ عادي -", callback_data="stopPostNormal")],[Button("- ⛔ اجباري طوارئ -", callback_data="stopPostForce")],[Button("- ✅ الغاء الاجباري -", callback_data="unblockList")],[Button("- العوده -", callback_data="posting")]])
    await callback.message.edit_text("⏹️ ايقاف النشر", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(unblockList)$"))
async def unblockList(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    forced=[a for a in db.get("force_stopped",[]) if a in db["accounts"] and (db["accounts"][a]["owner"]==uid or is_admin(uid))]
    blocked=[(k,v) for k,v in db.get("blocked",{}).items() if v.get("owner")==uid or is_admin(uid)]
    if not forced and not blocked: return await callback.message.edit_text("ما عندك ايقاف ✅", reply_markup=backMarkup)
    txt="⛔ الايقاف:\n\n"; markup=[]
    for ak in forced:
        phone=db["accounts"].get(ak,{}).get("phone",ak); txt+=f"{phone} ⛔\n"
        markup.append([Button(f"✅ الغاء + شغل: {phone}", callback_data=f"unforceAndStart_{ak}")])
    for k,v in blocked:
        ap=db["accounts"].get(v.get("acc"),{}).get("phone",v.get("acc")); gt=db["groups"].get(v.get("grp"),{}).get("title",v.get("grp"))[:20]; txt+=f"{ap} - {gt}\n"
        markup.append([Button(f"✅ الغاء حظر: {ap} - {gt}", callback_data=f"unblock_{v.get('acc')}__{v.get('grp')}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text(txt, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(unforceAndStart_|unforce_)"))
async def unforceCb(_: Client, callback: CallbackQuery):
    ak=callback.data.replace("unforceAndStart_","").replace("unforce_","")
    if unforce_acc(ak):
        phone=db["accounts"].get(ak,{}).get("phone",ak)
        await callback.message.edit_text(f"✅ تم الغاء الايقاف {phone}", reply_markup=Markup([[Button("▶️ بدء النشر", callback_data="startPost")],[Button("- العوده -", callback_data="toHome")]]))
    else: await callback.message.edit_text("مو موجود", reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(unblock_)"))
async def unblockCb(_: Client, callback: CallbackQuery):
    rest=callback.data.replace("unblock_","")
    if "__" in rest:
        ak,gid=rest.split("__",1)
        if bkey(ak,gid) in db.get("blocked",{}): del db["blocked"][bkey(ak,gid)]; save(); await callback.message.edit_text("✅ تم الغاء الحظر", reply_markup=backMarkup)
        else: await callback.message.edit_text("مو موجود", reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(startPost|stopPostNormal)$"))
async def chooseAccForPost(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; mode="start" if callback.data=="startPost" else "stop"
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    if not accs: return await callback.message.edit_text("ما عندك حساب", reply_markup=backMarkup)
    markup=[[Button("كل الحسابات", callback_data=f"{mode}Post_ALL")]]
    for k in accs:
        label=db["accounts"][k].get("phone",k)
        markup.append([Button(label+(" ⛔ موقوف" if is_force(k) else ""), callback_data=f"{mode}PostAcc_{k}" if not is_force(k) else f"unforce_{k}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text("اختر الحساب:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(stopPostForce)$"))
async def stopForceMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    if not accs: return await callback.message.edit_text("ما عندك حساب", reply_markup=backMarkup)
    markup=[[Button("⛔ ايقاف لكل الحسابات", callback_data="force_ALL")]]
    for k in accs: markup.append([Button(f"⛔ ايقاف: {db['accounts'][k].get('phone',k)}", callback_data=f"force_{k}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text("⛔ ايقاف اجباري طوارئ", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(force_)"))
async def forceCb(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; ak=callback.data.replace("force_","")
    if ak=="ALL":
        for k in [kk for kk,v in db["accounts"].items() if v["owner"]==uid]: stop_all_acc(uid,k); force_acc(k)
        return await callback.message.edit_text("⛔ تم ايقاف كل الحسابات ✅", reply_markup=Markup([[Button("✅ الغاء الايقاف", callback_data="unblockList")],[Button("- العوده -", callback_data="toHome")]]))
    stop_all_acc(uid,ak); force_acc(ak); phone=db["accounts"].get(ak,{}).get("phone",ak)
    await callback.message.edit_text(f"⛔ تم ايقاف {phone} ✅", reply_markup=Markup([[Button("✅ الغاء الايقاف", callback_data="unblockList")],[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(startPostAcc_|stopPostAcc_|startPost_ALL|stopPost_ALL)"))
async def chooseGrpForPost(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; data=callback.data
    mode="start" if data.startswith("start") else "stop"
    acc_part="ALL" if data.endswith("_ALL") else data.replace(f"{mode}PostAcc_","")
    if mode=="start" and acc_part!="ALL" and is_force(acc_part):
        return await callback.message.edit_text(f"⛔ موقوف اجبارياً", reply_markup=Markup([[Button("✅ الغاء + شغل", callback_data=f"unforceAndStart_{acc_part}")],[Button("- العوده -", callback_data="posting")]]))
    grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid]
    if not grps: return await callback.message.edit_text("ما عندك مجموعة", reply_markup=backMarkup)
    markup=[[Button("كل المجموعات", callback_data=f"{mode}Grp_ALL__{acc_part}")]]
    for k,v in grps:
        label=v.get('title',k)[:30]
        if acc_part!="ALL" and is_blocked(acc_part,k): label+=" ⛔ انطرد"
        markup.append([Button(label, callback_data=f"{mode}Grp_{k}__{acc_part}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text("اختر المجموعة:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(startGrp_|stopGrp_)"))
async def doPostGrp(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; data=callback.data
    mode="start" if data.startswith("start") else "stop"
    rest=data.replace(f"{mode}Grp_",""); grp_id,acc_part=rest.split("__",1) if "__" in rest else (rest,"ALL")
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
    grps=list(db["groups"].keys()) if grp_id=="ALL" else [grp_id]
    if mode=="start":
        for a in accs:
            if is_force(a): return await callback.message.edit_text("⛔ موقوف اجبارياً", reply_markup=backMarkup)
        key=f"{uid}_posting"
        if key in posting_tasks: return await callback.message.edit_text("⚠️ النشر شغال اصلاً", reply_markup=backMarkup)
        s=get_settings(uid); s["last_post_accs"]=accs; s["last_post_groups"]=grps; save()
        posting_tasks[key]=asyncio.create_task(posting_loop(uid))
        await callback.message.edit_text(f"✅ بدء النشر 🔁\nالوضع: {'عدة كلايش 🎲' if s.get('caption_mode')=='multi' else 'كليشة وحدة 📝'}\nالكليشة: {s.get('caption','')[:100]}", reply_markup=backMarkup)
    else:
        key=f"{uid}_posting"
        if key in posting_tasks: posting_tasks[key].cancel(); del posting_tasks[key]; await callback.message.edit_text("⏹️ تم ايقاف النشر ✅", reply_markup=backMarkup)
        else: await callback.message.edit_text("⚠️ متوقف اصلاً", reply_markup=backMarkup)

def stop_post(uid,acc_key,grp_id):
    key=f"{uid}_posting"
    if key in posting_tasks:
        s=get_settings(uid)
        if s.get("last_post_accs")==[acc_key] and s.get("last_post_groups")==[grp_id]:
            posting_tasks[key].cancel(); del posting_tasks[key]; return True
    return False
def stop_all_acc(uid,acc_key):
    key=f"{uid}_posting"
    if key in posting_tasks: posting_tasks[key].cancel(); del posting_tasks[key]; return 1
    return 0

async def posting_loop(uid):
    while True:
        try:
            s=get_settings(uid)
            accs=s.get("last_post_accs",[k for k,v in db["accounts"].items() if v["owner"]==uid])
            grps=s.get("last_post_groups",list(db["groups"].keys()))
            for acc_key in accs:
                if is_force(acc_key): continue
                for grp_id in grps:
                    if is_blocked(acc_key,grp_id): continue
                    await send_one(uid,acc_key,grp_id)
                    await asyncio.sleep(random.randint(5,15))
            delay=random.randint(s["delay_min"],s["delay_max"]) if s["random_enabled"] else s["delay"]
            await asyncio.sleep(delay)
        except asyncio.CancelledError: break
        except Exception as e: print(e); await asyncio.sleep(10)

async def send_one(uid,acc_key,grp_id):
    s=get_settings(uid); acc=db["accounts"].get(acc_key)
    if not acc or is_force(acc_key) or is_blocked(acc_key,grp_id): return False
    try:
        client=await get_user_client(acc_key)
        try: me=await client.get_me()
        except: raise AuthKeyUnregistered("جلسة منتهية")
        caption_to_send=random.choice(s["captions"]) if s.get("caption_mode")=="multi" and s.get("captions") else s.get("caption","اهلا بكم 🔥")
        is_reply=False
        if s.get("stealth_enabled"):
            ck=f"{acc_key}_{grp_id}"; c=stealth_counter.get(ck,0)
            if c % 3 == 2: is_reply=True
            stealth_counter[ck]=c+1
        if is_reply:
            try:
                msgs=[]
                async for m in client.get_chat_history(int(grp_id), limit=20):
                    if m.text and m.from_user and m.from_user.id!=me.id: msgs.append(m)
                if msgs:
                    target=random.choice(msgs)
                    if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
                        await client.send_photo(int(grp_id), s["media_file"], caption=caption_to_send, reply_to_message_id=target.id)
                    else:
                        await client.send_message(int(grp_id), caption_to_send, reply_to_message_id=target.id)
                    stats_today["count"]+=1; db.setdefault("stats_per_user",{})[str(uid)]=db["stats_per_user"].get(str(uid),0)+1; save(); return True
            except: pass
        if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
            await client.send_photo(int(grp_id), s["media_file"], caption=caption_to_send)
        else:
            await client.send_message(int(grp_id), caption_to_send)
        stats_today["count"]+=1; db.setdefault("stats_per_user",{})[str(uid)]=db["stats_per_user"].get(str(uid),0)+1; save(); return True
    except FloodWait as e:
        if s["protect_enabled"]: await app.send_message(owner, f"🛡️ FloodWait {e.value}")
        await asyncio.sleep(e.value+5); return False
    except (UserDeactivated, AuthKeyUnregistered, SessionRevoked) as e:
        acc["status"]="معطل"; save()
        if s["protect_enabled"]: await app.send_message(uid, f"⚠️ حساب {acc_key} تعطل: {e}")
        return False
    except Exception as e:
        msg=str(e)
        if any(x in msg for x in ["USER_NOT_PARTICIPANT","UserNotParticipant","CHAT_WRITE_FORBIDDEN","ChatWriteForbidden","USER_KICKED","kicked","not participant"]) or "403" in msg or "banned from sending" in msg.lower() or "USER_BANNED" in msg:
            if "banned from sending" in msg.lower() or "USER_BANNED" in msg:
                await app.send_message(uid, f"⏳ حسابك انحظر مؤقتاً من الـ API\nالبوت راح يوقف حتى لا يتحول لحظر دائم")
                force_acc(acc_key); return False
            db.setdefault("blocked",{})[bkey(acc_key,grp_id)]={"owner":uid,"acc":acc_key,"grp":grp_id,"reason":f"انطرد: {e}","time":dt.now().strftime("%Y-%m-%d %H:%M:%S")}; save()
            try:
                t2=db["groups"].get(str(grp_id),{}).get("title",grp_id)
                await app.send_message(uid, f"⛔ طرد تلقائي\nالحساب {acc.get('phone')} انطرد من:\n{t2}\nتم ايقاف النشر لهاي المجموعة فقط.")
            except: pass
            return False
        print(f"خطأ نشر: {e}")
        if s["protect_enabled"]: await app.send_message(uid, f"⚠️ خطأ نشر {acc_key}: {e}")
        return False

# ===== الادمن =====
@app.on_message(filters.command("admin") & filters.private & filters.user(owner))
async def adminCmd(_: Client, message: Message):
    await message.reply(f"مرحبا عزيزي في لوحة المالك", reply_markup=Markup([[Button("- الغاء VIP -", callback_data="vipDel"), Button("- تفعيل VIP -", callback_data="vipAdd")],[Button("- الاحصائيات -", callback_data="statics"), Button("- قناة الاشتراك -", callback_data="vipForced")],[Button("- 📢 اذاعة -", callback_data="broadcastMenu")]]))

@app.on_callback_query(filters.regex(r"^(statics)$"))
async def statics(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    ch=get_forced() or "مو مفعل"
    total_forced=await get_forced_total()
    caption=f"- عدد المستخدمين: {len(db['users'])}\n- عدد الحسابات: {len(db['accounts'])}\n- عدد المجموعات: {len(db['groups'])}\n- عدد القنوات: {len(db.get('channels',{}))}\n- شغال: {len(posting_tasks)}\n- اليوم: {stats_today['count']}\n- 📢 اجباري: {ch}\n- 👥 مشتركين القناة الكلي: {total_forced}\n- 🚫 اللي حظروا البوت: {len(db.get('blocked_users',[]))}\n- VIP: {len(db['vip'])}"
    await callback.message.edit_text(caption, reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(vipAdmin)$"))
async def vipAdmin(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    markup=Markup([[Button("➕ تفعيل VIP", callback_data="vipAdd"), Button("➖ الغاء VIP", callback_data="vipDel")],[Button("📋 قائمة VIP", callback_data="vipList"), Button("📢 اشتراك اجباري", callback_data="vipForced")],[Button("📢 اذاعة", callback_data="broadcastMenu")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text("👑 VIP", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(broadcastMenu)$"))
async def broadcastMenu(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    markup=Markup([[Button(f"👤 للمستخدمين ({len(db['users'])})", callback_data="broadcast_users")],[Button(f"👥 للمجموعات ({len(db['groups'])})", callback_data="broadcast_groups")],[Button(f"📢 للقنوات ({len(db.get('channels',{}))})", callback_data="broadcast_channels")],[Button("🌍 للكل", callback_data="broadcast_all")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text("📢 اذاعة\n\nاختر وين تريد تدز:", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(broadcast_users|broadcast_groups|broadcast_channels|broadcast_all)$"))
async def broadcastAsk(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    target=callback.data.replace("broadcast_","")
    await callback.message.delete()
    try: ask=await wait_input(owner,f"📢 اذاعة لـ {target}\n\nدز الرسالة (نص / صورة / فيديو)\n/cancel للالغاء",timeout=120,reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- نفد الوقت.")
    if is_cancel(ask.text or ""): return await ask.reply("- تم الالغاء.")
    await ask.reply(f"⏳ جاري الارسال لـ {target} ...")
    sent,failed=await do_broadcast(target,ask)
    await ask.reply(f"✅ تمت الاذاعة\n\n📤 وصلت لـ: {sent}\n❌ فشل: {failed}\n🎯 النوع: {target}\n🚫 اللي حظروا البوت: {len(db.get('blocked_users',[]))}", reply_markup=toHomeMarkup)

@app.on_callback_query(filters.regex(r"^(vipAdd)$"))
async def vipAdd(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    await callback.message.delete()
    try: ask=await wait_input(callback.from_user.id, "- ارسل ايدي المستخدم لتفعيل VIP", timeout=30, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- نفد الوقت.")
    try: await app.get_users(int(ask.text))
    except: return await ask.reply("- لم يتم ايجاد هذا المستخدم.")
    _id=int(ask.text)
    markup=Markup([[Button("📅 يوم", callback_data=f"vipDur_day_{_id}"), Button("📅 اسبوع", callback_data=f"vipDur_week_{_id}")],[Button("📅 شهر", callback_data=f"vipDur_month_{_id}"), Button("♾️ مدى", callback_data=f"vipDur_lifetime_{_id}")]])
    await ask.reply("اختر المدة:", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(vipDur_)"))
async def vipDur(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    p=callback.data.split("_",3); dur=p[2]; target=p[3]
    exp="lifetime" if dur=="lifetime" else (dt.now()+timedelta(days={"day":1,"week":7,"month":30}[dur])).isoformat()
    db["vip"][target]={"expire":exp,"notified":False}; save()
    await callback.message.edit_text(f"تم تفعيل VIP {target} ✅", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(vipDel)$"))
async def vipDel(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    await callback.message.delete()
    try: ask=await wait_input(callback.from_user.id, "- ارسل ايدي المستخدم لالغاء VIP", timeout=30, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- نفد الوقت.")
    db["vip"].pop(ask.text,None); save()
    await ask.reply("- تم الغاء اشتراك هذا المستخدم.", reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(vipList)$"))
async def vipList(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    txt="📋 VIP:\n\n" + ("\n".join([f"{k} - {vip_left(int(k)) if k.isdigit() else v}" for k,v in db["vip"].items()]) if db["vip"] else "لا يوجد")
    await callback.message.edit_text(txt, reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(vipForced)$"))
async def vipForced(_: Client, callback: CallbackQuery):
    if callback.from_user.id!=owner: return
    cur=get_forced() or "مو مفعل"
    await callback.message.delete()
    try: ask=await wait_input(callback.from_user.id, f"📢 القناة الحالية:\n{cur}\n\nدز رابط جديد او ارسل 'الغاء' للتعطيل\n⚠️ البوت لازم ادمن", timeout=60, reply_markup=ForceReply(selective=True))
    except TimeOut: return await callback.message.reply("- نفد الوقت.")
    txt=ask.text.strip()
    if txt.lower() in ["الغاء","cancel","none","-","ايقاف","تعطيل"]:
        s=get_settings(owner); s["forced_channel"]=None; save(); return await ask.reply("تم تعطيل الاجباري ✅", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))
    cleaned=txt.replace("https://","").replace("http://","").replace("t.me/","").replace("telegram.me/","").replace("@","").split("/")[0].split("?")[0].strip()
    s=get_settings(owner); s["forced_channel"]="@"+cleaned; save()
    total=await get_forced_total()
    await ask.reply(f"تم ✅ اجباري = @{cleaned}\n📊 عدد المشتركين الكلي: {total}", reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(checkMyVip)$"))
async def checkMyVip(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if is_vip(uid): await callback.message.edit_text(f"VIP ✅\n{vip_left(uid)}", reply_markup=backMarkup)
    else: await callback.message.edit_text(f"عادي ❌\nراسل: {DEV}", reply_markup=Markup([[Button("📩 راسل", url=f"https://t.me/{DEV.replace('@','')}")]]))

@app.on_callback_query(filters.regex(r"^(checkAcc)$"))
async def checkAcc(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; txt="🔍 فحص:\n\n"
    for k,v in db["accounts"].items():
        if v["owner"]!=uid and not is_admin(uid): continue
        running=f"{uid}_posting" in posting_tasks
        txt+=f"{v.get('phone',k)} - {'شغال ✅' if running else 'متوقف ⏹️'}{' ⛔ ايقاف' if is_force(k) else ''}\n"
    await callback.message.edit_text(txt, reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(noop)$"))
async def noopCb(_: Client, callback: CallbackQuery):
    await callback.answer(" ", show_alert=False)

async def vip_checker():
    while True:
        now=dt.now()
        for uid,v in list(db["vip"].items()):
            if v.get("expire")=="lifetime": continue
            try:
                exp=dt.fromisoformat(v["expire"])
                if (exp-now).total_seconds()<=86400 and not v.get("notified"):
                    v["notified"]=True; save()
                    try: await app.send_message(int(uid),"⚠️ اشتراكك VIP راح يخلص باجر!")
                    except: pass
                if now>exp:
                    del db["vip"][uid]; save()
                    try: await app.send_message(int(uid),"❌ انتهى اشتراكك VIP")
                    except: pass
            except: pass
        await asyncio.sleep(3600)

# ===== تقرير يومي: لكل VIP تقريره + للادمن الكل =====
async def daily_report():
    while True:
        await asyncio.sleep(60)
        try:
            now=_timezone.localize(dt.now())
            today_str=now.strftime("%Y-%m-%d")
            if now.hour==2 and now.minute==59:
                if db.get("last_report_date")==today_str:
                    await asyncio.sleep(61); continue
                db["last_report_date"]=today_str; save()
                total=stats_today.get("count",0)
                per_user=dict(db.get("stats_per_user",{}))
                for uid_str, count in list(per_user.items()):
                    if count==0: continue
                    try:
                        uid=int(uid_str)
                        s=get_settings(uid)
                        if not s.get("report_enabled",True): continue
                        if is_vip(uid) and uid!=owner:
                            await app.send_message(uid, f"📊 تقرير يومي\nنشرت اليوم: {count}")
                            await asyncio.sleep(0.5)
                    except: pass
                try:
                    text=f"📊 تقرير يومي كامل\n📅 {today_str}\n\n🔥 المجموع الكلي: {total}\n\n"
                    if not per_user or all(v==0 for v in per_user.values()):
                        text+="ماكو نشر اليوم"
                    else:
                        for uid_str, count in per_user.items():
                            if count==0: continue
                            u=db["users"].get(uid_str,{})
                            text+=f"👤 {u.get('name','مجهول')} (@{u.get('username','ماكو')})\n🆔 {uid_str}\n📤 نشر: {count}\n\n"
                    await app.send_message(owner, text)
                except Exception as e: print(f"خطأ تقرير ادمن: {e}")
                stats_today["count"]=0
                db["stats_per_user"]={}; save()
        except Exception as e: print(f"خطأ تقرير: {e}")
        await asyncio.sleep(1)

async def reStartPosting():
    await asyncio.sleep(30)
    for uid in list(db["settings"].keys()):
        s=db["settings"][uid]
        if s.get("last_post_accs") and s.get("last_post_groups"):
            key=f"{uid}_posting"
            if key not in posting_tasks: posting_tasks[key]=asyncio.create_task(posting_loop(int(uid)))

async def main():
    asyncio.create_task(reStartPosting()); asyncio.create_task(vip_checker()); asyncio.create_task(daily_report()); asyncio.create_task(backup_loop())
    await app.start(); await idle()
if __name__=="__main__":
    loop.run_until_complete(main())
