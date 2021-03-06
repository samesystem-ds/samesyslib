import io
import sys
from pathlib import Path
from typing import Set, Dict, Union

from ruamel import yaml

ConfigType = Dict[str, Dict[str, Union[str, int]]]

def load_config(config_path: Union[str, Path]) -> ConfigType:
    '''Safely load yaml type configurations
    
    Examples
    --------
    config_path = Path("/opt/settings/config.yml")
    conf = load_config(config_path)
    '''
    with io.open(file=config_path, mode="rt") as config_file:
        return yaml.safe_load(config_file)


def hms_format(seconds: int) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:>02.0f}:{:>02.0f}:{:>05.2f}".format(hours, minutes, seconds)


def list_files(dir: Union[str, Path]) -> str:
    from subprocess import check_output
    print(check_output(["ls", dir]).decode("utf8"))
    return check_output(["ls", dir]).decode("utf8")
