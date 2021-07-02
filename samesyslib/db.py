import json
from functools import wraps
from time import time
import logging
import tempfile

from sqlalchemy import create_engine, engine
import pandas as pd

logging.basicConfig(level=logging.INFO)


def timing(f):
    '''
    add documentation here

    Examples:
        >>> add examples
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        verbose = False
        if kwargs is not None:
            if 'timing_verbose' in kwargs.keys():
                verbose = kwargs['timing_verbose']
        start = time()
        result = f(*args, **kwargs)
        end = time()
        if verbose:
            print ('Function: {}. Elapsed time: {} s'.format(f.__name__, round(end-start, 1)))
        return result
    return wrapper


class POptimiseDataTypesMixin:
    def mem_usage(self, pandas_obj:pd.DataFrame, **kwargs:dict) -> str:
        if isinstance(pandas_obj,pd.DataFrame):
            usage_b = pandas_obj.memory_usage(deep=True).sum()
        else: # we assume if not a df it's a series
            usage_b = pandas_obj.memory_usage(deep=True)
        usage_mb = usage_b / 1024 ** 2 # convert bytes to megabytes
        return "{:03.2f} MB".format(usage_mb)

    @timing
    def optimize_pandas_datatypes(self, data:pd.DataFrame, **kwargs: dict) -> pd.DataFrame:
        verbose = False
        if kwargs is not None:
            if 'optimize_verbose' in kwargs.keys():
                verbose = kwargs['optimize_verbose']
        if verbose:
            logging.info('OPTIMIZING PANDAS DATAFRAMES DATATYPES')
        memory_before = self.mem_usage(data)
        result = data.select_dtypes(include=['int']).apply(pd.to_numeric, downcast='unsigned')
        data[result.columns] = result

        result = data.select_dtypes(include=['float']).apply(pd.to_numeric, downcast='float')
        data[result.columns] = result

        if verbose:
            logging.info('RAM usage before/after optimization: {} / {}'.format(memory_before, self.mem_usage(data)))
        return data

class DB(POptimiseDataTypesMixin):
    def __init__(self, connection_parms, conn=None, if_pymysql=False):
        if type(conn) is engine.Engine:
            self.engine = conn
        else:
            if type(connection_parms) is dict:
                self.params = connection_parms
            else:
                self.params = json.loads(connection_parms)
            if not self.params:
                raise Exception('DB connection params not provided')
            if if_pymysql:
                pymysql = '+pymysql'
            else:
                pymysql = ''
            self.engine = create_engine(
                f"mysql{pymysql}://{self.params['login']}:"
                f"{self.params['password']}@"
                f"{self.params['host']}"\
                f":{self.params['port']}/"
                f"{self.params['schema']}?charset=utf8mb4&local_infile=1"
                , pool_pre_ping=True
            )
        self._check_local_infile()

    def _check_local_infile(self):
        SQL = "SHOW GLOBAL VARIABLES LIKE 'local_infile';"
        result = self.engine.execute(SQL).fetchone()
        assert result[0] == 'local_infile', 'Check For local_infile value'
        assert result[1] == 'ON', '[CL ERROR] local_infile value IS OFF'

    @timing
    def get(self, query: str=None, **kwargs: dict) -> pd.DataFrame:
        verbose = False
        if kwargs is not None:
            if 'verbose' in kwargs.keys():
                verbose = kwargs['verbose']
        if verbose:
            logging.info(f"Executing query:\n{query}")
        df = self.optimize_pandas_datatypes(pd.read_sql_query(query, self.engine), **kwargs)
        if verbose:
            logging.info(f"Returned table shape: {df.shape}")
        return df

    @timing
    def send_single(
        self, pdf:pd.DataFrame, table:str=None, chunksize:int=10000, 
        if_exists:str='replace', index:bool=False, method:str='multi', **kwargs:dict) -> pd.DataFrame:
        try:
            pdf.to_sql(table, self.engine, chunksize=chunksize, if_exists=if_exists, index=index, method=method)
        except Exception as e:
            logging.error('SQL EXCEPTION: {}'.format(str(e)))
        return table

    @timing
    def execute(self, sql: str, **kwargs: dict):
        verbose = False
        if kwargs is not None:
            if 'verbose' in kwargs.keys():
                verbose = kwargs['verbose']

        if verbose:
            logging.info(f"""Executing query:\n{sql}""")

        result =  self.engine.execute(sql)
        if verbose:
            logging.info(f"Inserted rows:{result.rowcount}")
        
        return result

    @timing
    def run(self, sql, **kwargs):
        with self.engine.begin() as conn:
            conn.execute(sql)


    @timing
    def send_append(self, pdf:pd.DataFrame, table:str = None, schema: str = None, **kwargs) -> str:
        verbose = False
        if kwargs is not None:
            if 'verbose' in kwargs.keys():
                verbose = kwargs['verbose']

        table_name = table
        if schema is None:
            schema = self.params['schema']

        try:
            with self.engine.connect() as conn:
                conn.execute(f"USE {schema}")

                if not conn.execute(f'show tables like "{table_name}"'):
                    create_stmt = pd.io.sql.get_schema(pdf, table_name, con=self.engine)
                    if verbose:
                        logging.info(f"Executing query:\n{create_stmt}")
                    conn.execute(create_stmt)
    
                with tempfile.NamedTemporaryFile() as tf:
                    pdf.to_csv(tf.name, encoding='utf-8', header=True, \
                                doublequote=True, sep=',', index=False, na_rep='NULL')

                    load_stmt = f"""
                    LOAD DATA LOCAL INFILE '{tf.name}' 
                    INTO TABLE {schema}.{table_name} FIELDS TERMINATED BY ',' ENCLOSED BY '\"' 
                    IGNORE 1 LINES;
                    """
                    if verbose:
                        logging.info(f"Executing query:\n{load_stmt}")
                    rows = conn.execute(load_stmt)

                logging.info(f'Successfully loaded csv into table {schema}.{table} {rows.rowcount} rows.')

        except Exception as e:
            logging.error(f'SQL EXCEPTION: {str(e)}')

        return f"{schema}.{table}"


    @timing
    def send(
        self, pdf: pd.DataFrame, table: str=None, schema:str=None, 
        if_exists:str='replace', index:bool=False, **kwargs:dict) -> str:
        if if_exists != 'replace':
            return self.send_append(pdf, table=table, if_exists=if_exists, index=index, **kwargs)
        
        verbose = False
        if kwargs is not None:
            if 'verbose' in kwargs.keys():
                verbose = kwargs['verbose']

        tmp_prefix='_tmp'
        if schema is None:
            schema = self.params['schema']

        try:
            with self.engine.connect() as conn:
                query = f"DROP TABLE IF EXISTS {schema}.{table}, {schema}.{table + tmp_prefix};"
                if verbose:
                    logging.info(f"Executing query:\n{query}")
                conn.execute(query)
                with tempfile.NamedTemporaryFile() as tf:
                    pdf.to_csv(tf.name, encoding='utf-8', header=True, chunksize=300000, \
                                doublequote=True, sep=',', index=False, na_rep='NULL')
                    conn.execute(f"USE {schema};")
                    create_stmt = pd.io.sql.get_schema(pdf, table+tmp_prefix, con=self.engine)
                    if verbose:
                        logging.info(f"Executing query:\n{create_stmt}")
                    conn.execute(create_stmt)

                    load_stmt = f"""
                    LOAD DATA LOCAL INFILE '{tf.name}' 
                    INTO TABLE {schema}.{table+tmp_prefix} 
                    FIELDS TERMINATED BY ',' ENCLOSED BY '\"' IGNORE 1 LINES;
                    """
                    if verbose:
                        logging.info(f"Executing query:\n{load_stmt}")
                    rows = conn.execute(load_stmt)
                    conn.execute(f"RENAME TABLE {schema}.{table + tmp_prefix} TO {schema}.{table};")
            logging.info(f'Succuessfully loaded csv into table {schema}.{table} {rows.rowcount} rows.')

        except Exception as e:
            logging.error(f'SQL EXCEPTION: {str(e)}')

        return f"{schema}.{table}"