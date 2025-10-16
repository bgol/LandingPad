# -*- coding: utf-8 -*-

from zipfile import ZipFile, ZIP_DEFLATED

__version_info__ = None
__version__ = None

def set_VERSION(file_name):
    with open(file_name, "rt") as f:
        for line in f:
            if line.startswith("__version_info__"):
                exec(line, globals())
            if line.startswith("__version__"):
                exec(line, globals())
                break

def main():
    file_list = [
        "load.py",
        "README.md",
    ]
    set_VERSION(file_list[0])
    base_name = "LandingPad"
    zip_name = f"{base_name}_v{__version__}.zip"
    print("make:", zip_name)
    with ZipFile(zip_name, 'w', compression=ZIP_DEFLATED) as zip_arch:
        for file_name in file_list:
            arch_name = f"{base_name}/{file_name}"
            print(" add:", arch_name)
            zip_arch.write(file_name, arch_name)

if __name__ == "__main__":
    main()
