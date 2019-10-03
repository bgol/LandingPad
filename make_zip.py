# -*- coding: utf-8 -*-

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

VERSION = "0.0"

def set_VERSION(file_name):
    with open(file_name, "rt") as f:
        for line in f:
            if line.startswith("VERSION "):
                exec(line, globals())
                break

def main():
    file_list = [
        "load.py",
        "README.md",
    ]
    set_VERSION(file_list[0])
    base_name = "LandingPad"
    zip_name = "{}_v{}.zip".format(base_name, VERSION)
    print("make:", zip_name)
    with ZipFile(zip_name, 'w', compression=ZIP_DEFLATED) as zip_arch:
        for file_name in file_list:
            arch_name = "{}/{}".format(base_name, file_name)
            print(" add:", arch_name)
            zip_arch.write(file_name, arch_name)

if __name__ == "__main__":
    main()
