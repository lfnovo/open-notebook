import asyncio
from open_notebook.database.connection import SurrealConnection
from open_notebook.database.repository import repo_query
import json

async def main():
    await SurrealConnection.connect()
    res = await repo_query("SELECT id, name, type, provider FROM model")
    print(json.dumps(res, indent=2))
    await SurrealConnection.close()

asyncio.run(main())
