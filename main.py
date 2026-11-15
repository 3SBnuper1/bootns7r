# main.py - اصلاح الايقاف الاجباري - يرجع يشتغل بعد الالغاء
import asyncio, json, os, random, datetime, logging
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError, SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError, UserNotParticipantError

API_ID = int(os.getenv("API_ID", "9661697"))
API_HASH = os.getenv("API_HASH", "4ae76784fdfecd5df142004955bb8393")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN") or "9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8"
ADMIN_ID = int(os.getenv("ADMIN_ID", "5723475089"))
DEVELOPER = "@i999l9"
DATA_FILE = "data.json"
logging.basicConfig(level=logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("telethon.client.updates").setLevel(logging.CRITICAL)

def load():
    if not os.path.exists(DATA_FILE):
        return {"users":{}, "accounts":{}, "groups":{}, "vip":{}, "settings":{}, "blocked":{}, "force_stopped":[]}
    with open(DATA_FILE, encoding="utf-8") as f:
        d = json.load(f)
    if "blocked" not in d: d["blocked"] = {}
    if "force_stopped" not in d: d["force_stopped"] = []
    # تنظيف قديم: اذا اكو ALL عالق من النسخة القديمة، نمسحه لان هو سبب المشكلة
    if "ALL" in d["force_stopped"]:
        d["force_stopped"].remove("ALL")
    return d
def save():
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(db,f,ensure_ascii=False,indent=2)
db = load()
if "blocked" not in db: db["blocked"] = {}
if "force_stopped" not in db: db["force_stopped"] = []
if "ALL" in db["force_stopped"]:
    db["force_stopped"].remove("ALL"); save()

def get_settings(uid):
    uid=str(uid)
    if uid not in db["settings"]:
        db["settings"][uid]={"caption":"اهلا بكم 🔥","delay":60,"delay_min":60,"delay_max":120,
        "media_enabled":False,"protect_enabled":True,"report_enabled":True,"random_enabled":False,
        "media_file":None,"media_type":None,"forced_channel":None}
        save()
    return db["settings"][uid]
def get_forced_channel():
    s = db["settings"].get(str(ADMIN_ID), {})
    return s.get("forced_channel")
def is_admin(uid): return uid==ADMIN_ID
def is_vip(uid):
    if is_admin(uid): return True
    v=db["vip"].get(str(uid))
    if not v: return False
    if v.get("expire")=="lifetime": return True
    try:
        exp=datetime.datetime.fromisoformat(v["expire"])
        if datetime.datetime.now() > exp:
            del db["vip"][str(uid)]; save(); return False
        return True
    except: return False
def vip_left(uid):
    v=db["vip"].get(str(uid))
    if not v: return None
    if v.get("expire")=="lifetime": return "مدى الحياة ♾️"
    exp=datetime.datetime.fromisoformat(v["expire"])
    left=exp-datetime.datetime.now()
    return f"{left.days} يوم - ينتهي {exp.strftime('%Y-%m-%d %H:%M')}"

# --- الايقاف الاجباري - طوارئ ---
def is_account_force_stopped(acc_key):
    # فقط اذا اسم الحساب نفسه موجود بالقائمة - ماكو ALL بعد
    return acc_key in db.get("force_stopped", [])
def force_stop_account(acc_key):
    if acc_key not in db["force_stopped"]:
        db["force_stopped"].append(acc_key); save()
def unforce_account(acc_key):
    if acc_key in db["force_stopped"]:
        db["force_stopped"].remove(acc_key); save(); return True
    return False
def block_key(acc_key, grp_id): return f"{acc_key}__{grp_id}"
def is_blocked(acc_key, grp_id): return block_key(acc_key, grp_id) in db.get("blocked", {})
def force_block(uid, acc_key, grp_id, reason="انطرد"):
    db.setdefault("blocked", {})
    db["blocked"][block_key(acc_key, grp_id)] = {"owner":uid, "acc":acc_key, "grp":grp_id, "reason":reason, "time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save()

def main_kb(uid):
    rows=[[Button.inline("📁 إدارة الحسابات","accounts")]]
    rows.append([Button.inline("🚀 إدارة النشر","posting"), Button.inline("👥 إدارة المجموعات","groups")])
    if is_admin(uid):
        rows.append([Button.inline("📊 الإحصائيات","stats"), Button.inline("👑 قسم الـ VIP","vip_admin")])
    rows.append([Button.inline("👑 فحص اشتراكي","check_my_vip"), Button.inline("🔍 فحص الحسابات","check_acc")])
    return rows
def back_kb(): return [[Button.inline("🔙 رجوع","main")]]

bot = TelegramClient("bot", API_ID, API_HASH)
posting_tasks={}
stats_today={"count":0}
login_tmp={}
account_clients={}
tasks_started=False

async def get_account_client(acc_key):
    if acc_key in account_clients:
        try:
            c = account_clients[acc_key]
            if await c.is_user_authorized():
                return c
        except: pass
    acc = db["accounts"].get(acc_key)
    if not acc: return None
    client = TelegramClient(StringSession(acc["session"]), API_ID, API_HASH)
    await client.connect()
    account_clients[acc_key] = client
    print(f"✅ جلسة الحساب {acc.get('phone')} بقت نشطة")
    return client

async def resolve_group_id(client, grp_id_or_link):
    if isinstance(grp_id_or_link, str) and "t.me" in grp_id_or_link:
        link = grp_id_or_link.strip()
        try:
            if "t.me/+" in link or "t.me/joinchat/" in link:
                from telethon.tl.functions.messages import CheckChatInviteRequest
                h = link.split("+")[-1].split("/")[-1].split("?")[0]
                res = await client(CheckChatInviteRequest(h))
                if hasattr(res, "chat") and res.chat:
                    gid = str(res.chat.id)
                    return "-100"+gid if not gid.startswith("-100") else gid
            else:
                username = link.split("t.me/")[-1].split("/")[0].replace("@","").split("?")[0]
                ent = await client.get_entity(username)
                gid = str(ent.id)
                return "-100"+gid if gid.isdigit() and not gid.startswith("-100") else gid
        except Exception as e:
            print(f"فشل تحويل الرابط لايدي: {e}")
            return None
    return grp_id_or_link

async def leave_group_real(client, grp_id):
    try:
        ent = await client.get_entity(int(grp_id))
        try:
            from telethon.tl.functions.channels import LeaveChannelRequest
            await client(LeaveChannelRequest(ent))
            return True
        except Exception:
            pass
        try:
            from telethon.tl.functions.messages import DeleteChatUserRequest
            me = await client.get_me()
            await client(DeleteChatUserRequest(int(grp_id), me.id))
            return True
        except Exception:
            pass
        try:
            from telethon.tl.functions.messages import DeleteChatUserRequest
            me = await client.get_me()
            await client(DeleteChatUserRequest(ent, me.id))
            return True
        except Exception as e:
            print(f"فشل المغادرة: {e}")
            return False
    except Exception as e:
        print(f"فشل المغادرة get_entity: {e}")
        return False

async def check_forced(uid):
    ch = get_forced_channel()
    if not ch: return True
    if is_admin(uid): return True
    try:
        await bot.get_participant(ch, uid)
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return True

async def check_vip_gate(e, uid):
    if is_admin(uid): return True
    if not await check_forced(uid):
        ch = get_forced_channel()
        await e.respond(f"⚠️ الاشتراك الاجباري\n\nيجب عليك الاشتراك بالقناة اولاً حتى تستخدم البوت:\n{ch}\n\nبعد ما تشترك دوس /start",
        buttons=[[Button.url("📢 اشترك بالقناة", f"https://t.me/{ch.replace('@','')}")], [Button.inline("✅ تحققت من الاشتراك","check_forced")]])
        return False
    if not is_vip(uid):
        await e.respond(f"❌ انت غير مشترك VIP\n\nهذا البوت للمشتركين فقط.\n\nراسل المطور للتفعيل:\n{DEVELOPER}\n\nبعد التفعيل دز /start",
        buttons=[[Button.url("📩 راسل المطور", f"https://t.me/{DEVELOPER.replace('@','')}")]])
        return False
    return True

async def send_one(uid, acc_key, grp_id):
    s=get_settings(uid)
    acc=db["accounts"].get(acc_key)
    if not acc: return False
    if is_account_force_stopped(acc_key):
        print(f"⛔ ايقاف اجباري طوارئ: {acc_key}")
        return False
    if is_blocked(acc_key, grp_id):
        print(f"⛔ محظور: {acc_key} -> {grp_id}")
        return False
    try:
        client = await get_account_client(acc_key)
        if not await client.is_user_authorized():
            raise AuthKeyUnregisteredError("جلسة منتهية")
        real_id = grp_id
        if isinstance(grp_id, str) and ("t.me" in grp_id or "http" in grp_id):
            real_id = await resolve_group_id(client, grp_id)
            if real_id and real_id != grp_id and grp_id in db["groups"]:
                db["groups"][real_id] = db["groups"].pop(grp_id)
                save()
            if not real_id:
                await bot.send_message(uid, f"⚠️ ما كدرت احول رابط الكروب لايدي: {grp_id}")
                return False
        if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
            await client.send_file(int(real_id), s["media_file"], caption=s["caption"])
        else:
            await client.send_message(int(real_id), s["caption"])
        stats_today["count"]+=1
        print(f"✅ نشر: حساب {acc.get('phone')} -> كروب {real_id}")
        return True
    except FloodWaitError as e:
        if s["protect_enabled"]:
            await bot.send_message(ADMIN_ID, f"🛡️ حماية: حساب {acc_key} انحظر FloodWait {e.seconds} ثانية")
            return False
        await asyncio.sleep(e.seconds); return await send_one(uid,acc_key,grp_id)
    except (UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError) as e:
        acc["status"]="معطل"; acc["reason"]=str(e); save()
        if s["protect_enabled"]:
            await bot.send_message(uid, f"⚠️ حساب {acc_key} تعطل: {e}")
        return False
    except Exception as e:
        msg = str(e)
        if any(x in msg for x in ["USER_NOT_PARTICIPANT", "UserNotParticipant", "CHAT_WRITE_FORBIDDEN", "ChatWriteForbidden", "USER_KICKED", "kicked", "not participant", "CHAT_ADMIN_REQUIRED", "PEER_ID_INVALID"]) or "403" in msg:
            force_block(uid, acc_key, grp_id, f"انطرد تلقائياً: {e}")
            stop_post(uid, acc_key, grp_id)
            try:
                grp_title = db["groups"].get(str(grp_id), {}).get("title", grp_id)
                await bot.send_message(uid, f"⛔ كشف طرد تلقائي\n\nالحساب {acc.get('phone')} انطرد من المجموعة:\n{grp_title}\n\nتم ايقاف النشر لهاي المجموعة فقط تلقائياً.\nباقي المجموعات شغالة طبيعي.")
            except: pass
            print(f"⛔ انطرد: {acc_key} -> {grp_id}")
            return False
        print(f"خطأ نشر {acc_key} -> {grp_id}: {e}")
        if s["protect_enabled"]:
            await bot.send_message(uid, f"⚠️ خطأ بالنشر {acc_key}: {e}")
        return False

async def posting_loop(uid, acc_key, grp_id):
    s=get_settings(uid)
    print(f"▶️ بدأ النشر المستمر: {acc_key} -> {grp_id}")
    while True:
        try:
            if is_account_force_stopped(acc_key):
                print(f"⛔ ايقاف اجباري طوارئ، توقف: {acc_key}")
                break
            if is_blocked(acc_key, grp_id):
                print(f"⛔ محظور انطرد، توقف: {acc_key} -> {grp_id}")
                break
            await send_one(uid, acc_key, grp_id)
            delay=random.randint(s["delay_min"], s["delay_max"]) if s["random_enabled"] else s["delay"]
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print(f"⏹️ توقف النشر: {acc_key} -> {grp_id}")
            break
        except Exception as e:
            print(f"خطأ باللوب: {e}")
            await asyncio.sleep(10)

def start_post(uid, acc_key, grp_id):
    if is_account_force_stopped(acc_key):
        return "force_stopped"
    if is_blocked(acc_key, grp_id):
        return "blocked"
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks: return False
    posting_tasks[key]=asyncio.create_task(posting_loop(uid,acc_key,grp_id))
    return True
def stop_post(uid, acc_key, grp_id):
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks:
        posting_tasks[key].cancel(); del posting_tasks[key]; return True
    return False
def stop_all_for_account(uid, acc_key):
    cnt=0
    for k in list(posting_tasks.keys()):
        if k.startswith(f"{uid}_{acc_key}_"):
            posting_tasks[k].cancel(); del posting_tasks[k]; cnt+=1
    return cnt

async def vip_checker():
    while True:
        now=datetime.datetime.now()
        for uid,v in list(db["vip"].items()):
            if v.get("expire")=="lifetime": continue
            try:
                exp=datetime.datetime.fromisoformat(v["expire"])
                if (exp-now).total_seconds() <= 86400 and not v.get("notified"):
                    v["notified"]=True; save()
                    try: await bot.send_message(int(uid),"⚠️ تنبيه: اشتراكك الـ VIP راح يخلص باجر!")
                    except: pass
                if now>exp:
                    del db["vip"][uid]; save()
                    try: await bot.send_message(int(uid),"❌ انتهى اشتراكك الـ VIP")
                    except: pass
            except: pass
        await asyncio.sleep(3600)

async def daily_report():
    while True:
        now=datetime.datetime.now()
        target=now.replace(hour=23,minute=59,second=0)
        if target<now: target+=datetime.timedelta(days=1)
        await asyncio.sleep((target-now).total_seconds())
        for uid,s in list(db["settings"].items()):
            if s.get("report_enabled"):
                try: await bot.send_message(int(uid), f"📊 تقرير يومي\nنشرت اليوم: {stats_today['count']} رسالة")
                except: pass
        stats_today["count"]=0

user_state={}

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid=e.sender_id; sender=await e.get_sender()
    is_new=str(uid) not in db["users"]
    db["users"][str(uid)]={"name":sender.first_name or "","username":sender.username or "","id":uid,"time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save()
    if is_new and uid!=ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"🔔 دخل مستخدم جديد\nالاسم: {sender.first_name}\nاليوزر: @{sender.username}\nالايدي: {uid}\nالوقت: {db['users'][str(uid)]['time']}")
    if not await check_vip_gate(e, uid):
        return
    await e.respond("🤖 بوت النشر التلقائي\nاهلا بك في لوحة التحكم", buttons=main_kb(uid))

@bot.on(events.CallbackQuery)
async def cb(e):
    uid=e.sender_id; data=e.data.decode()
    if data=="check_forced":
        if await check_forced(uid):
            if not is_vip(uid) and not is_admin(uid):
                await e.edit(f"❌ انت غير مشترك VIP\n\nراسل المطور للتفعيل:\n{DEVELOPER}", buttons=[[Button.url("📩 راسل المطور", f"https://t.me/{DEVELOPER.replace('@','')}")]])
                return
            await e.edit("🤖 بوت النشر التلقائي\nاهلا بك في لوحة التحكم", buttons=main_kb(uid))
        else:
            await e.answer("ما اشتركت بعد! اشترك اولاً", alert=True)
        return
    if not is_admin(uid) and not is_vip(uid):
        if data not in ["check_my_vip","main"]:
            await e.answer("❌ انت غير مشترك VIP - راسل المطور @i999l9", alert=True)
            return
    await e.answer()
    s=get_settings(uid)
    if data=="main":
        await e.edit("🤖 بوت النشر التلقائي\nاهلا بك في لوحة التحكم", buttons=main_kb(uid)); return
    if data=="accounts":
        accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid or is_admin(uid)]
        txt="📁 إدارة الحسابات\n\n" + ("\n".join([f"{v.get('phone',k)} - {v.get('status','🟢')} " + ("⛔ ايقاف اجباري" if is_account_force_stopped(k) else "") for k,v in accs]) if accs else "لا توجد حسابات")
        btns=[]
        for k,v in accs:
            btns.append([Button.inline(f"{v.get('phone',k)}",f"noop"), Button.inline("🗑 حذف",f"del_acc_{k}")])
        btns.append([Button.inline("➕ إضافة حساب جديد","add_acc")])
        btns.append([Button.inline("🔙 رجوع","main")])
        await e.edit(txt, buttons=btns); return
    if data=="add_acc":
        user_state[uid]="wait_phone"
        await e.edit("📱 دز رقمك مع رمز الدولة\nمثال: +9647701234567", buttons=back_kb()); return
    if data.startswith("del_acc_"):
        k=data.replace("del_acc_","")
        if k in account_clients:
            try: await account_clients[k].disconnect()
            except: pass
            del account_clients[k]
        db["accounts"].pop(k,None); save(); await e.edit("تم حذف الحساب ✅", buttons=back_kb()); return
    if data=="groups":
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid or is_admin(uid)]
        txt="👥 إدارة المجموعات\n\n" + ("\n".join([f"{v.get('title',k)}" for k,v in grps]) if grps else "لا توجد مجموعات")
        btns=[]
        for k,v in grps:
            btns.append([Button.inline(v.get('title',k)[:30],"noop"), Button.inline("🚪 حذف + مغادرة",f"del_grp_{k}")])
        btns.append([Button.inline("➕ إضافة مجموعة جديدة","add_grp_choose_acc")])
        btns.append([Button.inline("🔙 رجوع","main")])
        await e.edit(txt, buttons=btns); return
    if data.startswith("del_grp_"):
        grp_id=data.replace("del_grp_","")
        grp_title = db["groups"].get(grp_id, {}).get("title", grp_id)[:30]
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        btns=[[Button.inline("🚪 مغادرة بكل الحسابات",f"leave_grp_{grp_id}__ALL")]]
        for k in accs:
            btns.append([Button.inline(f"🚪 مغادرة بحساب {db['accounts'][k].get('phone',k)}", f"leave_grp_{grp_id}__{k}")])
        btns.append([Button.inline("🗑 حذف من البوت فقط بدون مغادرة",f"del_only_{grp_id}")])
        btns.append([Button.inline("🔙 رجوع","groups")])
        await e.edit(f"🚪 حذف المجموعة:\n{grp_title}\n\nتبي الحساب يغادر من الكروب فعلاً بالتليجرام؟\nولا بس تحذفها من البوت؟", buttons=btns); return
    if data.startswith("leave_grp_"):
        rest=data.replace("leave_grp_","")
        if "__" in rest:
            grp_id, acc_part = rest.split("__",1)
        else:
            grp_id, acc_part = rest, "ALL"
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
        grp_title = db["groups"].get(grp_id, {}).get("title", grp_id)
        ok=0; fail=0
        for a in accs:
            try:
                client = await get_account_client(a)
                stop_post(uid, a, grp_id)
                if await leave_group_real(client, grp_id):
                    ok+=1
                else:
                    fail+=1
            except Exception as ex:
                print(f"فشل مغادرة {a}: {ex}")
                fail+=1
        db["groups"].pop(grp_id, None); save()
        await e.edit(f"تم ✅\n\n🚪 غادر من الكروب: {ok} حساب\n❌ فشل: {fail} حساب\nالمجموعة: {grp_title}\nتم حذفها من البوت ايضاً.", buttons=back_kb()); return
    if data.startswith("del_only_"):
        grp_id=data.replace("del_only_","")
        db["groups"].pop(grp_id,None); save(); await e.edit("تم حذف المجموعة من البوت فقط ✅\nالحساب بقى داخل الكروب بالتليجرام.", buttons=back_kb()); return
    if data=="add_grp_choose_acc":
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs: await e.edit("اضف حساب اولا", buttons=back_kb()); return
        btns=[[Button.inline("كل الحسابات","add_grp_all")]]+[[Button.inline(db["accounts"][k].get("phone",k),f"add_grp_acc_{k}")] for k in accs]+[[Button.inline("🔙 رجوع","main")]]
        await e.edit("اختر الحساب للمجموعة الجديدة:", buttons=btns); return
    if data.startswith("add_grp_acc_") or data=="add_grp_all":
        user_state[uid]=f"wait_grp_{data}"; await e.edit("ارسل رابط الكروب كامل (مثلاً https://t.me/+xxxx او https://t.me/group):", buttons=back_kb()); return
    if data=="posting":
        btns=[[Button.inline("▶️ بدء النشر","start_post"), Button.inline("⏹️ إيقاف النشر","stop_post")],
              [Button.inline("📝 تعيين الكليشة","set_caption")],
              [Button.inline("⏱️ تعيين المدة بين الرسائل","set_delay")],
              [Button.inline("⚙️ إعدادات النشر التلقائي","auto_settings")],
              [Button.inline("🔙 رجوع","main")]]
        await e.edit("🚀 إدارة النشر", buttons=btns); return
    if data=="stop_post":
        btns=[[Button.inline("⏹️ إيقاف عادي","stop_post_normal")],
              [Button.inline("⛔ إيقاف إجباري - طوارئ","stop_post_force")],
              [Button.inline("✅ إلغاء الإيقاف الإجباري","unblock_list")],
              [Button.inline("🔙 رجوع","posting")]]
        await e.edit("⏹️ إيقاف النشر\n\n⏹️ عادي: يوقف بس وتكدر ترجع تشغله\n⛔ إجباري - طوارئ: يوقف كل النشر مال الحساب نهائياً، وما يخليه يحاول ينشر بأي مجموعة، لحد ما تلغي الايقاف\n\nملاحظة: اذا الحساب انطرد من مجموعة معينة، البوت يوقفه تلقائياً لهاي المجموعة فقط.", buttons=btns); return
    if data=="unblock_list":
        forced = [a for a in db.get("force_stopped", []) if a in db["accounts"] and (db["accounts"][a]["owner"]==uid or is_admin(uid))]
        blocked=[(k,v) for k,v in db.get("blocked", {}).items() if v.get("owner")==uid or is_admin(uid)]
        txt="⛔ الإيقاف الإجباري:\n\n"
        btns=[]
        if forced:
            txt += "--- ايقاف طوارئ (كل النشر) ---\n"
            for acc_key in forced:
                phone = db["accounts"].get(acc_key, {}).get("phone", acc_key)
                txt += f"{phone} ⛔\n"
                btns.append([Button.inline(f"✅ الغاء ايقاف + شغل النشر: {phone}", f"unforce_and_start_{acc_key}")])
                btns.append([Button.inline(f"✅ الغاء ايقاف فقط: {phone}", f"unforce_{acc_key}")])
        if blocked:
            txt += "\n--- انطرد من مجموعة معينة ---\n"
            for k,v in blocked:
                acc_phone = db["accounts"].get(v.get("acc"), {}).get("phone", v.get("acc"))
                grp_title = db["groups"].get(v.get("grp"), {}).get("title", v.get("grp"))[:20]
                txt += f"{acc_phone} - {grp_title}\n"
                btns.append([Button.inline(f"✅ الغاء حظر: {acc_phone} - {grp_title}", f"unblock_{v.get('acc')}__{v.get('grp')}")])
        if not forced and not blocked:
            await e.edit("ما عندك اي ايقاف اجباري ✅", buttons=back_kb()); return
        btns.append([Button.inline("🔙 رجوع","posting")])
        await e.edit(txt, buttons=btns); return
    if data.startswith("unforce_and_start_"):
        acc_key=data.replace("unforce_and_start_","")
        if unforce_account(acc_key):
            phone = db["accounts"].get(acc_key, {}).get("phone", acc_key)
            await e.edit(f"✅ تم إلغاء الإيقاف الإجباري للحساب {phone}\n\nهسه الحساب رجع طبيعي 100%.\nروح بدء النشر > اختر الحساب > اختر المجموعة، وراح يشتغل فوراً.", buttons=[[Button.inline("▶️ روح بدء النشر","start_post")],[Button.inline("🔙 رجوع","main")]])
        else:
            await e.edit("مو موجود", buttons=back_kb())
        return
    if data.startswith("unforce_"):
        acc_key=data.replace("unforce_","")
        if unforce_account(acc_key):
            await e.edit(f"✅ تم إلغاء الإيقاف الإجباري\n\nهسه الحساب رجع طبيعي، تكدر تدوس بدء النشر وراح يشتغل.", buttons=[[Button.inline("▶️ بدء النشر","start_post")],[Button.inline("🔙 رجوع","main")]])
        else:
            await e.edit("مو موجود", buttons=back_kb())
        return
    if data.startswith("unblock_"):
        rest = data.replace("unblock_","")
        if "__" in rest:
            acc_key, grp_id = rest.split("__",1)
            if block_key(acc_key, grp_id) in db.get("blocked", {}):
                del db["blocked"][block_key(acc_key, grp_id)]; save()
                await e.edit(f"✅ تم إلغاء حظر هاي المجموعة\n\nهسه تكدر ترجع تشغل النشر بيها.", buttons=back_kb())
            else:
                await e.edit("مو موجود", buttons=back_kb())
        return
    if data in ["start_post","stop_post_normal"]:
        mode="start" if data=="start_post" else "stop"
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs:
            await e.edit("ما عندك حساب، ضيف حساب اولاً", buttons=back_kb()); return
        # اذا الحساب موقوف اجباري، نعرضه مع زر الغاء مباشر
        btns=[[Button.inline("كل الحسابات",f"{mode}_post_ALL")]]
        for k in accs:
            label = db["accounts"][k].get("phone",k)
            if is_account_force_stopped(k):
                label += " ⛔ موقوف اجباري - دوس لالغاء"
                btns.append([Button.inline(label, f"unforce_{k}")])
            else:
                btns.append([Button.inline(label,f"{mode}_post_ACC_{k}")])
        btns.append([Button.inline("🔙 رجوع","posting")])
        title = "اختر الحساب للنشر:" if mode=="start" else "اختر الحساب للإيقاف العادي:"
        if mode=="start" and any(is_account_force_stopped(k) for k in accs):
            title += "\n\n⚠️ حساب موقوف اجباري - دوس عليه حتى تلغي الايقاف ويرجع يشتغل"
        await e.edit(title, buttons=btns); return
    if data=="stop_post_force":
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs:
            await e.edit("ما عندك حساب", buttons=back_kb()); return
        btns=[[Button.inline("⛔ ايقاف اجباري لكل الحسابات", "force_ALL")]]
        for k in accs:
            label = db["accounts"][k].get("phone",k)
            if is_account_force_stopped(k):
                label += " ⛔ موقوف اصلاً"
            btns.append([Button.inline(f"⛔ ايقاف اجباري: {label}", f"force_{k}")])
        btns.append([Button.inline("🔙 رجوع","posting")])
        await e.edit("⛔ إيقاف إجباري - طوارئ\n\nاختر الحساب اللي تريد توقفه اجبارياً:\n\nراح يوقف كل النشر مال هذا الحساب، وما راح يحاول ينشر بأي مجموعة، لحد ما تلغي الايقاف.\nبدون اختيار مجموعة.", buttons=btns); return
    if data.startswith("force_"):
        acc_key=data.replace("force_","")
        if acc_key=="ALL":
            for k in [kk for kk,v in db["accounts"].items() if v["owner"]==uid]:
                stop_all_for_account(uid, k)
                force_stop_account(k)
            await e.edit(f"⛔ تم الإيقاف الإجباري لكل الحسابات ✅\n\nكل النشر توقف.\n\nللالغاء والرجوع للنشر: إيقاف النشر > إلغاء الإيقاف الإجباري > الغاء ايقاف + شغل النشر", buttons=[[Button.inline("✅ إلغاء الإيقاف الإجباري","unblock_list")],[Button.inline("🔙 رجوع","main")]]); return
        else:
            cnt = stop_all_for_account(uid, acc_key)
            force_stop_account(acc_key)
            phone = db["accounts"].get(acc_key, {}).get("phone", acc_key)
            await e.edit(f"⛔ تم الإيقاف الإجباري للحساب {phone} ✅\n\nتم ايقاف {cnt} نشر شغال.\nما راح يحاول ينشر بأي مجموعة بعد.\n\nللرجوع للنشر: إيقاف النشر > إلغاء الإيقاف الإجباري > الغاء ايقاف + شغل النشر", buttons=[[Button.inline("✅ إلغاء الإيقاف الإجباري","unblock_list")],[Button.inline("🔙 رجوع","main")]]); return
    if data.startswith("start_post_ACC_") or data.startswith("stop_post_ACC_") or data in ["start_post_ALL","stop_post_ALL"]:
        mode="start" if data.startswith("start") else "stop"
        if data.endswith("_ALL"):
            acc_part="ALL"
        else:
            acc_part=data.replace(f"{mode}_post_ACC_","")
        # اذا الحساب موقوف اجباري وانت تحاول تشغله، نعرض زر الغاء فوراً
        if mode=="start" and acc_part!="ALL" and is_account_force_stopped(acc_part):
            phone = db["accounts"].get(acc_part, {}).get("phone", acc_part)
            await e.edit(f"⛔ هذا الحساب {phone} موقوف اجبارياً\n\nما راح يشتغل لحد ما تلغي الايقاف.\nدوس الزر حتى يرجع يشتغل فوراً:", buttons=[[Button.inline("✅ الغاء الايقاف + شغل النشر", f"unforce_and_start_{acc_part}")],[Button.inline("🔙 رجوع","posting")]]); return
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid]
        if not grps:
            await e.edit("ما عندك مجموعة، ضيف مجموعة اولاً", buttons=back_kb()); return
        btns=[[Button.inline("كل المجموعات",f"{mode}_GRP_ALL__{acc_part}")]]
        for k,v in grps:
            label = v.get('title',k)[:30]
            suffix = ""
            if acc_part!="ALL" and is_blocked(acc_part, k):
                suffix = " ⛔ انطرد"
            btns.append([Button.inline(label+suffix, f"{mode}_GRP_{k}__{acc_part}")])
        btns.append([Button.inline("🔙 رجوع","posting")])
        title = "اختر المجموعة للنشر:" if mode=="start" else "اختر المجموعة للإيقاف العادي:"
        await e.edit(title, buttons=btns); return
    if data.startswith("start_GRP_") or data.startswith("stop_GRP_"):
        mode="start" if data.startswith("start") else "stop"
        rest=data.replace(f"{mode}_GRP_","")
        if "__" in rest:
            grp_id, acc_part = rest.split("__",1)
        else:
            grp_id, acc_part = rest, "ALL"
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
        grps=list(db["groups"].keys()) if grp_id=="ALL" else [grp_id]
        cnt=0; already=0; blocked_cnt=0; force_cnt=0; force_accs=[]
        for a in accs:
            for g in grps:
                real_g = g
                if isinstance(g, str) and "t.me" in g:
                    cl = await get_account_client(a)
                    real_g = await resolve_group_id(cl, g) or g
                    if real_g != g and g in db["groups"]:
                        db["groups"][real_g] = db["groups"].pop(g)
                        save()
                if mode=="start":
                    res = start_post(uid,a,real_g)
                    if res==True: cnt+=1
                    elif res=="blocked": blocked_cnt+=1
                    elif res=="force_stopped":
                        force_cnt+=1
                        if a not in force_accs: force_accs.append(a)
                    else: already+=1
                else:
                    if stop_post(uid,a,real_g): cnt+=1
                    else: already+=1
        if mode=="start":
            if force_cnt>0 and cnt==0:
                # كلها موقوفة اجبارياً - نعرض زر الغاء مباشر
                btns=[]
                for fa in force_accs:
                    phone = db["accounts"].get(fa, {}).get("phone", fa)
                    btns.append([Button.inline(f"✅ الغاء الايقاف + شغل النشر: {phone}", f"unforce_and_start_{fa}")])
                btns.append([Button.inline("🔙 رجوع","posting")])
                await e.edit(f"⛔ الحساب موقوف اجبارياً\n\nما راح يشتغل لحد ما تلغي الايقاف.\nدوس الزر حتى يرجع يشتغل فوراً:", buttons=btns); return
            msg = ""
            if cnt>0: msg += f"✅ تم بدء النشر المستمر لـ {cnt} 🔁\n\nالنشر راح يبقى مستمر كل {s['delay']} ثانية لحد ما توقفه انت.\n\nالكليشة: {s['caption'][:100]}\n"
            if already>0: msg += f"\n⚠️ النشر شغال اصلاً لـ {already}\n"
            if blocked_cnt>0: msg += f"\n⛔ {blocked_cnt} انطرد من المجموعة - ما راح ينشر بيها."
            if force_cnt>0: msg += f"\n⛔ {force_cnt} موقوف اجبارياً طوارئ - الغي الايقاف اولاً."
            await e.edit(msg or "تم", buttons=back_kb())
        else:
            if cnt>0:
                await e.edit(f"⏹️ تم إيقاف النشر لـ {cnt} ✅", buttons=back_kb())
            else:
                await e.edit(f"⚠️ النشر متوقف اصلاً", buttons=back_kb())
        return
    if data=="set_caption":
        user_state[uid]="wait_caption"; await e.edit("ارسل الكليشة الجديدة:", buttons=back_kb()); return
    if data=="set_delay":
        if s["random_enabled"]:
            user_state[uid]="wait_delay_random"; await e.edit("النشر العشوائي مفعل 🎲\nارسل المدة هكذا: 60-120", buttons=back_kb())
        else:
            user_state[uid]="wait_delay"; await e.edit("ارسل المدة بالثواني.\n⚠️ لا تخلي الفاصل أقل من 60 ثانية لتجنب الحظر.", buttons=back_kb())
        return
    if data=="auto_settings":
        def t(v): return "✅ مفعل" if v else "❌ معطل"
        btns=[[Button.inline(f"🖼️ النشر بالصور والفيديو: {t(s['media_enabled'])}","toggle_media")],
              [Button.inline(f"🛡️ الحماية من الحظر: {t(s['protect_enabled'])}","toggle_protect")],
              [Button.inline(f"📊 التقرير اليومي: {t(s['report_enabled'])}","toggle_report")],
              [Button.inline(f"🎲 النشر العشوائي: {t(s['random_enabled'])}","toggle_random")],
              [Button.inline("🔙 رجوع","posting")]]
        await e.edit("⚙️ إعدادات النشر التلقائي", buttons=btns); return
    if data.startswith("toggle_"):
        key={"toggle_media":"media_enabled","toggle_protect":"protect_enabled","toggle_report":"report_enabled","toggle_random":"random_enabled"}[data]
        s[key]=not s[key]; save()
        if key=="media_enabled" and s[key]:
            user_state[uid]="wait_media"; await e.edit("النشر بالصور مفعل ✅\nارسل الان الصورة او الفيديو:", buttons=back_kb()); return
        await e.edit("تم التحديث ✅", buttons=[[Button.inline("🔙 رجوع","auto_settings")]]); return
    if data=="stats":
        if not is_admin(uid): await e.edit("هذا القسم للادمن فقط", buttons=back_kb()); return
        active=len(posting_tasks)
        blocked_n=len(db.get("blocked",{}))
        forced_n=len(db.get("force_stopped",[]))
        await e.edit(f"📊 الإحصائيات\n\nعدد المستخدمين: {len(db['users'])}\nعدد الحسابات: {len(db['accounts'])}\nعدد المجموعات: {len(db['groups'])}\nنشر شغال حالياً: {active}\nنشرت اليوم: {stats_today['count']}\nانطرد: {blocked_n}\nايقاف اجباري طوارئ: {forced_n}", buttons=back_kb()); return
    if data=="vip_admin":
        if not is_admin(uid): await e.edit("للادمن فقط", buttons=back_kb()); return
        btns=[[Button.inline("➕ تفعيل VIP لمستخدم","vip_add")],[Button.inline("➖ إلغاء VIP","vip_del")],[Button.inline("📋 قائمة الـ VIP","vip_list")],[Button.inline("📢 الاشتراك الإجباري","vip_forced")],[Button.inline("🔙 رجوع","main")]]
        await e.edit("👑 قسم الـ VIP", buttons=btns); return
    if data=="vip_add":
        user_state[uid]="wait_vip_id"; await e.edit("ارسل ايدي المستخدم لتفعيل VIP:", buttons=back_kb()); return
    if data=="vip_del":
        user_state[uid]="wait_vip_del"; await e.edit("ارسل ايدي المستخدم لإلغاء VIP:", buttons=back_kb()); return
    if data=="vip_list":
        txt="📋 قائمة الـ VIP:\n\n" + "\n".join([f"{k} - {vip_left(int(k)) if k.isdigit() else v}" for k,v in db["vip"].items()]) if db["vip"] else "لا يوجد VIP"
        await e.edit(txt, buttons=back_kb()); return
    if data=="vip_forced":
        user_state[uid]="wait_forced"; await e.edit("ارسل يوزر القناة للاشتراك الاجباري (مثلا @channel) او ارسل 'الغاء':", buttons=back_kb()); return
    if data.startswith("vip_dur_"):
        _,_,dur,target=data.split("_",3)
        if dur=="lifetime": exp="lifetime"
        else:
            days={"day":1,"week":7,"month":30}[dur]
            exp=(datetime.datetime.now()+datetime.timedelta(days=days)).isoformat()
        db["vip"][target]={"expire":exp,"notified":False}; save()
        await e.edit(f"تم تفعيل VIP للمستخدم {target} ✅", buttons=back_kb()); return
    if data=="check_my_vip":
        if is_vip(uid): await e.edit(f"اشتراكك: VIP ✅\n{vip_left(uid)}", buttons=back_kb())
        else: await e.edit(f"اشتراكك: عادي ❌\nما عندك VIP\nراسل المطور للتفعيل: {DEVELOPER}", buttons=[[Button.url("📩 راسل المطور", f"https://t.me/{DEVELOPER.replace('@','')}")]])
        return
    if data=="check_acc":
        txt="🔍 فحص الحسابات:\n\n"
        for k,v in db["accounts"].items():
            if v["owner"]!=uid and not is_admin(uid): continue
            running=any(k in kk for kk in posting_tasks.keys())
            forced_txt = " ⛔ ايقاف اجباري - دوس بدء النشر والغي الايقاف" if is_account_force_stopped(k) else ""
            txt+=f"{v.get('phone',k)} - {v.get('status','🟢')} - النشر: {'شغال ✅' if running else 'متوقف ⏹️'}{forced_txt}\n"
        await e.edit(txt, buttons=back_kb()); return

@bot.on(events.NewMessage)
async def on_msg(e):
    uid=e.sender_id; st=user_state.get(uid)
    if not st or e.text and e.text.startswith("/"): return
    if not is_admin(uid) and not is_vip(uid):
        await e.respond(f"❌ انت غير مشترك VIP\nراسل المطور للتفعيل: {DEVELOPER}")
        return
    s=get_settings(uid)
    txt=(e.text or "").strip()
    if st=="wait_phone":
        phone=txt
        if not phone.startswith("+"):
            await e.respond("دز الرقم مع + مثلاً +964770..."); return
        try:
            client=TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            sent=await client.send_code_request(phone)
            login_tmp[uid]={"phone":phone,"hash":sent.phone_code_hash,"client":client}
            user_state[uid]="wait_code"
            await e.respond(f"تم ارسال الكود الى {phone}\nدز الكود اللي وصلك (5 ارقام):")
        except Exception as ex:
            await e.respond(f"خطأ بالرقم: {ex}")
        return
    if st=="wait_code":
        tmp=login_tmp.get(uid)
        if not tmp: await e.respond("صارت مشكلة، دز الرقم من جديد"); user_state[uid]="wait_phone"; return
        try:
            await tmp["client"].sign_in(tmp["phone"], txt, phone_code_hash=tmp["hash"])
            sess=tmp["client"].session.save()
            key=f"acc_{len(db['accounts'])+1}"
            db["accounts"][key]={"owner":uid,"session":sess,"phone":tmp["phone"],"status":"🟢 موجود","reason":"-"}; save()
            account_clients[key]=tmp["client"]
            login_tmp.pop(uid,None); user_state.pop(uid,None)
            await e.respond(f"تم اضافة الحساب ✅\nالرقم: {tmp['phone']}\nالجلسة بقت نشطة ✅", buttons=main_kb(uid))
        except SessionPasswordNeededError:
            user_state[uid]="wait_2fa"
            await e.respond("🔐 عندك تحقق بخطوتين\nدز كلمة المرور الثانوية:")
        except PhoneCodeInvalidError:
            await e.respond("الكود غلط، دز الكود الصحيح:")
        except Exception as ex:
            await e.respond(f"خطأ: {ex}")
        return
    if st=="wait_2fa":
        tmp=login_tmp.get(uid)
        if txt=="ماعندي":
            await e.respond("لازم تدز كلمة المرور الثانوية حتى يكمل الدخول"); return
        try:
            await tmp["client"].sign_in(password=txt)
            sess=tmp["client"].session.save()
            key=f"acc_{len(db['accounts'])+1}"
            db["accounts"][key]={"owner":uid,"session":sess,"phone":tmp["phone"],"status":"🟢 موجود","reason":"-"}; save()
            account_clients[key]=tmp["client"]
            login_tmp.pop(uid,None); user_state.pop(uid,None)
            await e.respond(f"تم اضافة الحساب ✅\nالرقم: {tmp['phone']}\nالجلسة بقت نشطة ✅", buttons=main_kb(uid))
        except Exception as ex:
            await e.respond(f"كلمة المرور غلط: {ex}\nحاول مرة ثانية:")
        return
    if st.startswith("wait_grp_"):
        link = txt.strip()
        chosen = st.replace("wait_grp_", "")
        accs = []
        if chosen.startswith("add_grp_acc_"):
            acc_key = chosen.replace("add_grp_acc_", "")
            if acc_key in db["accounts"] and db["accounts"][acc_key]["owner"] == uid:
                accs = [(acc_key, db["accounts"][acc_key])]
            else:
                await e.respond("الحساب مو موجود"); user_state.pop(uid,None); return
            mode_txt = f"للحساب {db['accounts'][acc_key].get('phone')}"
        else:
            accs = [ (k,v) for k,v in db["accounts"].items() if v["owner"]==uid ]
            mode_txt = "لجميع الحسابات"
        if not accs:
            await e.respond("ما عندك حساب، ضيف حساب اولاً"); user_state.pop(uid,None); return
        await e.respond(f"جاري فحص {mode_txt} ودخولهم للكروب ... ⏳")
        joined = 0; skipped = 0; failed = ""; group_id_final = None
        for acc_key, acc in accs:
            try:
                client = await get_account_client(acc_key)
                if "t.me/+" in link or "t.me/joinchat/" in link:
                    from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
                    h = link.split("+")[-1].split("/")[-1].split("?")[0].strip()
                    try:
                        cres = await client(CheckChatInviteRequest(h))
                        if hasattr(cres, "chat") and cres.chat:
                            group_id_final = str(cres.chat.id)
                            if not group_id_final.startswith("-100"):
                                group_id_final = "-100" + group_id_final
                            skipped += 1
                            continue
                    except Exception:
                        pass
                    try:
                        res = await client(ImportChatInviteRequest(h))
                        chat_obj = None
                        if hasattr(res, "chats") and res.chats:
                            chat_obj = res.chats[0]
                        elif hasattr(res, "chat") and res.chat:
                            chat_obj = res.chat
                        elif hasattr(res, "updates"):
                            if hasattr(res.updates, "chats") and res.updates.chats:
                                chat_obj = res.updates.chats[0]
                            elif hasattr(res.updates, "chat") and res.updates.chat:
                                chat_obj = res.updates.chat
                        if chat_obj:
                            group_id_final = str(chat_obj.id)
                            if not group_id_final.startswith("-100"):
                                group_id_final = "-100" + group_id_final
                        else:
                            try:
                                cres2 = await client(CheckChatInviteRequest(h))
                                if hasattr(cres2, "chat") and cres2.chat:
                                    group_id_final = str(cres2.chat.id)
                                    if not group_id_final.startswith("-100"):
                                        group_id_final = "-100" + group_id_final
                            except: pass
                        joined += 1
                    except UserAlreadyParticipantError:
                        skipped += 1
                        try:
                            cres = await client(CheckChatInviteRequest(h))
                            if hasattr(cres, "chat") and cres.chat:
                                group_id_final = str(cres.chat.id)
                                if not group_id_final.startswith("-100"):
                                    group_id_final = "-100" + group_id_final
                        except: pass
                    except Exception as ex:
                        msg = str(ex)
                        if "already" in msg.lower() or "participant" in msg.lower():
                            skipped += 1
                            try:
                                cres = await client(CheckChatInviteRequest(h))
                                if hasattr(cres, "chat") and cres.chat:
                                    group_id_final = str(cres.chat.id)
                                    if not group_id_final.startswith("-100"):
                                        group_id_final = "-100" + group_id_final
                            except: pass
                        elif "FLOOD" in msg:
                            failed += f"\n{acc.get('phone')}: انحظر مؤقتاً من الدخول للكروبات (Flood) - انتظر ساعة"
                        elif "INVITE_HASH_EXPIRED" in msg or "InviteHashExpired" in msg:
                            failed += f"\n{acc.get('phone')}: رابط الدعوة منتهي / ملغي - جيب رابط جديد"
                        elif "INVITE_HASH_INVALID" in msg:
                            failed += f"\n{acc.get('phone')}: الرابط غلط - انسخه كامل من التليجرام"
                        elif "USER_ALREADY" in msg:
                            skipped += 1
                        else:
                            failed += f"\n{acc.get('phone')}: {ex}"
                elif "t.me/" in link:
                    try:
                        username = link.split("t.me/")[-1].split("/")[0].split("?")[0].replace("@","")
                        group_entity = await client.get_entity(username)
                        group_id_final = str(group_entity.id)
                        if not group_id_final.startswith("-100") and group_id_final.isdigit():
                            group_id_final = "-100" + group_id_final
                        try:
                            from telethon.tl.functions.channels import GetParticipantRequest
                            await client(GetParticipantRequest(group_entity, await client.get_me()))
                            skipped += 1
                            continue
                        except Exception:
                            pass
                        from telethon.tl.functions.channels import JoinChannelRequest
                        await client(JoinChannelRequest(username))
                        joined += 1
                    except UserAlreadyParticipantError:
                        skipped += 1
                    except Exception as ex:
                        if "already" in str(ex).lower() or "participant" in str(ex).lower():
                            skipped += 1
                        else:
                            failed += f"\n{acc.get('phone')}: {ex}"
                else:
                    failed += f"\n{acc.get('phone')}: الرابط مو صحيح - لازم يبدي بـ https://t.me/"
            except Exception as ex:
                failed += f"\n{acc.get('phone')}: {ex}"
        if not group_id_final:
            user_state.pop(uid,None)
            await e.respond(f"❌ فشل الانضمام\n\nالسبب:\n{failed}\n\n---\nتأكد من:\n1. الرابط نسخته كامل من التليجرام\n2. الحساب مو محظور من دخول الكروبات\n3. الكروب ما حذف الرابط القديم", buttons=main_kb(uid))
            return
        db["groups"][group_id_final] = {"owner":uid, "title":link, "link":link}
        save(); user_state.pop(uid,None)
        await e.respond(f"تم ✅ ({mode_txt})\n\n✅ دخل جديد: {joined} حساب\n⏭️ موجود اصلاً: {skipped} حساب\n🆔 ايدي الكروب: {group_id_final}\n{failed}", buttons=main_kb(uid))
        return
    if st=="wait_caption":
        s["caption"]=txt; save(); user_state.pop(uid,None); await e.respond("تم حفظ الكليشة ✅", buttons=main_kb(uid)); return
    if st=="wait_delay":
        try:
            d=int(txt)
            if d<60:
                await e.respond(f"⚠️ انت دزت {d} ثانية، هذا خطر و ممكن ينحظر حسابك، دز 'اي' للتأكيد او رقم جديد")
                user_state[uid]="wait_delay_confirm"; return
            s["delay"]=d; save(); user_state.pop(uid,None); await e.respond(f"تم تعيين المدة: {d} ثانية ✅", buttons=main_kb(uid)); return
        except: await e.respond("ارسل رقم صحيح"); return
    if st=="wait_delay_confirm":
        if txt=="اي":
            s["delay"]=30; save(); user_state.pop(uid,None); await e.respond("تم التأكيد، المدة 30 ثانية ⚠️ انتبه للحظر", buttons=main_kb(uid)); return
        try: s["delay"]=int(txt); save(); user_state.pop(uid,None); await e.respond("تم ✅", buttons=main_kb(uid)); return
        except: await e.respond("دز رقم"); return
    if st=="wait_delay_random":
        try:
            a,b=txt.split("-"); s["delay_min"]=int(a); s["delay_max"]=int(b); save(); user_state.pop(uid,None); await e.respond(f"تم: من {a} الى {b} ثانية عشوائي 🎲", buttons=main_kb(uid)); return
        except: await e.respond("ارسل هكذا: 60-120"); return
    if st=="wait_media":
        if e.photo or e.video:
            path=f"media_{uid}.jpg"; await e.download_media(path); s["media_file"]=path; s["media_type"]="photo" if e.photo else "video"; save(); user_state.pop(uid,None)
            await e.respond("تم حفظ الصورة/الفيديو ✅", buttons=main_kb(uid)); return
        await e.respond("ارسل صورة او فيديو"); return
    if st=="wait_vip_id":
        target=txt; user_state[uid]=f"wait_vip_dur_{target}"
        await e.respond("اختر المدة:", buttons=[[Button.inline("📅 يوم","vip_dur_day_"+target),Button.inline("📅 اسبوع","vip_dur_week_"+target)],[Button.inline("📅 شهر","vip_dur_month_"+target),Button.inline("♾️ مدى الحياة","vip_dur_lifetime_"+target)]]); return
    if st=="wait_vip_del":
        db["vip"].pop(txt,None); save(); user_state.pop(uid,None); await e.respond("تم إلغاء VIP ✅", buttons=main_kb(uid)); return
    if st=="wait_forced":
        if txt=="الغاء": s["forced_channel"]=None
        else: s["forced_channel"]=txt
        save(); user_state.pop(uid,None); await e.respond(f"تم: الاشتراك الاجباري = {s['forced_channel']}", buttons=main_kb(uid)); return

async def main():
    global tasks_started
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            if not tasks_started:
                asyncio.create_task(vip_checker())
                asyncio.create_task(daily_report())
                tasks_started=True
            print("Bot Running... - البوت شغال ومستمر ✅")
            await bot.run_until_disconnected()
        except Exception as e:
            print(f"البوت فصل، جاري اعادة التشغيل بعد 5 ثواني... الخطأ: {e}")
            await asyncio.sleep(5)
            continue

if __name__=="__main__":
    asyncio.run(main())
