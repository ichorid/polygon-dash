from pony import orm
from polydash.log import LOGGER
from polydash.definitions import DB_FILE, DB_P2P_FILE
from polydash.model.transaction_p2p import db_p2p

# PonyORM set up
db = orm.Database()


def start_db():
    db.bind(provider='sqlite', filename=DB_FILE, create_db=True)
    db.generate_mapping(create_tables=True)
    LOGGER.info('database is successfully started up')


def start_p2p_db():
    db_p2p.bind(
        provider='postgres',
        password='1234567890',
        user='postgres',
        host='localhost',
        port=5432,
        database='p2p_collector')
    db_p2p.generate_mapping(create_tables=True)
