#!/bin/bash

# Test MusicAI API Endpoints
# Run the server first: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "=================================================="
echo "Testing MusicAI API"
echo "=================================================="

# Test 1: Health Check
echo -e "\n[TEST 1] Health Check"
echo "GET /health"
curl -s "${BASE_URL}/health" | python3 -m json.tool

# Test 2: Root endpoint
echo -e "\n\n[TEST 2] Root endpoint"
echo "GET /"
curl -s "${BASE_URL}/" | python3 -m json.tool

# Test 3: API Docs
echo -e "\n\n[TEST 3] API Documentation"
echo "GET /docs"
echo "Visit: ${BASE_URL}/docs"

# Test 4: Generate Music
echo -e "\n\n[TEST 4] Generate Music"
echo "POST ${API_URL}/music/generate"
RESPONSE=$(curl -s -X POST "${API_URL}/music/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A peaceful piano melody in C major",
    "duration": 10,
    "title": "Test Generation"
  }')

echo "$RESPONSE" | python3 -m json.tool

# Extract job_id
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ -n "$JOB_ID" ]; then
    echo -e "\nGenerated Job ID: $JOB_ID"

    # Test 5: Check Job Status
    echo -e "\n\n[TEST 5] Check Job Status"
    echo "GET ${API_URL}/music/status/$JOB_ID"
    sleep 2  # Wait a bit for processing
    curl -s "${API_URL}/music/status/$JOB_ID" | python3 -m json.tool
fi

# Test 6: List all jobs
echo -e "\n\n[TEST 6] List All Jobs"
echo "GET ${API_URL}/music/jobs"
curl -s "${API_URL}/music/jobs" | python3 -m json.tool

# Test 7: Analyze Music (upload MIDI)
echo -e "\n\n[TEST 7] Analyze Uploaded MIDI"
echo "POST ${API_URL}/music/analyze/upload"
if [ -f "poc_output/melody.mid" ]; then
    curl -s -X POST "${API_URL}/music/analyze/upload" \
      -F "file=@poc_output/melody.mid" \
      -F "generate_explanation=true" | python3 -m json.tool
else
    echo "No MIDI file found to test. Run poc_test_simple.py first."
fi

echo -e "\n\n=================================================="
echo "API Testing Complete!"
echo "=================================================="
