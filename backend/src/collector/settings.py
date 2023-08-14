from pydantic import BaseSettings


class PostgresSettings(BaseSettings):
    # ACHTUNG!
    # BaseSettings class gets default values from env variables.
    # So, the priority is : config > env > default.
    # As the 'user' var is typically set for the current user,
    # it will override the default from this file unless you specify it in the .yaml file.
    password: str = None
    user: str = 'postgres'
    host: str = 'localhost'
    port: int = 5432
    database: str = 'p2p_collector'


class MempoolBotConnectionSettings(BaseSettings):
    url: str = None


class TransactionDumperSettings(BaseSettings):
    tx_hashes_cache_size: int = 1000000
    validators_cache_size: int = 10000
    batch_size_limit: int = 5000
    stats_every_n_transactions: int = 1000


class CollectorSettings(BaseSettings):
    poller_bots: list[MempoolBotConnectionSettings] = None
    database_connection: PostgresSettings = None
    transaction_dumper: TransactionDumperSettings = TransactionDumperSettings()
