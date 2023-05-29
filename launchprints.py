import datetime
from farm.farm import Farm


def main():
    farm = Farm()
    farm.launch_prints()
    farm.launch_prints_for_printers_in_group()

    if len(farm.launched_prints) > 0:
        print(f"<{datetime.datetime.now()}> LAUNCHED PRINTS:")
        for launched_print, printfile in farm.launched_prints:
            print(f" [+] {launched_print} -> {printfile}")


if __name__ == "__main__":
    main()
