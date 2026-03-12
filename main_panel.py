# main_panel.py - خادم لوحة تحكم STRAVEX مع جميع دوال البوت

import threading
import time
import json
import os
import html
import requests
import base64
from datetime import datetime, timedelta
import urllib3
import random
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# ===============================================
# إعدادات التشفير (من main.py الأصلي)
# ===============================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    print("✅ تم تحميل مكتبة Crypto بنجاح")
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad, unpad
        print("✅ تم تحميل مكتبة Cryptodome بنجاح")
    except ImportError:
        print("❌ يجب تثبيت pycryptodome أولاً: pip install pycryptodome")
        exit()

# بيانات التشفير
ENCRYPTION_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
ENCRYPTION_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ===============================================
# ملفات البيانات (مثل main.py)
# ===============================================
DATA_FILE = "users2.json"
GROUPS_FILE = "groups2.json"
MAINTENANCE_FILE = "maintenance2.json"

# بيانات القناة الإجبارية (اختياري في لوحة التحكم)
SUBSCRIPTION_CHANNEL_ID = -1003536665917
SUBSCRIPTION_CHANNEL_LINK = "https://t.me/stravex_oficiel "

# ===============================================
# المتغيرات العامة
# ===============================================
JWT_TOKEN = None
users = {}
group_activations = {}
maintenance_mode = False

# ===============================================
# تحميل وحفظ البيانات (من main.py)
# ===============================================
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
    return {}

def save_users():
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=4)

def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                if isinstance(data, dict):
                    return {k: v for k, v in data.items()}
            except json.JSONDecodeError:
                pass
    return {}

def save_groups():
    with open(GROUPS_FILE, "w", encoding="utf-8") as file:
        json.dump(group_activations, file, ensure_ascii=False, indent=4)

def load_maintenance_status():
    if os.path.exists(MAINTENANCE_FILE):
        with open(MAINTENANCE_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file).get("maintenance_mode", False)
            except json.JSONDecodeError:
                pass
    return False

def save_maintenance_status(status):
    with open(MAINTENANCE_FILE, "w", encoding="utf-8") as file:
        json.dump({"maintenance_mode": status}, file)

# تحميل البيانات عند بدء التشغيل
users = load_users()
group_activations = load_groups()
maintenance_mode = load_maintenance_status()

# ===============================================
# دوال التشفير المساعدة (من main.py)
# ===============================================
def encrypt_packet(plain_text, key=ENCRYPTION_KEY, iv=ENCRYPTION_IV):
    plain_text_bytes = bytes.fromhex(plain_text)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text_bytes, AES.block_size))
    return cipher_text.hex()

def decrypt_packet(cipher_text, key=ENCRYPTION_KEY, iv=ENCRYPTION_IV):
    cipher_text_bytes = bytes.fromhex(cipher_text)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plain_text = unpad(cipher.decrypt(cipher_text_bytes), AES.block_size)
    return plain_text.hex()

def dec_to_hex(ask):
    ask_result = hex(ask)
    final_result = str(ask_result)[2:]
    if len(final_result) == 1:
        final_result = "0" + final_result
        return final_result
    else:
        return final_result

def encrypt_api(plain_text):
    return encrypt_packet(plain_text, ENCRYPTION_KEY, ENCRYPTION_IV)

def decrypt_api(cipher_text):
    return decrypt_packet(cipher_text, ENCRYPTION_KEY, ENCRYPTION_IV)

def Encrypt_ID(number):
    number = int(number)
    encoded_bytes = []
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        encoded_bytes.append(byte)
        if not number:
            break
    return bytes(encoded_bytes).hex()

def Encrypt(number):
    number = int(number)
    encoded_bytes = []
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        encoded_bytes.append(byte)
        if not number:
            break
    return bytes(encoded_bytes).hex()

def Decrypt(encoded_bytes):
    encoded_bytes = bytes.fromhex(encoded_bytes)
    number = 0
    shift = 0
    for byte in encoded_bytes:
        value = byte & 0x7F
        number |= value << shift
        shift += 7
        if not byte & 0x80:
            break
    return number

# ===============================================
# وظائف JWT (من main.py - بدون تغيير)
# ===============================================
def TOKEN_MAKER(OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, uid):
    now = datetime.now()
    now = str(now)[:len(str(now)) - 7]
    data = bytes.fromhex('1a13323032352d30372d33302031313a30323a3531220966726565206669726528013a07312e3131342e32422c416e64726f6964204f5320372e312e32202f204150492d323320284e32473438382f373030323530323234294a0848616e6468656c645207416e64726f69645a045749464960c00c68840772033332307a1f41524d7637205646507633204e454f4e20564d48207c2032343635207c203480019a1b8a010f416472656e6f2028544d292036343092010d4f70656e474c20455320332e319a012b476f6f676c657c31663361643662372d636562342d343934622d383730622d623164616364373230393131a2010c3139372e312e31322e313335aa0102656eb201203939366136323964626364623339363462653662363937386635643831346462ba010134c2010848616e6468656c64ca011073616d73756e6720534d2d473935354eea014066663930633037656239383135616633306134336234613966363031393531366530653463373033623434303932353136643064656661346365663531663261f00101ca0207416e64726f6964d2020457494649ca03203734323862323533646566633136343031386336303461316562626665626466e003daa907e803899b07f003bf0ff803ae088004999b078804daa9079004999b079804daa907c80403d204262f646174612f6170702f636f6d2e6474732e667265656669726574682d312f6c69622f61726de00401ea044832303837663631633139663537663261663465376665666630623234643964397c2f646174612f6170702f636f6d2e6474732e667265656669726574682d312f626173652e61704bf00403f804018a050233329a050a32303139313138363933a80503b205094f70656e474c455332b805ff7fc00504e005dac901ea0507616e64726f6964f2055c4b71734854394748625876574c6668437950416c52526873626d43676542557562555551317375746d525536634e30524f3751453141486e496474385963784d614c575437636d4851322b7374745279377830663935542b6456593d8806019006019a060134a2060134b2061e40001147550d0c074f530b4d5c584d57416657545a065f2a091d6a0d5033')
    data = data.replace(OLD_OPEN_ID.encode(), NEW_OPEN_ID.encode())
    data = data.replace(OLD_ACCESS_TOKEN.encode(), NEW_ACCESS_TOKEN.encode())
    d = encrypt_api(data.hex())
    Final_Payload = bytes.fromhex(d)
    
    headers = {
        "Host": "loginbp.ggblueshark.com",
        "X-Unity-Version": "2018.4.11f1",
        "Accept": "*/*",
        "Authorization": "Bearer",
        "ReleaseVersion": "OB52",
        "X-GA": "v1 1",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(Final_Payload)),
        "User-Agent": "Free%20Fire/2019118692 CFNetwork/3826.500.111.2.2 Darwin/24.4.0",
        "Connection": "keep-alive"
    }
    
    URL = "https://loginbp.ggblueshark.com/MajorLogin"
    RESPONSE = requests.post(URL, headers=headers, data=Final_Payload, verify=False)
    
    if RESPONSE.status_code == 200:
        if len(RESPONSE.text) < 10:
            return False
        BASE64_TOKEN = RESPONSE.text[RESPONSE.text.find("eyJhbGciOiJIUzI1NiIsInN2ciI6IjEiLCJ0eXAiOiJKV1QifQ"):-1]
        second_dot_index = BASE64_TOKEN.find(".", BASE64_TOKEN.find(".") + 1)
        BASE64_TOKEN = BASE64_TOKEN[:second_dot_index + 44]
        return BASE64_TOKEN
    else:
        print(f"MajorLogin failed with status: {RESPONSE.status_code}")
        return False

def fetch_jwt_token_direct():
    """جلب التوكن مباشرة - من main.py السطر 262"""
    try:
        uid = "4589113906"
        password = "13D433BA6AC2D4E1599FC56E076522B6BD305439F0EA6A16C98802AC9375A382"
        
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
        }
        data = {
            "uid": f"{uid}",
            "password": f"{password}",
            "response_type": "token",
            "client_type": "2",
            "client_secret": "",
            "client_id": "100067",
        }
        
        response = requests.post(url, headers=headers, data=data)
        print(f"📩 استجابة Garena API: {response.text}")
        
        data = response.json()
        
        if "access_token" not in data or "open_id" not in data:
            print(f"❌ مفاتيح مفقودة في الاستجابة: {data}")
            return None

        NEW_ACCESS_TOKEN = data['access_token']
        NEW_OPEN_ID = data['open_id']
        OLD_ACCESS_TOKEN = "ff90c07eb9815af30a43b4a9f6019516e0e4c703b44092516d0defa4cef51f2a"
        OLD_OPEN_ID = "996a629dbcdb3964be6b6978f5d814db"
        
        token = TOKEN_MAKER(OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, uid)
        if token:
            print(f"✅ تم توليد التوكن بنجاح: {token[:30]}...")
            return token
        else:
            print("❌ فشل توليد التوكن")
            return None
            
    except Exception as e:
        print(f"⚠️ خطأ أثناء جلب التوكن: {e}")
        return None

def fetch_jwt_token():
    return fetch_jwt_token_direct()

# ===============================================
# وظائف API الأساسية (من main.py - بدون تغيير)
# ===============================================
def send_friend_request(player_id):
    """إرسال طلب صداقة - من main.py"""
    global JWT_TOKEN
    if not JWT_TOKEN:
        return "⚠️ التوكن غير متاح حاليًا"
    
    enc_id = Encrypt_ID(player_id)
    payload = f"08a7c4839f1e10{enc_id}1801" 
    encrypted_payload = encrypt_api(payload)
    
    url = "https://clientbp.ggblueshark.com/RequestAddingFriend"
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        r = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), timeout=15, verify=False)
        
        if r.status_code == 200:
            if "BR_FRIEND_NOT_SAME_REGION" in r.text:
                return "❌ اللاعب ليس في نفس منطقتك"
            return "✅ تم إرسال طلب الصداقة بنجاح!"
                    
        elif r.status_code == 400:
            if "BR_FRIEND_NOT_SAME_REGION" in r.text:
                return "❌ اللاعب ليس في نفس منطقتك"
            return "❌ خطأ في الطلب"
        elif r.status_code == 401:
            JWT_TOKEN = None
            return "❌ التوكن غير صالح"
        elif r.status_code == 404:
            return "❌ اللاعب غير موجود"
        else:
            return f"❌ فشل إرسال الطلب. كود: {r.status_code}"
            
    except Exception as e:
        return f"❌ حدث خطأ: {str(e)}"

def remove_friend(player_id):
    """حذف صديق - من main.py"""
    global JWT_TOKEN
    if not JWT_TOKEN:
        return "⚠️ التوكن غير متاح حاليًا"
    
    enc_id = Encrypt_ID(player_id)
    payload = f"08a7c4839f1e10{enc_id}1802"  
    encrypted_payload = encrypt_api(payload)
    
    url = "https://clientbp.ggblueshark.com/RemoveFriend"
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        r = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), timeout=15, verify=False)
        
        if r.status_code == 200:
            return "✅ تم الحذف بنجاح!"
        elif r.status_code == 401:
            JWT_TOKEN = None
            return "❌ التوكن غير صالح"
        elif r.status_code == 400:
            return f"❌ فشل الحذف: {r.text}"
        elif r.status_code == 404:
            return "❌ اللاعب غير موجود"
        else:
            return f"❌ فشل الحذف. كود: {r.status_code}"
            
    except Exception as e:
        return f"❌ حدث خطأ: {str(e)}"

def get_player_info(uid):
    """جلب معلومات اللاعب - من main.py"""
    try:
        res = requests.get(f"https://tmk-all-info.vercel.app/info/{uid}", timeout=10)
        data = res.json()
        info = data["basicInfo"]
        name = info["nickname"]
        region = info["region"]
        level = info["level"]
        return name, region, level
    except Exception as e:
        print(f"⚠️ Error fetching info for {uid}: {e}")
        return "غير معروف", "N/A", "N/A"

def format_remaining_time(expiry_time):
    remaining = int(expiry_time - time.time())
    if remaining <= 0:
        return "⛔ انتهت الصلاحية"

    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = ((remaining % 86400) % 3600) // 60
    seconds = remaining % 60

    parts = []
    if days > 0:
        parts.append(f"{days} يوم")
    if hours > 0:
        parts.append(f"{hours} ساعة")
    if minutes > 0:
        parts.append(f"{minutes} دقيقة")
    parts.append(f"{seconds} ثانية")

    return " ".join(parts)

def get_total_users_count():
    count = 0
    for uid, data in users.items():
        if isinstance(data, dict) and "name" in data and "expiry" in data:
            count += 1
    return count

# ===============================================
# خيوط الخلفية (من main.py)
# ===============================================
def update_jwt_periodically():
    global JWT_TOKEN
    while True:
        new_token = fetch_jwt_token()
        if new_token:
            JWT_TOKEN = new_token
            print("🔄 تم تحديث التوكن بنجاح")
        else:
            print("⚠️ فشل تحديث التوكن")
        time.sleep(5 * 3600)  # كل 5 ساعات

def remove_expired_users():
    now = time.time()
    expired = [uid for uid, d in users.items() if d.get("expiry") and d["expiry"] <= now]
    for uid in expired:
        if "added_by_tele_id" in users[uid]:
            remove_friend(uid)
        del users[uid]
    save_users()

def check_expired_users():
    while True:
        remove_expired_users()
        time.sleep(60)

def reset_daily_adds():
    now = datetime.now()
    for tele_id in list(users.keys()):
        if 'last_reset_day' in users[tele_id]:
            last_reset = datetime.fromtimestamp(users[tele_id]['last_reset_day'])
            if now.date() > last_reset.date():
                users[tele_id]['adds_today'] = 0
                users[tele_id]['last_reset_day'] = now.timestamp()
    save_users()

def daily_reset_timer():
    while True:
        reset_daily_adds()
        time.sleep(3600)

# بدء الخيوط
print("🔄 جاري جلب التوكن للمرة الأولى...")
for _ in range(5):
    JWT_TOKEN = fetch_jwt_token()
    if JWT_TOKEN:
        print("✅ تم جلب التوكن بنجاح!")
        break
    time.sleep(3)

threading.Thread(target=update_jwt_periodically, daemon=True).start()
threading.Thread(target=check_expired_users, daemon=True).start()
threading.Thread(target=daily_reset_timer, daemon=True).start()

# ===============================================
# خادم HTTP للوحة التحكم
# ===============================================
class PanelHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_html_page()
        elif self.path == '/api/stats':
            self.send_json_response({
                'connected': JWT_TOKEN is not None,
                'users_count': get_total_users_count(),
                'groups_count': len(group_activations)
            })
        elif self.path == '/api/users':
            self.send_json_response({'users': users})
        elif self.path.startswith('/api/user/'):
            uid = self.path.split('/')[-1]
            if uid in users:
                self.send_json_response({'user': users[uid]})
            else:
                self.send_json_response({'error': 'User not found'}, 404)
        else:
            # محاولة إرسال ملف index.html
            try:
                with open('index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
            except:
                self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}
        
        if self.path == '/api/connect':
            response = self.handle_connect(data)
        elif self.path == '/api/send-request':
            response = self.handle_send_request(data)
        elif self.path == '/api/remove-friend':
            response = self.handle_remove_friend(data)
        elif self.path == '/api/add-user':
            response = self.handle_add_user(data)
        elif self.path == '/api/remove-user':
            response = self.handle_remove_user(data)
        elif self.path == '/api/remove-all':
            response = self.handle_remove_all()
        elif self.path == '/api/maintenance':
            response = self.handle_maintenance(data)
        else:
            response = {'success': False, 'message': 'Unknown endpoint'}
        
        self.send_json_response(response)
    
    def send_html_page(self):
        """إرسال صفحة HTML للوحة التحكم"""
        html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STRAVEX - لوحة التحكم</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Cairo', sans-serif; background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; padding: 20px; color: white; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #00ffff; }
        .logo { font-size: 28px; font-weight: bold; background: linear-gradient(135deg, #00ffff, #ff00ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .status { padding: 8px 15px; border-radius: 20px; background: rgba(0,255,0,0.1); border: 1px solid #00ff00; }
        .status.offline { background: rgba(255,0,0,0.1); border-color: #ff0000; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px; border: 1px solid #00ffff; }
        .card h2 { color: #00ffff; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; margin-bottom: 5px; color: #ccc; }
        .input-group input, .input-group select { width: 100%; padding: 10px; background: rgba(0,0,0,0.5); border: 1px solid #00ffff; border-radius: 8px; color: white; font-family: 'Cairo', sans-serif; }
        button { background: linear-gradient(135deg, #00ffff, #ff00ff); color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; width: 100%; font-family: 'Cairo', sans-serif; font-weight: bold; }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .message { margin-top: 10px; padding: 10px; border-radius: 8px; display: none; }
        .message.success { background: rgba(0,255,0,0.1); border: 1px solid #00ff00; display: block; color: #00ff00; }
        .message.error { background: rgba(255,0,0,0.1); border: 1px solid #ff0000; display: block; color: #ff0000; }
        .users-list { max-height: 400px; overflow-y: auto; }
        .user-item { background: rgba(255,255,255,0.05); border: 1px solid #00ffff; border-radius: 8px; padding: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .user-info { flex: 1; }
        .user-name { font-weight: bold; }
        .user-id { color: #00ffff; font-size: 12px; }
        .user-expiry { color: #ff00ff; font-size: 12px; }
        .delete-btn { background: none; border: none; color: #ff4444; cursor: pointer; font-size: 18px; }
        .stats { display: flex; gap: 20px; }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #00ffff; }
        .stat-label { color: #ccc; font-size: 14px; }
        .footer { text-align: center; padding: 20px; color: #ccc; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">STRAVEX PANEL</div>
            <div class="status" id="connectionStatus">غير متصل</div>
        </div>
        
        <div class="stats" style="margin-bottom: 30px;">
            <div class="stat">
                <div class="stat-value" id="totalUsers">0</div>
                <div class="stat-label">المستخدمين</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="activeGroups">0</div>
                <div class="stat-label">المجموعات</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="botStatus">-</div>
                <div class="stat-label">حالة البوت</div>
            </div>
        </div>
        
        <div class="grid">
            <!-- بطاقة إرسال طلب صداقة -->
            <div class="card">
                <h2><i class="fas fa-user-plus"></i> إرسال طلب صداقة</h2>
                <div class="input-group">
                    <label>معرف اللاعب</label>
                    <input type="text" id="targetUid" placeholder="أدخل UID">
                </div>
                <div class="input-group">
                    <label>المدة (أيام)</label>
                    <select id="duration">
                        <option value="1">1 يوم</option>
                        <option value="7">7 أيام</option>
                        <option value="30">30 يوم</option>
                    </select>
                </div>
                <button onclick="sendFriendRequest()" id="sendBtn">إرسال الطلب</button>
                <div id="requestResult" class="message"></div>
            </div>
            
            <!-- بطاقة حذف صديق -->
            <div class="card">
                <h2><i class="fas fa-user-minus"></i> حذف صديق</h2>
                <div class="input-group">
                    <label>معرف الصديق</label>
                    <input type="text" id="removeUid" placeholder="أدخل UID">
                </div>
                <button onclick="removeFriend()" id="removeBtn">حذف</button>
                <div id="removeResult" class="message"></div>
            </div>
        </div>
        
        <!-- قائمة الأصدقاء -->
        <div class="card">
            <h2><i class="fas fa-users"></i> قائمة الأصدقاء</h2>
            <div class="users-list" id="friendsList">
                <p style="text-align: center; color: #ccc;">لا يوجد أصدقاء</p>
            </div>
        </div>
    </div>
    
    <script>
        async function sendFriendRequest() {
            const uid = document.getElementById('targetUid').value;
            const duration = document.getElementById('duration').value;
            
            if (!uid) {
                showMessage('requestResult', '❌ الرجاء إدخال UID', false);
                return;
            }
            
            showMessage('requestResult', '🔄 جاري الإرسال...', true);
            
            try {
                const response = await fetch('/api/send-request', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({uid: uid, duration: duration})
                });
                const data = await response.json();
                
                if (data.success) {
                    showMessage('requestResult', '✅ ' + data.message, true);
                    document.getElementById('targetUid').value = '';
                    loadFriends();
                } else {
                    showMessage('requestResult', '❌ ' + data.message, false);
                }
            } catch (e) {
                showMessage('requestResult', '❌ خطأ في الاتصال', false);
            }
        }
        
        async function removeFriend() {
            const uid = document.getElementById('removeUid').value;
            
            if (!uid) {
                showMessage('removeResult', '❌ الرجاء إدخال UID', false);
                return;
            }
            
            try {
                const response = await fetch('/api/remove-friend', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({uid: uid})
                });
                const data = await response.json();
                
                if (data.success) {
                    showMessage('removeResult', '✅ ' + data.message, true);
                    document.getElementById('removeUid').value = '';
                    loadFriends();
                } else {
                    showMessage('removeResult', '❌ ' + data.message, false);
                }
            } catch (e) {
                showMessage('removeResult', '❌ خطأ في الاتصال', false);
            }
        }
        
        async function loadFriends() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                const friendsList = document.getElementById('friendsList');
                const users = data.users || {};
                
                if (Object.keys(users).length === 0) {
                    friendsList.innerHTML = '<p style="text-align: center; color: #ccc;">لا يوجد أصدقاء</p>';
                    return;
                }
                
                let html = '';
                for (const [uid, user] of Object.entries(users)) {
                    if (user.name) {
                        html += `
                            <div class="user-item">
                                <div class="user-info">
                                    <div class="user-name">${user.name}</div>
                                    <div class="user-id">${uid}</div>
                                    <div class="user-expiry">${user.expiry ? new Date(user.expiry*1000).toLocaleDateString() : 'غير محدد'}</div>
                                </div>
                                <button class="delete-btn" onclick="deleteFriend('${uid}')"><i class="fas fa-trash"></i></button>
                            </div>
                        `;
                    }
                }
                friendsList.innerHTML = html;
                
                document.getElementById('totalUsers').textContent = Object.keys(users).length;
                
            } catch (e) {
                console.error('Error loading friends:', e);
            }
        }
        
        async function deleteFriend(uid) {
            if (!confirm('هل أنت متأكد من حذف هذا الصديق؟')) return;
            
            document.getElementById('removeUid').value = uid;
            await removeFriend();
        }
        
        function showMessage(elementId, message, isSuccess) {
            const el = document.getElementById(elementId);
            el.textContent = message;
            el.className = 'message ' + (isSuccess ? 'success' : 'error');
        }
        
        async function updateStatus() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                const statusEl = document.getElementById('connectionStatus');
                if (data.connected) {
                    statusEl.textContent = 'متصل';
                    statusEl.className = 'status';
                } else {
                    statusEl.textContent = 'غير متصل';
                    statusEl.className = 'status offline';
                }
                
                document.getElementById('botStatus').textContent = data.connected ? '✅' : '❌';
            } catch (e) {
                console.error('Status update error:', e);
            }
        }
        
        // تحميل البيانات عند فتح الصفحة
        loadFriends();
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def handle_connect(self, data):
        """تسجيل الدخول بحساب ضيف"""
        global JWT_TOKEN
        uid = data.get('uid', '4589113906')
        password = data.get('password', '13D433BA6AC2D4E1599FC56E076522B6BD305439F0EA6A16C98802AC9375A382')
        
        new_token = fetch_jwt_token_direct()
        if new_token:
            JWT_TOKEN = new_token
            return {'success': True, 'message': '✅ تم الاتصال بنجاح'}
        else:
            return {'success': False, 'message': '❌ فشل الاتصال'}
    
    def handle_send_request(self, data):
        """إرسال طلب صداقة"""
        global JWT_TOKEN
        uid = data.get('uid')
        duration = int(data.get('duration', 1))
        
        if not uid:
            return {'success': False, 'message': 'الرجاء إدخال UID'}
        
        if not JWT_TOKEN:
            return {'success': False, 'message': 'البوت غير متصل'}
        
        # إرسال طلب الصداقة
        result = send_friend_request(uid)
        
        if "✅" in result:
            # جلب معلومات اللاعب
            name, region, level = get_player_info(uid)
            
            # حفظ المستخدم
            users[uid] = {
                "name": name,
                "expiry": time.time() + duration * 86400,
                "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_users()
            
            return {'success': True, 'message': f'تم إرسال الطلب إلى {name}'}
        else:
            return {'success': False, 'message': result}
    
    def handle_remove_friend(self, data):
        """حذف صديق"""
        global JWT_TOKEN
        uid = data.get('uid')
        
        if not uid:
            return {'success': False, 'message': 'الرجاء إدخال UID'}
        
        if not JWT_TOKEN:
            return {'success': False, 'message': 'البوت غير متصل'}
        
        if uid in users:
            result = remove_friend(uid)
            if "✅" in result:
                del users[uid]
                save_users()
                return {'success': True, 'message': result}
            else:
                return {'success': False, 'message': result}
        else:
            return {'success': False, 'message': 'اللاعب غير موجود'}
    
    def handle_add_user(self, data):
        """إضافة مستخدم يدويًا"""
        uid = data.get('uid')
        name = data.get('name', 'غير معروف')
        days = int(data.get('days', 1))
        
        if not uid:
            return {'success': False, 'message': 'الرجاء إدخال UID'}
        
        users[uid] = {
            "name": name,
            "expiry": time.time() + days * 86400,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users()
        
        return {'success': True, 'message': f'✅ تم إضافة {name}'}
    
    def handle_remove_user(self, data):
        uid = data.get('uid')
        if uid in users:
            del users[uid]
            save_users()
            return {'success': True, 'message': '✅ تم الحذف'}
        return {'success': False, 'message': '❌ اللاعب غير موجود'}
    
    def handle_remove_all(self):
        users.clear()
        save_users()
        return {'success': True, 'message': '✅ تم حذف الكل'}
    
    def handle_maintenance(self, data):
        global maintenance_mode
        maintenance_mode = data.get('enable', False)
        save_maintenance_status(maintenance_mode)
        return {'success': True, 'message': f'✅ وضع الصيانة: {maintenance_mode}'}

# ===============================================
# تشغيل الخادم
# ===============================================
def run_server():
    port = 8080
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, PanelHandler)
    
    print("=" * 60)
    print("🔥 STRAVEX PANEL - لوحة التحكم")
    print("=" * 60)
    print(f"✅ الخادم يعمل على: http://localhost:{port}")
    print(f"✅ حالة التوكن: {'متاح' if JWT_TOKEN else 'غير متاح'}")
    print(f"✅ عدد المستخدمين: {get_total_users_count()}")
    print("=" * 60)
    print("⚠️  اضغط Ctrl+C للإيقاف")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف الخادم")

if __name__ == "__main__":
    run_server()