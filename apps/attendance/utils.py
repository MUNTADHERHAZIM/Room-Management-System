import socket
import hashlib
import hmac
import time
from django.conf import settings


def get_local_ips():
    """
    تكتشف عناوين الـ IP المحلية (IPv4) الخاصة بجهاز الأستاذ (الخادم)
    لاستخدامها في إرشاد الطلاب للاتصال بدون إنترنت.
    """
    ips = []
    try:
        # الحصول على كافة الواجهات الشبكية عدا الـ Localhost
        hostname = socket.gethostname()
        addresses = socket.getaddrinfo(hostname, None)
        for addr in addresses:
            ip = addr[4][0]
            # تصفية عناوين IPv4 فقط واستبعاد الـ localhost والـ IPv6
            if "." in ip and not ip.startswith("127."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    
    # حل بديل إذا فشلت الطريقة الأولى
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # لا يتطلب اتصالاً فعلياً بالإنترنت لتحديد الكارت المفعّل
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            ips.append(local_ip)
        except Exception:
            ips.append("127.0.0.1")
            
    return list(set(ips))


def generate_qr_otp(session_token, time_step=30, is_fixed=False):
    """
    تولد رمز QR مشفر للجلسة:
    - إذا كان is_fixed=True: يولد رمزاً ثابتاً طوال الجلسة (نمط تثبيت الرمز).
    - إذا كان ديناميكياً: يتغير الرمز على الشاشة كل 30 ثانية لمنع تصوير الشاشة وتمريرها.
    """
    if is_fixed:
        fixed_hash = hashlib.sha256(f"FIXED:{session_token}".encode("utf-8")).hexdigest()[:16]
        return f"FIXED-{fixed_hash}"

    time_block = int(time.time() // time_step)
    key = session_token.encode("utf-8")
    message = str(time_block).encode("utf-8")
    hmac_digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{time_block}-{hmac_digest[:16]}"


def validate_qr_otp(session_token, otp_string, session_pin=None, time_step=30, max_valid_seconds=1800):
    """
    تتحقق من صحة الرمز الممسوح أمنياً:
    1. تقبل النمط الثابت (Fixed Mode) طالما الجلسة مفتوحة.
    2. تقبل رمز الـ PIN إذا طابق الجلسة.
    3. في النمط الديناميكي: تمنح الطالب مهلة تصل إلى 30 دقيقة (1800 ثانية) بعد مسح الكود
       لكتابة اسمه ورقمه الجامعي وإرسال التحضير براحة تامة دون انتهاء الصلاحية!
    """
    if not otp_string:
        return False
        
    try:
        # 1. فحص النمط الثابت (تثبيت الرمز)
        if otp_string.startswith("FIXED-"):
            expected_fixed = f"FIXED-{hashlib.sha256(f'FIXED:{session_token}'.encode('utf-8')).hexdigest()[:16]}"
            return hmac.compare_digest(otp_string, expected_fixed)
            
        # 2. فحص مطابقة الـ PIN
        if session_pin:
            clean_pin = str(session_pin).strip().upper()
            if otp_string.upper() in (clean_pin, f"PIN-{clean_pin}"):
                return True

        # 3. فحص الرمز الديناميكي
        parts = otp_string.split("-")
        if len(parts) != 2:
            return False
        
        scanned_time_block = int(parts[0])
        scanned_hash = parts[1]
        
        # التأكد من صحة التوقيع الأمني أولاً لمنع التلاعب
        key = session_token.encode("utf-8")
        message = str(scanned_time_block).encode("utf-8")
        expected_digest = hmac.new(key, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(scanned_hash, expected_digest[:16]):
            return False
            
        # فحص العمر الزمني للرمز: نمنح الطالب 30 دقيقة (1800 ثانية) من وقت المسح
        scanned_timestamp = scanned_time_block * time_step
        current_timestamp = time.time()
        
        age = current_timestamp - scanned_timestamp
        # نقبل الرمز طالما عمره أقل من 30 دقيقة مع سماح 60 ثانية لفروق التوقيت
        if -60 <= age <= max_valid_seconds:
            return True
            
        return False
    except Exception:
        return False



def get_device_fingerprint(request):
    """
    تولد بصمة فريدة لجهاز الطالب بناءً على بيانات المتصفح والعنوان
    للمساعدة في كشف تسجيل الطلاب المتكرر من نفس الهاتف.
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    accept_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    # نستخدم البيانات المتوفرة لتكوين سلسلة نصية فريدة للجهاز
    fingerprint_raw = f"{user_agent}|{accept_lang}"
    return hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()
