#!/bin/bash
# Re-push all custom files to the container after docker compose up -d
# Run this from your project root: bash repush.sh

CONTAINER="kavach-open-notebook-open_notebook-1"

echo "Waiting for container to be ready..."
sleep 15

echo "Pushing backend files..."
docker cp "api/main.py"                "$CONTAINER:/app/api/main.py"
docker cp "api/routers/mindmap.py"     "$CONTAINER:/app/api/routers/mindmap.py"
docker cp "api/routers/infographic.py" "$CONTAINER:/app/api/routers/infographic.py"
docker cp "open_notebook/graphs/summary.py"    "$CONTAINER:/app/open_notebook/graphs/summary.py"
docker cp "open_notebook/graphs/infographic.py" "$CONTAINER:/app/open_notebook/graphs/infographic.py"
docker cp "open_notebook/graphs/mind_map.py"   "$CONTAINER:/app/open_notebook/graphs/mind_map.py"

echo "Pushing frontend files..."
docker cp "frontend/src/components/layout/AppSidebar.tsx"        "$CONTAINER:/app/frontend/src/components/layout/AppSidebar.tsx"
docker cp "frontend/src/components/source/MindMapDialog.tsx"     "$CONTAINER:/app/frontend/src/components/source/MindMapDialog.tsx"
docker cp "frontend/src/components/source/InfographicDialog.tsx" "$CONTAINER:/app/frontend/src/components/source/InfographicDialog.tsx"
docker cp "frontend/src/components/source/SummaryDialog.tsx"     "$CONTAINER:/app/frontend/src/components/source/SummaryDialog.tsx"
docker cp "frontend/src/components/sources/SourceCard.tsx"       "$CONTAINER:/app/frontend/src/components/sources/SourceCard.tsx"
# Create studio dir if it doesn't exist, then copy
docker exec "$CONTAINER" mkdir -p /app/frontend/src/components/studio
docker cp "frontend/src/components/studio/SourcePickerDialog.tsx" "$CONTAINER:/app/frontend/src/components/studio/SourcePickerDialog.tsx"
docker cp "frontend/src/lib/api/mindmap.ts"    "$CONTAINER:/app/frontend/src/lib/api/mindmap.ts"
docker cp "frontend/src/lib/api/infographic.ts" "$CONTAINER:/app/frontend/src/lib/api/infographic.ts"
docker cp "frontend/src/lib/locales/en-US/index.ts" "$CONTAINER:/app/frontend/src/lib/locales/en-US/index.ts"
docker cp "frontend/src/app/layout.tsx"             "$CONTAINER:/app/frontend/src/app/layout.tsx"
docker cp "frontend/public/KavachLogo.png"          "$CONTAINER:/app/frontend/public/KavachLogo.png"
docker cp "frontend/src/components/source/SourceDetailContent.tsx" "$CONTAINER:/app/frontend/src/components/source/SourceDetailContent.tsx"

echo ""
echo "Patching built Next.js output (title + favicon)..."
docker exec "$CONTAINER" sh -c "
  # Patch RSC payloads (used for client-side navigation)
  for f in /app/frontend/.next/server/app/*.rsc; do
    sed -i 's|Open Notebook|Notebook|g' \"\$f\"
    sed -i 's|favicon\.ico[^\"]*|logo(1).svg?v=2|g' \"\$f\"
    sed -i 's|/logo(1)\.svg\"|/logo(1).svg?v=2\"|g' \"\$f\"
    sed -i 's|\"children\":\"Kavach\"|\"children\":\"Notebook\"|g' \"\$f\"
  done
  # Patch HTML files
  for f in /app/frontend/.next/server/app/*.html; do
    sed -i 's|Open Notebook|Notebook|g' \"\$f\"
    sed -i 's|favicon\.ico[^\"]*|logo(1).svg?v=2|g' \"\$f\"
    sed -i 's|href=\"/logo(1)\.svg\"|href=\"/logo(1).svg?v=2\"|g' \"\$f\"
    sed -i 's|<title>Kavach</title>|<title>Notebook</title>|g' \"\$f\"
  done
  # Patch JS chunks
  find /app/frontend/.next/static/chunks -name '*.js' | xargs grep -l 'logo(1)' 2>/dev/null | while read f; do
    sed -i 's|/logo(1)\.svg\"|/logo(1).svg?v=2\"|g' \"\$f\"
  done
  # Remove MindMapButton from SourceDetailContent chunk
  sed -i 's|(0,s\.jsx)(J\.MindMapButton,{sourceId:e,sourceTitle:W\.title}),||g' /app/frontend/.next/static/chunks/0d032ae2b6632ae8.js 2>/dev/null || true
  echo 'Next.js patches applied'
"

echo ""
echo "All files pushed. Restarting API (graceful)..."
# Use SIGTERM (kill -15) so uvicorn shuts down cleanly and releases port 5055
# before supervisord restarts it — avoids "address already in use" crash loop
docker exec "$CONTAINER" /bin/sh -c "
  for pid in \$(ls /proc | grep '^[0-9]'); do
    cmdline=\$(cat /proc/\$pid/cmdline 2>/dev/null | tr '\0' ' ')
    case \"\$cmdline\" in
      *uvicorn*api.main*) kill -15 \$pid; echo \"Sent SIGTERM to PID \$pid\";;
    esac
  done
" 2>/dev/null || true

echo "Waiting 12s for clean restart..."
sleep 12
echo "Done. Check logs with: docker logs $CONTAINER --tail 20"
