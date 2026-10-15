import io
import uuid
import datetime
import time
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q

from django.core.paginator import Paginator
from apps.core.models import Department
from apps.schedules.models import Schedule
from apps.exams.models import Student
from apps.subjects.models import Subject
from apps.instructors.models import Instructor
from apps.rooms.models import Room
from apps.core.decorators import permission_required
from .models import AttendanceSession, AttendanceRecord
from .utils import get_local_ips, generate_qr_otp, validate_qr_otp, get_device_fingerprint


@login_required
@permission_required('can_access_attendance')
def session_list(request):
    """
    لوحة تحكم الحضور العامة للأستاذ وإحصائيات بوابة الحضور.
    """
    schedules = Schedule.objects.filter(is_active=True).select_related("room", "instructor", "subject")
    sessions = AttendanceSession.objects.all().select_related("schedule", "schedule__subject", "schedule__room", "subject", "room", "instructor")
    
    today = datetime.date.today()
    active_sessions = sessions.filter(is_active=True)
    past_sessions = sessions.filter(is_active=False)

    # إحصائيات اليوم العامة لبطاقات الـ KPIs
    today_records = AttendanceRecord.objects.filter(session__date=today)
    today_present_count = today_records.filter(status="حاضر").count()
    today_absent_count = today_records.filter(status="غائب").count()
    today_late_count = today_records.filter(status="متأخر").count()
    today_excused_count = today_records.filter(status="مستأذن").count()
    today_total_records = today_records.count()
    
    attendance_rate = round((today_present_count / today_total_records * 100), 1) if today_total_records > 0 else 0

    subjects = Subject.objects.filter(is_active=True)
    instructors = Instructor.objects.filter(is_active=True)
    rooms = Room.objects.filter(is_active=True)
    departments = Department.objects.all()

    return render(request, "attendance/dashboard.html", {
        "schedules": schedules,
        "active_sessions": active_sessions,
        "past_sessions": past_sessions[:10],
        "today": today,
        "subjects": subjects,
        "instructors": instructors,
        "rooms": rooms,
        "departments": departments,
        "today_present_count": today_present_count,
        "today_absent_count": today_absent_count,
        "today_late_count": today_late_count,
        "today_excused_count": today_excused_count,
        "today_total_records": today_total_records,
        "attendance_rate": attendance_rate,
        "total_sessions_count": sessions.count(),
    })



@login_required
def offline_setup_guide(request):
    """
    صفحة دليل إعداد نقطة الاتصال (Hotspot) للأستاذ.
    تكتشف عناوين الـ IP الخاصة بالجهاز لعرضها للطلاب.
    """
    local_ips = get_local_ips()
    host_port = request.get_port()
    
    # تجهيز الروابط المباشرة التي سيكتبها الطلاب
    guide_urls = [f"http://{ip}:{host_port}" for ip in local_ips]
    
    return render(request, "attendance/offline_guide.html", {
        "local_ips": local_ips,
        "host_port": host_port,
        "guide_urls": guide_urls,
    })


@login_required
def create_session(request, schedule_pk):
    """
    إنشاء جلسة حضور جديدة لحصة معينة لتاريخ اليوم.
    """
    schedule = get_object_or_404(Schedule, pk=schedule_pk)
    today = datetime.date.today()
    
    # التحقق مما إذا كانت هناك جلسة حضور مفتوحة اليوم لهذه الحصة مسبقاً
    session, created = AttendanceSession.objects.get_or_create(
        schedule=schedule,
        date=today,
        defaults={
            "session_token": str(uuid.uuid4()),
            "is_active": True
        }
    )
    
    if not created and not session.is_active:
        # إعادة تنشيط الجلسة إذا كانت مغلقة
        session.is_active = True
        session.session_token = str(uuid.uuid4())
        session.save()
        messages.success(request, f"تم إعادة فتح جلسة الحضور للمادة {schedule.subject.name}")
    elif created:
        messages.success(request, f"تم إنشاء جلسة حضور جديدة للمادة {schedule.subject.name}")
    else:
        messages.info(request, f"جلسة الحضور نشطة بالفعل للمادة {schedule.subject.name}")
        
    return redirect("attendance:session_detail", pk=session.pk)

@login_required
def create_adhoc_session(request):
    """
    إنشاء جلسة حضور استثنائية (Ad-Hoc) دون الحاجة لجدول مسبق
    """
    if request.method == "POST":
        subject_id = request.POST.get("subject_id")
        instructor_id = request.POST.get("instructor_id")
        room_id = request.POST.get("room_id")
        
        subject = get_object_or_404(Subject, pk=subject_id)
        instructor = get_object_or_404(Instructor, pk=instructor_id)
        room = get_object_or_404(Room, pk=room_id)
        
        session = AttendanceSession.objects.create(
            session_type='استثنائية',
            subject=subject,
            instructor=instructor,
            room=room,
            date=datetime.date.today(),
            session_token=str(uuid.uuid4()),
            is_active=True
        )
        messages.success(request, f"تم إنشاء جلسة حضور سريعة للمادة {subject.name}")
        return redirect("attendance:session_detail", pk=session.pk)
    
    return redirect("attendance:session_list")


@login_required
def session_detail(request, pk):
    """
    لوحة تحكم الأستاذ التفاعلية لعرض الـ QR وعداد الحاضرين اللحظي.
    تدعم التحديث اللحظي عبر HTMX.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    records = session.records.select_related("student", "student__department").order_by("-scanned_at")
    
    # إحصائيات سريعة
    total_present = records.filter(status="حاضر").count()
    total_late = records.filter(status="متأخر").count()
    total_excused = records.filter(status="مستأذن").count()
    total_absent = records.filter(status="غائب").count()
    
    # فحص تعارض بصمة الأجهزة (إذا تكررت نفس البصمة لأكثر من طالب)
    fingerprints = {}
    for r in records:
        if r.device_fingerprint:
            fingerprints[r.device_fingerprint] = fingerprints.get(r.device_fingerprint, 0) + 1
            
    # تمييز السجلات التي تحتوي على تكرار بصمة جهاز
    duplicate_fingerprints = {fp for fp, count in fingerprints.items() if count > 1}
    for r in records:
        r.has_fp_conflict = r.device_fingerprint in duplicate_fingerprints

    # إغلاق الجلسة يدوياً
    if request.method == "POST" and "close_session" in request.POST:
        session.is_active = False
        session.save()
        messages.success(request, "تم إغلاق الجلسة وحفظ تقرير الحضور بنجاح.")
        return redirect("attendance:session_list")

    # جلب قائمة الطلاب للتحضير اليدوي السريع
    if session.session_type == 'مجدولة' and session.schedule:
        department = session.schedule.room.department
        stage = session.schedule.subject.stage if hasattr(session.schedule.subject, 'stage') else 'الأولى'
    else:
        department = session.room.department if session.room else None
        stage = session.subject.stage if session.subject and hasattr(session.subject, 'stage') else 'الأولى'
    
    students = Student.objects.filter(department=department, is_active=True).order_by("name")

    context = {
        "session": session,
        "records": records,
        "total_present": total_present,
        "total_late": total_late,
        "total_excused": total_excused,
        "total_absent": total_absent,
        "duplicate_count": len(duplicate_fingerprints),
        "students": students,
    }

    # إذا كان الطلب قادماً من HTMX لتحديث قائمة الحاضرين فقط
    if request.headers.get("HX-Request"):
        return render(request, "attendance/partials/student_table.html", context)

    return render(request, "attendance/session_detail.html", context)


def rotate_qr(request, pk):
    """
    ممر API لتوليد رمز QR مشفر:
    - يدعم النمط الثابت (mode=fixed) لتثبيت الرمز طوال الجلسة بدون أي انتهاء صلاحية.
    - يدعم النمط الديناميكي (mode=dynamic) مع منح الطالب 30 دقيقة بعد المسح لإتمام التسجيل.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    if not session.is_active:
        return JsonResponse({"success": False, "error": "الجلسة مغلقة"})
        
    mode = request.GET.get("mode", "dynamic")
    is_fixed = (mode == "fixed")
    
    otp = generate_qr_otp(session.session_token, time_step=30, is_fixed=is_fixed)
    
    # بناء رابط التحضير الذي سيمسحه الطالب
    host = request.get_host()
    # إذا كان الأستاذ يفتح لوحة التحكم عبر localhost أو 127.0.0.1، سنقوم باستبداله بالـ IP الحقيقي للشبكة
    if "localhost" in host or "127.0.0.1" in host:
        local_ips = get_local_ips()
        if local_ips and local_ips[0] != "127.0.0.1":
            port = request.get_port()
            host = f"{local_ips[0]}:{port}"

    full_url = f"http://{host}/attendance/scan/{otp}/"
    seconds_left = 9999 if is_fixed else (30 - (int(time.time()) % 30))
    
    return JsonResponse({
        "success": True,
        "token": otp,
        "url": full_url,
        "seconds_left": seconds_left,
        "is_fixed": is_fixed,
        "pin": session.session_pin
    })


def student_scan(request, otp_token):
    """
    صفحة الطالب التي تفتح عند مسح الـ QR.
    تتعرف تلقائياً على الجلسة بناءً على الرمز وتتحقق من صحته ووقته.
    """
    # البحث عن جلسة حضور نشطة تطابق الرمز الأمني
    active_sessions = AttendanceSession.objects.filter(is_active=True)
    matched_session = None
    
    for session in active_sessions:
        if validate_qr_otp(session.session_token, otp_token, session_pin=session.session_pin):
            matched_session = session
            break
            
    if not matched_session:
        return render(request, "attendance/student_scan.html", {
            "success": False,
            "error": "رمز التحضير منتهي الصلاحية أو غير صالح. يرجى مسح الرمز الجديد المعروض على الشاشة."
        })

    # جلب الطلاب المسجلين    # نربط الطلاب بالقسم والمرحلة الخاصة بمادة الجلسة
    if matched_session.session_type == 'مجدولة' and matched_session.schedule:
        department = matched_session.schedule.room.department
        stage = matched_session.schedule.subject.stage if hasattr(matched_session.schedule.subject, 'stage') else 'الأولى'
    else:
        department = matched_session.room.department if matched_session.room else None
        stage = matched_session.subject.stage if matched_session.subject and hasattr(matched_session.subject, 'stage') else 'الأولى'
    
    
    # جلب قائمة طلاب القسم للمرحلة الحالية لتسهيل عملية التحضير الذكي
    students = Student.objects.filter(
        department=department,
        is_active=True
    ).order_by("name")

    return render(request, "attendance/student_scan.html", {
        "success": True,
        "session": matched_session,
        "students": students,
        "otp_token": otp_token
    })


@csrf_exempt
def submit_attendance(request, pk):
    """
    ممر API لتأكيد وتسجيل حضور الطالب أمنياً.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة الطلب غير صالحة"}, status=405)
        
    session = get_object_or_404(AttendanceSession, pk=pk)
    if not session.is_active:
        return JsonResponse({"success": False, "error": "نعتذر، جلسة الحضور مغلقة حالياً!"}, status=400)
        
    otp_token = request.POST.get("otp_token")
    # يسمح بتخطي التحقق من رمز الـ QR إذا كان الطلب مرسلاً من شاشة ماسح الأستاذ المسجل دخوله
    is_scanner_bypass = request.user.is_authenticated and request.POST.get("bypass_otp") == "true"
    
    if not is_scanner_bypass:
        # التحقق من صلاحية الرمز مع دعم النمط الثابت والمهلة الواسعة (30 دقيقة)
        if not validate_qr_otp(session.session_token, otp_token, session_pin=session.session_pin):
            return JsonResponse({"success": False, "error": "انتهت صلاحية الرمز! يرجى إعادة مسح الـ QR المحدث من شاشة الأستاذ."}, status=400)

        
    student_id = request.POST.get("student")
    university_id = request.POST.get("university_id")
    
    # البحث عن الطالب إما عبر معرفه أو رقمه الجامعي
    student = None
    if student_id:
        student = Student.objects.filter(pk=student_id, is_active=True).first()
    elif university_id:
        student = Student.objects.filter(university_id=university_id, is_active=True).first()
        
    if not student:
        return JsonResponse({"success": False, "error": "الطالب غير مسجل بالنظام أو الرقم الجامعي خاطئ!"}, status=404)
        
    # التحقق من بصمة الجهاز
    device_fp = get_device_fingerprint(request)
    
    # تسجيل الحضور
    record, created = AttendanceRecord.objects.get_or_create(
        session=session,
        student=student,
        defaults={
            "status": "حاضر",
            "device_fingerprint": device_fp
        }
    )
    
    if not created:
        return JsonResponse({"success": True, "info": "تم تسجيل حضورك مسبقاً بنجاح!", "student_name": student.name})
        
    return JsonResponse({
        "success": True,
        "message": "تم تسجيل حضورك بنجاح! شكراً لك.",
        "student_name": student.name
    })


@login_required
def export_excel(request, pk):
    """
    تصدير قائمة حضور الجلسة كملف إكسل (Excel) منسق باحترافية عالية.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    records = session.records.select_related("student", "student__department").order_by("student__name")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "قائمة الحضور"
    
    # ضبط الكتابة من اليمين لليسار
    ws.views.sheetView[0].showGridLines = True
    ws.sheet_properties.tabColor = "1047A3"
    
    # الخطوط والأنماط
    title_font = Font(name="Arial", size=16, bold=True, color="1E3A8A")
    meta_font = Font(name="Arial", size=11, bold=True, color="475569")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=11, color="000000")
    
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    even_row_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    # ترويسة التقرير
    ws.merge_cells("A1:F1")
    ws["A1"] = f"تقرير حضور ذكي بالـ QR - مادة: {session.get_subject_name}"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40
    
    # بيانات وصفية للجلسة
    ws["A3"] = "الأستاذ:"
    ws["A3"].font = meta_font
    ws["B3"] = session.get_instructor_name
    ws["B3"].font = data_font
    
    ws["C3"] = "القاعة الدراسية:"
    ws["C3"].font = meta_font
    ws["D3"] = session.get_room_name
    ws["D3"].font = data_font
    
    ws["E3"] = "تاريخ اليوم:"
    ws["E3"].font = meta_font
    ws["F3"] = session.date.strftime("%Y-%m-%d")
    ws["F3"].font = data_font
    
    # رؤوس الجدول
    headers = ["الرقم الجامعي", "اسم الطالب الكامل", "القسم الدراسي", "المرحلة", "توقيت تسجيل الحضور", "الحالة"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    
    ws.row_dimensions[5].height = 25
    
    # تعبئة البيانات
    row_idx = 6
    for record in records:
        student = record.student
        scanned_time = timezone.localtime(record.scanned_at).strftime("%I:%M:%S %p") if record.scanned_at else "-"
        
        row_data = [
            student.university_id,
            student.name,
            student.department.name,
            student.stage,
            scanned_time,
            record.status
        ]
        
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "right", vertical="center")
            cell.border = thin_border
            # تعبئة متبادلة للصفوف لجمالية العرض
            if row_idx % 2 == 0:
                cell.fill = even_row_fill
                
        ws.row_dimensions[row_idx].height = 20
        row_idx += 1
        
    # ضبط العرض التلقائي للأعمدة
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                # نأخذ طول النص التقريبي
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        
    # تصدير الملف للمتصفح
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="attendance_{session.get_subject_name}_{session.date}.xlsx"'
    wb.save(response)
    return response


@login_required
def export_pdf(request, pk):
    """
    تصدير قائمة حضور الجلسة كملف PDF رسمي منسق بصيغة A4 يدعم اللغة العربية تماماً.
    """
    import os
    session = get_object_or_404(AttendanceSession, pk=pk)
    records = session.records.select_related("student", "student__department").order_by("student__name")
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="attendance_{session.pk}.pdf"'
    
    # تجهيز الملف بحدود A4
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    
    elements = []
    
    from apps.core.pdf_utils import register_arabic_fonts, reshape_arabic
    font_name = register_arabic_fonts()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Title"].fontName = font_name
            
    # العناوين والترويسة
    title_style = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Title"],
        alignment=1, # توسيط
        fontSize=16,
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        "ArabicMeta",
        parent=styles["Normal"],
        alignment=2, # يمين
        fontSize=10,
        leading=15
    )
    
    elements.append(Paragraph(reshape_arabic(f"تقرير حضور الطلاب الرسمي - نظام الـ QR الذكي"), title_style))
    elements.append(Spacer(1, 0.2 * cm))
    
    # تفاصيل الجلسة كجدول علوي بسيط
    meta_info = [
        [reshape_arabic(f"الأستاذ: {session.get_instructor_name}"), reshape_arabic(f"المادة: {session.get_subject_name}")],
        [reshape_arabic(f"القاعة: {session.get_room_name}"), reshape_arabic(f"التاريخ: {session.date.strftime('%Y-%m-%d')}")],
        [reshape_arabic(f"عدد الطلاب الحاضرين: {records.count()} طالب"), ""]
    ]
    meta_table = Table(meta_info, colWidths=[9 * cm, 9 * cm])
    meta_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 0.8 * cm))
    
    # شبكة الحضور
    # الترويسات
    grid = [[
        reshape_arabic("توقيع الطالب"),
        reshape_arabic("وقت التحضير"),
        reshape_arabic("المرحلة"),
        reshape_arabic("القسم الدراسي"),
        reshape_arabic("اسم الطالب الكامل"),
        reshape_arabic("الرقم الجامعي"),
    ]]
    
    # السجلات
    for i, record in enumerate(records, 1):
        student = record.student
        scanned_time = timezone.localtime(record.scanned_at).strftime("%I:%M %p") if record.scanned_at else "-"
        grid.append([
            "", # توقيع الطالب
            reshape_arabic(scanned_time),
            reshape_arabic(student.stage),
            reshape_arabic(student.department.name),
            reshape_arabic(student.name),
            reshape_arabic(student.university_id)
        ])
        
    # بناء الجدول
    table = Table(grid, colWidths=[3 * cm, 2.5 * cm, 2 * cm, 3.5 * cm, 5 * cm, 2 * cm])
    
    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.1, 0.2, 0.4)), # كحلي داكن
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]
    
    # تلوين متبادل للصفوف
    for idx in range(1, len(grid)):
        if idx % 2 == 0:
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.Color(0.95, 0.96, 0.98)))
            
    table.setStyle(TableStyle(table_style))
    elements.append(table)
    elements.append(Spacer(1, 1.5 * cm))
    
    # تذييل التوقيعات للأستاذ والعميد
    signature_data = [
        ["", ""],
        [reshape_arabic("توقيع أستاذ المادة: ........................"), reshape_arabic("مصادقة رئيس القسم الدراسي: ........................")]
    ]
    signature_table = Table(signature_data, colWidths=[9 * cm, 9 * cm])
    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(signature_table)
    
    doc.build(elements)
    return response


def digital_id(request):
    """
    صفحة عرض كارت الهوية الرقمية للطلاب (Digital ID).
    تتيح للطالب إدخال رقمه الجامعي والحصول على كارت هوية بترميز QR ثابت،
    والذي يمكن للطالب أخذ لقطة شاشة له للتحضير به أوفلاين بالكامل.
    """
    student = None
    error = None
    search = request.GET.get("university_id", "")
    
    if search:
        student = Student.objects.filter(university_id=search, is_active=True).select_related("department").first()
        if not student:
            error = "عذراً، هذا الرقم الجامعي غير مسجل أو غير نشط في النظام!"
            
    return render(request, "attendance/digital_id.html", {
        "student": student,
        "error": error,
        "search_query": search
    })


@login_required
def scanner_view(request, pk):
    """
    صفحة ماسح الـ QR للطلاب الخاصة بالأستاذ.
    تفتح كاميرا جهاز الأستاذ لمسح بطاقات هوية الطلاب وتسجيل حضورهم فوراً أوفلاين.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    return render(request, "attendance/scanner.html", {
        "session": session
    })


def student_join_by_pin(request):
    """
    نظام التحضير الذاتي للطالب عبر رمز الجلسة السري (PIN) والرقم الجامعي.
    حالة الطوارئ عند عدم القدرة على مسح الـ QR.
    """
    if request.method == "POST":
        pin = request.POST.get("pin", "").strip().upper()
        university_id = request.POST.get("university_id", "").strip()
        
        session = AttendanceSession.objects.filter(session_pin=pin, is_active=True).first()
        if not session:
            return render(request, "attendance/join_by_pin.html", {
                "error": "رمز الجلسة غير صحيح أو أن الجلسة قد أُغلقت.", 
                "pin": pin, 
                "uid": university_id
            })
            
        student = Student.objects.filter(university_id=university_id, is_active=True).first()
        if not student:
            return render(request, "attendance/join_by_pin.html", {
                "error": "الرقم الجامعي غير مسجل في النظام.", 
                "pin": pin, 
                "uid": university_id
            })
            
        # Check device fingerprint
        device_fp = get_device_fingerprint(request)
        
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={
                "status": "حاضر",
                "device_fingerprint": device_fp,
                "notes": "تم التحضير يدوياً عبر رمز الـ PIN"
            }
        )
        
        if not created:
            return render(request, "attendance/join_by_pin.html", {
                "success": True, 
                "info": True, 
                "student": student,
                "session": session
            })
            
        return render(request, "attendance/join_by_pin.html", {
            "success": True, 
            "student": student,
            "session": session
        })
        
    return render(request, "attendance/join_by_pin.html")


# ==========================================
# ميزات المرونة العالية والسجل العام الشامل
# ==========================================

def _get_session_context(session):
    """دالة مساعدة لبناء السياق الموحد لجدول حضور الجلسة"""
    records = session.records.select_related("student", "student__department").order_by("-scanned_at")
    total_present = records.filter(status="حاضر").count()
    total_late = records.filter(status="متأخر").count()
    total_excused = records.filter(status="مستأذن").count()
    total_absent = records.filter(status="غائب").count()
    
    fingerprints = {}
    for r in records:
        if r.device_fingerprint:
            fingerprints[r.device_fingerprint] = fingerprints.get(r.device_fingerprint, 0) + 1
            
    duplicate_fingerprints = {fp for fp, count in fingerprints.items() if count > 1}
    for r in records:
        r.has_fp_conflict = r.device_fingerprint in duplicate_fingerprints

    if session.session_type == 'مجدولة' and session.schedule:
        department = session.schedule.room.department
    else:
        department = session.room.department if session.room else None
    
    students = Student.objects.filter(department=department, is_active=True).order_by("name") if department else Student.objects.filter(is_active=True).order_by("name")

    return {
        "session": session,
        "records": records,
        "total_present": total_present,
        "total_late": total_late,
        "total_excused": total_excused,
        "total_absent": total_absent,
        "duplicate_count": len(duplicate_fingerprints),
        "students": students,
    }


@login_required
def toggle_record_status(request, pk):
    """
    تغيير حالة حضور طالب يدوياً وبمرونة كاملة (حاضر / غائب / متأخر / مستأذن) مع إضافة ملاحظة.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        new_status = request.POST.get("status")
        notes = request.POST.get("notes", "").strip()

        student = get_object_or_404(Student, pk=student_id)
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={"status": new_status, "notes": notes}
        )
        if not created:
            record.status = new_status
            if notes:
                record.notes = notes
            record.save()

        messages.success(request, f"تم تحديث حالة الطالب {student.name} إلى ({new_status}).")

    if request.headers.get("HX-Request"):
        ctx = _get_session_context(session)
        return render(request, "attendance/partials/student_table.html", ctx)

    return redirect("attendance:session_detail", pk=session.pk)


@login_required
def mark_remaining_absent(request, pk):
    """
    تحضير كافة الطلاب المتبقين في القسم كـ غائبين بنقرة واحدة عند إنهاء الجلسة.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.method == "POST":
        if session.session_type == 'مجدولة' and session.schedule:
            department = session.schedule.room.department
        else:
            department = session.room.department if session.room else None

        students = Student.objects.filter(is_active=True)
        if department:
            students = students.filter(department=department)

        existing_ids = session.records.values_list("student_id", flat=True)
        unrecorded_students = students.exclude(id__in=existing_ids)

        new_records = [
            AttendanceRecord(
                session=session,
                student=student,
                status="غائب",
                notes="تم التسجيل كغائب تلقائياً"
            )
            for student in unrecorded_students
        ]
        AttendanceRecord.objects.bulk_create(new_records)
        messages.success(request, f"تم تحضير {len(new_records)} طالب كـ غائبين بنجاح.")

    if request.headers.get("HX-Request"):
        ctx = _get_session_context(session)
        return render(request, "attendance/partials/student_table.html", ctx)

    return redirect("attendance:session_detail", pk=session.pk)


@login_required
def add_manual_record(request, pk):
    """
    إضافة طالب يدوياً للجلسة مع تحديد الحالة والعذر المرفق.
    """
    session = get_object_or_404(AttendanceSession, pk=pk)
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        status = request.POST.get("status", "حاضر")
        notes = request.POST.get("notes", "").strip()

        student = get_object_or_404(Student, pk=student_id)
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={"status": status, "notes": notes}
        )
        if not created:
            record.status = status
            record.notes = notes
            record.save()

        messages.success(request, f"تم إضافة/تحديث حضور الطالب {student.name} بنجاح.")

    if request.headers.get("HX-Request"):
        ctx = _get_session_context(session)
        return render(request, "attendance/partials/student_table.html", ctx)

    return redirect("attendance:session_detail", pk=session.pk)


def _build_history_queryset(request):
    """دالة مساعدة لفلترة سجلات الحضور الشاملة"""
    records = AttendanceRecord.objects.select_related(
        "session", "student", "student__department",
        "session__schedule", "session__subject", "session__room", "session__instructor",
        "session__schedule__subject", "session__schedule__room", "session__schedule__instructor"
    ).all().order_by("-session__date", "-scanned_at")

    department_id = request.GET.get("department")
    stage = request.GET.get("stage")
    subject_id = request.GET.get("subject")
    status = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    search = request.GET.get("search", "").strip()

    if department_id:
        records = records.filter(student__department_id=department_id)
    if stage:
        records = records.filter(student__stage=stage)
    if subject_id:
        records = records.filter(
            Q(session__schedule__subject_id=subject_id) | Q(session__subject_id=subject_id)
        )
    if status:
        records = records.filter(status=status)
    if date_from:
        records = records.filter(session__date__gte=date_from)
    if date_to:
        records = records.filter(session__date__lte=date_to)
    if search:
        records = records.filter(
            Q(student__name__icontains=search) | Q(student__university_id__icontains=search)
        )

    return records


@login_required
@permission_required('can_access_attendance')
def attendance_history(request):
    """
    سجل الحضور العام والتقارير الشاملة لجميع الجلسات والطلاب مع الفلترة والتصدير.
    """
    records_qs = _build_history_queryset(request)

    # حساب ملخص الإحصائيات لنتائج الفلترة
    total_records = records_qs.count()
    present_count = records_qs.filter(status="حاضر").count()
    absent_count = records_qs.filter(status="غائب").count()
    late_count = records_qs.filter(status="متأخر").count()
    excused_count = records_qs.filter(status="مستأذن").count()
    attendance_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0

    # تقسيم الصفحات Paginator
    paginator = Paginator(records_qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.all()
    subjects = Subject.objects.filter(is_active=True)

    return render(request, "attendance/history.html", {
        "page_obj": page_obj,
        "total_records": total_records,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "excused_count": excused_count,
        "attendance_rate": attendance_rate,
        "departments": departments,
        "subjects": subjects,
        "selected_dept": request.GET.get("department", ""),
        "selected_stage": request.GET.get("stage", ""),
        "selected_subject": request.GET.get("subject", ""),
        "selected_status": request.GET.get("status", ""),
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "search_query": request.GET.get("search", ""),
    })


@login_required
def student_attendance_detail(request, student_pk):
    """
    عرض الكارت التفصيلي وسجل الحضور الكامل لطالب معين ومستوى إنذار الغياب.
    """
    student = get_object_or_404(Student, pk=student_pk)
    records = AttendanceRecord.objects.filter(student=student).select_related(
        "session", "session__subject", "session__schedule", "session__schedule__subject"
    ).order_by("-session__date")

    total = records.count()
    present = records.filter(status="حاضر").count()
    absent = records.filter(status="غائب").count()
    late = records.filter(status="متأخر").count()
    excused = records.filter(status="مستأذن").count()

    attendance_rate = round((present / total * 100), 1) if total > 0 else 100.0
    absent_rate = round((absent / total * 100), 1) if total > 0 else 0.0

    # تقييم الإنذار
    if absent_rate >= 15:
        warning_info = {"status": "محروم", "badge_class": "bg-red-600 text-white", "desc": "تجاوز نسبة الغياب المسموحة (15%) - صدر بحقه حرمان."}
    elif absent_rate >= 10:
        warning_info = {"status": "إنذار نهائي", "badge_class": "bg-amber-600 text-white", "desc": "تجاوز نسبة غياب (10%) - إنذار غياب نهائي."}
    elif absent_rate >= 5:
        warning_info = {"status": "إنذار أول", "badge_class": "bg-yellow-500 text-white", "desc": "تجاوز نسبة غياب (5%) - تنبيه غياب أولي."}
    else:
        warning_info = {"status": "منتظم", "badge_class": "bg-emerald-600 text-white", "desc": "حضور منتظم دون إنذارات."}

    return render(request, "attendance/student_history.html", {
        "student": student,
        "records": records,
        "total": total,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_rate": attendance_rate,
        "absent_rate": absent_rate,
        "warning_info": warning_info,
    })


@login_required
def export_history_excel(request):
    """
    تصدير السجل الشامل للحضور المفلتر بملف Excel احترافي.
    """
    records = _build_history_queryset(request)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "سجل الحضور الشامل"

    ws.views.sheetView[0].showGridLines = True
    ws.sheet_properties.tabColor = "1E3A8A"

    title_font = Font(name="Arial", size=16, bold=True, color="1E3A8A")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=11, color="000000")

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    even_row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    ws.merge_cells("A1:G1")
    ws["A1"] = "تقرير سجل الحضور والغياب الشامل"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    headers = ["تاريخ الجلسة", "الرقم الجامعي", "اسم الطالب", "القسم", "المادة الدراسية", "حالة الحضور", "ملاحظات / عذر"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    ws.row_dimensions[3].height = 25

    row_idx = 4
    for record in records:
        student = record.student
        session = record.session
        date_str = session.date.strftime("%Y-%m-%d")

        row_data = [
            date_str,
            student.university_id,
            student.name,
            student.department.name if student.department else "-",
            session.get_subject_name,
            record.status,
            record.notes or "-"
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.alignment = Alignment(horizontal="center" if col_idx != 3 else "right", vertical="center")
            cell.border = thin_border
            if row_idx % 2 == 0:
                cell.fill = even_row_fill
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="master_attendance_report.xlsx"'
    wb.save(response)
    return response


@login_required
def export_history_pdf(request):
    """
    تصدير السجل الشامل المفلتر بملف PDF رسمي.
    """
    import os
    records = _build_history_queryset(request)[:200] # حد أقصى 200 سجل لسرعة توليد PDF

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="master_attendance_report.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm
    )
    elements = []

    from apps.core.pdf_utils import register_arabic_fonts, reshape_arabic
    font_name = register_arabic_fonts()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Title"].fontName = font_name

    title_style = ParagraphStyle(
        "ArabicTitle", parent=styles["Title"],
        alignment=1, fontSize=16, spaceAfter=15
    )
    elements.append(Paragraph(reshape_arabic("تقرير سجل الحضور والغياب الشامل للنظام"), title_style))
    elements.append(Spacer(1, 0.4 * cm))

    grid = [[
        reshape_arabic("ملاحظات"),
        reshape_arabic("الحالة"),
        reshape_arabic("المادة"),
        reshape_arabic("القسم"),
        reshape_arabic("اسم الطالب"),
        reshape_arabic("الرقم الجامعي"),
        reshape_arabic("التاريخ"),
    ]]

    for rec in records:
        grid.append([
            reshape_arabic(rec.notes or "-"),
            reshape_arabic(rec.status),
            reshape_arabic(rec.session.get_subject_name),
            reshape_arabic(rec.student.department.name if rec.student.department else "-"),
            reshape_arabic(rec.student.name),
            reshape_arabic(rec.student.university_id),
            reshape_arabic(rec.session.date.strftime("%Y-%m-%d")),
        ])

    table = Table(grid, colWidths=[3*cm, 2*cm, 3.5*cm, 3*cm, 4*cm, 2*cm, 2.5*cm])
    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.1, 0.2, 0.4)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]

    for idx in range(1, len(grid)):
        if idx % 2 == 0:
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.Color(0.95, 0.96, 0.98)))

    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    return response

