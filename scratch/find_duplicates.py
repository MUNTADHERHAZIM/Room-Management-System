from apps.exams.models import Student
from django.db.models import Count

duplicates = Student.objects.values('university_id').annotate(count=Count('id')).filter(count__gt=1)

if duplicates.exists():
    print(f"Found {duplicates.count()} university IDs with duplicates.")
    for d in duplicates:
        print(f"University ID: {d['university_id']} is repeated {d['count']} times")
else:
    print("No duplicates found in the database. All university IDs are unique.")
