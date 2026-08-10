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


def generate_qr_otp(session_token, time_step=10):
    """
    تولد رمز OTP ديناميكي يتغير كل (time_step) ثوانٍ (الافتراضي 10 ثوانٍ)
    بناءً على التوقيت الحالي ومفتاح الجلسة السري.
    """
    time_block = int(time.time() // time_step)
    # استخدام HMAC أمني
    key = session_token.encode("utf-8")
    message = str(time_block).encode("utf-8")
    hmac_digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    # نأخذ أول 16 حرفاً فقط للتبسيط
    return f"{time_block}-{hmac_digest[:16]}"


def validate_qr_otp(session_token, otp_string, time_step=10):
    """
    تتحقق من صحة الرمز الممسوح.
    تسمح بالرمز الحالي والرمز السابق (بفارق خطوة واحدة) لتفادي أي تأخير طفيف في الإرسال.
    """
    try:
        parts = otp_string.split("-")
        if len(parts) != 2:
            return False
        
        scanned_time_block = int(parts[0])
        scanned_hash = parts[1]
        
        current_time_block = int(time.time() // time_step)
        
        # السماح بفرق خطوة زمنية واحدة فقط (مثلاً، تأخير إرسال لـ 10 ثوانٍ)
        if abs(current_time_block - scanned_time_block) > 1:
            return False
            
        # إعادة حساب الـ HMAC للتأكد من عدم التلاعب
        key = session_token.encode("utf-8")
        message = str(scanned_time_block).encode("utf-8")
        expected_digest = hmac.new(key, message, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(scanned_hash, expected_digest[:16])
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
