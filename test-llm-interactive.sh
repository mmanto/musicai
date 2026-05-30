#!/bin/bash
# Interactive LLM Test
# Tests the LLM client directly inside the reasoning container

echo "=== Interactive LLM Test ==="
echo "This script tests the LLM client inside the reasoning container"
echo "to diagnose Ollama connectivity and model issues"
echo ""

# Check if reasoning container is running
if ! docker ps | grep -q "musicai-reasoning"; then
    echo "❌ Reasoning container is not running"
    echo "Start it with: docker-compose up -d reasoning"
    exit 1
fi

echo "Running LLM test inside reasoning container..."
echo ""

docker exec -it musicai-reasoning python3 << 'EOF'
import asyncio
import sys
import os
sys.path.insert(0, '/app/src')

print("=" * 60)
print("LLM CLIENT DIAGNOSTIC TEST")
print("=" * 60)
print()

try:
    from neural.llm_client import OllamaClient, Message

    async def test_llm():
        # Get config from environment
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
        model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
        timeout = int(os.getenv('OLLAMA_TIMEOUT', '120'))

        print(f"📋 Configuration:")
        print(f"   Base URL: {base_url}")
        print(f"   Model: {model}")
        print(f"   Timeout: {timeout}s")
        print()

        # Test connection first
        print("🔌 Test 1: Connection Test")
        print("-" * 60)
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        print("✅ Successfully connected to Ollama")
                        data = await resp.json()
                        if 'models' in data:
                            print(f"   Found {len(data['models'])} models:")
                            for m in data['models'][:5]:
                                print(f"   - {m.get('name', 'unknown')}")
                        print()
                    else:
                        print(f"❌ Connection failed with status: {resp.status}")
                        return
        except asyncio.TimeoutError:
            print(f"❌ Connection timeout to {base_url}")
            print("   Ollama may not be running or accessible")
            return
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return

        # Initialize client
        print("🤖 Test 2: Initialize LLM Client")
        print("-" * 60)
        try:
            client = OllamaClient(
                base_url=base_url,
                model=model,
                temperature=0.7,
                max_tokens=500,
                timeout=timeout
            )
            print("✅ LLM Client initialized successfully")
            print()
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return

        # Test 1: Simple greeting
        print("💬 Test 3: Simple Greeting")
        print("-" * 60)
        messages1 = [
            Message(role="system", content="Eres un profesor de música."),
            Message(role="user", content="Hola")
        ]

        try:
            print("Sending: 'Hola'")
            response1 = await client.chat(messages1)
            print(f"✅ SUCCESS")
            print(f"Response length: {len(response1.content)} characters")
            print(f"Response preview:")
            print(f"   {response1.content[:200]}")
            if len(response1.content) > 200:
                print("   ...")
            print()
        except asyncio.TimeoutError:
            print(f"❌ TIMEOUT ERROR: Request took longer than {timeout}s")
            print("   Try increasing OLLAMA_TIMEOUT in docker-compose.yml")
            print()
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print()
            import traceback
            traceback.print_exc()
            return

        # Test 2: Music theory question (the problematic one)
        print("🎵 Test 4: Music Theory Question (Cadencia Conclusiva)")
        print("-" * 60)
        messages2 = [
            Message(role="system", content="Eres un profesor de música experto."),
            Message(role="user", content="¿Puedes hablarme sobre una cadencia conclusiva?")
        ]

        try:
            print("Sending: '¿Puedes hablarme sobre una cadencia conclusiva?'")
            response2 = await client.chat(messages2)
            print(f"✅ SUCCESS")
            print(f"Response length: {len(response2.content)} characters")
            print(f"Full response:")
            print("-" * 60)
            print(response2.content)
            print("-" * 60)
            print()
        except asyncio.TimeoutError:
            print(f"❌ TIMEOUT ERROR: Request took longer than {timeout}s")
            print("   The model may be too slow or overloaded")
            print()
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print()
            import traceback
            traceback.print_exc()

        # Test 3: Extract concepts (pattern parser simulation)
        print("🎼 Test 5: Concept Extraction")
        print("-" * 60)
        message = "puedes hablarme sobre una cadencia conclusiva?"

        # Simulate pattern parser
        music_terms = ["cadencia", "escala", "acorde", "intervalo", "arpegio"]
        found_terms = [term for term in music_terms if term in message.lower()]

        if found_terms:
            print(f"✅ Found music terms: {found_terms}")
        else:
            print("❌ No music terms detected")
        print()

    print("Starting async test...")
    print()
    asyncio.run(test_llm())

    print("=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print("If all tests passed: The LLM client is working correctly")
    print("If connection failed: Check Ollama is running on host")
    print("If timeout: Increase OLLAMA_TIMEOUT or use faster model")
    print("If model error: Ensure 'ollama pull qwen2.5:7b' was run")
    print()

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("The reasoning service may not be properly built")
    print()
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
EOF

echo ""
echo "Test complete!"
echo ""
echo "Next steps based on results:"
echo "- If connection failed: Start Ollama on host (ollama serve)"
echo "- If model not found: Pull model (ollama pull qwen2.5:7b)"
echo "- If timeout: Increase timeout or use lighter model"
echo "- If successful: The issue may be in the REST API layer"
