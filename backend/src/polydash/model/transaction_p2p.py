from pony import orm
from pony.orm import db_session

db_p2p = orm.Database()

sql_insert_or_select = """
WITH input_rows(hash) AS (
   VALUES {values_sql} 
   )
, ins AS (
   INSERT INTO transaction (hash) 
   SELECT * FROM input_rows
   ON CONFLICT (hash) DO NOTHING
   RETURNING id 
   )
   SELECT 'i' AS source
     , id 
FROM   ins
UNION  ALL
SELECT 's' AS source
     , c.id
FROM   input_rows
JOIN transaction c USING (hash)
"""


class Validator(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    pubkey = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')


class Transaction(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    hash = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')

    @classmethod
    @db_session
    def insert_or_select_hashes(cls, hashes: list[bytes]):
        # This procedure tries to insert the hashes into the table,
        # if it fails, it tries to select the hashes from the table.
        # The functions return a list of tuples (source, id)

        cursor = db_p2p.get_connection().cursor()
        values_sql = ', '.join(cursor.mogrify("(%s::bytea)", (value,)).decode('utf-8') for value in hashes)
        sql = sql_insert_or_select.format(values_sql=values_sql)
        cursor = db_p2p.execute(sql)
        return cursor.fetchall()


class TransactionSeenEvent(db_p2p.Entity):
    id = orm.PrimaryKey(int, size=64, auto=True)
    transaction = orm.Required(Transaction)
    validator = orm.Required(Validator)
    timestamp = orm.Required(int)
