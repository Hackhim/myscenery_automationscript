from pyrtable.fields import StringField, AttachmentField, SingleRecordLinkField, IntegerField, FloatField
import math

from . import Base

class PrintFileRecord(Base):
    class Meta:
        table_id = 'TPROD_PrintFiles'
    
    name = StringField('Name', read_only=True)
    gcode = AttachmentField('File', read_only=True)
    time = IntegerField('Time', read_only=True)
    filament_used = FloatField('Filament used', read_only=True)
    size_x = IntegerField('Size x', read_only=True)
    size_y = IntegerField('Size y', read_only=True)
    size_z = IntegerField('Size z', read_only=True)
    
    printer_profile = SingleRecordLinkField('Printer Profile', linked_class='farm.model.printer.PrinterProfileRecord')

    def __repr__(self):
        return f'<PrintFileRecord: name=({self.name}), profile={self.printer_profile}>'

    def get_weight_used(self, filament_profile):
        r = filament_profile.diameter / 2
        h = self.filament_used * 1000
        v = (math.pi * r**2 * h) / 1000
        p = round(v * filament_profile.density, 2)

        return p