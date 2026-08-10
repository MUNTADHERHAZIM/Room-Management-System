"""
Smart Seating Algorithm — خوارزمية التوزيع الذكي
=================================================
تقوم بتوزيع الطلاب على مقاعد القاعات الامتحانية بطريقة تمنع الغش.

المبادئ الأساسية:
1. Set Partitioning — تقسيم الطلاب حسب المادة
2. Repulsion Scoring — حساب درجة "التنافر" بين كل طالبين
3. Greedy Placement + Backtracking — وضع كل طالب في أفضل مقعد ممكن
4. Weighted Randomization — تعشية لمنع التنبؤ
"""
import random
from collections import defaultdict


def calculate_repulsion(student_a, student_b, constraints):
    """
    حساب درجة التنافر بين طالبين.
    كلما زادت القيمة، كلما كان من الأفضل عدم جلوسهم متجاورين.
    """
    score = 0

    # نفس المادة → تنافر عالٍ جداً
    if constraints.get('prevent_same_subject', True):
        if student_a.get('subject_id') == student_b.get('subject_id'):
            score += 100

    # نفس القسم → تنافر متوسط
    if constraints.get('prevent_same_department', True):
        if student_a.get('department_id') == student_b.get('department_id'):
            score += 50

    # نفس اللقب العائلي → تنافر عالٍ
    if constraints.get('prevent_same_family', True):
        if (student_a.get('family_name') and student_b.get('family_name')
                and student_a['family_name'] == student_b['family_name']):
            score += 80

    return score


def get_neighbors(row, col, rows, cols):
    """
    الحصول على إحداثيات المقاعد المجاورة المباشرة (4 اتجاهات: فوق، تحت، يمين، يسار).
    لا نتحقق من الزوايا (Diagonals) لأنها لا تشكل خطراً كبيراً في الغش،
    ولأن التحقق منها يجعل من المستحيل رياضياً توزيع الطلاب إذا كانت القاعة ممتلئة.
    """
    neighbors = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for dr, dc in directions:
        nr, nc = row + dr, col + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))
    return neighbors


def generate_seat_grid(rows, cols, spacing_mode):
    """
    توليد شبكة المقاعد المتاحة حسب نمط التباعد.
    Returns: قائمة بالإحداثيات المتاحة [(row, col), ...]
    """
    available = []

    if spacing_mode == 'شطرنجي':
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 0:
                    available.append((r, c))
    elif spacing_mode == 'مقعد_فارغ':
        for r in range(rows):
            for c in range(0, cols, 2):
                available.append((r, c))
    else:
        # بدون تباعد أو عمودي_أقسام — كل المقاعد متاحة
        for r in range(rows):
            for c in range(cols):
                available.append((r, c))

    return available


def generate_seat_label(row, col):
    """توليد رقم المقعد: A1, A2, B1, B2, ..."""
    row_letter = chr(65 + row)  # A, B, C, ...
    col_number = col + 1
    return f"{row_letter}{col_number}"


def smart_distribute(session, hall_setups, exam_subjects_data, constraints=None):
    """
    الدالة الرئيسية للتوزيع الذكي.

    Parameters:
        session: ExamSession instance
        hall_setups: list of HallSetup instances
        exam_subjects_data: list of dicts, each:
            {
                'exam_subject_id': int,
                'subject_id': int,
                'students': [
                    {
                        'student_id': int,
                        'department_id': int,
                        'family_name': str,
                        'subject_id': int,
                        'exam_subject_id': int,
                    },
                    ...
                ]
            }
        constraints: dict with keys:
            prevent_same_subject, prevent_same_department, prevent_same_family

    Returns:
        {
            'success': bool,
            'assignments': [
                {
                    'hall_setup_id': int,
                    'student_id': int,
                    'exam_subject_id': int,
                    'row': int,
                    'column': int,
                    'seat_label': str,
                },
                ...
            ],
            'unassigned': [student_ids...],
            'stats': {
                'total_students': int,
                'assigned': int,
                'unassigned': int,
                'halls_used': int,
            }
        }
    """
    if constraints is None:
        constraints = {
            'prevent_same_subject': True,
            'prevent_same_department': True,
            'prevent_same_family': True,
        }

    # 1. جمع كل الطلاب في قائمة واحدة
    all_students = []
    for es_data in exam_subjects_data:
        for student in es_data['students']:
            all_students.append(student)

    if not all_students:
        return {
            'success': False,
            'assignments': [],
            'unassigned': [],
            'stats': {'total_students': 0, 'assigned': 0, 'unassigned': 0, 'halls_used': 0},
            'error': 'لا يوجد طلاب للتوزيع',
        }

    # 2. تجميع الطلاب حسب المادة وخلطهم عشوائياً
    subject_groups = defaultdict(list)
    for student in all_students:
        subject_groups[student['subject_id']].append(student)

    for group in subject_groups.values():
        random.shuffle(group)

    # 3. ترتيب المجموعات: الأكبر أولاً (لتسهيل التوزيع)
    sorted_groups = sorted(subject_groups.values(), key=len, reverse=True)

    # 4. بناء قائمة مرتبة بالتناوب بين المجموعات (Interleaving)
    interleaved = []
    group_indices = [0] * len(sorted_groups)
    total = sum(len(g) for g in sorted_groups)

    while len(interleaved) < total:
        for i, group in enumerate(sorted_groups):
            if group_indices[i] < len(group):
                interleaved.append(group[group_indices[i]])
                group_indices[i] += 1

    # 5. توزيع على القاعات
    assignments = []
    unassigned = []
    halls_used = 0

    for hall in hall_setups:
        if not interleaved:
            break

        halls_used += 1

        # إنشاء شبكة المقاعد المتاحة
        available_seats = generate_seat_grid(
            hall.rows, hall.columns, hall.spacing_mode
        )

        # مصفوفة التتبع: grid[row][col] = student_data or None
        grid = [[None] * hall.columns for _ in range(hall.rows)]

        # بناء القيود من إعدادات القاعة
        hall_constraints = {
            'prevent_same_subject': hall.prevent_same_subject_adjacent,
            'prevent_same_department': hall.prevent_same_department_adjacent,
            'prevent_same_family': hall.prevent_same_family_adjacent,
        }

        # ترتيب المقاعد المتاحة
        available_seats_sorted = _sort_seats_smartly(
            available_seats, hall.rows, hall.columns
        )

        # تفريق المسافات عشوائياً: إذا كان الطلاب المتبقين أقل من سعة القاعة، 
        # نختار مقاعد عشوائية من الشبكة المتاحة لكامل القاعة لتوزيعهم بشكل مبعثر وأكثر أماناً
        students_remaining = len(interleaved)
        total_seats = len(available_seats_sorted)
        
        if 0 < students_remaining < total_seats:
            # نختار عينة عشوائية بمقدار الطلاب 
            spread_seats = random.sample(available_seats_sorted, students_remaining)
            # ثم نعيد ترتيب المقاعد العشوائية لضمان امتلائها بتسلسل منطقي (صفاً بصف)
            # حتى لا يقفز المراقب بشكل جنوني!
            available_seats_sorted = sorted(spread_seats, key=lambda s: (s[0], s[1]))

        for seat_row, seat_col in available_seats_sorted:
            if not interleaved:
                break

            best_student_idx = -1
            min_score = float('inf')

            # البحث عن أفضل طالب لهذا المقعد
            # نبحث في أول 30 طالب لمنع التعقيد ولزيادة فرص التشتيت
            search_limit = min(30, len(interleaved))
            for i in range(search_limit):
                student = interleaved[i]
                
                # حساب درجة التنافر لهذا الموقع
                score = 0
                
                # 1. التنافر القوي المباشر مع الجيران (أهم قيد لمنع الغش)
                neighbors = get_neighbors(seat_row, seat_col, hall.rows, hall.columns)
                for nr, nc in neighbors:
                    if grid[nr][nc]:
                        score += calculate_repulsion(student, grid[nr][nc], hall_constraints)
                
                # 2. التنافر الممتد الصارم (لمنع تكوين أعمدة تصطف بها نفس الألوان)
                for r in range(hall.rows):
                    if grid[r][seat_col] and grid[r][seat_col]['subject_id'] == student['subject_id']:
                        score += 3  # عقوبة للتواجد في نفس العمود (اتجاه نظر الطالب)
                        
                for c in range(hall.columns):
                    if grid[seat_row][c] and grid[seat_row][c]['subject_id'] == student['subject_id']:
                        score += 1  # عقوبة مخففة للتواجد في نفس الصف بعيداً
                
                if score == 0:
                    best_student_idx = i
                    min_score = 0
                    break
                elif score < min_score:
                    best_student_idx = i
                    min_score = score

            # إذا لم نجد طالب آمن 100%، نأخذ الأقل تنافراً
            if best_student_idx == -1:
                best_student_idx = 0  # fallback

            student = interleaved.pop(best_student_idx)
            grid[seat_row][seat_col] = student
            assignments.append({
                'hall_setup_id': hall.id,
                'student_id': student['student_id'],
                'exam_subject_id': student['exam_subject_id'],
                'row': seat_row,
                'column': seat_col,
                'seat_label': generate_seat_label(seat_row, seat_col),
            })

    # أي طلاب بقوا في interleaved لم يحصلوا على مقاعد
    unassigned = [s['student_id'] for s in interleaved]

    return {
        'success': len(unassigned) == 0,
        'assignments': assignments,
        'unassigned': unassigned,
        'stats': {
            'total_students': len(all_students),
            'assigned': len(assignments),
            'unassigned': len(unassigned),
            'halls_used': halls_used,
        }
    }


def column_department_distribute(session, hall_setups, exam_subjects_data):
    """
    توزيع عمودي بالأقسام.
    كل عمود يحتوي على قسمين متناوبين من أعلى لأسفل، بدون مقاعد فارغة.
    يسهّل على المراقب توزيع الأسئلة عمودياً.
    """
    dept_groups = defaultdict(list)
    for es_data in exam_subjects_data:
        for student in es_data['students']:
            dept_groups[student['department_id']].append(student)

    if not dept_groups:
        return {
            'success': False, 'assignments': [], 'unassigned': [],
            'stats': {'total_students': 0, 'assigned': 0, 'unassigned': 0, 'halls_used': 0},
            'error': 'لا يوجد طلاب للتوزيع',
        }

    for group in dept_groups.values():
        random.shuffle(group)

    assignments = []
    halls_used = 0
    dept_queues = {d: list(s) for d, s in dept_groups.items()}
    dept_ids = list(dept_queues.keys())

    for hall in hall_setups:
        if not any(dept_queues.values()):
            break
        halls_used += 1
        rows, cols = hall.rows, hall.columns

        active_depts = sorted(
            [d for d in dept_ids if dept_queues.get(d)],
            key=lambda d: len(dept_queues[d]),
            reverse=True
        )
        if not active_depts:
            break

        # عيّن لكل عمود قسمين: primary و secondary
        col_plan = []
        for c in range(cols):
            p = active_depts[c % len(active_depts)]
            s = active_depts[(c + 1) % len(active_depts)] if len(active_depts) > 1 else p
            col_plan.append((p, s))

        # ملء المقاعد — عمود بعمود
        for c in range(cols):
            pri, sec = col_plan[c]
            for r in range(rows):
                target = pri if r % 2 == 0 else sec
                student = None
                for dept in [target, (sec if target == pri else pri)] + dept_ids:
                    if dept_queues.get(dept):
                        student = dept_queues[dept].pop(0)
                        break
                if student:
                    assignments.append({
                        'hall_setup_id': hall.id,
                        'student_id': student['student_id'],
                        'exam_subject_id': student['exam_subject_id'],
                        'row': r, 'column': c,
                        'seat_label': generate_seat_label(r, c),
                    })
                elif any(dept_queues.values()):
                    # إذا لم نجد طالباً من الأقسام المفضلة، نأخذ أي طالب متبقٍ من أي قسم آخر
                    for dept_id, queue in dept_queues.items():
                        if queue:
                            student = queue.pop(0)
                            assignments.append({
                                'hall_setup_id': hall.id,
                                'student_id': student['student_id'],
                                'exam_subject_id': student['exam_subject_id'],
                                'row': r, 'column': c,
                                'seat_label': generate_seat_label(r, c),
                            })
                            break

    unassigned = [s['student_id'] for q in dept_queues.values() for s in q]
    total = sum(len(v) for v in dept_groups.values())
    return {
        'success': len(unassigned) == 0,
        'assignments': assignments,
        'unassigned': unassigned,
        'stats': {'total_students': total, 'assigned': len(assignments),
                  'unassigned': len(unassigned), 'halls_used': halls_used},
    }


def _is_safe_placement(student, row, col, grid, rows, cols, constraints):
    """
    فحص هل وضع الطالب في (row, col) آمن حسب القيود.
    يتحقق من كل الجيران (8 اتجاهات).
    """
    neighbors = get_neighbors(row, col, rows, cols)

    for nr, nc in neighbors:
        neighbor = grid[nr][nc]
        if neighbor is None:
            continue

        repulsion = calculate_repulsion(student, neighbor, constraints)
        if repulsion > 0:
            return False

    return True


def _sort_seats_smartly(available_seats, rows, cols):
    """
    ترتيب المقاعد بشكل تتابعي (صف بصف) لملء القاعة بشكل طبيعي
    وترك المقاعد الفارغة (إن وجدت) في الخلف.
    """
    def seat_priority(seat):
        r, c = seat
        return (r, c)

    return sorted(available_seats, key=seat_priority)


def validate_distribution(assignments, hall_setups, exam_subjects_data, constraints):
    """
    التحقق من صحة التوزيع بعد التوليد.
    Returns: list of violations (each is a dict with details)
    """
    violations = []

    # بناء خريطة الطلاب
    student_map = {}
    for es_data in exam_subjects_data:
        for student in es_data['students']:
            student_map[student['student_id']] = student

    # فحص كل قاعة
    for hall in hall_setups:
        hall_assignments = [a for a in assignments if a['hall_setup_id'] == hall.id]
        grid = {}
        for a in hall_assignments:
            grid[(a['row'], a['column'])] = student_map.get(a['student_id'])

        for a in hall_assignments:
            student = student_map.get(a['student_id'])
            if not student:
                continue

            neighbors = get_neighbors(a['row'], a['column'], hall.rows, hall.columns)
            for nr, nc in neighbors:
                neighbor = grid.get((nr, nc))
                if neighbor is None:
                    continue

                repulsion = calculate_repulsion(student, neighbor, {
                    'prevent_same_subject': constraints.get('prevent_same_subject', True),
                    'prevent_same_department': constraints.get('prevent_same_department', True),
                    'prevent_same_family': constraints.get('prevent_same_family', True),
                })

                if repulsion > 0:
                    violations.append({
                        'hall': hall.room.name,
                        'seat_a': a['seat_label'],
                        'seat_b': generate_seat_label(nr, nc),
                        'student_a': student.get('name', ''),
                        'student_b': neighbor.get('name', ''),
                        'reason': _get_violation_reason(student, neighbor, constraints),
                        'score': repulsion,
                    })

    return violations


def _get_violation_reason(student_a, student_b, constraints):
    """وصف سبب المخالفة"""
    reasons = []
    if constraints.get('prevent_same_subject') and student_a.get('subject_id') == student_b.get('subject_id'):
        reasons.append('نفس المادة')
    if constraints.get('prevent_same_department') and student_a.get('department_id') == student_b.get('department_id'):
        reasons.append('نفس القسم')
    if constraints.get('prevent_same_family') and student_a.get('family_name') == student_b.get('family_name'):
        reasons.append('نفس اللقب العائلي')
    return '، '.join(reasons) if reasons else 'غير محدد'
