import argparse
import random
import sys
from datetime import datetime
from multiprocessing import Process

import pynng

from collector.common import serialize_transactions, REQUEST_POP_TRANSACTIONS


def gen_fake_transactions(rng, max_transactions):
    out = []
    for _ in range(rng.randint(0, max_transactions)):
        out.append((rng.randbytes(32), rng.randint(0, 1630000000)))
    return out


def start_listener(port, max_transactions):
    rng = random.Random(port)
    url = f'tcp://127.0.0.1:{port}'

    with pynng.Rep0() as sock:
        sock.listen(url)
        while True:
            msg = sock.recv_msg()
            content = msg.bytes.decode()
            if content == REQUEST_POP_TRANSACTIONS:
                print("BOT RECEIVED TRANSACTIONS REQUEST")
                src = b"abcdef"
                serialized = serialize_transactions(src, gen_fake_transactions(rng, max_transactions))
                sock.send(serialized)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='BorDataFaker',
        description="""
        This utility starts a number of PyNNG listener processes, 
        listens for incoming connections from the Collector process, 
        and sends back fake transactions data. It should be used for 
        performance testing of Guardian Labs MEV-Dashboard Data Collector Daemon""")

    parser.add_argument('-n', '--num-listeners', type=int, default=1,
                        help='total number of listener processes')
    parser.add_argument('-p', '--starting-port', type=int, default=50000,
                        help='starting port number for listener processes')
    parser.add_argument('-m', '--max-transactions', type=int, default=10,
                        help='maximum number of transactions to send back on single request')
    args = parser.parse_args()

    print(f"""Starting {args.num_listeners} listeners at ports 
              {args.starting_port}-{args.starting_port + args.num_listeners - 1}""")
    for i in range(args.num_listeners):
        p = Process(target=start_listener(args.starting_port + i, args.max_transactions))
        p.start()
