import multiprocessing
import time
from multiprocessing import Process
from threading import Thread
from time import sleep

import cachetools
import pynng
from pony.orm import db_session
from psycopg2.extras import execute_values

from collector.settings import CollectorSettings, PostgresSettings, MempoolBotConnectionSettings, \
    TransactionDumperSettings

from collector.common import REQUEST_POP_TRANSACTIONS, deserialize_events
from polydash.model.transaction_p2p import Transaction, TransactionSeenEvent, Validator, db_p2p


class TransactionDumper:

    def __init__(self, input_queue, settings: TransactionDumperSettings):
        self.__input_queue = input_queue
        self.__settings = settings

        self.__processor_thread = None
        self.__hash_cache = cachetools.LRUCache(100000)
        self.__validator_cache = cachetools.LRUCache(10000)
        # Default batch size is tuned ad hoc for best performance.
        # In general, bandwidth grows proportional to the batch size.
        # However, if the batch is too big, there can be slowdowns.

        self.dumped_count = 0
        self.__prev_dumped_count = 0
        self.__start_tm = None
        self.__leftovers = []
        self.cache_hits = 0

    def __start_processing(self):
        self.__start_tm = time.perf_counter()
        while True:
            self.__processing_loop()

    def __processing_loop(self):
        batch = self.__leftovers
        orig_leftovers_len = len(self.__leftovers)
        self.__leftovers = []
        while not self.__input_queue.empty() and len(batch) < self.__settings.batch_size_limit:
            batch.append(self.__input_queue.get())
        if not batch:
            return

        new_hashes = set()
        new_validators = set()
        events_to_insert = []
        for event in batch:
            validator, tx_hash, tx_timestamp = event
            if (validator_id := self.__validator_cache.get(validator)) is None:
                new_validators.add(validator)

            if (tx_hash_id := self.__hash_cache.get(tx_hash)) is None:
                new_hashes.add(tx_hash)

            if validator_id is not None and tx_hash_id is not None:
                events_to_insert.append((validator_id, tx_hash_id, tx_timestamp))
            else:
                # These are the events (transaction seeings) with previously unseen
                # transaction hashes and/or validator ids.
                # We don't want to mess with them now. Instead, we will process them
                # first at the next iteration of the loop, when the caches will already
                # have the required mappings.
                # Note that we can't just add the stuff to the queue - there exists a possibility
                # that too many new events in the queue will evict the mappings that were
                # just added, so the whole pipeline will become stuck.
                self.__leftovers.append(event)

        # Select/insert validator ids and transaction hashes unknown to local cache
        for _, validator_id, validator in Validator.insert_or_select_hashes(list(new_validators)):
            self.__validator_cache[bytes(validator)] = validator_id
        for _, tx_id, tx_hash in Transaction.insert_or_select_hashes(list(new_hashes)):
            self.__hash_cache[bytes(tx_hash)] = tx_id

        self.dumped_count += len(events_to_insert)

        with db_session:
            execute_values(
                db_p2p.get_connection().cursor(),
                "INSERT INTO transactionseenevent (validator, transaction, timestamp) VALUES %s",
                events_to_insert)

        self.cache_hits += (len(events_to_insert) - orig_leftovers_len)

        # transaction = Transaction.get(hash=tx_hash) or Transaction(hash=tx_hash)
        # TransactionSeenEvent(transaction=transaction, validator=validator, timestamp=tx_timestamp, )
        if (self.dumped_count - self.__prev_dumped_count) > self.__settings.stats_every_n_transactions:
            elapsed_time = time.perf_counter() - self.__start_tm
            print(f"time {elapsed_time}")
            print(f"Avg. performance: {self.dumped_count / elapsed_time} trans/sec (Total trans.: {self.dumped_count})")
            print(f"Cache hits: {(100 * self.cache_hits) // self.dumped_count}% ")
            print(f"Cache hits: {len(events_to_insert)} {orig_leftovers_len} ")
            print(self.__input_queue.qsize())
            self.__prev_dumped_count = self.dumped_count

    def __create_processor_thread(self):
        self.__processor_thread = Thread(target=self.__start_processing)
        self.__processor_thread.start()

    def start(self):
        self.__create_processor_thread()


class Collector:
    def __init__(self, settings: CollectorSettings):
        self.__settings = settings
        self.__bot_to_dumper_queue = multiprocessing.Queue(maxsize=10000)
        self.__transaction_dumper = TransactionDumper(
            self.__bot_to_dumper_queue, settings.transaction_dumper)
        self.__poller_bots = {bot_settings.url: BotPoller(self.__bot_to_dumper_queue, bot_settings) for bot_settings in
                              settings.poller_bots}

    def start(self):
        self.__transaction_dumper.start()
        for bot in self.__poller_bots.values():
            bot.start()


class BotPoller:
    def __init__(self, output_queue: multiprocessing.Queue, settings: MempoolBotConnectionSettings):
        self.__poller_thread = None
        self.__output_queue = output_queue
        self.settings = settings

    def start(self):
        self.__create_poller_thread()

    def __start_polling(self):
        while True:
            try:
                with pynng.Req0() as sock:
                    sock.dial(self.settings.url)
                    print(f"Connection established to {self.settings.url}")

                    while True:
                        self.__poller_loop(sock)
            except pynng.exceptions.ConnectionRefused:
                print(f"Bot {self.settings.url} refused connection, retrying in 5 seconds")
                sleep(5)

    def __poller_loop(self, sock):
        # print(f"COLLECTOR SENDING TRANSACTIONS REQUEST")
        sock.send(REQUEST_POP_TRANSACTIONS.encode())
        msg = sock.recv_msg()
        src, trans_list = deserialize_events(msg.bytes)
        # print(f"COLLECTOR RECEIVED {len(trans_list)} TRANSACTIONS")
        for transaction in trans_list:
            self.__output_queue.put((src,) + transaction)
        # sleep(0.3)

    def __create_poller_thread(self):
        self.__poller_thread = Process(target=self.__start_polling)
        self.__poller_thread.start()
