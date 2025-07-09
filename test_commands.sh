#!/bin/bash

echo "=== Testing Surreal Commands Integration ==="
echo ""

# Base URL
BASE_URL="http://localhost:5055/api"

# 1. Test text processing command
echo "1. Testing text processing command (uppercase)..."
curl -X POST "$BASE_URL/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "process_text",
    "app": "open_notebook",
    "input": {
      "text": "Hello, this is a test message!",
      "operation": "uppercase"
    }
  }' | jq .

echo ""
echo "2. Testing text processing with delay (3 seconds)..."
curl -X POST "$BASE_URL/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "process_text",
    "app": "open_notebook",
    "input": {
      "text": "Testing async behavior with delay",
      "operation": "reverse",
      "delay_seconds": 3
    }
  }' | jq .

echo ""
echo "3. Testing data analysis command..."
curl -X POST "$BASE_URL/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "analyze_data",
    "app": "open_notebook",
    "input": {
      "numbers": [10, 20, 30, 40, 50],
      "analysis_type": "basic"
    }
  }' | jq .

echo ""
echo "4. Testing error scenario (empty numbers array)..."
curl -X POST "$BASE_URL/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "analyze_data",
    "app": "open_notebook",
    "input": {
      "numbers": [],
      "analysis_type": "basic"
    }
  }' | jq .

echo ""
echo "5. Testing word count operation..."
curl -X POST "$BASE_URL/commands/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "process_text",
    "app": "open_notebook",
    "input": {
      "text": "This is a sample text with multiple words to count",
      "operation": "word_count"
    }
  }' | jq .

echo ""
echo "Please save the job_ids from above to check status!"
echo ""
echo "6. To check job status (replace JOB_ID with actual ID):"
echo "curl \"$BASE_URL/commands/jobs/{JOB_ID}\" | jq ."

echo ""
echo "7. To list all jobs:"
echo "curl \"$BASE_URL/commands/jobs\" | jq ."

echo ""
echo "=== Test Commands Complete ==="
echo ""
echo "Manual status check example:"
echo "Replace JOB_ID with one of the job IDs returned above:"
echo "curl \"$BASE_URL/commands/jobs/JOB_ID\" | jq ."