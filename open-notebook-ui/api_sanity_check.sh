#!/bin/bash

# API Sanity Check Script for Open Notebook Node.js Frontend

# Base URL for the API
BASE_URL="http://localhost:3000/api"

# Function to print a header for each section
print_header() {
    echo ""
    echo "======================================================================"
    echo "  $1"
    echo "======================================================================"
    echo ""
}

# Function to check the result of a curl command
check_result() {
    if [ $? -eq 0 ]; then
        echo "✅  SUCCESS: $1"
        echo "----------------------------------------------------------------------"
        echo "$2"
        echo ""
    else
        echo "❌  FAILURE: $1"
        echo "----------------------------------------------------------------------"
        echo "$2"
        echo ""
    fi
}

# --- Notebooks ---
print_header "Testing Notebooks API"

# GET all notebooks
echo "Testing GET /api/notebooks..."
response=$(curl -s -X GET $BASE_URL/notebooks)
check_result "GET /api/notebooks" "$response"

# POST a new notebook
echo "Testing POST /api/notebooks..."
response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"name": "Sanity Check Notebook", "description": "A notebook for sanity checks"}' $BASE_URL/notebooks)
notebook_id=$(echo "$response" | jq -r '.id' 2>/dev/null)
if [ -z "$notebook_id" ]; then
    # Fallback for stringified JSON
    notebook_id=$(echo "$response" | jq -r 'fromjson | .id' 2>/dev/null)
fi
check_result "POST /api/notebooks" "$response"

# GET the new notebook by ID
echo "Testing GET /api/notebooks/:id..."
response=$(curl -s -X GET $BASE_URL/notebooks/$notebook_id)
check_result "GET /api/notebooks/:id" "$response"

# PUT (update) the new notebook
echo "Testing PUT /api/notebooks/:id..."
response=$(curl -s -X PUT -H "Content-Type: application/json" -d '{"name": "Updated Sanity Check Notebook", "description": "An updated description", "archived": true}' $BASE_URL/notebooks/$notebook_id)
check_result "PUT /api/notebooks/:id" "$response"

# --- Sources ---
print_header "Testing Sources API"

# POST a new text source
echo "Testing POST /api/sources (text)..."
response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"notebook_id": "'$notebook_id'", "source_type": "text", "content": "This is a test text source."}' $BASE_URL/sources)
check_result "POST /api/sources (text)" "$response"

# POST a new link source
echo "Testing POST /api/sources (link)..."
response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"notebook_id": "'$notebook_id'", "source_type": "link", "url": "https://sanity-check.com"}' $BASE_URL/sources)
check_result "POST /api/sources (link)" "$response"

# --- Notes ---
print_header "Testing Notes API"

# POST a new note
echo "Testing POST /api/notes..."
response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"notebook_id": "'$notebook_id'", "title": "Sanity Check Note", "content": "This is a sanity check note."}' $BASE_URL/notes)
check_result "POST /api/notes" "$response"

# --- Search ---
print_header "Testing Search API"

# GET text search
echo "Testing GET /api/search/text..."
response=$(curl -s -G --data-urlencode "keyword=sanity" $BASE_URL/search/text)
check_result "GET /api/search/text" "$response"

# GET vector search
echo "Testing GET /api/search/vector..."
response=$(curl -s -G --data-urlencode "keyword=sanity" $BASE_URL/search/vector)
check_result "GET /api/search/vector" "$response"

# --- Models ---
print_header "Testing Models API"

# GET all models
echo "Testing GET /api/models/all..."
response=$(curl -s -X GET $BASE_URL/models/all)
check_result "GET /api/models/all" "$response"

# GET models by type
echo "Testing GET /api/models/by_type/language..."
response=$(curl -s -X GET $BASE_URL/models/by_type/language)
check_result "GET /api/models/by_type/language" "$response"

# GET default models
echo "Testing GET /api/models/defaults..."
response=$(curl -s -X GET $BASE_URL/models/defaults)
check_result "GET /api/models/defaults" "$response"

# GET available providers
echo "Testing GET /api/models/providers..."
response=$(curl -s -X GET $BASE_URL/models/providers)
check_result "GET /api/models/providers" "$response"

# --- Transformations ---
print_header "Testing Transformations API"

# GET all transformations
echo "Testing GET /api/transformations/all..."
response=$(curl -s -X GET $BASE_URL/transformations/all)
check_result "GET /api/transformations/all" "$response"

# GET default prompts
echo "Testing GET /api/transformations/defaults..."
response=$(curl -s -X GET $BASE_URL/transformations/defaults)
check_result "GET /api/transformations/defaults" "$response"

# --- Podcasts ---
print_header "Testing Podcasts API"

# GET podcast configs
echo "Testing GET /api/podcasts/configs..."
response=$(curl -s -X GET $BASE_URL/podcasts/configs)
check_result "GET /api/podcasts/configs" "$response"

# GET podcast episodes
echo "Testing GET /api/podcasts/episodes..."
response=$(curl -s -X GET $BASE_URL/podcasts/episodes)
check_result "GET /api/podcasts/episodes" "$response"

# --- Settings ---
print_header "Testing Settings API"

# GET content settings
echo "Testing GET /api/settings/content..."
response=$(curl -s -X GET $BASE_URL/settings/content)
check_result "GET /api/settings/content" "$response"

# --- Cleanup ---
print_header "Cleaning up test data"

# DELETE the test notebook
echo "Testing DELETE /api/notebooks/:id..."
response=$(curl -s -X DELETE $BASE_URL/notebooks/$notebook_id)
check_result "DELETE /api/notebooks/:id" "$response"

echo ""
echo "Sanity check complete."
