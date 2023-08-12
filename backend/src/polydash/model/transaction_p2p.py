from pony import orm

db_p2p = orm.Database()

class Validator(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    pubkey = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')


class Transaction(db_p2p.Entity):
    id = orm.PrimaryKey(int, auto=True)
    hash = orm.Required(bytes, unique=True)
    events = orm.Set('TransactionSeenEvent')

    def select_or_insert_hash(self, _hash):
        pass


class TransactionSeenEvent(db_p2p.Entity):
    id = orm.PrimaryKey(int, size=64, auto=True)
    transaction = orm.Required(Transaction)
    validator = orm.Required(Validator)
    timestamp = orm.Required(int)

