from pathlib import Path
from typing import Set, Dict, Union

def hms_format(seconds: int) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:>02.0f}:{:>02.0f}:{:>05.2f}".format(hours, minutes, seconds)

def list_files(dir: Union[str, Path]) -> str:
    from subprocess import check_output
    print(check_output(["ls", dir]).decode("utf8"))
    return check_output(["ls", dir]).decode("utf8")
