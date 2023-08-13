from pony import orm
from pony.orm import db_session

db_p2p = orm.Database()

# See https://stackoverflow.com/a/42217872/5553928 for explanation
sql_insert_or_select = """
WITH input_rows({column_name}) AS (
   VALUES {values_sql} 
   )
, ins AS (
   INSERT INTO {table_name} ({column_name}) 
   SELECT * FROM input_rows
   ON CONFLICT ({column_name}) DO NOTHING
   RETURNING id, {column_name}
   )
   SELECT 'i' AS source
     , id , {column_name} 
FROM   ins
UNION  ALL
SELECT 's' AS source
     , c.id , {column_name}
FROM   input_rows
JOIN {table_name} c USING ({column_name})
"""


@db_session
def insert_or_select_hashes(table_name:str, column_name:str, hashes: list[bytes]):
    # This procedure tries to insert the hashes into the table,
    # if it fails, it tries to select the hashes from the table.
    # The functions return a list of tuples (source, id)
    # In return tuples, source is either 'i' or's', for 'insert' or 'select' respectively.
    # Note that this procedure has pretty high overhead with CTE creation,
    # so it should be ideally used with bigger batches.

    if not hashes:
        return []
    cursor = db_p2p.get_connection().cursor()
    values_sql = ', '.join(cursor.mogrify("(%s::bytea)", (value,)).decode('utf-8') for value in hashes)
    sql = sql_insert_or_select.format(
        values_sql=values_sql,
        table_name=table_name,
        column_name=column_name
    )
    cursor = db_p2p.execute(sql)
    return cursor.fetchall()


class Validator(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    pubkey = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')

    @classmethod
    @db_session
    def insert_or_select_hashes(cls, hashes: list[bytes]):
        return insert_or_select_hashes('validator', 'pubkey', hashes)


class Transaction(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    hash = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')

    @classmethod
    @db_session
    def insert_or_select_hashes(cls, hashes: list[bytes]):
        return insert_or_select_hashes('transaction', 'hash', hashes)


class TransactionSeenEvent(db_p2p.Entity):
    id = orm.PrimaryKey(int, size=64, auto=True)
    transaction = orm.Required(Transaction)
    validator = orm.Required(Validator)
    timestamp = orm.Required(int)
