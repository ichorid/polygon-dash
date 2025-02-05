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
    database: str = 'polydash'


class BlockRetrieverSettings(BaseSettings):
    block_rpc_url: str = None


class W3RouterSettings(BaseSettings):
    w3_rpc_url: str = "http://localhost/rpc/update_nodes"


class PolydashSettings(BaseSettings):
    postgres_connection: PostgresSettings = PostgresSettings()
    block_retriever: BlockRetrieverSettings = BlockRetrieverSettings()
    w3_router: W3RouterSettings = W3RouterSettings()
    port: int = 5500
    host: str = '0.0.0.0'
