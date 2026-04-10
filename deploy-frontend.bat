@echo off
echo ========================================
echo  Full Deploy to Docker (Windows)
echo ========================================

set CONTAINER=kavach-open-notebook-open_notebook-1
set ROOT=%~dp0

echo.
echo [1/4] Building Next.js locally...
cd /d "%ROOT%frontend"
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed. Aborting.
    exit /b 1
)

echo.
echo [2/4] Copying frontend build output...
docker cp "%ROOT%frontend\.next\." %CONTAINER%:/app/frontend/.next/

echo.
echo [3/4] Copying backend Python + prompt files...
cd /d "%ROOT%"
docker cp "api\routers\source_chat.py"              %CONTAINER%:/app/api/routers/source_chat.py
docker cp "api\routers\chat.py"                     %CONTAINER%:/app/api/routers/chat.py
docker cp "api\routers\mindmap.py"                  %CONTAINER%:/app/api/routers/mindmap.py
docker cp "api\models.py"                           %CONTAINER%:/app/api/models.py
docker cp "open_notebook\graphs\source_chat.py"     %CONTAINER%:/app/open_notebook/graphs/source_chat.py
docker cp "open_notebook\utils\context_builder.py"  %CONTAINER%:/app/open_notebook/utils/context_builder.py
docker cp "prompts\source_chat\system.jinja"        %CONTAINER%:/app/prompts/source_chat/system.jinja

echo.
echo [4/4] Restarting container...
docker restart %CONTAINER%
if %ERRORLEVEL% neq 0 (
    echo ERROR: Container restart failed.
    exit /b 1
)

echo.
echo ========================================
echo  Done! Full deploy completed.
echo ========================================
