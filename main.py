from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button
from pyrogram.errors import ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid, UserNotParticipant, ChatWriteForbidden, BotMethodInvalid, FloodWait, UserDeactivated, AuthKeyUnregistered, SessionRevoked
import os
os.system("pip install pyrolistener")
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json, os, random

# ===== نفس برمجة الكود الثاني - Pyrogram =====
app = Client("autoPost", api_id="9661697", api_hash="4ae76784fdfecd5df142004955bb8393", bot_token="9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8")
loop = get_event_loop()
listener = Listener(client=app)
owner = 5723475089
DEV = "@i999l9"
_timezone = timezone("Asia/Baghdad")

# ===== نفس التخزين مال الكود الاول، بس بملف واحد مثل الكود الثاني =====
users_db = "data.json"
def write(fp, data):
    with open(fp, "w", encoding="utf-8") as file: json.dump(data, file, indent=2, ensure_ascii=False)
def read(fp):
    if not os.path.exists(fp):
        write(fp, {"users":{},"accounts":{},"groups":{},"vip":{},"settings":{},"blocked":{},"force_stopped":[],"subscribed":[],"referrals":{}})
    with open(fp, encoding="utf-8") as file: return json.load(file)
db = read(users_db)
users = db["users"]
accounts = db["accounts"]
groups_db = db["groups"]

def save(): write(users_db, db)
def get_settings(uid):
    uid=str(uid)
    if uid not in db["settings"]:
        db["settings"][uid]={"caption":"اهلا بكم 🔥","captions":["اهلا بكم 🔥"],"caption_mode":"single","delay":60,"delay_min":60,"delay_max":120,"media_enabled":False,"protect_enabled":True,"report_enabled":True,"random_enabled":False,"stealth_enabled":False,"media_file":None,"media_type":None,"forced_channel":None}
        save()
    s=db["settings"][uid]
    if "captions" not in s: s["captions"]=[s.get("caption","اهلا بكم 🔥")]
    if "caption_mode" not in s: s["caption_mode"]="single"
    if "stealth_enabled" not in s: s["stealth_enabled"]=False
    return s
def get_forced():
    s=db["settings"].get(str(owner),{}); ch=s.get("forced_channel")
    if not ch: return None
    if ch=="NEED_FORWARD": return "NEED_FORWARD"
    if str(ch).startswith("-100"): return str(ch)
    if ch: return "@"+ch.replace("@","").strip()
    return None
def is_admin(uid): return uid==owner
def is_vip(uid):
    if is_admin(uid): return True
    v=db["vip"].get(str(uid))
    if not v: return False
    if v.get("expire")=="lifetime": return True
    try:
        exp=datetime.fromisoformat(v["expire"])
        if datetime.now()>exp: del db["vip"][str(uid)]; save(); return False
        return True
    except: return False
def vip_left(uid):
    v=db["vip"].get(str(uid))
    if not v: return None
    if v.get("expire")=="lifetime": return "مدى الحياة"
    exp=datetime.fromisoformat(v["expire"]); left=exp-datetime.now()
    return f"{left.days} يوم - {exp.strftime('%Y-%m-%d')}"
def is_force(acc): return acc in db.get("force_stopped",[])
def force_acc(acc):
    if acc not in db["force_stopped"]: db["force_stopped"].append(acc); save()
def unforce_acc(acc):
    if acc in db["force_stopped"]: db["force_stopped"].remove(acc); save(); return True
    return False
def bkey(a,g): return f"{a}__{g}"
def is_blocked(a,g): return bkey(a,g) in db.get("blocked",{})
def force_block(uid,a,g,reason="انطرد"):
    db.setdefault("blocked",{})
    db["blocked"][bkey(a,g)]={"owner":uid,"acc":a,"grp":g,"reason":reason,"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}; save()
def t(v): return "✅ مفعل" if v else "❌ معطل"

# ===== نفس الـ Markup مال الكود الثاني، بس بكل ازرار الكود الاول =====
def mainMarkup(uid):
    r=[
        [Button("- 📁 الحسابات -", callback_data="accounts")],
        [Button("- 🚀 النشر -", callback_data="posting"), Button("- 👥 المجموعات -", callback_data="groups")],
        [Button("- 👥 احالتي 🎁 -", callback_data="myRef"), Button("- 🥷 التخفي -", callback_data="stealthInfo")],
        [Button("- ℹ️ معلومات حول البوت -", callback_data="aboutBot")],
    ]
    if is_admin(uid): r.append([Button("- 📊 احصائيات -", callback_data="statics"), Button("- 👑 VIP -", callback_data="vipAdmin")])
    r.append([Button("- 👑 اشتراكي -", callback_data="checkMyVip"), Button("- 🔍 فحص -", callback_data="checkAcc")])
    return Markup(r)
refMarkupForAll = Markup([[Button("- احالتي 🎁 -", callback_data="myRef")],[Button("- ℹ️ معلومات حول البوت -", callback_data="aboutBot")]])
backMarkup = Markup([[Button("- العوده -", callback_data="toHome")]])
toHomeMarkup = Markup([[Button("- الصفحه الرئيسيه -", callback_data="toHome")]])

# ===== نشر Pyrogram - حلقة وحدة مثل الكود الثاني =====
posting_tasks = {}
account_clients = {}
stats_today = {"count":0}
stealth_counter = {}

async def get_user_client(acc_key):
    if acc_key in account_clients:
        try:
            c=account_clients[acc_key]
            if await c.get_me(): return c
        except: pass
    acc=db["accounts"].get(acc_key)
    if not acc: return None
    c=Client(acc_key, api_id=app.api_id, api_hash=app.api_hash, session_string=acc["session"], in_memory=True)
    await c.start(); account_clients[acc_key]=c; return c

async def notify_admin(kind, uid):
    try:
        u=await app.get_users(uid)
        full=f"{u.first_name or ''} {u.last_name or ''}".strip() or "بدون اسم"
        username=f"@{u.username}" if u.username else "بدون يوزر"
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if kind=="new": msg=f"🔔 دخل مستخدم جديد للبوت\n\n👤 الاسم: {full}\n🔗 اليوزر: {username}\n🆔 الايدي: `{uid}`\n🕐 الوقت: {now}\n👥 عدد المستخدمين الكلي: {len(db.get('users',{}))}"
        else: msg=f"🔔 اشتراك جديد بقناة البوت\n\nقام {full}\n🔗 اليوزر: {username}\n🆔 الايدي: `{uid}`\n🕐 الوقت: {now}\nبالاشتراك بقناة البوت\n\n👥 عدد المشتركين الكلي: {len(db.get('subscribed',[]))}"
        await app.send_message(owner, msg)
    except Exception as ex: print("notify:",ex)

async def subscription(message):
    uid=message.from_user.id
    ch=get_forced()
    if not ch or ch=="NEED_FORWARD": return True
    if is_admin(uid): return True
    try:
        await app.get_chat_member(ch, uid); return True
    except UserNotParticipant: return ch
    except: return True

def timeCalc(limit):
    start=datetime.now(_timezone); end=start+timedelta(days=limit)
    return {"current_date":start.strftime("%Y-%m-%d"),"end_date":end.strftime("%Y-%m-%d"),"endTime":end.strftime("%H:%M"),"hours":limit*24,"minutes":limit*24*60}

# ===== START - نفس الكود الثاني + احالة الكود الاول =====
@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    uid=message.from_user.id
    ref_code=None
    if len(message.command)>1 and message.command[1].startswith("ref_"): ref_code=message.command[1].replace("ref_","")
    is_new=str(uid) not in db["users"]
    db["users"][str(uid)]={"name":message.from_user.first_name or "","username":message.from_user.username or "","id":uid,"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}; save()
    if is_new and uid!=owner:
        await notify_admin("new", uid)
        if ref_code and ref_code!=str(uid) and ref_code in db["users"]:
            db.setdefault("referrals",{})
            if ref_code not in db["referrals"]: db["referrals"][ref_code]={"invited":[],"rewarded":False}
            if uid not in db["referrals"][ref_code]["invited"]:
                db["referrals"][ref_code]["invited"].append(uid); save()
                cnt=len(db["referrals"][ref_code]["invited"])
                try: await app.send_message(int(ref_code), f"👥 احالة جديدة!\nواحد دخل من رابطك، صار عندك {cnt}/3\nاذا وصلت 3 تاخذ يوم VIP مجاني 🎁")
                except: pass
                if cnt>=3 and not db["referrals"][ref_code].get("rewarded"):
                    db["referrals"][ref_code]={"invited":[],"rewarded":False}
                    old=db["vip"].get(ref_code)
                    if old and old.get("expire")!="lifetime":
                        try: new_exp=datetime.fromisoformat(old["expire"])+timedelta(days=1)
                        except: new_exp=datetime.now()+timedelta(days=1)
                    else: new_exp=datetime.now()+timedelta(days=1)
                    db["vip"][ref_code]={"expire":new_exp.isoformat(),"notified":False}; save()
                    try: await app.send_message(int(ref_code), "🎁 مبروك! جبت 3 احالات\nحصلت على يوم VIP مجاني 👑")
                    except: pass
    # اشتراك اجباري - مثل الكود الثاني
    sub=await subscription(message)
    if isinstance(sub, str):
        return await message.reply(f"- عذرا عزيزي عليك الإشتراك بقناة البوت أولا لتتمكن استخدامه\n- القناه: {sub}\n- اشترك ثم ارسل /start")
    if not is_vip(uid):
        return await message.reply(f"❌ غير مشترك VIP\nراسل المطور:\n{DEV}\n\n🎁 او جيب 3 اشخاص من رابطك وتاخذ يوم VIP مجاني!", reply_markup=refMarkupForAll)
    await message.reply("- مرحبا بك عزيزي في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات", reply_markup=mainMarkup(uid), reply_to_message_id=message.id)

@app.on_callback_query(filters.regex(r"^(toHome|main)$"))
async def toHome(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid==owner: pass
    elif not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    await callback.message.edit_text("- مرحبا بك عزيزي في بوت النشر التلقائي", reply_markup=mainMarkup(uid))

@app.on_callback_query(filters.regex(r"^(checkForced)$"))
async def checkForced(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    await sleep(2)
    if await subscription(callback.message):
        if not is_vip(uid): return await callback.message.edit_text(f"❌ غير VIP\nراسل: {DEV}", reply_markup=Markup([[Button("📩 راسل المطور", url=f"https://t.me/{DEV.replace('@','')}")]]))
        if uid!=owner and uid not in db.get("subscribed",[]):
            db["subscribed"].append(uid); save(); await notify_admin("sub", uid)
        await callback.message.edit_text("- مرحبا بك في بوت النشر", reply_markup=mainMarkup(uid))
    else:
        ch=get_forced()
        await callback.message.edit_text(f"⚠️ ما اشتركت بعد!\nاشترك:\n{ch}", reply_markup=Markup([[Button("📢 اشترك", url=f"https://t.me/{str(ch).replace('@','')}")],[Button("✅ تحققت", callback_data="checkForced")]]))

# ===== معلومات + احالة + تخفي - للكل، حتى اللي مو VIP =====
@app.on_callback_query(filters.regex(r"^(aboutBot)$"))
async def aboutBot(_: Client, callback: CallbackQuery):
    txt="""ℹ️ معلومات حول البوت - شنو يسوي بالتفصيل؟

🚀 النشر:
- تضيف حساباتك التليجرام للبوت
- تضيف المجموعات اللي تريد تنشر بيها
- تكتب كليشة النشر (نص + صورة او فيديو اختياري) - كليشة وحدة او عدة كلايش
- البوت ينشر الكليشة بكل المجموعات تلقائياً

🛡️ الحماية - مثل الكود الثاني:
1. حلقة وحدة: ينشر سوبر ورا سوبر، مو 6 رسائل بنفس الثانية
2. انتظار صغير بين كل سوبر وسوبر: 5-15 ثانية عشوائي
3. تأخير عشوائي 60-120 ثانية بين كل دورة
4. ايقاف تلقائي اذا انحظر او انطرد
5. ايقاف اجباري طوارئ

🥷 وضع التخفي:
- النشرة 1 و 2: نشر عادي
- النشرة 3: رد على رسالة موجودة بنفس نص النشر

👥 الاحالة: كل 3 يدخلون من رابطك = يوم VIP مجاني
👑 VIP: نشر اسرع، حسابات اكثر
"""
    uid=callback.from_user.id
    back=Markup([[Button("- العوده -", callback_data="toHome")]]) if is_vip(uid) else refMarkupForAll
    await callback.message.edit_text(txt, reply_markup=back)

@app.on_callback_query(filters.regex(r"^(myRef)$"))
async def myRef(_: Client, callback: CallbackQuery):
    uid=str(callback.from_user.id)
    me=await app.get_me()
    link=f"https://t.me/{me.username}?start=ref_{uid}"
    cnt=len(db.get("referrals",{}).get(uid,{"invited":[]}).get("invited",[]))
    back=Markup([[Button("- العوده -", callback_data="toHome")]]) if is_vip(int(uid)) else refMarkupForAll
    await callback.message.edit_text(f"👥 نظام الاحالة 🎁\n\n🔗 رابطك:\n{link}\n\n👥 جبت: {cnt}/3\n🎁 كل 3 اشخاص يدخلون من رابطك تاخذ يوم VIP مجاني!", reply_markup=back)

@app.on_callback_query(filters.regex(r"^(stealthInfo)$"))
async def stealthInfo(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid!=owner and not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    s=get_settings(uid); cur=s.get("stealth_enabled",False)
    txt=f"""🥷 وضع التخفي
اذا شغلته:
النشر الاول والثاني: ينشر عادي
النشر الثالث: يرد على رسالة موجودة بالسوبر بنفس نص النشر بالضبط
الحالة الحالية: {'✅ شغال' if cur else '❌ مطفي'}
"""
    btn=Button("❌ طفي التخفي", callback_data="toggleStealth") if cur else Button("✅ شغل التخفي", callback_data="toggleStealth")
    await callback.message.edit_text(txt, reply_markup=Markup([[btn],[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(toggleStealth)$"))
async def toggleStealth(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    s=get_settings(uid); s["stealth_enabled"]=not s.get("stealth_enabled",False); save()
    await callback.answer(f"{'تم تشغيل التخفي 🥷' if s['stealth_enabled'] else 'تم اطفاء التخفي'}", show_alert=True)
    await stealthInfo(_, callback)

# ===== الحسابات - مثل الكود الثاني login + كل خواص الكود الاول =====
@app.on_callback_query(filters.regex(r"^(accounts)$"))
async def accountsMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid!=owner and not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid or is_admin(uid)]
    txt="📁 الحسابات\n\n"
    for k,v in accs: txt+=f"{v.get('phone',k)} - {v.get('status','🟢')}{' ⛔ ايقاف' if is_force(k) else ''}\n"
    if not accs: txt+="لا توجد حسابات"
    markup=[]
    for k,v in accs: markup.append([Button(v.get('phone',k), callback_data="noop"), Button("🗑 حذف", callback_data=f"delAcc_{k}")])
    markup.append([Button("- ➕ اضافة -", callback_data="addAcc")]); markup.append([Button("- العوده -", callback_data="toHome")])
    await callback.message.edit_text(txt, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(addAcc)$"))
async def addAcc(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid!=owner and not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    await callback.message.delete()
    try: ask=await listener.listen(from_id=uid, chat_id=uid, text="- أرسل رقم الهاتف الخاص بك: \n\n- يمكنك ارسال /cancel لإلغاء التسجيل.", reply_markup=ForceReply(selective=True, placeholder="+9647700000"), timeout=30)
    except exceptions.TimeOut: return await callback.message.reply("- نفد وقت استلام رقم الهاتف", reply_markup=backMarkup)
    if ask.text=="/cancel": return await ask.reply("- تم إلغاء العمليه.", reply_to_message_id=ask.id)
    create_task(registration(ask))

async def registration(message: Message):
    uid=message.from_user.id; _number=message.text
    lmsg=await message.reply("- جارٍ تسجيل الدخول إلى حسابك")
    reMarkup=Markup([[Button("- إعادة المحاوله -", callback_data="addAcc"), Button("- العوده -", callback_data="toHome")]])
    client=Client("registration", in_memory=True, api_id=app.api_id, api_hash=app.api_hash)
    await client.connect()
    try: p_code_hash=await client.send_code(_number)
    except PhoneNumberInvalid: return await lmsg.edit_text("- رقم الهاتف الذي ادخلته خاطئ", reply_markup=reMarkup)
    try: code=await listener.listen(from_id=uid, chat_id=uid, text="- تم ارسال كود إلى خاصك قم بإرساله من فضلك.", timeout=120, reply_markup=ForceReply(selective=True, placeholder="1 2 3 4 5 6"))
    except exceptions.TimeOut: return await lmsg.reply("- نفذ وقت استلام الكود.", reply_markup=reMarkup)
    try: await client.sign_in(_number, p_code_hash.phone_code_hash, code.text.replace(" ",""))
    except PhoneCodeInvalid: return await code.reply("- لقد قمت بإدخال كود خاطئ.", reply_markup=reMarkup, reply_to_message_id=code.id)
    except PhoneCodeExpired: return await code.reply("- الكود منتهي الصلاحية.", reply_markup=reMarkup, reply_to_message_id=code.id)
    except SessionPasswordNeeded:
        try: password=await listener.listen(from_id=uid, chat_id=uid, text="- ادخل كلمة مرور التحقق بخطوتين من فضلك.", reply_markup=ForceReply(selective=True, placeholder="- YOUR PASSWORD: "), timeout=180, reply_to_message_id=code.id)
        except exceptions.TimeOut: return await lmsg.reply("- نفذ وقت استلام كلمة المرور.", reply_markup=reMarkup)
        try: await client.check_password(password.text)
        except PasswordHashInvalid: return await password.reply("- كلمة مرور خاطئه.", reply_markup=reMarkup)
    session=await client.export_session_string()
    await client.disconnect()
    key=f"acc_{int(datetime.now().timestamp())}_{random.randint(100,999)}"
    db["accounts"][key]={"owner":uid,"session":session,"phone":_number,"status":"🟢 موجود","reason":"-"}; save()
    await app.send_message(uid, f"تم اضافة ✅ {_number}\n\nهل تريد انضمام الحساب للمجموعات؟", reply_markup=Markup([[Button("✅ اي نعم", callback_data=f"joinPrompt_{key}")],[Button("❌ لا، بعدين", callback_data="toHome")]]))

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
    markup=[]
    for gid,g in grps: markup.append([Button(f"➕ انضمام | {g.get('title',gid)[:30]}", callback_data=f"doJoin_{key}_{gid}")])
    markup.append([Button("✅ تم", callback_data="toHome")])
    await callback.message.edit_text("📋 اختر المجموعات اللي تريد الحساب ينضم الها:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(doJoin_)"))
async def doJoin(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    try: _,key,gid=callback.data.split("_",2)
    except: return await callback.answer("خطأ", show_alert=True)
    acc=db["accounts"].get(key)
    if not acc: return await callback.answer("الحساب مو موجود", show_alert=True)
    g=db["groups"].get(gid); link=g.get("link") if isinstance(g,dict) else g
    try:
        client=await get_user_client(key)
        # Pyrogram: join_chat يقبل الرابط او الايدي
        try: await client.join_chat(link if link else int(gid))
        except Exception as e:
            if "already" in str(e).lower() or "participant" in str(e).lower(): pass
            else: raise e
        await callback.answer("تم الانضمام ✅")
        markup=[]
        for gid2,g2 in db["groups"].items():
            if g2.get("owner")!=uid and not is_admin(uid): continue
            title2=g2.get("title",gid2) if isinstance(g2,dict) else str(g2)
            if gid2==gid: markup.append([Button(f"✅ انضم | {title2[:30]}", callback_data=f"done_{key}_{gid2}")])
            else: markup.append([Button(f"➕ انضمام | {title2[:30]}", callback_data=f"doJoin_{key}_{gid2}")])
        markup.append([Button("✅ تم", callback_data="toHome")])
        await callback.message.edit_text("📋 اختر المجموعات اللي تريد الحساب ينضم الها:", reply_markup=Markup(markup))
    except Exception as ex: await callback.answer(f"فشل: {ex}", show_alert=True)

# ===== المجموعات - مثل الكود الثاني newSuper/currentSupers + خواص الكود الاول =====
@app.on_callback_query(filters.regex(r"^(groups)$"))
async def groupsMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid!=owner and not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid or is_admin(uid)]
    txt="👥 المجموعات\n\n"
    for k,v in grps: txt+=f"{v.get('title',k)}\n"
    if not grps: txt+="لا توجد مجموعات"
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
    try: ask=await listener.listen(from_id=uid, chat_id=uid, text="- ارسل رابط السوبر لإضافته.\n- يمكنك ارسال /cancel لألغاء العمليه.", reply_markup=ForceReply(selective=True, placeholder="- Super group URL: "), timeout=60)
    except exceptions.TimeOut: return await callback.message.reply("نفذ وقت استلام الرابط", reply_markup=backMarkup)
    if ask.text=="/cancel": return await ask.reply("- تم إلغاء العمليه", reply_to_message_id=ask.id)
    # نفس منطق الكود الثاني: اضافة سوبر، وبعدين الانضمام مثل الكود الاول
    create_task(add_group_logic(ask, callback.data))

async def add_group_logic(message, chosen):
    uid=message.from_user.id; link=message.text.strip()
    accs=[]
    if chosen.startswith("addGrpAcc_"):
        ak=chosen.replace("addGrpAcc_","")
        if ak in db["accounts"] and db["accounts"][ak]["owner"]==uid: accs=[(ak, db["accounts"][ak])]
        else: return await message.reply("الحساب مو موجود")
        mode_txt=f"للحساب {db['accounts'][ak].get('phone')}"
    else:
        accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid]; mode_txt="لجميع الحسابات"
    if not accs: return await message.reply("ما عندك حساب")
    await message.reply(f"جاري دخول {mode_txt} ... ⏳")
    joined=0; skipped=0; failed=""; gid_final=None; title_final=link
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
        except Exception as ex: failed+=f"\n{acc.get('phone')}: {ex}"
    if not gid_final: return await message.reply(f"❌ فشل\n{failed}", reply_markup=mainMarkup(uid))
    db["groups"][gid_final]={"owner":uid,"title":title_final,"link":link}; save()
    await message.reply(f"تم ✅ ({mode_txt})\n✅ دخل: {joined}\n⏭️ موجود: {skipped}\n🆔 {gid_final}\n{failed}", reply_markup=mainMarkup(uid))

@app.on_callback_query(filters.regex(r"^(delGrp_)"))
async def delGrpAsk(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; grp_id=callback.data.replace("delGrp_","")
    grp_title=db["groups"].get(grp_id,{}).get("title",grp_id)[:30]
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    markup=[[Button("🚪 مغادرة بكل الحسابات", callback_data=f"leaveGrp_{grp_id}__ALL")]]
    for k in accs: markup.append([Button(f"🚪 مغادرة {db['accounts'][k].get('phone',k)}", callback_data=f"leaveGrp_{grp_id}__{k}")])
    markup.append([Button("🗑 حذف من البوت فقط", callback_data=f"delOnly_{grp_id}")]); markup.append([Button("🔙 رجوع", callback_data="groups")])
    await callback.message.edit_text(f"🚪 حذف:\n{grp_title}\nالحساب يغادر فعلاً؟", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(leaveGrp_)"))
async def leaveGrp(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; rest=callback.data.replace("leaveGrp_",""); grp_id,acc_part=rest.split("__",1) if "__" in rest else (rest,"ALL")
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
    grp_title=db["groups"].get(grp_id,{}).get("title",grp_id); ok=0; fail=0
    for a in accs:
        try:
            client=await get_user_client(a)
            # ايقاف النشر لهاي المجموعة
            stop_post(uid,a,grp_id)
            await client.leave_chat(int(grp_id)); ok+=1
        except: fail+=1
    db["groups"].pop(grp_id,None); save()
    await callback.message.edit_text(f"تم ✅\n🚪 غادر: {ok}\n❌ فشل: {fail}\n{grp_title}", reply_markup=backMarkup)

@app.on_callback_query(filters.regex(r"^(delOnly_)"))
async def delOnly(_: Client, callback: CallbackQuery):
    grp_id=callback.data.replace("delOnly_",""); db["groups"].pop(grp_id,None); save()
    await callback.message.edit_text("تم حذف من البوت فقط ✅", reply_markup=backMarkup)

# ===== النشر - ببرمجة الكود الثاني + كل خواص الكود الاول =====
@app.on_callback_query(filters.regex(r"^(posting)$"))
async def postingMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    if uid!=owner and not is_vip(uid): return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)
    markup=Markup([[Button("- ▶️ بدء -", callback_data="startPost"), Button("- ⏹️ ايقاف -", callback_data="stopPost")],[Button("- 📝 الكليشة -", callback_data="setCaption")],[Button("- ⏱️ المدة -", callback_data="setDelay")],[Button("- ⚙️ اعدادات -", callback_data="autoSettings")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text("🚀 النشر", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(setCaption)$"))
async def setCaption(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; s=get_settings(uid)
    cur_mode=s.get("caption_mode","single"); cur_count=len(s.get("captions",[]))
    markup=Markup([[Button("- 📝 كليشة وحدة -", callback_data="captionSingle")],[Button("- 📝 عدة كلايش -", callback_data="captionMulti")],[Button("- 📋 عرض الكلايش الحالية -", callback_data="captionShow")],[Button("- العوده -", callback_data="toHome")]])
    await callback.message.edit_text(f"📝 الكليشة\n\nالوضع الحالي: {'عدة كلايش' if cur_mode=='multi' else 'كليشة وحدة'}\nعدد الكلايش: {cur_count}\n\nشلون تريد تنشر؟", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(captionSingle)$"))
async def captionSingle(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    await callback.message.delete()
    try: ask=await listener.listen(from_id=uid, chat_id=uid, text="📝 دز الكليشة الوحدة:\nمثال: اهلا بكم 🔥", reply_markup=ForceReply(selective=True), timeout=120)
    except exceptions.TimeOut: return await callback.message.reply("- انتهى الوقت.")
    s=get_settings(uid); s["caption"]=ask.text; s["captions"]=[ask.text]; s["caption_mode"]="single"; save()
    await ask.reply(f"✅ تم حفظ كليشة وحدة:\n{ask.text}\n\nهسه النشر راح يكون بنفس الكليشة دائماً", reply_to_message_id=ask.id, reply_markup=toHomeMarkup)

@app.on_callback_query(filters.regex(r"^(captionMulti)$"))
async def captionMulti(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    await callback.message.delete()
    try: ask=await listener.listen(from_id=uid, chat_id=uid, text="📝 دز عدة كلايش، كل كليشة بسطر:\n\nمثال:\nاهلا بكم 🔥\nعرض اليوم خصم 50%\nتوصيل لكل المحافظات 🚀\n\nالبوت كل نشرة راح يختار وحدة عشوائياً", reply_markup=ForceReply(selective=True), timeout=120)
    except exceptions.TimeOut: return await callback.message.reply("- انتهى الوقت.")
    lines=[l.strip() for l in (ask.text or "").split("\n") if l.strip()]
    if len(lines)<2: return await ask.reply("⚠️ لازم تدز كليشتين على الاقل، كل وحدة بسطر", reply_to_message_id=ask.id)
    s=get_settings(uid); s["captions"]=lines; s["caption"]=lines[0]; s["caption_mode"]="multi"; save()
    txt2="✅ تم حفظ عدة كلايش:\n\n"+"\n".join([f"{i}. {c}" for i,c in enumerate(lines,1)])+"\n\n🎲 البوت كل نشرة راح يختار وحدة عشوائياً"
    await ask.reply(txt2, reply_to_message_id=ask.id, reply_markup=toHomeMarkup)

@app.on_callback_query(filters.regex(r"^(captionShow)$"))
async def captionShow(_: Client, callback: CallbackQuery):
    s=get_settings(callback.from_user.id); caps=s.get("captions",[])
    txt="📋 الكلايش الحالية:\n\n"+"\n".join([f"{i}. {c}\n---" for i,c in enumerate(caps,1)]) if caps else "ماكو كلايش"
    await callback.message.edit_text(txt, reply_markup=Markup([[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(setDelay)$"))
async def setDelay(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; s=get_settings(uid)
    await callback.message.delete()
    try: ask=await listener.listen(from_id=uid, chat_id=uid, text="ارسل المدة بالثواني." if not s["random_enabled"] else "ارسل هكذا: 60-120", reply_markup=ForceReply(selective=True), timeout=60)
    except exceptions.TimeOut: return await callback.message.reply("- انتهى الوقت.")
    if s["random_enabled"]:
        try: a,b=ask.text.split("-"); s["delay_min"]=int(a); s["delay_max"]=int(b); save(); await ask.reply(f"تم: {a}-{b} 🎲", reply_markup=toHomeMarkup)
        except: await ask.reply("ارسل 60-120")
    else:
        try:
            d=int(ask.text)
            if d<60:
                s["delay"]=30; save(); await ask.reply("تم 30 ثانية ⚠️", reply_markup=toHomeMarkup)
            else: s["delay"]=d; save(); await ask.reply(f"تم: {d} ثانية ✅", reply_markup=toHomeMarkup)
        except: await ask.reply("ارسل رقم")

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
        try: ask=await listener.listen(from_id=uid, chat_id=uid, text="ارسل الصورة:", reply_markup=ForceReply(selective=True), timeout=60)
        except exceptions.TimeOut: return await callback.message.reply("- انتهى الوقت.")
        if ask.photo or ask.video:
            path=f"media_{uid}.jpg"; await ask.download(path); s["media_file"]=path; s["media_type"]="photo" if ask.photo else "video"; save()
            await ask.reply("تم حفظ ✅", reply_markup=toHomeMarkup)
        else: await ask.reply("ارسل صورة")
        return
    if key=="stealth_enabled":
        await callback.message.edit_text(f"{'✅ تم تشغيل وضع التخفي 🥷\nهسه كل 3 نشرات، الثالثة راح تكون رد بنفس نص النشر.' if s[key] else '❌ تم اطفاء وضع التخفي'}", reply_markup=Markup([[Button("- العوده -", callback_data="autoSettings")]])); return
    await callback.message.edit_text("تم ✅", reply_markup=Markup([[Button("- العوده -", callback_data="autoSettings")]]))

# ===== ايقاف / بدء - مثل الكود الثاني، بس لكل حساب ومجموعة مثل الكود الاول =====
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
    txt="⛔ الايقاف الاجباري:\n\n"; markup=[]
    for acc_key in forced:
        phone=db["accounts"].get(acc_key,{}).get("phone",acc_key); txt+=f"{phone} ⛔\n"
        markup.append([Button(f"✅ الغاء + شغل: {phone}", callback_data=f"unforceAndStart_{acc_key}")]); markup.append([Button(f"✅ الغاء فقط: {phone}", callback_data=f"unforce_{acc_key}")])
    for k,v in blocked:
        ap=db["accounts"].get(v.get("acc"),{}).get("phone",v.get("acc")); gt=db["groups"].get(v.get("grp"),{}).get("title",v.get("grp"))[:20]; txt+=f"{ap} - {gt}\n"
        markup.append([Button(f"✅ الغاء حظر: {ap} - {gt}", callback_data=f"unblock_{v.get('acc')}__{v.get('grp')}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text(txt, reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(unforceAndStart_|unforce_)"))
async def unforceCb(_: Client, callback: CallbackQuery):
    acc_key=callback.data.replace("unforceAndStart_","").replace("unforce_","")
    if unforce_acc(acc_key):
        phone=db["accounts"].get(acc_key,{}).get("phone",acc_key)
        await callback.message.edit_text(f"✅ تم الغاء الايقاف {phone}\nهسه رجع طبيعي.", reply_markup=Markup([[Button("▶️ بدء النشر", callback_data="startPost")],[Button("- العوده -", callback_data="toHome")]]))
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
        if is_force(k): markup.append([Button(label+" ⛔ موقوف - الغاء", callback_data=f"unforce_{k}")])
        else: markup.append([Button(label, callback_data=f"{mode}PostAcc_{k}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text("اختر الحساب:", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(stopPostForce)$"))
async def stopForceMenu(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id
    accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
    if not accs: return await callback.message.edit_text("ما عندك حساب", reply_markup=backMarkup)
    markup=[[Button("⛔ ايقاف لكل الحسابات", callback_data="force_ALL")]]
    for k in accs:
        label=db["accounts"][k].get("phone",k)
        if is_force(k): label+=" ⛔ موقوف"
        markup.append([Button(f"⛔ ايقاف: {label}", callback_data=f"force_{k}")])
    markup.append([Button("- العوده -", callback_data="posting")])
    await callback.message.edit_text("⛔ ايقاف اجباري طوارئ", reply_markup=Markup(markup))

@app.on_callback_query(filters.regex(r"^(force_)"))
async def forceCb(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; acc_key=callback.data.replace("force_","")
    if acc_key=="ALL":
        for k in [kk for kk,v in db["accounts"].items() if v["owner"]==uid]: stop_all_acc(uid,k); force_acc(k)
        return await callback.message.edit_text("⛔ تم ايقاف كل الحسابات ✅", reply_markup=Markup([[Button("✅ الغاء الايقاف", callback_data="unblockList")],[Button("- العوده -", callback_data="toHome")]]))
    cnt=stop_all_acc(uid,acc_key); force_acc(acc_key); phone=db["accounts"].get(acc_key,{}).get("phone",acc_key)
    await callback.message.edit_text(f"⛔ تم ايقاف {phone} ✅\nتم ايقاف {cnt} نشر.", reply_markup=Markup([[Button("✅ الغاء الايقاف", callback_data="unblockList")],[Button("- العوده -", callback_data="toHome")]]))

@app.on_callback_query(filters.regex(r"^(startPostAcc_|stopPostAcc_|startPost_ALL|stopPost_ALL)"))
async def chooseGrpForPost(_: Client, callback: CallbackQuery):
    uid=callback.from_user.id; data=callback.data
    mode="start" if data.startswith("start") else "stop"
    acc_part="ALL" if data.endswith("_ALL") else data.replace(f"{mode}PostAcc_","")
    if mode=="start" and acc_part!="ALL" and is_force(acc_part):
        phone=db["accounts"].get(acc_part,{}).get("phone",acc_part)
        return await callback.message.edit_text(f"⛔ {phone} موقوف اجبارياً", reply_markup=Markup([[Button("✅ الغاء + شغل", callback_data=f"unforceAndStart_{acc_part}")],[Button("- العوده -", callback_data="posting")]]))
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
    # ===== نفس منطق الكود الثاني: حلقة وحدة لكل مستخدم، مو مهام متوازية =====
    if mode=="start":
        # نفحص الايقاف والحظر قبل البدء
        for a in accs:
            if is_force(a): return await callback.message.edit_text("⛔ موقوف اجبارياً", reply_markup=Markup([[Button(f"✅ الغاء: {db['accounts'][a].get('phone',a)}", callback_data=f"unforceAndStart_{a}")],[Button("- العوده -", callback_data="posting")]]))
        key=f"{uid}_posting"
        if key in posting_tasks: return await callback.message.edit_text("⚠️ النشر شغال اصلاً", reply_markup=backMarkup)
        # نخزن الاختيار ونبدأ حلقة وحدة
        db["settings"][str(uid)]["last_post_accs"]=accs
        db["settings"][str(uid)]["last_post_groups"]=grps
        save()
        posting_tasks[key]=create_task(posting_loop_pyrogram(uid))
        s=get_settings(uid); caps=s.get("captions",[s.get("caption","")])
        await callback.message.edit_text(f"✅ بدء النشر 🔁\nالوضع: {'عدة كلايش ('+str(len(caps))+') 🎲' if s.get('caption_mode')=='multi' else 'كليشة وحدة 📝'}\nالكليشة: {s.get('caption','')[:100]}", reply_markup=backMarkup)
    else:
        key=f"{uid}_posting"
        if key in posting_tasks: posting_tasks[key].cancel(); del posting_tasks[key]; await callback.message.edit_text("⏹️ تم ايقاف النشر ✅", reply_markup=backMarkup)
        else: await callback.message.edit_text("⚠️ متوقف اصلاً", reply_markup=backMarkup)

def stop_post(uid,acc_key,grp_id):
    # للتوافق مع الكود الاول - نوقف الحلقة الكاملة اذا كانت تشمل هالمجموعة
    key=f"{uid}_posting"
    if key in posting_tasks:
        # اذا كان النشر لحساب ومجموعة وحدة فقط، نوقفه
        s=get_settings(uid)
        if s.get("last_post_accs")==[acc_key] and s.get("last_post_groups")==[grp_id]:
            posting_tasks[key].cancel(); del posting_tasks[key]; return True
    return False
def stop_all_acc(uid,acc_key):
    key=f"{uid}_posting"
    if key in posting_tasks: posting_tasks[key].cancel(); del posting_tasks[key]; return 1
    return 0

# ===== النشر Pyrogram - نفس posting() مال الكود الثاني =====
async def posting_loop_pyrogram(uid):
    s=get_settings(uid)
    while True:
        try:
            accs=s.get("last_post_accs",[k for k,v in db["accounts"].items() if v["owner"]==uid])
            grps=s.get("last_post_groups",list(db["groups"].keys()))
            # نعيد قراءة الاعدادات كل دورة مثل الكود الثاني
            s=get_settings(uid)
            for acc_key in accs:
                if is_force(acc_key): continue
                for grp_id in grps:
                    if is_blocked(acc_key,grp_id): continue
                    ok=await send_one_pyrogram(uid,acc_key,grp_id)
                    if not ok and s.get("protect_enabled"):
                        # اذا انحظر او انطرد، نكمل للكروب اللي بعده مثل الكود الثاني
                        pass
                    # انتظار صغير بين كل سوبر وسوبر - مثل الكود الثاني + حماية
                    await sleep(random.randint(5,15))
            delay=random.randint(s["delay_min"],s["delay_max"]) if s["random_enabled"] else s["delay"]
            await sleep(delay)
        except asyncio.CancelledError: break
        except Exception as e: print(e); await sleep(10)

async def send_one_pyrogram(uid,acc_key,grp_id):
    s=get_settings(uid); acc=db["accounts"].get(acc_key)
    if not acc: return False
    if is_force(acc_key): return False
    if is_blocked(acc_key,grp_id): return False
    try:
        client=await get_user_client(acc_key)
        try: me=await client.get_me()
        except: raise AuthKeyUnregistered("جلسة منتهية")
        if s.get("caption_mode")=="multi" and s.get("captions"): caption_to_send=random.choice(s["captions"])
        else: caption_to_send=s.get("caption","اهلا بكم 🔥")
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
                    stats_today["count"]+=1; return True
                raise Exception("ماكو رسالة للرد")
            except: pass
        if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
            await client.send_photo(int(grp_id), s["media_file"], caption=caption_to_send)
        else:
            await client.send_message(int(grp_id), caption_to_send)
        stats_today["count"]+=1; return True
    except FloodWait as e:
        if s["protect_enabled"]: await app.send_message(owner, f"🛡️ FloodWait {e.value} للحساب {acc_key}")
        await sleep(e.value+5); return False
    except (UserDeactivated, AuthKeyUnregistered, SessionRevoked) as e:
        acc["status"]="معطل"; acc["reason"]=str(e); save()
        if s["protect_enabled"]: await app.send_message(uid, f"⚠️ حساب {acc_key} تعطل: {e}")
        return False
    except Exception as e:
        msg=str(e)
        if any(x in msg for x in ["USER_NOT_PARTICIPANT","UserNotParticipant","CHAT_WRITE_FORBIDDEN","ChatWriteForbidden","USER_KICKED","kicked","not participant","PEER_ID_INVALID"]) or "403" in msg or "banned from sending" in msg.lower() or "USER_BANNED" in msg:
            if "banned from sending" in msg.lower() or "USER_BANNED" in msg:
                await app.send_message(uid, f"⏳ حسابك انحظر مؤقتاً من الـ API (تقدر تراسل بيدك عادي)\nالبوت راح يوقف 4 ساعات حتى لا يتحول لحظر دائم")
                force_acc(acc_key); return False
            force_block(uid,acc_key,grp_id,f"انطرد: {e}")
            try:
                t2=db["groups"].get(str(grp_id),{}).get("title",grp_id)
                await app.send_message(uid, f"⛔ طرد تلقائي\nالحساب {acc.get('phone')} انطرد من:\n{t2}\nتم ايقاف النشر لهاي المجموعة فقط.")
            except: pass
            return False
        print(f"خطأ نشر: {e}")
        if s["protect_enabled"]: await app.send_message(uid, f"⚠️ خطأ نشر {acc_key}: {e}")
        return False

# ===== الادمن - نفس الكود الثاني admin + كل خواص الكود الاول =====
async def Owner(_, __: Client, message: Message): return (message.from_user.id==owner)
isOwner = filters.create(Owner)
adminMarkup = Markup([[Button("- الغاء VIP -", callback_data="cancelVIP"), Button("- تفعيل VIP -", callback_data="addVIP")],[Button("- الاحصائيات -", callback_data="statics"), Button("- قنوات الإشتراك -", callback_data="channels")]])

@app.on_message(filters.command("admin") & filters.private & isOwner)
@app.on_callback_query(filters.regex("toAdmin") & isOwner)
async def admin(_: Client, message: Union[Message, CallbackQuery]):
    fname=message.from_user.first_name; caption=f"مرحبا عزيزي [{fname}](tg://settings) في لوحة المالك"
    func=message.reply if isinstance(message, Message) else message.message.edit_text
    await func(caption, reply_markup=adminMarkup)

@app.on_callback_query(filters.regex(r"^(statics)$") & isOwner)
async def statics(_: Client, callback: CallbackQuery):
    ch=get_forced() or "مو مفعل"; ct="خاصة" if str(ch).startswith("-100") else ("عامة" if ch!="مو مفعل" else "")
    caption=f"- عدد المستخدمين الكلي: {len(db['users'])}\n- عدد الحسابات: {len(db['accounts'])}\n- عدد المجموعات: {len(db['groups'])}\n- شغال: {len(posting_tasks)}\n- اليوم: {stats_today['count']}\n- 📢 اجباري: {ch} {ct}\n\n- عدد مستخدمين VIP الحاليين: {len(db['vip'])}"
    await callback.message.edit_text(caption, reply_markup=Markup([[Button("- الصفحه الرئيسيه -", callback_data="toAdmin")]]))

@app.on_callback_query(filters.regex(r"^(vipAdmin)$") & isOwner)
async def vipAdmin(_: Client, callback: CallbackQuery):
    markup=Markup([[Button("➕ تفعيل VIP", callback_data="vipAdd"), Button("➖ الغاء VIP", callback_data="vipDel")],[Button("📋 قائمة VIP", callback_data="vipList"), Button("📢 اشتراك اجباري", callback_data="vipForced")],[Button("- العوده -", callback_data="toAdmin")]])
    await callback.message.edit_text("👑 VIP", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(vipAdd)$") & isOwner)
async def vipAdd(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    try: ask=await listener.listen(from_id=callback.from_user.id, chat_id=callback.from_user.id, text="- ارسل ايدي المستخدم ليتم تفعيل VIP له", reply_markup=ForceReply(selective=True, placeholder="- user id: "), timeout=30)
    except exceptions.TimeOut: return await callback.message.reply("- نفذ وقت استلام ايدي المستخدم.")
    try: await app.get_users(int(ask.text))
    except: return await ask.reply("- لم يتم ايجاد هذا المستخدم.")
    _id=int(ask.text)
    markup=Markup([[Button("📅 يوم", callback_data=f"vipDur_day_{_id}"), Button("📅 اسبوع", callback_data=f"vipDur_week_{_id}")],[Button("📅 شهر", callback_data=f"vipDur_month_{_id}"), Button("♾️ مدى", callback_data=f"vipDur_lifetime_{_id}")]])
    await ask.reply("اختر المدة:", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(vipDur_)") & isOwner)
async def vipDur(_: Client, callback: CallbackQuery):
    p=callback.data.split("_",3); dur=p[2]; target=p[3]
    if dur=="lifetime": exp="lifetime"
    else: exp=(datetime.now()+timedelta(days={"day":1,"week":7,"month":30}[dur])).isoformat()
    db["vip"][target]={"expire":exp,"notified":False}; save()
    await callback.message.edit_text(f"تم تفعيل VIP {target} ✅", reply_markup=Markup([[Button("- العوده -", callback_data="toAdmin")]]))

@app.on_callback_query(filters.regex(r"^(vipDel)$") & isOwner)
async def vipDel(_: Client, callback: CallbackQuery):
    await callback.message.delete()
    try: ask=await listener.listen(from_id=callback.from_user.id, chat_id=callback.from_user.id, text="- ارسل ايدي المستخدم ليتم الغاء VIP الخاص به", reply_markup=ForceReply(selective=True, placeholder="- user id: "), timeout=30)
    except exceptions.TimeOut: return await callback.mess