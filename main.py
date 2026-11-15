import asyncio, json, os, random, datetime, logging
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError, SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError, UserNotParticipantError
API_ID=int(os.getenv("API_ID","9661697"))
API_HASH=os.getenv("API_HASH","4ae76784fdfecd5df142004955bb8393")
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "9277873259:AAGFetmQuOavf11wc0OVYATMnxoftpbH8A8"
ADMIN_ID=int(os.getenv("ADMIN_ID","5723475089"))
DEV="@i999l9"
DATA_FILE="data.json"
logging.basicConfig(level=logging.WARNING)
def load():
    if not os.path.exists(DATA_FILE):
        return {"users":{},"accounts":{},"groups":{},"vip":{},"settings":{},"blocked":{},"force_stopped":[]}
    with open(DATA_FILE,encoding="utf-8") as f:
        d=json.load(f)
    if "blocked" not in d: d["blocked"]={}
    if "force_stopped" not in d: d["force_stopped"]=[]
    if "ALL" in d["force_stopped"]: d["force_stopped"].remove("ALL")
    return d
def save():
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(db,f,ensure_ascii=False,indent=2)
db=load()
def clean_ch(raw):
    if not raw: return None
    t=raw.strip()
    if t.lower() in ["الغاء","cancel","none","-"]: return None
    if t.startswith("-100") and t[1:].isdigit(): return t
    t=t.replace("https://","").replace("http://","").replace("t.me/","").replace("telegram.me/","").replace("@","").split("/")[0].split("?")[0].strip()
    if not t: return None
    if t.startswith("+") or "joinchat" in t: return "NEED_FORWARD"
    return "@"+t
def get_settings(uid):
    uid=str(uid)
    if uid not in db["settings"]:
        db["settings"][uid]={"caption":"اهلا بكم 🔥","delay":60,"delay_min":60,"delay_max":120,"media_enabled":False,"protect_enabled":True,"report_enabled":True,"random_enabled":False,"media_file":None,"media_type":None,"forced_channel":None}
        save()
    return db["settings"][uid]
def get_forced():
    s=db["settings"].get(str(ADMIN_ID),{})
    ch=s.get("forced_channel")
    if not ch: return None
    if ch=="NEED_FORWARD": return "NEED_FORWARD"
    if str(ch).startswith("-100"): return str(ch)
    return clean_ch(ch)
def is_admin(uid): return uid==ADMIN_ID
def is_vip(uid):
    if is_admin(uid): return True
    v=db["vip"].get(str(uid))
    if not v: return False
    if v.get("expire")=="lifetime": return True
    try:
        exp=datetime.datetime.fromisoformat(v["expire"])
        if datetime.datetime.now()>exp:
            del db["vip"][str(uid)]; save(); return False
        return True
    except Exception: return False
def vip_left(uid):
    v=db["vip"].get(str(uid))
    if not v: return None
    if v.get("expire")=="lifetime": return "مدى الحياة"
    exp=datetime.datetime.fromisoformat(v["expire"])
    left=exp-datetime.datetime.now()
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
    db["blocked"][bkey(a,g)]={"owner":uid,"acc":a,"grp":g,"reason":reason,"time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save()
def main_kb(uid):
    r=[[Button.inline("📁 الحسابات","accounts")]]
    r.append([Button.inline("🚀 النشر","posting"),Button.inline("👥 المجموعات","groups")])
    if is_admin(uid): r.append([Button.inline("📊 احصائيات","stats"),Button.inline("👑 VIP","vip_admin")])
    r.append([Button.inline("👑 اشتراكي","check_my_vip"),Button.inline("🔍 فحص","check_acc")])
    return r
def back_kb(): return [[Button.inline("🔙 رجوع","main")]]
bot=TelegramClient("bot",API_ID,API_HASH)
posting_tasks={}; stats_today={"count":0}; login_tmp={}; account_clients={}; tasks_started=False
async def get_client(acc_key):
    if acc_key in account_clients:
        try:
            c=account_clients[acc_key]
            if await c.is_user_authorized(): return c
        except Exception: pass
    acc=db["accounts"].get(acc_key)
    if not acc: return None
    client=TelegramClient(StringSession(acc["session"]),API_ID,API_HASH)
    await client.connect(); account_clients[acc_key]=client; return client
async def resolve_gid(client,link_or_id):
    if isinstance(link_or_id,str) and "t.me" in link_or_id:
        link=link_or_id.strip()
        try:
            if "t.me/+" in link or "t.me/joinchat/" in link:
                from telethon.tl.functions.messages import CheckChatInviteRequest
                h=link.split("+")[-1].split("/")[-1].split("?")[0]
                res=await client(CheckChatInviteRequest(h))
                if hasattr(res,"chat") and res.chat:
                    gid=str(res.chat.id)
                    return "-100"+gid if not gid.startswith("-100") else gid
            else:
                username=link.split("t.me/")[-1].split("/")[0].replace("@","").split("?")[0]
                ent=await client.get_entity(username)
                gid=str(ent.id)
                return "-100"+gid if gid.isdigit() and not gid.startswith("-100") else gid
        except Exception as e:
            print(e); return None
    return link_or_id
async def leave_real(client,gid):
    try: ent=await client.get_entity(int(gid))
    except Exception: return False
    try:
        from telethon.tl.functions.channels import LeaveChannelRequest
        await client(LeaveChannelRequest(ent)); return True
    except Exception: pass
    try:
        from telethon.tl.functions.messages import DeleteChatUserRequest
        me=await client.get_me(); await client(DeleteChatUserRequest(int(gid),me.id)); return True
    except Exception: return False
async def check_forced(uid):
    ch=get_forced()
    if not ch or ch=="NEED_FORWARD": return True
    if is_admin(uid): return True
    target=int(ch) if str(ch).startswith("-100") else ch
    try:
        await bot.get_participant(target,uid); return True
    except UserNotParticipantError: return False
    except Exception as e:
        print(e)
        try: await bot.send_message(ADMIN_ID,f"⚠️ مشكلة اشتراك اجباري\n{ch}\n{e}\nتأكد البوت ادمن بالقناة")
        except Exception: pass
        return False
async def check_gate(e,uid):
    if is_admin(uid): return True
    if not await check_forced(uid):
        ch=get_forced()
        if str(ch).startswith("-100"):
            await e.respond(f"⚠️ الاشتراك الاجباري\nاشترك بالقناة الخاصة اولاً.\nراسل المطور:\n{DEV}",buttons=[[Button.url("📩 راسل المطور",f"https://t.me/{DEV.replace('@','')}")],[Button.inline("✅ تحققت","check_forced")]])
        else:
            await e.respond(f"⚠️ الاشتراك الاجباري\nاشترك بالقناة اولاً:\n{ch}",buttons=[[Button.url("📢 اشترك",f"https://t.me/{str(ch).replace('@','')}")],[Button.inline("✅ تحققت","check_forced")]])
        return False
    if not is_vip(uid):
        await e.respond(f"❌ غير مشترك VIP\nراسل المطور:\n{DEV}",buttons=[[Button.url("📩 راسل المطور",f"https://t.me/{DEV.replace('@','')}")]])
        return False
    return True
def forced_btns():
    ch=get_forced()
    if str(ch).startswith("-100"): return [[Button.url("📩 راسل المطور",f"https://t.me/{DEV.replace('@','')}")],[Button.inline("✅ تحققت","check_forced")]]
    return [[Button.url("📢 اشترك",f"https://t.me/{str(ch).replace('@','')}")],[Button.inline("✅ تحققت","check_forced")]]
async def send_one(uid,acc_key,grp_id):
    s=get_settings(uid); acc=db["accounts"].get(acc_key)
    if not acc: return False
    if is_force(acc_key): return False
    if is_blocked(acc_key,grp_id): return False
    try:
        client=await get_client(acc_key)
        if not await client.is_user_authorized(): raise AuthKeyUnregisteredError("جلسة منتهية")
        real_id=grp_id
        if isinstance(grp_id,str) and ("t.me" in grp_id or "http" in grp_id):
            real_id=await resolve_gid(client,grp_id)
            if real_id and real_id!=grp_id and grp_id in db["groups"]:
                db["groups"][real_id]=db["groups"].pop(grp_id); save()
            if not real_id:
                await bot.send_message(uid,f"⚠️ ما كدرت احول الرابط: {grp_id}"); return False
        if s["media_enabled"] and s["media_file"] and os.path.exists(s["media_file"]):
            await client.send_file(int(real_id),s["media_file"],caption=s["caption"])
        else:
            await client.send_message(int(real_id),s["caption"])
        stats_today["count"]+=1; return True
    except FloodWaitError as e:
        if s["protect_enabled"]: await bot.send_message(ADMIN_ID,f"🛡️ FloodWait {e.seconds} للحساب {acc_key}"); return False
        await asyncio.sleep(e.seconds); return await send_one(uid,acc_key,grp_id)
    except (UserDeactivatedError,AuthKeyUnregisteredError,SessionRevokedError) as e:
        acc["status"]="معطل"; acc["reason"]=str(e); save()
        if s["protect_enabled"]: await bot.send_message(uid,f"⚠️ حساب {acc_key} تعطل: {e}")
        return False
    except Exception as e:
        msg=str(e)
        if any(x in msg for x in ["USER_NOT_PARTICIPANT","UserNotParticipant","CHAT_WRITE_FORBIDDEN","ChatWriteForbidden","USER_KICKED","kicked","not participant","PEER_ID_INVALID"]) or "403" in msg:
            force_block(uid,acc_key,grp_id,f"انطرد: {e}"); stop_post(uid,acc_key,grp_id)
            try:
                t=db["groups"].get(str(grp_id),{}).get("title",grp_id)
                await bot.send_message(uid,f"⛔ طرد تلقائي\nالحساب {acc.get('phone')} انطرد من:\n{t}\nتم ايقاف النشر لهاي المجموعة فقط.")
            except Exception: pass
            return False
        print(f"خطأ نشر: {e}")
        if s["protect_enabled"]: await bot.send_message(uid,f"⚠️ خطأ نشر {acc_key}: {e}")
        return False
async def posting_loop(uid,acc_key,grp_id):
    s=get_settings(uid)
    while True:
        try:
            if is_force(acc_key): break
            if is_blocked(acc_key,grp_id): break
            await send_one(uid,acc_key,grp_id)
            delay=random.randint(s["delay_min"],s["delay_max"]) if s["random_enabled"] else s["delay"]
            await asyncio.sleep(delay)
        except asyncio.CancelledError: break
        except Exception as e:
            print(e); await asyncio.sleep(10)
def start_post(uid,acc_key,grp_id):
    if is_force(acc_key): return "force_stopped"
    if is_blocked(acc_key,grp_id): return "blocked"
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks: return False
    posting_tasks[key]=asyncio.create_task(posting_loop(uid,acc_key,grp_id)); return True
def stop_post(uid,acc_key,grp_id):
    key=f"{uid}_{acc_key}_{grp_id}"
    if key in posting_tasks: posting_tasks[key].cancel(); del posting_tasks[key]; return True
    return False
def stop_all_acc(uid,acc_key):
    cnt=0
    for k in list(posting_tasks.keys()):
        if k.startswith(f"{uid}_{acc_key}_"): posting_tasks[k].cancel(); del posting_tasks[k]; cnt+=1
    return cnt
async def vip_checker():
    while True:
        now=datetime.datetime.now()
        for uid,v in list(db["vip"].items()):
            if v.get("expire")=="lifetime": continue
            try:
                exp=datetime.datetime.fromisoformat(v["expire"])
                if (exp-now).total_seconds()<=86400 and not v.get("notified"):
                    v["notified"]=True; save()
                    try: await bot.send_message(int(uid),"⚠️ اشتراكك VIP راح يخلص باجر!")
                    except Exception: pass
                if now>exp:
                    del db["vip"][uid]; save()
                    try: await bot.send_message(int(uid),"❌ انتهى اشتراكك VIP")
                    except Exception: pass
            except Exception: pass
        await asyncio.sleep(3600)
async def daily_report():
    while True:
        now=datetime.datetime.now(); target=now.replace(hour=23,minute=59,second=0)
        if target<now: target+=datetime.timedelta(days=1)
        await asyncio.sleep((target-now).total_seconds())
        for uid,s in list(db["settings"].items()):
            if s.get("report_enabled"):
                try: await bot.send_message(int(uid),f"📊 تقرير يومي\nنشرت اليوم: {stats_today['count']}")
                except Exception: pass
        stats_today["count"]=0
user_state={}
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid=e.sender_id; sender=await e.get_sender()
    is_new=str(uid) not in db["users"]
    db["users"][str(uid)]={"name":sender.first_name or "","username":sender.username or "","id":uid,"time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}; save()
    if is_new and uid!=ADMIN_ID:
        await bot.send_message(ADMIN_ID,f"🔔 مستخدم جديد\n{sender.first_name}\n@{sender.username}\n{uid}")
    if not await check_gate(e,uid): return
    await e.respond("🤖 بوت النشر\nاهلا بك",buttons=main_kb(uid))
@bot.on(events.CallbackQuery)
async def cb(e):
    uid=e.sender_id; data=e.data.decode()
    if data=="check_forced":
        if await check_forced(uid):
            if not is_vip(uid) and not is_admin(uid):
                await e.edit(f"❌ غير VIP\nراسل المطور:\n{DEV}",buttons=[[Button.url("📩 راسل المطور",f"https://t.me/{DEV.replace('@','')}")]]); return
            await e.edit("🤖 بوت النشر\nاهلا بك",buttons=main_kb(uid))
        else:
            ch=get_forced()
            if str(ch).startswith("-100"): await e.edit("⚠️ ما اشتركت بعد!\nالقناة خاصة، اشترك برابط الدعوة",buttons=forced_btns())
            else: await e.edit(f"⚠️ ما اشتركت بعد!\nاشترك:\n{ch}",buttons=forced_btns())
        return
    if not is_admin(uid):
        if not await check_forced(uid):
            ch=get_forced()
            if str(ch).startswith("-100"): await e.edit("⚠️ الاشتراك الاجباري\nاشترك بالقناة الخاصة اولاً",buttons=forced_btns())
            else: await e.edit(f"⚠️ الاشتراك الاجباري\nاشترك:\n{ch}",buttons=forced_btns())
            return
    if not is_admin(uid) and not is_vip(uid):
        if data not in ["check_my_vip","main"]: await e.answer("❌ غير VIP",alert=True); return
    await e.answer(); s=get_settings(uid)
    if data=="main": await e.edit("🤖 بوت النشر\nاهلا بك",buttons=main_kb(uid)); return
    if data=="accounts":
        accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid or is_admin(uid)]
        txt="📁 الحسابات\n\n"
        for k,v in accs: txt+=f"{v.get('phone',k)} - {v.get('status','🟢')}{' ⛔ ايقاف' if is_force(k) else ''}\n"
        if not accs: txt+="لا توجد حسابات"
        btns=[]
        for k,v in accs: btns.append([Button.inline(f"{v.get('phone',k)}","noop"),Button.inline("🗑 حذف",f"del_acc_{k}")])
        btns.append([Button.inline("➕ اضافة","add_acc")]); btns.append([Button.inline("🔙 رجوع","main")]); await e.edit(txt,buttons=btns); return
    if data=="add_acc": user_state[uid]="wait_phone"; await e.edit("📱 دز رقمك مع + \nمثال: +964770...",buttons=back_kb()); return
    if data.startswith("del_acc_"):
        k=data.replace("del_acc_","")
        if k in account_clients:
            try: await account_clients[k].disconnect()
            except Exception: pass
            del account_clients[k]
        db["accounts"].pop(k,None); save(); await e.edit("تم حذف الحساب ✅",buttons=back_kb()); return
    if data=="groups":
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid or is_admin(uid)]
        txt="👥 المجموعات\n\n"
        for k,v in grps: txt+=f"{v.get('title',k)}\n"
        if not grps: txt+="لا توجد مجموعات"
        btns=[]
        for k,v in grps: btns.append([Button.inline(v.get('title',k)[:30],"noop"),Button.inline("🚪 حذف + مغادرة",f"del_grp_{k}")])
        btns.append([Button.inline("➕ اضافة مجموعة","add_grp_choose_acc")]); btns.append([Button.inline("🔙 رجوع","main")]); await e.edit(txt,buttons=btns); return
    if data.startswith("del_grp_"):
        grp_id=data.replace("del_grp_",""); grp_title=db["groups"].get(grp_id,{}).get("title",grp_id)[:30]
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        btns=[[Button.inline("🚪 مغادرة بكل الحسابات",f"leave_grp_{grp_id}__ALL")]]
        for k in accs: btns.append([Button.inline(f"🚪 مغادرة {db['accounts'][k].get('phone',k)}",f"leave_grp_{grp_id}__{k}")])
        btns.append([Button.inline("🗑 حذف من البوت فقط",f"del_only_{grp_id}")]); btns.append([Button.inline("🔙 رجوع","groups")])
        await e.edit(f"🚪 حذف:\n{grp_title}\nالحساب يغادر فعلاً؟",buttons=btns); return
    if data.startswith("leave_grp_"):
        rest=data.replace("leave_grp_","")
        grp_id,acc_part=rest.split("__",1) if "__" in rest else (rest,"ALL")
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
        grp_title=db["groups"].get(grp_id,{}).get("title",grp_id); ok=0; fail=0
        for a in accs:
            try:
                client=await get_client(a); stop_post(uid,a,grp_id)
                if await leave_real(client,grp_id): ok+=1
                else: fail+=1
            except Exception: fail+=1
        db["groups"].pop(grp_id,None); save(); await e.edit(f"تم ✅\n🚪 غادر: {ok}\n❌ فشل: {fail}\n{grp_title}",buttons=back_kb()); return
    if data.startswith("del_only_"):
        grp_id=data.replace("del_only_",""); db["groups"].pop(grp_id,None); save(); await e.edit("تم حذف من البوت فقط ✅",buttons=back_kb()); return
    if data=="add_grp_choose_acc":
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs: await e.edit("اضف حساب اولا",buttons=back_kb()); return
        btns=[[Button.inline("كل الحسابات","add_grp_all")]]
        for k in accs: btns.append([Button.inline(db["accounts"][k].get("phone",k),f"add_grp_acc_{k}")])
        btns.append([Button.inline("🔙 رجوع","main")]); await e.edit("اختر الحساب:",buttons=btns); return
    if data.startswith("add_grp_acc_") or data=="add_grp_all":
        user_state[uid]=f"wait_grp_{data}"; await e.edit("ارسل رابط الكروب كامل:",buttons=back_kb()); return
    if data=="posting":
        btns=[[Button.inline("▶️ بدء","start_post"),Button.inline("⏹️ ايقاف","stop_post")],[Button.inline("📝 الكليشة","set_caption")],[Button.inline("⏱️ المدة","set_delay")],[Button.inline("⚙️ اعدادات","auto_settings")],[Button.inline("🔙 رجوع","main")]]
        await e.edit("🚀 النشر",buttons=btns); return
    if data=="stop_post":
        btns=[[Button.inline("⏹️ عادي","stop_post_normal")],[Button.inline("⛔ اجباري طوارئ","stop_post_force")],[Button.inline("✅ الغاء الاجباري","unblock_list")],[Button.inline("🔙 رجوع","posting")]]
        await e.edit("⏹️ ايقاف النشر",buttons=btns); return
    if data=="unblock_list":
        forced=[a for a in db.get("force_stopped",[]) if a in db["accounts"] and (db["accounts"][a]["owner"]==uid or is_admin(uid))]
        blocked=[(k,v) for k,v in db.get("blocked",{}).items() if v.get("owner")==uid or is_admin(uid)]
        txt="⛔ الايقاف الاجباري:\n\n"; btns=[]
        for acc_key in forced:
            phone=db["accounts"].get(acc_key,{}).get("phone",acc_key); txt+=f"{phone} ⛔\n"
            btns.append([Button.inline(f"✅ الغاء + شغل: {phone}",f"unforce_and_start_{acc_key}")]); btns.append([Button.inline(f"✅ الغاء فقط: {phone}",f"unforce_{acc_key}")])
        for k,v in blocked:
            ap=db["accounts"].get(v.get("acc"),{}).get("phone",v.get("acc")); gt=db["groups"].get(v.get("grp"),{}).get("title",v.get("grp"))[:20]; txt+=f"{ap} - {gt}\n"
            btns.append([Button.inline(f"✅ الغاء حظر: {ap} - {gt}",f"unblock_{v.get('acc')}__{v.get('grp')}")])
        if not forced and not blocked: await e.edit("ما عندك ايقاف ✅",buttons=back_kb()); return
        btns.append([Button.inline("🔙 رجوع","posting")]); await e.edit(txt,buttons=btns); return
    if data.startswith("unforce_and_start_"):
        acc_key=data.replace("unforce_and_start_","")
        if unforce_acc(acc_key):
            phone=db["accounts"].get(acc_key,{}).get("phone",acc_key); await e.edit(f"✅ تم الغاء الايقاف {phone}\nهسه رجع طبيعي.",buttons=[[Button.inline("▶️ بدء النشر","start_post")],[Button.inline("🔙 رجوع","main")]])
        else: await e.edit("مو موجود",buttons=back_kb())
        return
    if data.startswith("unforce_"):
        acc_key=data.replace("unforce_","")
        if unforce_acc(acc_key): await e.edit("✅ تم الغاء الايقاف",buttons=[[Button.inline("▶️ بدء النشر","start_post")],[Button.inline("🔙 رجوع","main")]])
        else: await e.edit("مو موجود",buttons=back_kb())
        return
    if data.startswith("unblock_"):
        rest=data.replace("unblock_","")
        if "__" in rest:
            ak,gid=rest.split("__",1)
            if bkey(ak,gid) in db.get("blocked",{}): del db["blocked"][bkey(ak,gid)]; save(); await e.edit("✅ تم الغاء الحظر",buttons=back_kb())
            else: await e.edit("مو موجود",buttons=back_kb())
        return
    if data in ["start_post","stop_post_normal"]:
        mode="start" if data=="start_post" else "stop"
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs: await e.edit("ما عندك حساب",buttons=back_kb()); return
        btns=[[Button.inline("كل الحسابات",f"{mode}_post_ALL")]]
        for k in accs:
            label=db["accounts"][k].get("phone",k)
            if is_force(k): btns.append([Button.inline(label+" ⛔ موقوف - الغاء",f"unforce_{k}")])
            else: btns.append([Button.inline(label,f"{mode}_post_ACC_{k}")])
        btns.append([Button.inline("🔙 رجوع","posting")]); await e.edit("اختر الحساب:",buttons=btns); return
    if data=="stop_post_force":
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid]
        if not accs: await e.edit("ما عندك حساب",buttons=back_kb()); return
        btns=[[Button.inline("⛔ ايقاف لكل الحسابات","force_ALL")]]
        for k in accs:
            label=db["accounts"][k].get("phone",k)
            if is_force(k): label+=" ⛔ موقوف"
            btns.append([Button.inline(f"⛔ ايقاف: {label}",f"force_{k}")])
        btns.append([Button.inline("🔙 رجوع","posting")]); await e.edit("⛔ ايقاف اجباري طوارئ",buttons=btns); return
    if data.startswith("force_"):
        acc_key=data.replace("force_","")
        if acc_key=="ALL":
            for k in [kk for kk,v in db["accounts"].items() if v["owner"]==uid]: stop_all_acc(uid,k); force_acc(k)
            await e.edit("⛔ تم ايقاف كل الحسابات ✅",buttons=[[Button.inline("✅ الغاء الايقاف","unblock_list")],[Button.inline("🔙 رجوع","main")]]); return
        cnt=stop_all_acc(uid,acc_key); force_acc(acc_key); phone=db["accounts"].get(acc_key,{}).get("phone",acc_key)
        await e.edit(f"⛔ تم ايقاف {phone} ✅\nتم ايقاف {cnt} نشر.",buttons=[[Button.inline("✅ الغاء الايقاف","unblock_list")],[Button.inline("🔙 رجوع","main")]]); return
    if data.startswith("start_post_ACC_") or data.startswith("stop_post_ACC_") or data in ["start_post_ALL","stop_post_ALL"]:
        mode="start" if data.startswith("start") else "stop"
        acc_part="ALL" if data.endswith("_ALL") else data.replace(f"{mode}_post_ACC_","")
        if mode=="start" and acc_part!="ALL" and is_force(acc_part):
            phone=db["accounts"].get(acc_part,{}).get("phone",acc_part)
            await e.edit(f"⛔ {phone} موقوف اجبارياً",buttons=[[Button.inline("✅ الغاء + شغل",f"unforce_and_start_{acc_part}")],[Button.inline("🔙 رجوع","posting")]]); return
        grps=[(k,v) for k,v in db["groups"].items() if v["owner"]==uid]
        if not grps: await e.edit("ما عندك مجموعة",buttons=back_kb()); return
        btns=[[Button.inline("كل المجموعات",f"{mode}_GRP_ALL__{acc_part}")]]
        for k,v in grps:
            label=v.get('title',k)[:30]
            if acc_part!="ALL" and is_blocked(acc_part,k): label+=" ⛔ انطرد"
            btns.append([Button.inline(label,f"{mode}_GRP_{k}__{acc_part}")])
        btns.append([Button.inline("🔙 رجوع","posting")]); await e.edit("اختر المجموعة:",buttons=btns); return
    if data.startswith("start_GRP_") or data.startswith("stop_GRP_"):
        mode="start" if data.startswith("start") else "stop"
        rest=data.replace(f"{mode}_GRP_","")
        grp_id,acc_part=rest.split("__",1) if "__" in rest else (rest,"ALL")
        accs=[k for k,v in db["accounts"].items() if v["owner"]==uid] if acc_part=="ALL" else [acc_part]
        grps=list(db["groups"].keys()) if grp_id=="ALL" else [grp_id]
        cnt=0; already=0; blocked_cnt=0; force_cnt=0; force_accs=[]
        for a in accs:
            for g in grps:
                real_g=g
                if isinstance(g,str) and "t.me" in g:
                    cl=await get_client(a); real_g=await resolve_gid(cl,g) or g
                    if real_g!=g and g in db["groups"]: db["groups"][real_g]=db["groups"].pop(g); save()
                if mode=="start":
                    res=start_post(uid,a,real_g)
                    if res is True: cnt+=1
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
                btns=[]
                for fa in force_accs:
                    phone=db["accounts"].get(fa,{}).get("phone",fa); btns.append([Button.inline(f"✅ الغاء: {phone}",f"unforce_and_start_{fa}")])
                btns.append([Button.inline("🔙 رجوع","posting")]); await e.edit("⛔ موقوف اجبارياً",buttons=btns); return
            msg=""
            if cnt>0: msg+=f"✅ بدء النشر {cnt} 🔁\nالكليشة: {s['caption'][:100]}\n"
            if already>0: msg+=f"\n⚠️ شغال: {already}\n"
            if blocked_cnt>0: msg+=f"\n⛔ انطرد: {blocked_cnt}\n"
            if force_cnt>0: msg+=f"\n⛔ موقوف: {force_cnt}\n"
            await e.edit(msg or "تم",buttons=back_kb())
        else:
            if cnt>0: await e.edit(f"⏹️ تم ايقاف {cnt} ✅",buttons=back_kb())
            else: await e.edit("⚠️ متوقف اصلاً",buttons=back_kb())
        return
    if data=="set_caption": user_state[uid]="wait_caption"; await e.edit("ارسل الكليشة:",buttons=back_kb()); return
    if data=="set_delay":
        if s["random_enabled"]: user_state[uid]="wait_delay_random"; await e.edit("ارسل هكذا: 60-120",buttons=back_kb())
        else: user_state[uid]="wait_delay"; await e.edit("ارسل المدة بالثواني.",buttons=back_kb())
        return
    if data=="auto_settings":
        def t(v): return "✅ مفعل" if v else "❌ معطل"
        btns=[[Button.inline(f"🖼️ صور: {t(s['media_enabled'])}","toggle_media")],[Button.inline(f"🛡️ حماية: {t(s['protect_enabled'])}","toggle_protect")],[Button.inline(f"📊 تقرير: {t(s['report_enabled'])}","toggle_report")],[Button.inline(f"🎲 عشوائي: {t(s['random_enabled'])}","toggle_random")],[Button.inline("🔙 رجوع","posting")]]
        await e.edit("⚙️ اعدادات",buttons=btns); return
    if data.startswith("toggle_"):
        key={"toggle_media":"media_enabled","toggle_protect":"protect_enabled","toggle_report":"report_enabled","toggle_random":"random_enabled"}[data]
        s[key]=not s[key]; save()
        if key=="media_enabled" and s[key]: user_state[uid]="wait_media"; await e.edit("ارسل الصورة:",buttons=back_kb()); return
        await e.edit("تم ✅",buttons=[[Button.inline("🔙 رجوع","auto_settings")]]); return
    if data=="stats":
        if not is_admin(uid): await e.edit("للادمن فقط",buttons=back_kb()); return
        ch=get_forced() or "مو مفعل"; ct="خاصة" if str(ch).startswith("-100") else ("عامة" if ch!="مو مفعل" else "")
        await e.edit(f"📊 احصائيات\nالمستخدمين: {len(db['users'])}\nالحسابات: {len(db['accounts'])}\nالمجموعات: {len(db['groups'])}\nشغال: {len(posting_tasks)}\nاليوم: {stats_today['count']}\n📢 اجباري: {ch} {ct}",buttons=back_kb()); return
    if data=="vip_admin":
        if not is_admin(uid): await e.edit("للادمن فقط",buttons=back_kb()); return
        btns=[[Button.inline("➕ تفعيل VIP","vip_add")],[Button.inline("➖ الغاء VIP","vip_del")],[Button.inline("📋 قائمة VIP","vip_list")],[Button.inline("📢 اشتراك اجباري","vip_forced")],[Button.inline("🔙 رجوع","main")]]
        await e.edit("👑 VIP",buttons=btns); return
    if data=="vip_add": user_state[uid]="wait_vip_id"; await e.edit("ارسل ايدي المستخدم:",buttons=back_kb()); return
    if data=="vip_del": user_state[uid]="wait_vip_del"; await e.edit("ارسل ايدي المستخدم للالغاء:",buttons=back_kb()); return
    if data=="vip_list":
        txt="📋 VIP:\n\n"
        for k,v in db["vip"].items(): txt+=f"{k} - {vip_left(int(k)) if k.isdigit() else v}\n"
        if not db["vip"]: txt+="لا يوجد"
        await e.edit(txt,buttons=back_kb()); return
    if data=="vip_forced":
        cur=get_forced() or "مو مفعل"; ct="خاصة" if str(cur).startswith("-100") else ("عامة" if cur!="مو مفعل" else "")
        user_state[uid]="wait_forced"
        await e.edit(f"📢 الحالي:\n{cur} {ct}\n\n1️⃣ عامة: دز https://t.me/xxx\n2️⃣ خاصة: حوّل رسالة من القناة\nاو ارسل 'الغاء'\n⚠️ البوت لازم ادمن",buttons=back_kb()); return
    if data.startswith("vip_dur_"):
        p=data.split("_",3); dur=p[2]; target=p[3]
        if dur=="lifetime": exp="lifetime"
        else: exp=(datetime.datetime.now()+datetime.timedelta(days={"day":1,"week":7,"month":30}[dur])).isoformat()
        db["vip"][target]={"expire":exp,"notified":False}; save(); await e.edit(f"تم تفعيل VIP {target} ✅",buttons=back_kb()); return
    if data=="check_my_vip":
        if is_vip(uid): await e.edit(f"VIP ✅\n{vip_left(uid)}",buttons=back_kb())
        else: await e.edit(f"عادي ❌\nراسل: {DEV}",buttons=[[Button.url("📩 راسل",f"https://t.me/{DEV.replace('@','')}")]])
        return
    if data=="check_acc":
        txt="🔍 فحص:\n\n"
        for k,v in db["accounts"].items():
            if v["owner"]!=uid and not is_admin(uid): continue
            running=any(k in kk for kk in posting_tasks.keys())
            txt+=f"{v.get('phone',k)} - {'شغال ✅' if running else 'متوقف ⏹️'}{' ⛔ ايقاف' if is_force(k) else ''}\n"
        await e.edit(txt,buttons=back_kb()); return
@bot.on(events.NewMessage)
async def on_msg(e):
    uid=e.sender_id; st=user_state.get(uid)
    if not st: return
    if e.text and e.text.startswith("/"): return
    if not is_admin(uid) and not is_vip(uid): await e.respond(f"❌ غير VIP\nراسل: {DEV}"); return
    s=get_settings(uid); txt=(e.text or "").strip()
    if st=="wait_forced":
        fwd=getattr(e.message,"fwd_from",None)
        if fwd is not None:
            ch_id=getattr(fwd,"channel_id",None)
            if ch_id:
                full_id=f"-100{ch_id}"; s["forced_channel"]=full_id; save(); user_state.pop(uid,None)
                await e.respond(f"تم ✅ قناة خاصة\n🆔 {full_id}\n⚠️ البوت لازم ادمن",buttons=main_kb(uid)); return
            await e.respond("⚠️ مو من قناة، حوّل من القناة نفسها"); return
        if txt.lower() in ["الغاء","cancel","none","-","ايقاف","تعطيل"]:
            s["forced_channel"]=None; save(); user_state.pop(uid,None); await e.respond("تم تعطيل الاجباري ✅",buttons=main_kb(uid)); return
        cleaned=clean_ch(txt)
        if cleaned=="NEED_FORWARD": await e.respond("⚠️ رابط خاص t.me/+ ما ينفع، حوّل رسالة من القناة"); return
        if cleaned: s["forced_channel"]=cleaned; save(); user_state.pop(uid,None); await e.respond(f"تم ✅ اجباري = {cleaned}\nعامة 🌐",buttons=main_kb(uid)); return
        await e.respond("دز رابط عامة او حوّل من خاصة"); return
    if st=="wait_phone":
        if not txt.startswith("+"): await e.respond("دز الرقم مع +"); return
        try:
            client=TelegramClient(StringSession(),API_ID,API_HASH); await client.connect(); sent=await client.send_code_request(txt)
            login_tmp[uid]={"phone":txt,"hash":sent.phone_code_hash,"client":client}; user_state[uid]="wait_code"; await e.respond(f"تم ارسال الكود الى {txt}\nدز الكود:")
        except Exception as ex: await e.respond(f"خطأ: {ex}")
        return
    if st=="wait_code":
        tmp=login_tmp.get(uid)
        if not tmp: await e.respond("دز الرقم من جديد"); user_state[uid]="wait_phone"; return
        try:
            await tmp["client"].sign_in(tmp["phone"],txt,phone_code_hash=tmp["hash"])
            sess=tmp["client"].session.save(); key=f"acc_{len(db['accounts'])+1}"
            db["accounts"][key]={"owner":uid,"session":sess,"phone":tmp["phone"],"status":"🟢 موجود","reason":"-"}; save(); account_clients[key]=tmp["client"]
            login_tmp.pop(uid,None); user_state.pop(uid,None); await e.respond(f"تم اضافة ✅ {tmp['phone']}",buttons=main_kb(uid))
        except SessionPasswordNeededError: user_state[uid]="wait_2fa"; await e.respond("🔐 تحقق بخطوتين\nدز كلمة المرور:")
        except PhoneCodeInvalidError: await e.respond("الكود غلط:")
        except Exception as ex: await e.respond(f"خطأ: {ex}")
        return
    if st=="wait_2fa":
        tmp=login_tmp.get(uid)
        if txt=="ماعندي": await e.respond("لازم تدز كلمة المرور"); return
        try:
            await tmp["client"].sign_in(password=txt); sess=tmp["client"].session.save(); key=f"acc_{len(db['accounts'])+1}"
            db["accounts"][key]={"owner":uid,"session":sess,"phone":tmp["phone"],"status":"🟢 موجود","reason":"-"}; save(); account_clients[key]=tmp["client"]
            login_tmp.pop(uid,None); user_state.pop(uid,None); await e.respond(f"تم ✅ {tmp['phone']}",buttons=main_kb(uid))
        except Exception as ex: await e.respond(f"غلط: {ex}")
        return
    if st.startswith("wait_grp_"):
        link=txt.strip(); chosen=st.replace("wait_grp_",""); accs=[]
        if chosen.startswith("add_grp_acc_"):
            ak=chosen.replace("add_grp_acc_","")
            if ak in db["accounts"] and db["accounts"][ak]["owner"]==uid: accs=[(ak,db["accounts"][ak])]
            else: await e.respond("الحساب مو موجود"); user_state.pop(uid,None); return
            mode_txt=f"للحساب {db['accounts'][ak].get('phone')}"
        else: accs=[(k,v) for k,v in db["accounts"].items() if v["owner"]==uid]; mode_txt="لجميع الحسابات"
        if not accs: await e.respond("ما عندك حساب"); user_state.pop(uid,None); return
        await e.respond(f"جاري دخول {mode_txt} ... ⏳")
        joined=0; skipped=0; failed=""; gid_final=None
        for ak,acc in accs:
            try:
                client=await get_client(ak)
                if "t.me/+" in link or "t.me/joinchat/" in link:
                    from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
                    h=link.split("+")[-1].split("/")[-1].split("?")[0].strip()
                    try:
                        cres=await client(CheckChatInviteRequest(h))
                        if hasattr(cres,"chat") and cres.chat:
                            gid_final=str(cres.chat.id)
                            if not gid_final.startswith("-100"): gid_final="-100"+gid_final
                            skipped+=1; continue
                    except Exception: pass
                    try:
                        res=await client(ImportChatInviteRequest(h)); chat_obj=None
                        if hasattr(res,"chats") and res.chats: chat_obj=res.chats[0]
                        elif hasattr(res,"chat") and res.chat: chat_obj=res.chat
                        elif hasattr(res,"updates"):
                            if hasattr(res.updates,"chats") and res.updates.chats: chat_obj=res.updates.chats[0]
                            elif hasattr(res.updates,"chat") and res.updates.chat: chat_obj=res.updates.chat
                        if chat_obj:
                            gid_final=str(chat_obj.id)
                            if not gid_final.startswith("-100"): gid_final="-100"+gid_final
                        else:
                            try:
                                c2=await client(CheckChatInviteRequest(h))
                                if hasattr(c2,"chat") and c2.chat:
                                    gid_final=str(c2.chat.id)
                                    if not gid_final.startswith("-100"): gid_final="-100"+gid_final
                            except Exception: pass
                        joined+=1
                    except UserAlreadyParticipantError:
                        skipped+=1
                        try:
                            cres=await client(CheckChatInviteRequest(h))
                            if hasattr(cres,"chat") and cres.chat:
                                gid_final=str(cres.chat.id)
                                if not gid_final.startswith("-100"): gid_final="-100"+gid_final
                        except Exception: pass
                    except Exception as ex:
                        msg=str(ex)
                        if "already" in msg.lower() or "participant" in msg.lower():
                            skipped+=1
                            try:
                                cres=await client(CheckChatInviteRequest(h))
                                if hasattr(cres,"chat") and cres.chat:
                                    gid_final=str(cres.chat.id)
                                    if not gid_final.startswith("-100"): gid_final="-100"+gid_final
                            except Exception: pass
                        elif "FLOOD" in msg: failed+=f"\n{acc.get('phone')}: Flood"
                        elif "INVITE_HASH_EXPIRED" in msg or "InviteHashExpired" in msg: failed+=f"\n{acc.get('phone')}: رابط منتهي"
                        elif "INVITE_HASH_INVALID" in msg: failed+=f"\n{acc.get('phone')}: رابط غلط"
                        elif "USER_ALREADY" in msg: skipped+=1
                        else: failed+=f"\n{acc.get('phone')}: {ex}"
                elif "t.me/" in link:
                    try:
                        username=link.split("t.me/")[-1].split("/")[0].split("?")[0].replace("@","")
                        ge=await client.get_entity(username); gid_final=str(ge.id)
                        if not gid_final.startswith("-100") and gid_final.isdigit(): gid_final="-100"+gid_final
                        try:
                            from telethon.tl.functions.channels import GetParticipantRequest
                            await client(GetParticipantRequest(ge,await client.get_me())); skipped+=1; continue
                        except Exception: pass
                        from telethon.tl.functions.channels import JoinChannelRequest
                        await client(JoinChannelRequest(username)); joined+=1
                    except UserAlreadyParticipantError: skipped+=1
                    except Exception as ex:
                        if "already" in str(ex).lower() or "participant" in str(ex).lower(): skipped+=1
                        else: failed+=f"\n{acc.get('phone')}: {ex}"
                else: failed+=f"\n{acc.get('phone')}: رابط غلط"
            except Exception as ex: failed+=f"\n{acc.get('phone')}: {ex}"
        if not gid_final: user_state.pop(uid,None); await e.respond(f"❌ فشل\n{failed}",buttons=main_kb(uid)); return
        db["groups"][gid_final]={"owner":uid,"title":link,"link":link}; save(); user_state.pop(uid,None)
        await e.respond(f"تم ✅ ({mode_txt})\n✅ دخل: {joined}\n⏭️ موجود: {skipped}\n🆔 {gid_final}\n{failed}",buttons=main_kb(uid)); return
    if st=="wait_caption": s["caption"]=txt; save(); user_state.pop(uid,None); await e.respond("تم حفظ الكليشة ✅",buttons=main_kb(uid)); return
    if st=="wait_delay":
        try:
            d=int(txt)
            if d<60:
                await e.respond(f"⚠️ {d} ثانية خطر، دز 'اي' للتأكيد"); user_state[uid]="wait_delay_confirm"; return
            s["delay"]=d; save(); user_state.pop(uid,None); await e.respond(f"تم: {d} ثانية ✅",buttons=main_kb(uid)); return
        except Exception: await e.respond("ارسل رقم"); return
    if st=="wait_delay_confirm":
        if txt=="اي": s["delay"]=30; save(); user_state.pop(uid,None); await e.respond("تم 30 ثانية ⚠️",buttons=main_kb(uid)); return
        try: s["delay"]=int(txt); save(); user_state.pop(uid,None); await e.respond("تم ✅",buttons=main_kb(uid)); return
        except Exception: await e.respond("دز رقم"); return
    if st=="wait_delay_random":
        try:
            a,b=txt.split("-"); s["delay_min"]=int(a); s["delay_max"]=int(b); save(); user_state.pop(uid,None); await e.respond(f"تم: {a}-{b} 🎲",buttons=main_kb(uid)); return
        except Exception: await e.respond("ارسل 60-120"); return
    if st=="wait_media":
        if e.photo or e.video:
            path=f"media_{uid}.jpg"; await e.download_media(path); s["media_file"]=path; s["media_type"]="photo" if e.photo else "video"; save(); user_state.pop(uid,None)
            await e.respond("تم حفظ ✅",buttons=main_kb(uid)); return
        await e.respond("ارسل صورة"); return
    if st=="wait_vip_id": target=txt; user_state[uid]=f"wait_vip_dur_{target}"; await e.respond("اختر المدة:",buttons=[[Button.inline("📅 يوم","vip_dur_day_"+target),Button.inline("📅 اسبوع","vip_dur_week_"+target)],[Button.inline("📅 شهر","vip_dur_month_"+target),Button.inline("♾️ مدى","vip_dur_lifetime_"+target)]]); return
    if st=="wait_vip_del": db["vip"].pop(txt,None); save(); user_state.pop(uid,None); await e.respond("تم الغاء VIP ✅",buttons=main_kb(uid)); return
async def main():
    global tasks_started
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            if not tasks_started: asyncio.create_task(vip_checker()); asyncio.create_task(daily_report()); tasks_started=True
            print("Bot Running...")
            await bot.run_until_disconnected()
        except Exception as e: print(f"فصل: {e}"); await asyncio.sleep(5); continue
if __name__=="__main__": asyncio.run(main())