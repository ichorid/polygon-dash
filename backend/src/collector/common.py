import xdrlib

REQUEST_POP_TRANSACTIONS = "pop_transactions"
MAGIC_TRANSACTIONS = 100


def serialize_transactions(src: bytes, transactions: list[(bytes, int)]):
    """
    Serialize a list of transactions into a byte string.
    """
    p = xdrlib.Packer()
    p.pack_int(MAGIC_TRANSACTIONS)
    p.pack_bytes(src)
    p.pack_int(len(transactions))
    for (tr_hash, timestamp) in transactions:
        p.pack_bytes(tr_hash)
        p.pack_int(timestamp)
    return p.get_buffer()


def deserialize_transactions(data: bytes):
    """
    Deserialize a list of transactions from a byte string.
    """
    u = xdrlib.Unpacker(data)
    transaction_magic = u.unpack_int()
    assert transaction_magic == MAGIC_TRANSACTIONS
    src = u.unpack_bytes()
    num_transactions = u.unpack_int()
    transactions = []
    for _ in range(num_transactions):
        tx = u.unpack_bytes()
        amount = u.unpack_int()
        transactions.append((tx, amount))
    u.done()  # Just to make sure we don't have any leftovers.
    return src, transactions
