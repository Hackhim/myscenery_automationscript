from pyrtable.fields import StringField, MultipleRecordLinkField, IntegerField

from . import Base

class PrintModelRecord(Base):
    class Meta:
        table_id = 'TPROD_PrintModel'
    
    name = StringField('Name', read_only=True)
    print_time = IntegerField('PrintTime', read_only=True)
    printfiles = MultipleRecordLinkField('Gcodes', linked_class='farm.model.printfile.PrintFileRecord')

    def __repr__(self):
        return f'<PrintModelRecord: name=({self.name})>'
    
    def get_gcode_for_printer_profile(self, printer_profile, default=None):
        for printfile in self.printfiles:
            if printfile.printer_profile.slug == printer_profile.slug:
                return printfile
        return default
