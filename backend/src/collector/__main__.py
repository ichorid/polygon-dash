import multiprocessing
import time
from multiprocessing import Process
from threading import Thread
from time import sleep

import yaml
from pony.orm import db_session, commit
import pynng

from collector.settings import CollectorSettings, PostgresSettings, MempoolBotConnectionSettings

from collector.common import REQUEST_POP_TRANSACTIONS, deserialize_transactions
from polydash.model.transaction_p2p import Transaction, TransactionSeenEvent, Validator, db_p2p


class TransactionDumper:
    def __init__(self, input_queue):
        self.__input_queue = input_queue
        self.__processor_thread = None

    def __start_processing(self):
        num_transactions, prev_num_transactions = 0, 0
        start_tm = time.perf_counter()
        with db_session:
            while True:
                num_transactions += 1
                validator, tx_hash, tx_timestamp = self.__input_queue.get()
                transaction = Transaction.get(hash=tx_hash) or Transaction(hash=tx_hash)
                validator = Validator.get(pubkey=validator) or Validator(pubkey=validator)
                TransactionSeenEvent(transaction=transaction, validator=validator, timestamp=tx_timestamp, )
                elapsed_time = time.perf_counter() - start_tm
                # Commit to DB every 10th second
                if int(elapsed_time) % 10 == 0:
                    commit()
                if (num_transactions - prev_num_transactions) > 1000:
                    print(f"Avg. performance: {num_transactions/elapsed_time} trans/sec")
                    prev_num_transactions = num_transactions

    def __create_processor_thread(self):
        self.__processor_thread = Thread(target=self.__start_processing)
        self.__processor_thread.start()

    def start(self):
        self.__create_processor_thread()


class Collector:
    def __init__(self, settings: CollectorSettings):
        self.settings = settings
        self.__bot_to_dumper_queue = multiprocessing.Queue()
        self.__transaction_dumper = TransactionDumper(self.__bot_to_dumper_queue)
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
        src, trans_list = deserialize_transactions(msg.bytes)
        # print(f"COLLECTOR RECEIVED {len(trans_list)} TRANSACTIONS")
        for transaction in trans_list:
            self.__output_queue.put_nowait((src,) + transaction)
        #sleep(0.3)

    def __create_poller_thread(self):
        self.__poller_thread = Process(target=self.__start_polling)
        self.__poller_thread.start()


def start_p2p_db(settings: PostgresSettings):
    db_p2p.bind(provider='postgres', **dict(settings))
    db_p2p.generate_mapping(create_tables=True)


if __name__ == "__main__":
    with open('collector_settings.yaml', 'r') as file:
        settings = CollectorSettings(**yaml.safe_load(file))

    #settings.poller_bots = [MempoolBotConnectionSettings(url=f'tcp://localhost:{50000 + i}') for i in range(100)]

    start_p2p_db(settings.database_connection)

    collector = Collector(settings)
    collector.start()
