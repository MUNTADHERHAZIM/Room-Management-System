from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Subject
from apps.core.models import Department

class SubjectResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    
    stage = fields.Field(attribute='get_stage_display', column_name='stage', readonly=True)

    class Meta:
        model = Subject
        fields = ('id', 'name', 'code', 'department', 'stage', 'hours_per_week', 'is_active')
        export_order = ('id', 'name', 'code', 'department', 'stage', 'hours_per_week', 'is_active')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
