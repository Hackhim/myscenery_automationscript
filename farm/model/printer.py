import sys
import enum
from pyrtable.fields import (
    IntegerField,
    StringField,
    SingleSelectionField,
    BooleanField,
    MultipleRecordLinkField,
    SingleRecordLinkField,
)

from . import Base
from .octoprint import Octoprint
from .print import PrintRecord

OCTOPRINT_TIMEOUT = 10


class Status(enum.Enum):
    OPERATIONAL = "Operational"
    PRINTING = "Printing"
    DISCONNECTED = "Disconnected"
    PAUSED = "Paused"
    HARVEST = "To harvest"
    MAINTENANCE = "Maintenance"
    RESTART = "To restart"
    SERIAL_PORT_ERROR = "Serial port error"


class GcodeFlavor(enum.Enum):
    MARLIN = "Marlin"


status_from_octoprint = {
    "Operational": Status.OPERATIONAL,
    "Cancelling": Status.OPERATIONAL,
    "Printing": Status.PRINTING,
    "Starting": Status.PRINTING,
    "Finishing": Status.PRINTING,
    "Disconnected": Status.DISCONNECTED,
    "Closed": Status.DISCONNECTED,
    "Pausing": Status.PAUSED,
}


class PrinterProfileRecord(Base):
    class Meta:
        table_id = "TPROD_PrinterProfiles"

    name = StringField("Name", read_only=True)
    slug = StringField("Slug", read_only=True)
    brand = SingleSelectionField("Brand", read_only=True)
    manufacturer = SingleSelectionField("Manufacturer", read_only=True)
    auto_eject = BooleanField("Auto Eject", read_only=True)
    auto_eject_temperature = IntegerField("Auto Eject Temperature", read_only=True)
    eject_gcode = StringField("Eject Gcode", read_only=True)
    # price = IntegerField('Price', read_only=True)
    size_x = IntegerField("Size x", read_only=True)
    size_y = IntegerField("Size y", read_only=True)
    size_z = IntegerField("Size z", read_only=True)
    flavor = SingleSelectionField("Gcode Flavor", choices=GcodeFlavor, read_only=True)

    def __repr__(self):
        return f"<PrinterProfileRecord: name=({self.name}), brand=({self.brand})>"


class PrinterGroupRecord(Base):
    class Meta:
        table_id = "TPROD_PrinterGroups"

    name = StringField("Name", read_only=True)

    def __repr__(self):
        return f"<PrinterGroupRecord: name=({self.name})>"


class PrinterRecord(Base):
    class Meta:
        table_id = "TPROD_Printers"

    name = StringField("Name", read_only=True)
    status = SingleSelectionField("Status", choices=Status)
    url = StringField("Printer URL", read_only=True)
    automated = BooleanField("Automated", read_only=True)
    clean_plate = BooleanField("Clean Plate")
    camera_url = StringField("Camera URL", read_only=True)
    octoprint_api_key = StringField("Octoprint API Key", read_only=True)

    prints = MultipleRecordLinkField(
        "Prints", linked_class="farm.model.print.PrintRecord"
    )
    filament = SingleRecordLinkField(
        "Filament", linked_class="farm.model.filament.FilamentRecord"
    )
    profile = SingleRecordLinkField(
        "PrinterProfile", linked_class="farm.model.printer.PrinterProfileRecord"
    )
    group = SingleRecordLinkField(
        "PrinterGroup", linked_class="farm.model.printer.PrinterGroupRecord"
    )

    @classmethod
    def get_ready(cls):
        ready_printers = cls.objects.filter(
            automated=True,
            status=Status.OPERATIONAL,
            clean_plate=True,
            filament__empty=False,
            profile__empty=False,
            group__empty=True,
        )
        return ready_printers

    @classmethod
    def get_ready_in_group(cls):
        ready_printers = cls.objects.filter(
            automated=True,
            status=Status.OPERATIONAL,
            clean_plate=True,
            profile__empty=False,
            group__empty=False,
        )
        return ready_printers

    @classmethod
    def get_next(cls):
        ready_printers = cls.get_ready()
        for p in ready_printers:
            return p
        return None

    def get_last_print(self):
        n_prints = len(self.prints)
        if n_prints > 0:
            return list(self.prints)[n_prints - 1]
        else:
            return None

    def get_active_print(self):
        active_prints = PrintRecord.get_active()
        for active in active_prints:
            if self.id == active.printer.id:
                return active
        return None


class Printer:
    UPLOAD_DIR = "3DFP"

    def __init__(self, record):
        self.record = record
        self.octoprint_timeout = OCTOPRINT_TIMEOUT
        self.octoprint: Octoprint = None

        self.create_octoprint_connection()
        self.init_upload_directory()

    def __repr__(self):
        return f"<{self.record.name}: {self.record.status} ({self.record.group})>"

    def __upload_dir_exists(self):
        files = self.octoprint.files()
        for f in files["files"]:
            if f["name"] == Printer.UPLOAD_DIR and f["type"] == "folder":
                return True
        return False

    def __create_upload_dir(self):
        self.octoprint.new_folder(Printer.UPLOAD_DIR)

    def init_upload_directory(self):
        if self.is_connected() and not self.__upload_dir_exists():
            self.__create_upload_dir()

    def clear_upload_directory(self):
        try:
            files = self.octoprint.files(location=Printer.UPLOAD_DIR, recursive=True)
        except Exception as e:
            raise (Exception(f"{self} - {e}"))

        for f in files["children"]:
            try:
                self.octoprint.delete(f["path"])
            except Exception as e:
                print(f"Error while clearing upload directory of {self}")
                print(e)

    def create_octoprint_connection(self):
        try:
            self.octoprint = Octoprint(
                url=self.record.url,
                api_key=self.record.octoprint_api_key,
                timeout=self.octoprint_timeout,
            )
        except Exception as e:
            self.octoprint = None
            self.record.status = Status.DISCONNECTED
            print(f"{self} - {e}", file=sys.stderr)
            # self.record.save()
            return False

        self.refresh_status()
        return True

    def refresh_status(self):
        if self.is_disconnected():
            self.create_octoprint_connection()
        else:
            raw_octo_status = self.octoprint.state()
            if not (raw_octo_status in status_from_octoprint.keys()):
                if "Failed to autodetect serial port" in raw_octo_status:
                    octo_status = Status.SERIAL_PORT_ERROR
                else:
                    raise Exception(
                        f'Octoprint status not found: "{raw_octo_status}", {self.__repr__()}'
                    )
            else:
                octo_status = status_from_octoprint[raw_octo_status]

            if self.is_printing() and octo_status == Status.OPERATIONAL:
                self.set_status(Status.HARVEST)
                active_print = self.record.get_active_print()
                if active_print:
                    active_print.finished()
                    if self.record.filament:
                        printfile = active_print.file_to_print.print_model.get_gcode_for_printer_profile(
                            self.record.profile
                        )
                        self.record.filament.used(
                            printfile.get_weight_used(self.record.filament.profile)
                        )
            elif (
                self.is_harvest() or self.is_operational()
            ) and octo_status == Status.PRINTING:
                self.record.clean_plate = False
                self.set_status(Status.PRINTING)
            elif self.is_maintenance() or self.is_restart():
                pass  # Do not update status
            elif self.is_harvest() and octo_status != Status.PRINTING:
                pass  # Do not update status
            elif (
                (self.is_disconnected() or self.is_operational())
                and octo_status == Status.OPERATIONAL
                and not self.record.clean_plate
            ):
                self.set_status(Status.HARVEST)
            elif (
                self.is_printing()
                and octo_status == Status.PRINTING
                and self.record.clean_plate
            ):
                self.record.clean_plate = False
                self.record.save()
            else:
                self.set_status(octo_status)

    def is_auto_eject(self):
        return self.record.profile.auto_eject

    def is_disconnected(self):
        return (
            self.record.status == Status.DISCONNECTED
            or self.record.status == Status.SERIAL_PORT_ERROR
        )

    def is_connected(self):
        return self.record.status != Status.DISCONNECTED

    def is_maintenance(self):
        return self.record.status == Status.MAINTENANCE

    def is_operational(self):
        return self.record.status == Status.OPERATIONAL

    def is_harvest(self):
        return self.record.status == Status.HARVEST

    def is_restart(self):
        return self.record.status == Status.RESTART

    def is_printing(self):
        return self.record.status == Status.PRINTING

    def is_currently_printing(self):
        print("IS CURRENTLY PRINTING")
        raw_octo_status = self.octoprint.state()
        print(raw_octo_status)
        printer_status = status_from_octoprint.get(raw_octo_status)
        print(printer_status)
        if printer_status is None:
            raise ValueError(f"Unkown printer status: {raw_octo_status}")
        return printer_status == Status.PRINTING

    def set_status(self, status):
        self.record.status = status
        self.record.save()

    def can_print(self, filetoprint):
        can_print = False

        printfile = filetoprint.print_model.get_gcode_for_printer_profile(
            self.record.profile
        )
        if not printfile:
            return False

        if self.record.group and filetoprint.printer_group:
            can_print = self.does_filetoprint_group_match(
                filetoprint
            ) and self.fit_in_bed(printfile)
        elif not self.record.group and not filetoprint.printer_group:
            have_enough_filament = self.have_enough_filament_for(printfile)
            colors_match = self.does_filetoprint_color_match(filetoprint)
            fit_in_bed = self.fit_in_bed(printfile)
            can_print = have_enough_filament and colors_match and fit_in_bed

        return can_print

    def fit_in_bed(self, printfile):
        return (
            printfile.size_x <= self.record.profile.size_x
            and printfile.size_y <= self.record.profile.size_y
            and printfile.size_z <= self.record.profile.size_z
        )

    def does_filetoprint_color_match(self, filetoprint):
        return self.record.filament.profile.color == filetoprint.color

    def have_enough_filament_for(self, printfile):
        return self.record.filament.weight_remaining >= printfile.get_weight_used(
            self.record.filament.profile
        )

    def does_filetoprint_group_match(self, filetoprint):
        return self.record.group.name == filetoprint.printer_group.name

    def upload(
        self,
        local_path,
        location="local",
        select=False,
        to_print=False,
        userdata=None,
        path=None,
    ):
        remote_path = Printer.UPLOAD_DIR
        self.octoprint.upload(
            local_path,
            select=select,
            print=to_print,
            userdata=userdata,
            path=remote_path,
        )
        return True

    def print(self, remote_filename):
        try:
            self.octoprint.select(
                location=f"{Printer.UPLOAD_DIR}/{remote_filename}", print=True
            )
            self.refresh_status()
            return True
        except Exception as e:
            raise (
                Exception(f"Error while launching {remote_filename} on {self}:\n{e}")
            )
            return False

    def cancel(self):
        try:
            self.octoprint.cancel()
            last_print = self.record.get_last_print()
            self.refresh_status()
        except Exception as e:
            print(e)

    def get_bed_temperature(self) -> float:
        return self.octoprint.get_bed_temperature()

    def get_auto_eject_temperature(self) -> int:
        return self.record.profile.auto_eject_temperature

    def get_eject_gcode_filenames(self) -> str:
        return self.record.profile.eject_gcode
