# Database - SurrealDB Configuration

Open Notebook stores everything except uploaded files and podcast audio in [SurrealDB](https://surrealdb.com). The API and the background worker both connect to it with the same five variables. Schema migrations run automatically when the API starts.

---

## Connection settings

```env
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
```

Set all five explicitly. The API and the job queue fall back to different defaults when a variable is missing (`open_notebook` versus `test` for namespace and database), and with mismatched values background jobs never get processed. Defaults and legacy names are in the [Environment Reference](environment-reference.md#database-surrealdb).

`SURREAL_USER` and `SURREAL_PASSWORD` must match the `--user` and `--pass` that SurrealDB was started with.

---

## Which `SURREAL_URL` to use

The host in `SURREAL_URL` is the database as seen **from wherever the API and worker run**.

| Open Notebook | SurrealDB | `SURREAL_URL` |
|---------------|-----------|---------------|
| Docker Compose (shipped file) | `surrealdb` service in the same compose file | `ws://surrealdb:8000/rpc` |
| Docker | On the host machine | `ws://host.docker.internal:8000/rpc` (on Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the service) |
| From source | Docker (`make database`) or installed locally | `ws://localhost:8000/rpc` |
| Single-container image | Inside the same container | `ws://localhost:8000/rpc` (see [Single Container](../1-INSTALLATION/single-container.md)) |
| Anywhere | Another machine | `ws://<db-host>:8000/rpc` |

`localhost` inside a container is the container itself, not your machine. Using `ws://localhost:8000/rpc` in the compose setup is the most common reason the API won't start.

The shipped compose file publishes SurrealDB on `127.0.0.1:8000` only, so other machines can't reach it. To connect from elsewhere, re-publish the port deliberately (see `docker-compose.override.yml.example` in the repository root), with real credentials and a firewall or SSH tunnel.

---

## Changing the credentials

With the shipped compose file, put the new values in a `.env` file next to `docker-compose.yml`:

```env
SURREAL_USER=notebook_admin
SURREAL_PASSWORD=a-long-random-password
```

The compose file passes them to both the `surrealdb` command and the `open_notebook` environment, so they stay in sync. Apply with `docker compose up -d`.

---

## Several instances on one SurrealDB

A SurrealDB server can hold many namespaces, and each namespace many databases. To run several independent Open Notebook instances against one server, give each instance its own `SURREAL_NAMESPACE` or `SURREAL_DATABASE`.

---

## When the API can't reach the database

While waiting for SurrealDB, the API logs `Database is not reachable yet (attempt n/12)` and retries. After the last attempt it logs `Database did not become reachable after 12 attempts` and stops, and the UI shows **Database Connection Failed**. See [Connection Issues → Database Connection Failed](../6-TROUBLESHOOTING/connection-issues.md#database-connection-failed).

Backups: [Advanced → Backup & Restore](advanced.md#backup--restore).
