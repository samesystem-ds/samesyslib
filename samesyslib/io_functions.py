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