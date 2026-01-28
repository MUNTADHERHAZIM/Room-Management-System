from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Room
from apps.core.models import Department

class RoomResource(resources.ModelResource):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    
    room_type = fields.Field(attribute='get_room_type_display', column_name='room_type', readonly=True)

    class Meta:
        model = Room
        fields = ('id', 'name', 'code', 'capacity', 'room_type', 'department', 'floor', 'is_active')
        export_order = ('id', 'name', 'code', 'department', 'room_type', 'capacity', 'floor', 'is_active')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
