import enum
from pyrtable.fields import (
    StringField,
    SingleSelectionField,
    MultipleRecordLinkField,
    SingleRecordLinkField,
)

from . import Base
from .filament import Color


class Priority(enum.Enum):
    A_NORMAL = "Normal"
    B_MEDIUM = "Medium"
    C_HIGH = "High"
    D_VERYHIGH = "+High"
    D_VERYVERYHIGH = "++High"


class FileToPrintRecord(Base):
    class Meta:
        table_id = "TPROD_FilesToPrint"

    name = StringField("Name", read_only=True)
    label_name = StringField("Label name", read_only=True)
    priority = SingleSelectionField("Priority", choices=Priority, read_only=True)
    color = SingleSelectionField("Color", choices=Color, read_only=True)

    # printfile = SingleRecordLinkField('PrintFile', linked_class='farm.model.printfile.PrintFileRecord')
    print_model = SingleRecordLinkField(
        "PrintModel", linked_class="farm.model.print_model.PrintModelRecord"
    )
    prints = MultipleRecordLinkField(
        "Prints", linked_class="farm.model.print.PrintRecord"
    )
    printer_group = SingleRecordLinkField(
        "PrinterGroup", linked_class="farm.model.printer.PrinterGroupRecord"
    )

    def __repr__(self):
        return f"<FileToPrintRecord: name=({self.name}), priority=({self.priority})>"

    @classmethod
    def get_next_files(cls):
        return cls.objects.filter(prints__empty=True, priority__empty=False)

    @classmethod
    def get_high_priority(cls):
        return cls.get_next_files().filter(priority=Priority.C_HIGH)

    @classmethod
    def get_medium_priority(cls):
        return cls.get_next_files().filter(priority=Priority.B_MEDIUM)

    @classmethod
    def get_normal_priority(cls):
        return cls.get_next_files().filter(priority=Priority.A_NORMAL)
