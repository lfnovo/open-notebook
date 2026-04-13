# SurrealDB
Start-Process powershell -NoExit -Command "C:\surrealdb\surreal.exe start --log info --user root --pass root rocksdb://./surreal_data"

# Backend with conda env
Start-Process powershell -NoExit -Command "conda run -p C:\Bhavesh\env uv run uvicorn api.main:app --host 127.0.0.1 --port 5055"

# Frontend
Start-Process powershell -NoExit -WorkingDirectory "$PWD\frontend" -Command "npm run dev"