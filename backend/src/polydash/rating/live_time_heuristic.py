import queue
import threading
import math
import traceback

from pony import orm
from pony.orm import select

from polydash.log import LOGGER
from polydash.model.node import Node
from polydash.model.risk import MinerRisk
from polydash.model.transaction_p2p import TransactionP2P
from polydash.model.block import Block

TRANSACTION_WINDOW_SIZE = 700  # ~10 blocks

EventQueue = queue.Queue()


@orm.db_session
def calculate_mean_variance(node_pubkey, tx_live_time):
    node = Node[node_pubkey]

    if node.variance != 0:
        is_outlier = not -3 <= (tx_live_time - node.mean) / math.sqrt(node.variance) <= 3
    else:
        is_outlier = True

    node.last_txs.append(tx_live_time)
    if len(node.last_txs) > TRANSACTION_WINDOW_SIZE:
        # if window size is exceeded, remove the oldest element
        old_element = node.last_txs.pop(0)

        old_mean = node.mean
        node.mean = node.mean - old_element / TRANSACTION_WINDOW_SIZE + tx_live_time / TRANSACTION_WINDOW_SIZE
        node.variance = (node.variance * TRANSACTION_WINDOW_SIZE
                         + (tx_live_time - old_mean) * (tx_live_time - node.mean)
                         - (old_element - old_mean) * (old_element - node.mean)) / TRANSACTION_WINDOW_SIZE
    else:
        old_mean = node.mean
        node.mean = (old_mean * (len(node.last_txs) - 1) + tx_live_time) / len(node.last_txs)
        if len(node.last_txs) > 1:
            node.variance = ((node.variance + old_mean ** 2) * (len(node.last_txs) - 1) + tx_live_time ** 2) / len(
                node.last_txs) - node.mean ** 2

    if is_outlier:
        node.outliers += 1
    node.n_txs += 1


def process_transaction(author_node_pubkey, tx):
    # find the transaction in the list of the ones seen by P2P
    with orm.db_session:
        # Pony kept throwing exception at me with both generator and lambda select syntax, so raw SQL
        if (tx_p2p := TransactionP2P.get_first_by_hash(tx.hash)) is None:
            # we haven't seen it
            return

    # get the live-time of this transaction
    live_time = tx.created - tx_p2p.tx_first_seen
    if live_time <= 0:
        return

    # calculate it
    calculate_mean_variance(author_node_pubkey, live_time)


def main_loop():
    while True:
        try:
            # get the block_number from some other thread
            block_number = EventQueue.get()

            with orm.db_session:
                # get block
                block = Block.get(number=block_number)
                # find the block's author
                author_node = Node.get(pubkey=block.validated_by)
                if author_node is None:
                    # no such node is remembered by us yet, create it
                    author_node = Node(pubkey=block.validated_by, outliers=0, mean=0, variance=0, n_txs=0, last_txs=[])

                # update our internal mean-variance state and find outliers
                for tx in block.transactions:
                    process_transaction(author_node.pubkey, tx)
            with orm.db_session:
                author_node = Node.get(pubkey=block.validated_by)
                MinerRisk.add_datapoint(block.validated_by, author_node.outliers, block.number)
        except Exception as e:
            traceback.print_exc()
            LOGGER.error('exception when calculating the live-time mean&variance happened: {}'.format(str(e)))


def start_live_time_heuristic():
    LOGGER.info('Starting LiveTimeMeanAndVariance thread...')
    threading.Thread(target=main_loop, daemon=True).start()
