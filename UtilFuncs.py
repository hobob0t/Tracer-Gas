from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import String, Float, DATETIME, BOOLEAN
from sqlalchemy import delete
import pandas as pd
from sqlalchemy import Column, Integer, and_


def check_or_create_db():
    # doesn't matter if the DB doesn't exist yet. sqlalchemy will create it
    engine, metadata = connect_and_reflect()

    if "Data" in metadata.tables.keys():
        print("Found table. Good to go")
    else:

        table = Table('Data', metadata,
                      Column('id', Integer, primary_key=True),
                      Column('Timestamp', DATETIME),
                      Column('Name', String),
                      Column('counts since last Zero', Integer),
                      Column('current counts', Integer),
                      Column('CO2 PPM', Integer),
                      Column('average IGRA Temp [C]', Float),
                      Column('RH', Float),
                      Column('RH Sensor Temp [C]', Float),
                      Column('pressure [mbar]', Integer),
                      Column('IGRA detector temp [C]', Float),
                      Column('IGRA source temp [C]', Float),
                      Column('error code', Integer),
                      Column('Warming Up', BOOLEAN),
                      Column('Zeroing', BOOLEAN),
                      Column('Source', String),
                      Column('Abs Pressure', Float),
                      Column('Temperature', Float),
                      Column('Volume Flow', Float),
                      Column('Mass Flow', Float),
                      Column('Setpoint', Float),
                      Column('Gas', String)
                      )
        metadata.create_all()
    engine.dispose()


def write_row(data: (list, dict)) -> bool:
    engine, metadata = connect_and_reflect()
    # create connection
    conn = engine.connect()
    # get table
    table = metadata.tables['Data']
    # insert
    stmt = table.insert().values(data)
    conn.execute(stmt)
    conn.close()
    engine.dispose()


def connect_and_reflect():
    db_uri = f'sqlite:///db.sqlite'
    engine = create_engine(db_uri)
    # Create a MetaData instance
    metadata = MetaData()
    # reflect db schema to MetaData
    metadata.reflect(bind=engine)
    return engine, metadata


def clear_db():
    '''
    Don't run this unless you want to delete all data
    this cannot be undone
    '''
    engine, metadata = connect_and_reflect()
    # create connection
    conn = engine.connect()
    # get table
    table = metadata.tables['Data']
    # delete
    conn.execute(delete(table))
    conn.close()
    engine.dispose()


def load_data(start_date=None, end_date=None):

    engine, metadata = connect_and_reflect()
    table = metadata.tables['Data']
    _from = Column("Name", String)
    _timestamp = Column("Timestamp", DATETIME)

    if start_date is not None and end_date is not None:
        stmt = table.select().where(and_(_timestamp >= start_date, _timestamp <= end_date))
        conn = engine.connect()
        # result = conn.execute(stmt)
        # use pandas built-in instead of doing query manually

        df = pd.read_sql(stmt, conn)
        conn.close()
        engine.dispose()

        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df.set_index("Timestamp", inplace=True)
        df = df.loc[df.index >= "2020-1-1"]

        # df = df.loc[df['Warming Up'] == False]
        # df = df.loc[df['Zeroing'] == False]

        return df


# Function to read
# last N lines of the file
def LastNlines(fname, N):
    # assert statement check
    # a condition
    assert N >= 0

    # declaring variable
    # to implement
    # exponential search
    pos = N + 1

    # list to store
    # last N lines
    lines = []

    # opening file using with() method
    # so that file get closed
    # after completing work
    with open(fname,'r') as f:

        # loop which runs
        # until size of list
        # becomes equal to N
        while len(lines) <= N:

            # try block
            try:
                # moving cursor from
                # left side to
                # pos line from end
                f.seek(-pos, 2)

            # exception block
            # to handle any run
            # time error
            except IOError:
                f.seek(0)
                break

            # finally block
            # to add lines
            # to list after
            # each iteration
            finally:
                lines = list(f)

            # increasing value
            # of variable
            # exponentially
            pos *= 2

    # returning the
    # whole list
    # which stores last
    # N lines
    return lines[-N:]