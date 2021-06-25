import threading
import datetime
import os
import uuid
import sys
import urllib

from smb.SMBConnection import SMBConnection
from dotenv import load_dotenv
load_dotenv()

from .model.printer import Printer, PrinterRecord
from .model.file_to_print import FileToPrintRecord
from .model.print import PrintRecord, State


class Farm():

    GCODES_DIR = os.getenv('LOCAL_GCODES_FOLDER_PATH')
    SMB_REMOTE_PATH = os.getenv('REMOTE_GCODES_FOLDER_PATH')

    def __init__(self):
        self.launched_prints = []

        init_functions = [
            self.__create_printers,
            self.__create_printqueue,
            self.__connect_to_smb,
        ]
        threads = []
        for init_func in init_functions:
            t = threading.Thread(target=init_func)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def __add_filetoprint_to_printqueue(self, file_to_print):
        #file_to_print.printfile
        self.printqueue.append(file_to_print)

    def __create_printer(self, printer_record):
        printer_record.profile
        if printer_record.filament:
            printer_record.filament.profile
        printer = Printer(printer_record)
        self.printers.append(printer)
    
    def refresh_printer(self, printer):
        printer.refresh_status()

    def __create_printqueue(self, printqueue_limit=200):
        self.printqueue = []
        files_to_print = list(FileToPrintRecord.get_next_files())
        
        files_to_print = sorted(sorted(files_to_print, key=lambda ftp: ftp.name), key=lambda ftp: ftp.priority.name, reverse=True)
        self.printqueue.extend(files_to_print[:printqueue_limit])
        #threads = []
        #for ftp in files_to_print[:printqueue_limit]:
        #    t = threading.Thread(target=self.__add_filetoprint_to_printqueue, args=(ftp,))
        #    threads.append(t)
        #    t.start()
        #for t in threads:
        #    t.join()
        
        #Order by priority and order name and printfile time
        self.printqueue = sorted(sorted(sorted(self.printqueue, key=lambda ftp: ftp.print_model.print_time, reverse=True), key=lambda ftp: ftp.name), key=lambda ftp: ftp.priority.name, reverse=True)

    def __create_printers(self):
        self.printers = []
        printers_records = PrinterRecord.get_all()
        threads = []
        for printer_record in printers_records:
            t = threading.Thread(target=self.__create_printer, args=(printer_record,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def refresh_printers(self):
        threads = []
        for printer in self.printers:
            t = threading.Thread(target=self.refresh_printer, args=(printer,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()


    def __find_printer_by_record(self, record):
        for printer in self.printers:
            if printer.record.id == record.id:
                return printer
        return None
    
    def get_printer_by_name(self, name):
        for printer in self.printers:
            if printer.record.name == name:
                return printer
        return None
    

    def __connect_to_smb(self):
        share_name = os.getenv('SMB_SHARE')
        userID = os.getenv('SMB_USERID')
        password = os.getenv('SMB_PASSWD')
        host = os.getenv('SMB_HOST')
        port = 445
        client_machine_name=''
        server_name=''
        domain_name=''

        conn = SMBConnection(userID, password, client_machine_name, server_name, domain=domain_name, use_ntlm_v2=True, is_direct_tcp=True)
        conn.connect(host, port)
        shares = conn.listShares()
        share_con = None
        
        for share in shares:
            if share.name == share_name:
                share_con = share

        self.smb_con = conn
        self.share = share_con
    
    def file_exists_on_nas(self, remote_path):
        shared_files = self.smb_con.listPath(self.share.name, os.path.dirname(remote_path))
        filename = os.path.basename(remote_path)
        for shared_file in shared_files:
            if filename == shared_file.filename:
                return True
        return False

    def download_gcode_from_nas(self, remote_path, local_path):
        f = open(local_path, 'wb')
        self.smb_con.retrieveFile(self.share.name, remote_path, f)
        f.close()



#    def get_next_printer(self):
#        next_printer = PrinterRecord.get_next()
#        if next_printer:
#            next_printer = self.__find_printer_by_record(next_printer)
#        return next_printer


    def launch_prints(self):
        threads = []
        matched_printers = self.match_printer_printqueue()

        for (printer, ftp) in matched_printers:
            try:
                self.launch_single_print(ftp, printer)
            except Exception as e:
                print(f'{printer}\n{ftp}', file=sys.stderr)
                print(e, file=sys.stderr)
        #    t = threading.Thread(target=self.launch_single_print, args=(ftp, printer,))
        #    threads.append(t)
        #    t.start()
        #
        #for t in threads:
        #    t.join()


    def match_printer_printqueue(self):
        files_to_print = []
        files_to_print.extend(self.printqueue)
        ready_printers = self.get_ready_printers()

        for printer in ready_printers:
            for ftp in files_to_print:
                if printer.can_print(ftp):
                    files_to_print.remove(ftp)
                    yield (printer, ftp)
                    break
    
    def get_ready_printers(self):
        printers_records = PrinterRecord.get_ready()
        ready_printers = []

        for printer_record in printers_records:
            printer = self.__find_printer_by_record(printer_record)
            if printer:
                ready_printers.append(printer)

        return ready_printers



    def launch_prints_for_printers_in_group(self):
        threads = []
        matched_printers = self.match_printer_printqueue_group()

        for (printer, ftp) in matched_printers:
            try:
                self.launch_single_print(ftp, printer)
            except Exception as e:
                print(f'{printer}\n{ftp}', file=sys.stderr)
                print(e, file=sys.stderr)
            #t = threading.Thread(target=self.launch_single_print, args=(ftp, printer,))
            #threads.append(t)
            #t.start()
        
        #for t in threads:
            #t.join()

    def match_printer_printqueue_group(self):
        files_to_print = []
        files_to_print.extend(self.printqueue)
        ready_printers = self.get_ready_printers_in_group()

        for printer in ready_printers:
            for file_to_print in files_to_print:
                if printer.can_print(file_to_print):
                    files_to_print.remove(file_to_print)
                    yield (printer, file_to_print)
                    break


    def get_ready_printers_in_group(self):
        printers_records = PrinterRecord.get_ready_in_group()
        ready_printers = []

        for printer_record in printers_records:
            printer = self.__find_printer_by_record(printer_record)
            if printer:
                ready_printers.append(printer)

        return ready_printers


    def launch_single_print(self, file_to_print, printer):
        printfile = file_to_print.print_model.get_gcode_for_printer_profile(printer.record.profile)
        filename = printfile.name
        #remote_filename = urllib.parse.quote_plus(filename)
        local_path = f"{Farm.GCODES_DIR}/{uuid.uuid4()}_{filename}"
        remote_path = os.path.join(self.SMB_REMOTE_PATH, printfile.printer_profile.slug, filename)
        
        #if not self.file_exists_on_nas(remote_path):
        #    raise(Exception(f'Path: {remote_path} not found in NAS.'))
        
        self.download_gcode_from_nas(remote_path, local_path)

        printer.clear_upload_directory()
        print_launched = printer.upload( (filename, open(local_path, 'rb')), to_print=True)
        #print_launched = printer.print(remote_filename)

        if(print_launched):
            print_ = PrintRecord(state=State.IN_PROGRESS, datetime_started=datetime.datetime.now(), printer=printer.record, file_to_print=file_to_print)
            print_.save()
            self.launched_prints.append((print_, printfile))
        
        os.remove(local_path)
