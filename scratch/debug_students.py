from apps.exams.models import ExamSession
from apps.students.models import Student
from apps.subjects.models import Subject

session = ExamSession.objects.get(pk=4)
print(f"--- Session: {session.name} ---")

unique_in_session = set()
for es in session.exam_subjects.all():
    s_count = es.students.count()
    print(f"In Session: {es.subject.name} -> {s_count} students")
    for s in es.students.all():
        unique_in_session.add(s.id)

print(f"Total Unique Students in Session: {len(unique_in_session)}")

# Check if there are students NOT in the session
all_students_count = Student.objects.count()
print(f"Total Students in Database: {all_students_count}")
