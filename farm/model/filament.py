import enum
from pyrtable.fields import StringField, SingleSelectionField, BooleanField, AttachmentField, MultipleRecordLinkField, SingleRecordLinkField, IntegerField, FloatField

from . import Base

class Color(enum.Enum):
    DARK_GREY = 'Dark Grey'
    BLUE = 'Blue'
    WHITE = 'White'
    ORANGE = 'Orange'
    GREEN = 'Green'
    YELLOW = 'Yellow'
    RED = 'Red'

class Material(enum.Enum):
    PLA = 'PLA'
    ABS = 'ABS'

class FilamentProfileRecord(Base):
    class Meta:
        table_id = 'TPROD_FilamentProfiles'
    
    name = StringField('Name', read_only=True)
    brand = SingleSelectionField('Brand', read_only=True)
    manufacturer = SingleSelectionField('Manufacturer', read_only=True)
    color = SingleSelectionField('Color', choices=Color, read_only=True)
    #price = IntegerField('Price', read_only=True)
    weight = FloatField('Weight [g]', read_only=True)
    material = SingleSelectionField('Material', choices=Material, read_only=True)
    diameter = FloatField('Diameter [mm]', read_only=True)
    density = FloatField('Density [g/cm3]', read_only=True)


    def __repr__(self):
        return f'<FilamentProfileRecord: name=({self.name})>'


class FilamentRecord(Base):
    class Meta:
        table_id = 'TPROD_Filaments'
    
    name = StringField('Name', read_only=True)
    in_trash = BooleanField('In trash', read_only=True)
    qr_code_printed = BooleanField('QR code Printed', read_only=True)
    remaining = FloatField('Remaining', read_only=True)
    weight_remaining = FloatField('Weight remaining')

    profile = SingleRecordLinkField('FilamentProfile', linked_class='farm.model.filament.FilamentProfileRecord')
    printer = SingleRecordLinkField('Printer', linked_class='farm.model.printer.PrinterRecord')

    def __repr__(self):
        return f'<FilamentRecord: name=({self.name})>'
    
    def used(self, weight):
        self.weight_remaining -= weight
        if self.weight_remaining < 0:
            self.weight_remaining = 0
        self.save()