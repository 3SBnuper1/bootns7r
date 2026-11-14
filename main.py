# main.py - بوت النشر التلقائي - النسخة النهائية + دخول بالرقم والكود
import asyncio, json, os, random, datetime, logging
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError, SessionPasswordNeededError, PhoneCodeInvalidError

API_ID = 9661697
API_HASH = "4ae76784fdfecd5df142004955bb8393"
BOT_TOKEN = "9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8"
ADMIN_ID = 5723475089
DATA_FILE = "data.json"
logging.basicConfig(level=logging.INFO)

def load():
    if not os.path.exists(DATA_FILE):
        return {"users":{}, "accounts":{}, "groups":{}, "vip":{}, "settings":{}}
    with open(DATA_FILE, encoding="utf-8") as f: return json.load(f)
def save():
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(db,f,ensure_ascii=False,indent=2)
db = load()

def get_settings(uid):
    uid=str(uid)
    if uid not in db["settings"]:
        db["settings"][uid]={"caption":"اهلا بكم 🔥","delay":60,"delay_min":60,"delay_max":120,
        "media_enabled":False,"protect_enabled":True,"report_enabled":True,"random_enabled":False,
        "media_file":None,"media_type":None,"forced_channel":None}
        save()
    return db["settings"][uid]

def is_admin(uid): return uid==ADMIN_ID
def is_vip(uid):
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
# حفظ مؤقت لعملية الدخول: uid -> {phone, phone_code_hash, client}
login_tmp={}

async def send_one(uid, acc_key, grp_id):
    s=get_settings(uid)
    acc=db["accounts"].get(acc_key)
    if not acc: return False
    try:
        client=TelegramClient(StringSession(acc["session"]), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            raise AuthKeyUnregisteredError("جلسة منتهية")
        if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
            await client.send_file(int(grp_id), s["media_file"], caption=s["caption"])
        else:
            await client.send_message(int(grp_id), s["caption"])
        await client.disconnect()
        stats_today["count"]+=1
        return True
    except FloodWaitError as e:
        if s["protect_enabled"]:
            await bot.send_message(ADMIN_ID, f"🛡️ حماية: حساب {acc_key} انحظر FloodWait {e.seconds} ثانية، وقفت النشر عنه")
            return False
        await asyncio.sleep(e.seconds); return await send_one(uid,acc_key,grp_id)
    except (UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError) as e:
        acc["status"]="معطل"; acc["reason"]=str(e); save()
        if s["protect_enabled"]:
            await bot.send_message(uid, f"⚠️ حساب {acc_key} تعطل: {e}")
        return False
    except Exception as e:
        if s["protect_enabled"]:
            await bot.send_message(uid, f"⚠️ خطأ بالنشر {acc_key}: {e}")
        return False

async def posting_loop(uid, acc_key, grp_id):
    s=get_settings(uid)
    while True:
        await send_one(uid, acc_key, grp_id)
        delay=random.randint(s["delay_min"], s["delay_max"]) if s["random_enabled"] else s["delay"]
        await asyncio.sleep(delay)

def start_post(uid, acc_key, grp_id):
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks: return False
    posting_tasks[key]=asyncio.create_task(posting_loop(uid,acc_key,grp_id))
    return True
def stop_post(uid, acc_key, grp_id):
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks:
        posting_tasks[key].cancel(); del posting_tasks[key]; return True
    return False

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
    await e.respond("🤖 بوت النشر التلقائي\nاهلا بك في لوحة التحكم", buttons=main_kb(uid))

@bot.on(events.CallbackQuery)
async def cb(e):
    uid=e.sender_id; data=e.data.decode(); await e.answer()
    s=get_settings(uid)
    if data=="main":
        await e.edit("🤖 بوت النشر التلقائي\nاهلا بك في لوحة التحكم", buttons=main_kb(uid)); return
    if data=="accounts":
        accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid or is_admin(uid)]
        txt="📁 إدارة الحسابات\n\n" + ("\n".join([f"{v.get('phone',k)} - {v.get('status','🟢')} " for k,v in accs]) if accs else "لا توجد حسابات")
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
        k=data.replace("del_acc_",""); db["accounts"].pop(k,None); save(); await e.edit("تم حذف الحساب ✅", buttons=back_kb()); return
    if data=="groups":
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid or is_admin(uid)]
        txt="👥 إدارة المجموعات\n\n" + ("\n".join([f"{v.get('title',k)}" for k,v in grps]) if grps else "لا توجد مجموعات")
        btns=[]
        for k,v in grps:
            btns.append([Button.inline(v.get('title',k),"noop"), Button.inline("🗑 حذف",f"del_grp_{k}")])
        btns.append([Button.inline("➕ إضافة مجموعة جديدة","add_grp_choose_acc")])
        btns.append([Button.inline("🔙 رجوع","main")])
        await e.edit(txt, buttons=btns); return
    if data=="add_grp_choose_acc":
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs: await e.edit("اضف حساب اولا", buttons=back_kb()); return
        btns=[[Button.inline("كل الحسابات","add_grp_all")]]+[[Button.inline(db["accounts"][k].get("phone",k),f"add_grp_acc_{k}")] for k in accs]+[[Button.inline("🔙 رجوع","main")]]
        await e.edit("اختر الحساب للمجموعة الجديدة:", buttons=btns); return
    if data.startswith("add_grp_acc_") or data=="add_grp_all":
        user_state[uid]=f"wait_grp_{data}"; await e.edit("ارسل ايدي الكروب او يوزره (مثلا -100123 او @group):", buttons=back_kb()); return
    if data.startswith("del_grp_"):
        k=data.replace("del_grp_",""); db["groups"].pop(k,None); save(); await e.edit("تم حذف المجموعة ✅", buttons=back_kb()); return
    if data=="posting":
        btns=[[Button.inline("▶️ بدء النشر","start_post"), Button.inline("⏹️ إيقاف النشر","stop_post")],
              [Button.inline("📝 تعيين الكليشة","set_caption")],
              [Button.inline("⏱️ تعيين المدة بين الرسائل","set_delay")],
              [Button.inline("⚙️ إعدادات النشر التلقائي","auto_settings")],
              [Button.inline("🔙 رجوع","main")]]
        await e.edit("🚀 إدارة النشر", buttons=btns); return
    if data in ["start_post","stop_post"]:
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        btns=[[Button.inline("كل الحسابات",f"{data}_all")]]+[[Button.inline(db["accounts"][k].get("phone",k),f"{data}_acc_{k}")] for k in accs]+[[Button.inline("🔙 رجوع","posting")]]
        await e.edit("لجميع الحسابات ام حساب واحد؟", buttons=btns); return
    if data.startswith("start_post_acc_") or data.startswith("stop_post_acc_") or data in ["start_post_all","stop_post_all"]:
        mode="start" if data.startswith("start") else "stop"
        acc_part=data.replace(f"{mode}_post_","")
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid]
        btns=[[Button.inline("كل المجموعات",f"{mode}_grp_all_{acc_part}")]]+[[Button.inline(v.get('title',k),f"{mode}_grp_{k}_{acc_part}")] for k,v in grps]+[[Button.inline("🔙 رجوع","posting")]]
        await e.edit("لجميع المجموعات ام مجموعة واحدة؟", buttons=btns); return
    if data.startswith("start_grp_") or data.startswith("stop_grp_"):
        parts=data.split("_"); mode=parts[0]; rest=data[len(mode+"_grp_"):]
        if rest.endswith("_all"):
            grp="all"; acc_part="all"
        else:
            grp, acc_part = rest.rsplit("_",1) if "_" in rest else (rest,"all")
        if grp=="all" or acc_part=="all":
            accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="all" else [acc_part]
            grps=list(db["groups"].keys()) if grp=="all" else [grp]
            cnt=0
            for a in accs:
                for g in grps:
                    if mode=="start":
                        if start_post(uid,a,g): cnt+=1
                    else:
                        if stop_post(uid,a,g): cnt+=1
            await e.edit(f"تم {'بدء' if mode=='start' else 'إيقاف'} النشر لـ {cnt} ✅", buttons=back_kb()); return
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
        await e.edit(f"📊 الإحصائيات\n\nعدد المستخدمين: {len(db['users'])}\nعدد الحسابات: {len(db['accounts'])}\nعدد المجموعات: {len(db['groups'])}", buttons=back_kb()); return
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
        else: await e.edit("اشتراكك: عادي ❌\nما عندك VIP", buttons=back_kb())
        return
    if data=="check_acc":
        txt="🔍 فحص الحسابات:\n\n"
        for k,v in db["accounts"].items():
            if v["owner"]!=uid and not is_admin(uid): continue
            running=any(k in kk for kk in posting_tasks.keys())
            txt+=f"{v.get('phone',k)} - {v.get('status','🟢')} - سبب: {v.get('reason','-')} - النشر: {'شغال ✅' if running else 'متوقف ⏹️'}\n"
        await e.edit(txt, buttons=back_kb()); return

@bot.on(events.NewMessage)
async def on_msg(e):
    uid=e.sender_id; st=user_state.get(uid)
    if not st or e.text and e.text.startswith("/"): return
    s=get_settings(uid)
    txt=(e.text or "").strip()

    # --- 1. اضافة حساب بالرقم ---
    if st=="wait_phone":
        phone=txt
        if not phone.startswith("+"):
            await e.respond("دز الرقم مع + مثلاً +964770..."); return
        # انشاء عميل مؤقت وارسال الكود
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
            # نجح بدون كلمة مرور ثانوية
            sess=tmp["client"].session.save()
            key=f"acc_{len(db['accounts'])+1}"
            db["accounts"][key]={"owner":uid,"session":sess,"phone":tmp["phone"],"status":"🟢 موجود","reason":"-"}; save()
            await tmp["client"].disconnect()
            login_tmp.pop(uid,None); user_state.pop(uid,None)
            await e.respond(f"تم اضافة الحساب ✅\nالرقم: {tmp['phone']}", buttons=main_kb(uid))
        except SessionPasswordNeededError:
            user_state[uid]="wait_2fa"
            await e.respond("🔐 عندك تحقق بخطوتين\nدز كلمة المرور الثانوية، واذا ما عندك دز 'ماعندي'؟\nاذا نسيتها، دزها هسه:")
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
            await tmp["client"].disconnect()
            login_tmp.pop(uid,None); user_state.pop(uid,None)
            await e.respond(f"تم اضافة الحساب ✅\nالرقم: {tmp['phone']}", buttons=main_kb(uid))
        except Exception as ex:
            await e.respond(f"كلمة المرور غلط: {ex}\nحاول مرة ثانية:")
        return

    if st.startswith("wait_grp_"):
        gid=txt; db["groups"][gid]={"owner":uid,"title":gid}; save(); user_state.pop(uid,None)
        await e.respond(f"تم اضافة المجموعة {gid} ✅", buttons=main_kb(uid)); return
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
    await bot.start(bot_token=BOT_TOKEN)
    asyncio.create_task(vip_checker()); asyncio.create_task(daily_report())
    print("Bot Running...")
    await bot.run_until_disconnected()

if __name__=="__main__":
    asyncio.run(main())
