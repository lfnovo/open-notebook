import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from loguru import logger
from sblpy.connection import SurrealSyncConnection

from open_notebook.exceptions import InvalidDatabaseSchema, NoSchemaFound

EXPECTED_VERSION = "0.0.2"


@contextmanager
def db_connection():
    connection = SurrealSyncConnection(
        host=os.environ["SURREAL_ADDRESS"],
        port=int(os.environ["SURREAL_PORT"]),
        user=os.environ["SURREAL_USER"],
        password=os.environ["SURREAL_PASS"],
        namespace=os.environ["SURREAL_NAMESPACE"],
        database=os.environ["SURREAL_DATABASE"],
        max_size=2.2**20,
        encrypted=False,  # Set to True if using SSL
    )
    try:
        yield connection
    finally:
        connection.socket.close()


def repo_query(query_str: str, vars: Optional[Dict[str, Any]] = None):
    with db_connection() as connection:
        try:
            result = connection.query(query_str, vars)
            return result
        except Exception as e:
            # logger.debug(f"Query: {query_str}, Variables: {vars}")
            logger.exception(e)
            raise


def check_database_version():
    try:
        result = repo_query("SELECT * FROM open_notebook:database_info;")

        if not result:
            raise NoSchemaFound("Database schema not found")

        version = result[0]["version"]
        logger.info(f"Connected to SurrealDB, using schema version {version}")

        if version != EXPECTED_VERSION:
            raise InvalidDatabaseSchema(
                f"Version mismatch. Expected {EXPECTED_VERSION}, got {version}"
            )
    except Exception as e:
        logger.error(e)
        raise e


def repo_create(table: str, data: Dict[str, Any]):
    query = f"CREATE {table} CONTENT {data};"
    # vars = {"table": table, "data": data}
    return repo_query(query)


def repo_update(id: str, data: Dict[str, Any]):
    query = "UPDATE $id CONTENT $data;"
    vars = {"id": id, "data": data}
    return repo_query(query, vars)


def repo_delete(id: str):
    query = "DELETE $id;"
    vars = {"id": id}
    return repo_query(query, vars)


def repo_relate(source: str, relationship: str, target: str):
    query = f"RELATE {source}->{relationship}->{target}"
    # CONTENT $content;"
    # vars = {
    #     "source": source,
    #     "relationship": relationship,
    #     "target": target,
    #  #   "content": {},  # You can add properties to the relation here if needed
    # }
    logger.debug(f"Executing RELATE query: {query}")
    result = repo_query(query)
    logger.debug(f"RELATE query result: {result}")
    return result


def execute_migration(script: str):
    with open(f"database/{script}", "r") as file:
        content = file.read()

    return repo_query(content)
