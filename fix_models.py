import asyncio
from open_notebook.database.repository import repo_query

async def main():
    models = await repo_query("SELECT id, name, type FROM model")
    for m in models:
        print(f"{m['id']}: {m['name']} ({m['type']})")
        if 'vision' in m['name'].lower() and m['type'] == 'language':
            print(f"Updating {m['name']} to vision")
            await repo_query("UPDATE $id SET type = 'vision'", {"id": m['id']})

asyncio.run(main())
