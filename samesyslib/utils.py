import sys
import io
from pathlib import Path
from typing import Set, Dict, Union, List

ConfigType = Dict[str, Dict[str, Union[str, int]]]

def load_config(config_path: Union[str, Path]) -> ConfigType:
    '''Safely load yaml type configurations
    
    Args:
        config_path (str, Path): path to your secrets

    Returns:
        dict: a dictionary of a certain structure

    Examples:

        .. code-block:: python

            # /opt/settings/config.yml
            database:
              user: 'root'
            # ----

            from pathlib import Path
            from samesyslib.utils import load_config

            config_path = Path("/opt/settings/config.yml")
            conf = load_config(config_path)

            conf['database']['user']
    '''
    from ruamel import yaml
    with io.open(file=config_path, mode="rt") as config_file:
        return yaml.safe_load(config_file)


def hms_format(seconds: int) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:>02.0f}:{:>02.0f}:{:>05.2f}".format(hours, minutes, seconds)


def list_files(dir: Union[str, Path]) -> List[str]:
    from subprocess import check_output
    print(check_output(["ls", dir]).decode("utf8"))
    return check_output(["ls", dir]).decode("utf8").strip().split('\n')


def sql_from_file(filename: Union[str, Path]) -> List[str]:
    with open(filename, 'r') as reader:
        sql_file = reader.read()       # reads as string
    # all SQL commands (split on ';')
    sql_commands = sql_file.split(';')
    return(sql_commands)

    
def get_col_types(df, columns=None):
    if not columns:
        columns = df.columns
    for col in columns:
        value = df[[col]].values[0][0]
        print(f'{col}: {type(value)}: {value}')


def dataset_summary(df):
    import pandas as pd
    df_s = pd.DataFrame(df.dtypes, columns = ['type'])
    df_s = df_s.merge(df.head(1).T, left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(df.tail(1).T, left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(pd.DataFrame(df.min(), columns = ['min']), left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(pd.DataFrame(df.max(), columns = ['max']), left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(pd.DataFrame(df.mean(numeric_only=None), columns = ['mean']), left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(pd.DataFrame(df.std(), columns = ['std']), left_index=True, right_index=True, how = 'outer')
    df_s = df_s.merge(pd.DataFrame(df.isnull().sum(), columns = ['n_miss']), left_index=True, right_index=True, how = 'outer')
    return df_s