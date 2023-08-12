import yaml

from collector.common import serialize_transactions, deserialize_transactions
from collector.settings import CollectorSettings


def test_serialize_transactions():
    trans_list = [(b'abcd', 123), (b'123a', 321)]
    src = b'ffff'
    ser = serialize_transactions(src, trans_list)
    assert src, trans_list == deserialize_transactions(ser)


def test_read_settings():
    with open('collector_settings.yaml', 'r') as file:
        settings = CollectorSettings(**yaml.safe_load(file))
