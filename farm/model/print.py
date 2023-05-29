import datetime
import enum
from pyrtable.fields import (
    StringField,
    SingleSelectionField,
    DateTimeField,
    SingleRecordLinkField,
)

from . import Base


class State(enum.Enum):
    IN_PROGRESS = "In Progress"
    FINISHED = "Finished"
    SUCCEED = "Succeed"
    FAILED = "Failed"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"


class PrintRecord(Base):
    class Meta:
        table_id = "TPROD_Prints"

    name = StringField("Name", read_only=True)
    state = SingleSelectionField("State", choices=State)
    datetime_started = DateTimeField("Datetime started")
    datetime_finished = DateTimeField("Datetime finished")
    printer = SingleRecordLinkField(
        "Printer", linked_class="farm.model.printer.PrinterRecord"
    )
    file_to_print = SingleRecordLinkField(
        "FileToPrint", linked_class="farm.model.file_to_print.FileToPrintRecord"
    )

    @classmethod
    def get_active(cls):
        return cls.objects.filter(state=State.IN_PROGRESS)

    def __repr__(self):
        return f"<PrintRecord: name={self.name}, state={self.state}>"

    def finished(self):
        self.state = State.FINISHED
        self.datetime_finished = datetime.datetime.now()
        self.save()
