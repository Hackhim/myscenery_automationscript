import enum
from pyrtable.fields import StringField, MultipleRecordLinkField, SingleRecordLinkField

from . import Base

class PrintModel(Base):
    class Meta:
        table_id = 'TPROD_PrintModel'
    
    name = StringField('Name', read_only=True)
    printfiles = MultipleRecordLinkField('Gcodes', linked_class='farm.model.printfile.PrintFileRecord')

    def __repr__(self):
        return f'<PrintModel: name=({self.name})>'
