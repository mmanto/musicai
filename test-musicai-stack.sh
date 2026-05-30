#!/bin/bash
# MusicAI Stack Diagnostic Tool
# Comprehensive testing of all layers

echo "=== MusicAI Stack Diagnostic Tool ==="
echo "Testing all layers to identify the issue with 'cadencia conclusiva' question"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function test_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${YELLOW}>>> $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

function test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

function test_fail() {
    echo -e "${RED}❌ $1${NC}"
}

function test_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Test 1: Docker containers
test_section "Test 1: Docker Containers Status"
if docker ps --filter "name=musicai" --format "{{.Names}}" | grep -q musicai; then
    test_pass "MusicAI containers are running"
    echo ""
    docker ps --filter "name=musicai" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -n 20
else
    test_fail "No MusicAI containers found"
    test_info "Run: docker-compose up -d"
fi

# Test 2: Ollama on host
test_section "Test 2: Ollama Service on Host"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    test_pass "Ollama is running on localhost:11434"

    # Check for model
    if command -v ollama &> /dev/null; then
        if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
            test_pass "Model qwen2.5:7b is installed"
        else
            test_fail "Model qwen2.5:7b is NOT installed"
            test_info "Run: ollama pull qwen2.5:7b"
        fi
    else
        test_info "Ollama CLI not in PATH, checking via API..."
        MODELS=$(curl -s http://localhost:11434/api/tags)
        if echo "$MODELS" | grep -q "qwen2.5:7b"; then
            test_pass "Model qwen2.5:7b is available"
        else
            test_fail "Model qwen2.5:7b not found in Ollama"
        fi
    fi
else
    test_fail "Ollama is NOT accessible on localhost:11434"
    test_info "Start Ollama with: ollama serve"
    test_info "Or install from: https://ollama.com/download"
fi

# Test 3: Reasoning service health
test_section "Test 3: Reasoning Service Health"
REASONING_HEALTH=$(curl -s http://localhost:8004/api/v1/health 2>/dev/null)
if [ $? -eq 0 ]; then
    test_pass "Reasoning service is responding on :8004"
    if command -v jq &> /dev/null; then
        echo "$REASONING_HEALTH" | jq '.'
    else
        echo "$REASONING_HEALTH"
    fi
else
    test_fail "Reasoning service is NOT responding on :8004"
    test_info "Check: docker logs musicai-reasoning"
fi

# Test 4: Chat teacher health
test_section "Test 4: Chat Teacher Health"
CHAT_HEALTH=$(curl -s http://localhost:8004/api/v1/chat-teacher/health 2>/dev/null)
if [ $? -eq 0 ]; then
    test_pass "Chat teacher endpoint is responding"
    if command -v jq &> /dev/null; then
        echo "$CHAT_HEALTH" | jq '.'

        # Check each component
        MUSIC_ANALYZER=$(echo "$CHAT_HEALTH" | jq -r '.components.music_analyzer')
        LLM_CLIENT=$(echo "$CHAT_HEALTH" | jq -r '.components.llm_client')
        PATTERN_PARSER=$(echo "$CHAT_HEALTH" | jq -r '.components.pattern_parser')

        if [ "$MUSIC_ANALYZER" = "true" ]; then
            test_pass "music_analyzer initialized"
        else
            test_fail "music_analyzer NOT initialized"
        fi

        if [ "$LLM_CLIENT" = "true" ]; then
            test_pass "llm_client initialized"
        else
            test_fail "llm_client NOT initialized"
        fi

        if [ "$PATTERN_PARSER" = "true" ]; then
            test_pass "pattern_parser initialized"
        else
            test_fail "pattern_parser NOT initialized"
        fi
    else
        echo "$CHAT_HEALTH"
    fi
else
    test_fail "Chat teacher endpoint is NOT responding"
    test_info "This is likely the source of the problem"
fi

# Test 5: Ollama connectivity from container
test_section "Test 5: Ollama Connectivity from Reasoning Container"
if docker exec musicai-reasoning curl -s -f http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then
    test_pass "Reasoning container CAN reach Ollama via host.docker.internal"
else
    test_fail "Reasoning container CANNOT reach Ollama via host.docker.internal"
    test_info "This is likely the root cause!"

    # Test host connectivity
    if docker exec musicai-reasoning ping -c 1 host.docker.internal > /dev/null 2>&1; then
        test_pass "host.docker.internal resolves to an IP"
        HOST_IP=$(docker exec musicai-reasoning getent hosts host.docker.internal | awk '{ print $1 }')
        test_info "Resolves to: $HOST_IP"
    else
        test_fail "host.docker.internal does NOT resolve"
        test_info "Check docker-compose.yml has: extra_hosts: - \"host.docker.internal:host-gateway\""
    fi

    # Try direct curl to check port
    test_info "Checking if port 11434 is reachable..."
    docker exec musicai-reasoning nc -zv host.docker.internal 11434 2>&1 || true
fi

# Test 6: Chat teacher with simple message
test_section "Test 6: Chat Teacher - Simple Message Test"
test_info "Sending: 'Hola'"
SIMPLE_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "conversation_history": []}' 2>/dev/null)

if echo "$SIMPLE_RESPONSE" | grep -q "explanation"; then
    test_pass "Chat teacher responds to simple message"
    if command -v jq &> /dev/null; then
        EXPLANATION=$(echo "$SIMPLE_RESPONSE" | jq -r '.explanation' | head -c 200)
        echo "Response preview: $EXPLANATION..."
    fi
else
    test_fail "Chat teacher failed to respond to simple message"
    echo "Full response:"
    echo "$SIMPLE_RESPONSE" | jq '.' 2>/dev/null || echo "$SIMPLE_RESPONSE"
fi

# Test 7: Chat teacher with theory question
test_section "Test 7: Chat Teacher - Theory Question (THE CRITICAL TEST)"
test_info "Sending: 'puedes hablarme sobre una cadencia conclusiva?'"
THEORY_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{"message": "puedes hablarme sobre una cadencia conclusiva?", "conversation_history": []}' 2>/dev/null)

if echo "$THEORY_RESPONSE" | grep -q "explanation"; then
    EXPLANATION=$(echo "$THEORY_RESPONSE" | jq -r '.explanation' 2>/dev/null)

    # Check if it's an error message
    if echo "$EXPLANATION" | grep -qi "siento\|error\|problema"; then
        test_fail "Chat teacher returned an ERROR response"
        echo "Error message: $EXPLANATION"
        test_info "This confirms the problem exists!"
    else
        test_pass "Chat teacher responds successfully to theory question"
        echo ""
        echo "Explanation preview:"
        echo "$EXPLANATION" | head -c 300
        echo ""
    fi

    # Check if visualization was generated
    if echo "$THEORY_RESPONSE" | jq -e '.visualization' > /dev/null 2>&1; then
        test_pass "Visualization was generated"
    else
        test_info "No visualization (text-only response)"
    fi
else
    test_fail "Chat teacher failed to respond to theory question"
    echo "Full response:"
    echo "$THEORY_RESPONSE" | jq '.' 2>/dev/null || echo "$THEORY_RESPONSE"
fi

# Test 8: Frontend configuration
test_section "Test 8: Frontend Configuration"
if docker ps | grep -q "musicai-chat-frontend"; then
    if docker exec musicai-chat-frontend env 2>/dev/null | grep -q "VITE_USE_REASONING_SERVICE=true"; then
        test_pass "Frontend is configured to use reasoning service"
    else
        test_fail "Frontend is NOT configured to use reasoning service"
        test_info "Frontend may be using backend instead"
    fi

    REASONING_URL=$(docker exec musicai-chat-frontend env 2>/dev/null | grep VITE_REASONING_API_URL)
    test_info "Configuration: $REASONING_URL"
else
    test_fail "Frontend container not running"
fi

# Test 9: Backend health
test_section "Test 9: Backend Health (Optional)"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    test_pass "Backend is responding on :8000"
else
    test_fail "Backend is NOT responding on :8000"
fi

# Test 10: Check reasoning logs for errors
test_section "Test 10: Recent Reasoning Service Logs"
test_info "Checking last 20 lines of reasoning logs for errors..."
docker logs musicai-reasoning --tail 20 2>&1 | grep -i "error\|exception\|timeout" || test_pass "No obvious errors in recent logs"

# Summary
test_section "DIAGNOSTIC SUMMARY"
echo ""
echo "Key findings:"
echo ""

# Determine the likely issue
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${RED}🔴 PRIMARY ISSUE: Ollama is not running on host${NC}"
    echo "   Solution: Start Ollama with 'ollama serve'"
elif ! docker exec musicai-reasoning curl -s -f http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then
    echo -e "${RED}🔴 PRIMARY ISSUE: Reasoning container cannot reach Ollama${NC}"
    echo "   Solution: Fix host.docker.internal connectivity"
    echo "   Check docker-compose.yml has extra_hosts configuration"
elif echo "$THEORY_RESPONSE" | jq -r '.explanation' 2>/dev/null | grep -qi "siento\|error\|problema"; then
    echo -e "${RED}🔴 PRIMARY ISSUE: LLM is returning error responses${NC}"
    echo "   The connection works but LLM processing fails"
    echo "   Check model availability and timeout settings"
else
    echo -e "${GREEN}✅ All tests passed! The system appears to be working.${NC}"
    echo "   If you still see issues in the UI, check browser console"
fi

echo ""
echo "Detailed diagnostics:"
echo "1. Run: docker logs musicai-reasoning --tail 100"
echo "2. Run: ./test-llm-interactive.sh (for deep LLM testing)"
echo "3. Run: ./monitor-logs.sh (to watch logs in real-time)"
echo ""
echo "=== Diagnostic Complete ==="
