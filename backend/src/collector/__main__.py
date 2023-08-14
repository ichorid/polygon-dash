import yaml

from collector.daemon_components import Collector
from collector.settings import MempoolBotConnectionSettings, CollectorSettings, PostgresSettings
from polydash.model.transaction_p2p import db_p2p


def start_p2p_db(settings: PostgresSettings):
    db_p2p.bind(provider='postgres', **dict(settings))
    db_p2p.generate_mapping(create_tables=True)


if __name__ == "__main__":
    with open('collector_settings.yaml', 'r') as file:
        settings = CollectorSettings(**yaml.safe_load(file))

    settings.poller_bots = [MempoolBotConnectionSettings(url=f'tcp://localhost:{50000 + i}') for i in range(100)]

    start_p2p_db(settings.database_connection)
    # print(Transaction.insert_or_select_hashes([b'dead']))
    # exit(0)

    collector = Collector(settings)
    collector.start()
