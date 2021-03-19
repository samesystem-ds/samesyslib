import json
from functools import wraps
from time import time
import logging
from sqlalchemy import create_engine
import pandas as pd
from pandas import isnull
import tempfile

logging.basicConfig(level=logging.INFO)


def timing(f):
    '''
    add documentation here

    Examples:
        >>> add examples
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        verbose = True
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
    def mem_usage(self, pandas_obj, **kwargs):
        if isinstance(pandas_obj,pd.DataFrame):
            usage_b = pandas_obj.memory_usage(deep=True).sum()
        else: # we assume if not a df it's a series
            usage_b = pandas_obj.memory_usage(deep=True)
        usage_mb = usage_b / 1024 ** 2 # convert bytes to megabytes
        return "{:03.2f} MB".format(usage_mb)

    @timing
    def optimize_pandas_datatypes(self, data, **kwargs):
        verbose = True
        if kwargs is not None:
            if 'optimize_verbose' in kwargs.keys():
                verbose = kwargs['optimize_verbose']

        logging.info('OPTIMISING PANDAS DATAFRAMES DATATYPES')
        memory_before = self.mem_usage(data)
        result = data.select_dtypes(include=['int']).apply(pd.to_numeric, downcast='unsigned')
        data[result.columns] = result

        result = data.select_dtypes(include=['float']).apply(pd.to_numeric, downcast='float')
        data[result.columns] = result

        # if 'date' in data.columns:
        #     data['date'] = pd.to_datetime(data.date, format='%Y-%m-%d %H:%m:%s', errors='coerce')

        # open_shops exclude for category optimise
        # gl_obj = data.select_dtypes(include=['object']).copy()
        # for col in gl_obj.columns:
        #     num_unique_values = len(gl_obj[col].unique())
        #     num_total_values = len(gl_obj[col])
        #     if num_unique_values / num_total_values < 0.5:
        #         data.loc[:,col] = gl_obj[col].astype('category')
        if verbose:
            logging.info('RAM usage before/after optimisation: {} / {}'.format(memory_before, self.mem_usage(data)))
        return data

class DB(POptimiseDataTypesMixin):
    def __init__(self, connection_parms):
        self.params = json.loads(connection_parms)
        if not self.params:
            raise Exception('DB connection params not provided')

        self.engine = create_engine(
            "mysql://{}:{}@{}:{}/{}?charset=utf8mb4&local_infile=1".format(
                self.params['login'], self.params['password'], self.params['host'], self.params['port'], self.params['schema']
            ), pool_pre_ping=True
        )

    @timing
    def get(self, query=None, **kwargs):
        return self.optimize_pandas_datatypes(pd.read_sql_query(query, self.engine), **kwargs)

    @timing
    def send_single(self, pdf, table=None, chunksize=10000, if_exists='replace', index=False, method='multi', **kwargs):
        try:
            pdf.to_sql(table, self.engine, chunksize=chunksize, if_exists=if_exists, index=index, method=method)
        except Exception as e:
            logging.error('SQL EXCEPTION: {}'.format(str(e)))
        return table

    @timing
    def execute(self, sql, **kwargs):
        return self.engine.execute(sql)

    @timing
    def send_append(self, pdf, table=None, schema=None, **kwargs):
        table_name = table
        if schema is None:
            schema = self.params['schema']

        try:
            tf = tempfile.NamedTemporaryFile()

            connection = self.engine.raw_connection()
            cursor = connection.cursor()

            cursor.execute("USE {}".format(schema))

            if not cursor.execute('show tables like "{}"'.format(table_name)):
                create_stmt = "{}".format(pd.io.sql.get_schema(pdf, table_name, con=self.engine))
                cursor.execute(create_stmt)
            connection.commit()

            pdf.to_csv(tf.name, encoding='utf-8', header=True, \
                        doublequote=True, sep=',', index=False, na_rep='NULL')

            load_stmt = "LOAD DATA LOCAL INFILE '{}' INTO TABLE {}.{} FIELDS TERMINATED BY ',' ENCLOSED BY '\"' IGNORE 1 LINES;".format(tf.name, schema, table_name)
            rows = cursor.execute(load_stmt)
            connection.commit()

            tf.close()
            logging.info('Succuessfully loaded csv into table {}.{} {} rows.'.format(schema, table, rows))

        except Exception as e:
            logging.error('SQL EXCEPTION: {}'.format(str(e)))

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            if tf:
                tf.close()

        return "{}.{}".format(schema, table)

    @timing
    def send(self, pdf, table=None, schema=None, if_exists='replace', index=False, **kwargs):
        if if_exists != 'replace':
            return self.send_append(pdf, table=table, if_exists=if_exists, index=index, **kwargs)

        tmp_prefix='_tmp'
        if schema is None:
            schema = self.params['schema']

        try:
            tf = tempfile.NamedTemporaryFile()

            connection = self.engine.raw_connection()
            cursor = connection.cursor()


            cursor.execute("DROP TABLE IF EXISTS {}.{}, {}.{};".format(schema, table, schema, table + tmp_prefix))
            connection.commit()

            pdf.to_csv(tf.name, encoding='utf-8', header=True, chunksize=300000, \
                        doublequote=True, sep=',', index=False, na_rep='NULL')

            cursor.execute("USE {}".format(schema))
            create_stmt = "{}".format(pd.io.sql.get_schema(pdf, table+tmp_prefix, con=self.engine))
            cursor.execute(create_stmt)

            load_stmt = "LOAD DATA LOCAL INFILE '{}' INTO TABLE {}.{} FIELDS TERMINATED BY ',' ENCLOSED BY '\"' IGNORE 1 LINES;".format(tf.name, schema, table+tmp_prefix)
            rows = cursor.execute(load_stmt)
            cursor.execute("RENAME TABLE {}.{} TO {}.{};".format(schema, table + tmp_prefix,schema, table))

            connection.commit()

            tf.close()
            cursor.close()
            logging.info('Succuessfully loaded csv into table {}.{} {} rows.'.format(schema, table, rows))

        except Exception as e:
            logging.error('SQL EXCEPTION: {}'.format(str(e)))

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            if tf:
                tf.close()

        return "{}.{}".format(schema, table)
