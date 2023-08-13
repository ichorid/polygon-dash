import argparse
import random
from multiprocessing import Process

import pynng

from collector.common import serialize_events, REQUEST_POP_TRANSACTIONS


def fake_event_generator(max_events, repeat_probability=0.9):
    rng = random.Random()
    max_events = max_events
    hashes_pool = set(rng.randbytes(32) for _ in range(max_events))

    while True:
        start_pool_size = len(hashes_pool)
        hashes_for_batch = set(random.sample(hashes_pool, k=rng.randint(0, max_events)))
        yield list((_hash, rng.randint(0, 1630000000)) for _hash in hashes_for_batch)
        hashes_to_remove = random.sample(hashes_pool, k=int(max_events*(1.0-repeat_probability)))
        hashes_pool.difference_update(hashes_to_remove)
        hashes_pool.update(rng.randbytes(32) for _ in range(len(hashes_to_remove)))
        assert len(hashes_pool) == start_pool_size


def start_listener(port, max_events):
    url = f'tcp://127.0.0.1:{port}'
    event_generator = fake_event_generator(max_events)

    with pynng.Rep0() as sock:
        sock.listen(url)
        while True:
            msg = sock.recv_msg()
            content = msg.bytes.decode()
            if content == REQUEST_POP_TRANSACTIONS:
                print("BOT RECEIVED TRANSACTIONS REQUEST")
                src = b"abcdef"
                batch_to_send = next(event_generator)
                serialized = serialize_events(src, batch_to_send)
                sock.send(serialized)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='BorDataFaker',
        description="""
        This utility starts a number of PyNNG listener processes, 
        listens for incoming connections from the Collector process, 
        and sends back fake events data. It should be used for 
        performance testing of Guardian Labs MEV-Dashboard Data Collector Daemon""")

    parser.add_argument('-n', '--num-listeners', type=int, default=1,
                        help='total number of listener processes')
    parser.add_argument('-p', '--starting-port', type=int, default=50000,
                        help='starting port number for listener processes')
    parser.add_argument('-m', '--max-events', type=int, default=10,
                        help='maximum number of events to send back on single request')
    args = parser.parse_args()

    print(f"""Starting {args.num_listeners} listeners at ports 
              {args.starting_port}-{args.starting_port + args.num_listeners - 1}""")
    for i in range(args.num_listeners):
        try:
            p = Process(target=start_listener(args.starting_port + i, args.max_events))
            p.start()
        except pynng.exceptions.AddressInUse:
            pass
