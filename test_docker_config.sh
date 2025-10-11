#!/bin/bash
# Test script to validate Docker configuration

set -e

echo "=== Docker Configuration Validation ==="
echo ""

# Check Dockerfile exists
echo "✓ Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    echo "  ✓ Dockerfile found"
else
    echo "  ✗ Dockerfile not found"
    exit 1
fi

# Check Dockerfile.single exists
echo "✓ Checking Dockerfile.single..."
if [ -f "Dockerfile.single" ]; then
    echo "  ✓ Dockerfile.single found"
else
    echo "  ✗ Dockerfile.single not found"
    exit 1
fi

# Check supervisord configs
echo "✓ Checking supervisord configurations..."
if [ -f "supervisord.conf" ] && [ -f "supervisord.single.conf" ]; then
    echo "  ✓ supervisord configs found"

    # Check if they reference 'frontend' instead of 'streamlit'
    if grep -q "\[program:frontend\]" supervisord.conf; then
        echo "  ✓ supervisord.conf uses frontend"
    else
        echo "  ✗ supervisord.conf still references streamlit"
        exit 1
    fi

    if grep -q "\[program:frontend\]" supervisord.single.conf; then
        echo "  ✓ supervisord.single.conf uses frontend"
    else
        echo "  ✗ supervisord.single.conf still references streamlit"
        exit 1
    fi
else
    echo "  ✗ supervisord configs not found"
    exit 1
fi

# Check frontend files
echo "✓ Checking frontend configuration..."
if [ -f "frontend/package.json" ] && [ -f "frontend/next.config.ts" ]; then
    echo "  ✓ Frontend files found"

    # Check if package.json has the correct start script
    if grep -q 'start.*8502' frontend/package.json; then
        echo "  ✓ package.json configured for port 8502"
    else
        echo "  ⚠ package.json may not be configured for port 8502"
    fi

    # Check if next.config.ts has standalone output
    if grep -q 'output.*standalone' frontend/next.config.ts; then
        echo "  ✓ next.config.ts has standalone output"
    else
        echo "  ⚠ next.config.ts may not have standalone output"
    fi
else
    echo "  ✗ Frontend files not found"
    exit 1
fi

# Check Dockerfile structure
echo "✓ Checking Dockerfile structure..."
if grep -q "nodejs" Dockerfile; then
    echo "  ✓ Dockerfile installs Node.js"
else
    echo "  ✗ Dockerfile does not install Node.js"
    exit 1
fi

if grep -q "npm.*build" Dockerfile; then
    echo "  ✓ Dockerfile builds frontend"
else
    echo "  ✗ Dockerfile does not build frontend"
    exit 1
fi

if grep -q "EXPOSE.*8502" Dockerfile; then
    echo "  ✓ Dockerfile exposes port 8502"
else
    echo "  ✗ Dockerfile does not expose port 8502"
    exit 1
fi

# Check Dockerfile.single structure
echo "✓ Checking Dockerfile.single structure..."
if grep -q "nodejs" Dockerfile.single; then
    echo "  ✓ Dockerfile.single installs Node.js"
else
    echo "  ✗ Dockerfile.single does not install Node.js"
    exit 1
fi

if grep -q "npm.*build" Dockerfile.single; then
    echo "  ✓ Dockerfile.single builds frontend"
else
    echo "  ✗ Dockerfile.single does not build frontend"
    exit 1
fi

if grep -q "EXPOSE.*8502" Dockerfile.single; then
    echo "  ✓ Dockerfile.single exposes port 8502"
else
    echo "  ✗ Dockerfile.single does not expose port 8502"
    exit 1
fi

# Check .dockerignore
echo "✓ Checking .dockerignore..."
if [ -f ".dockerignore" ]; then
    if grep -q "frontend/node_modules" .dockerignore; then
        echo "  ✓ .dockerignore excludes frontend/node_modules"
    else
        echo "  ⚠ .dockerignore may not exclude frontend/node_modules"
    fi

    if grep -q "frontend/.next" .dockerignore; then
        echo "  ✓ .dockerignore excludes frontend/.next"
    else
        echo "  ⚠ .dockerignore may not exclude frontend/.next"
    fi
else
    echo "  ✗ .dockerignore not found"
    exit 1
fi

# Check documentation
echo "✓ Checking documentation updates..."
if [ -f "docs/migration/streamlit-to-nextjs.md" ]; then
    echo "  ✓ Migration guide created"
else
    echo "  ⚠ Migration guide not found"
fi

echo ""
echo "=== All Checks Passed! ==="
echo ""
echo "The Docker configuration appears to be correct for the Next.js migration."
echo "To test the actual build, run:"
echo "  docker build -t test-open-notebook:multi ."
echo "  docker build -t test-open-notebook:single -f Dockerfile.single ."
