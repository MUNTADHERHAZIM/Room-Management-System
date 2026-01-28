from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Instructor
from apps.core.models import Department

class InstructorResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    
    academic_title = fields.Field(attribute='get_academic_title_display', column_name='academic_title', readonly=True)

    class Meta:
        model = Instructor
        fields = ('id', 'name', 'department', 'email', 'phone', 'academic_title', 'is_active')
        export_order = ('id', 'name', 'department', 'academic_title', 'email', 'phone', 'is_active')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
