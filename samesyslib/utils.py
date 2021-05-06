import sys
import io
from pathlib import Path
from typing import Set, Dict, Union, List
import logging
import os
from subprocess import check_output, STDOUT
import bz2
import pickle

import numpy as np

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



def get_git_info(repo_dir:str) -> dict:
    """
    Extract basic git info from CWD
    example:
        repo_dir = os.path.dirname(os.path.realpath(__file__))
    """
    branch = check_output(f"cd {repo_dir};\
                            git rev-parse --abbrev-ref HEAD",
                            shell=True,stderr=STDOUT).decode("utf8").rstrip()
    commit = check_output(f"cd {repo_dir};\
                            git rev-parse --short HEAD",
                            shell=True,stderr=STDOUT).decode("utf8").rstrip()
    return {'branch':branch, 'commit':commit}

def init_metadata(conn:object, table_name: str=None, schema:str=None, metadata: dict=None) -> None:
    """
    Write dictionary into DB table, initializing only passed keys, rest leaving as default/Null
    """
    table_structure = conn.get(
        f"""
        SELECT * FROM {schema}.{table_name} limit 0;
        """
    )
    for key in metadata.keys():
        table_structure.loc[0, key] = metadata[key]
    conn.send_append(table_structure, table_name, schema=schema)

def update_model_metadata(conn:object, run_id:str, key:str, value:object,
 run_id_col:str = None, table_name:str=None, table_schema:str = None) -> None:
    conn.execute(
        f"""
        UPDATE `{table_schema}`.`{table_name}`
        SET {key} = '{value}'
        WHERE {run_id_col} = '{run_id}'
        """, 
        verbose = True
    )

def split_array_into_batches(shop_list:object, batch_size: int):
    if shop_list.shape[0] > batch_size:
        return np.array_split(shop_list.values, np.ceil(shop_list.shape[0]/batch_size))
    else:
        return np.array_split(shop_list.values, 1)


def save_bzipped(obj: object, filename: object, protocol: int=-1):
    """
    Save python object into pickle and compress it
    """
    with bz2.BZ2File(filename, 'wb') as f:
        pickle.dump(obj, f, protocol)

def load_bzipped(data:object):
    """
    Reverse save_bzipped operation
    """
    return pickle.loads(bz2.decompress(data))

def read_batched_shops_data(conn:object, batch:list, table_schema:str, table_name:str):
    shops = ','.join(batch.astype(str)) 
    return conn.get(
        f"""
        SELECT *
        FROM {table_schema}.{table_name}
        WHERE shop_id in ({shops});
        """
    )
