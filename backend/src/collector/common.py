import xdrlib

REQUEST_POP_TRANSACTIONS = "pop_events"
MAGIC_TRANSACTIONS = 100


def serialize_events(src: bytes, events: list[(bytes, int)]):
    """
    Serialize a list of events into a byte string.
    """
    p = xdrlib.Packer()
    p.pack_int(MAGIC_TRANSACTIONS)
    p.pack_bytes(src)
    p.pack_int(len(events))
    for (tr_hash, timestamp) in events:
        p.pack_bytes(tr_hash)
        p.pack_int(timestamp)
    return p.get_buffer()


def deserialize_events(data: bytes):
    """
    Deserialize a list of events from a byte string.
    """
    u = xdrlib.Unpacker(data)
    event_magic = u.unpack_int()
    assert event_magic == MAGIC_TRANSACTIONS
    src = u.unpack_bytes()
    num_events = u.unpack_int()
    events = []
    for _ in range(num_events):
        tx = u.unpack_bytes()
        amount = u.unpack_int()
        events.append((tx, amount))
    u.done()  # Just to make sure we don't have any leftovers.
    return src, events
