# Estrategia de Testing MusicAI Stack
## Diagnóstico del Problema: "Lo siento, estoy teniendo problemas para procesar tu pregunta"

**Fecha**: 2025-12-25
**Problema**: Al ingresar "puedes hablarme sobre una cadencia conclusiva?" el sistema responde con un mensaje de error.
**Causa Probable**: Error en la comunicación con Ollama o generación de explicación en el Reasoning Service.

---

## 🎯 Análisis del Flujo de Datos

### Flujo Esperado
```
Frontend (5173)
    ↓ HTTP POST
Reasoning Service (8004) /api/v1/chat-teacher
    ↓ Extract concepts → pattern_parser.extract_concepts_for_visualization()
    ↓ Generate explanation → llm_client.chat()
    ↓ Ollama (11434) on host via host.docker.internal
    ↓ Generate visualization (if concepts found)
    ↓ Return hybrid response
Frontend renders response
```

### Punto de Falla Identificado
**Archivo**: `reasoning/src/api/rest/chat_teacher.py:288`
```python
return "Lo siento, hubo un error al generar la explicación. Por favor intenta de nuevo."
```

Este mensaje se activa cuando `_generate_explanation()` falla, lo que indica:
1. Problema de conexión con Ollama
2. Modelo no disponible
3. Timeout en la respuesta
4. Error en el LLM client

---

## 📋 Estrategia de Testing Capa por Capa

### CAPA 1: Infraestructura Base
**Objetivo**: Verificar que todos los servicios de infraestructura estén corriendo y accesibles.

#### Test 1.1: Verificar Estado de Contenedores
```bash
# Listar todos los contenedores
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verificar contenedores específicos
docker ps --filter "name=musicai" --format "table {{.Names}}\t{{.Status}}"
```

**Resultado Esperado**: Todos los contenedores deben estar en estado "Up" (healthy).

**Servicios a Verificar**:
- ✅ musicai-rabbitmq (healthy)
- ✅ musicai-redis (healthy)
- ✅ musicai-neo4j (healthy)
- ✅ musicai-reasoning (healthy)
- ✅ musicai-chat-backend (healthy)
- ✅ musicai-chat-frontend (running)

#### Test 1.2: Verificar Ollama en el Host
```bash
# Verificar si Ollama está corriendo en el host
curl http://localhost:11434/api/tags

# Verificar modelo específico
ollama list | grep "qwen2.5:7b"

# Si no está instalado, instalarlo
ollama pull qwen2.5:7b
```

**Resultado Esperado**:
- Ollama responde con lista de modelos
- El modelo `qwen2.5:7b` aparece en la lista

**Si Falla**:
```bash
# Instalar Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Iniciar servicio
systemctl start ollama
# o
ollama serve

# Descargar modelo
ollama pull qwen2.5:7b
```

#### Test 1.3: Verificar Conectividad desde Contenedor
```bash
# Probar conexión desde el contenedor reasoning
docker exec musicai-reasoning curl -f http://host.docker.internal:11434/api/tags

# Ver logs del reasoning service
docker logs musicai-reasoning --tail 50
```

**Resultado Esperado**: La llamada curl retorna lista de modelos sin error.

**Si Falla**: Verificar que `host.docker.internal` resuelve correctamente:
```bash
# Dentro del contenedor
docker exec musicai-reasoning ping -c 3 host.docker.internal
docker exec musicai-reasoning getent hosts host.docker.internal
```

---

### CAPA 2: Reasoning Service
**Objetivo**: Verificar que el Reasoning Service está funcionando correctamente.

#### Test 2.1: Health Check del Reasoning Service
```bash
# Health check general
curl http://localhost:8004/api/v1/health

# Health check del chat teacher
curl http://localhost:8004/api/v1/chat-teacher/health
```

**Resultado Esperado**:
```json
{
  "status": "healthy",
  "components": {
    "music_analyzer": true,
    "llm_client": true,
    "pattern_parser": true,
    "correction_store": true
  }
}
```

**Si Falla**: Revisar logs:
```bash
docker logs musicai-reasoning --tail 100 --follow
```

#### Test 2.2: Probar Endpoint de Chat Teacher Directamente
```bash
# Test simple sin conceptos musicales
curl -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola",
    "conversation_history": []
  }'

# Test con pregunta de teoría musical
curl -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Qué es una escala mayor?",
    "conversation_history": []
  }'

# Test con la pregunta problemática
curl -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{
    "message": "puedes hablarme sobre una cadencia conclusiva?",
    "conversation_history": []
  }'
```

**Resultado Esperado**:
```json
{
  "type": "text" o "hybrid",
  "explanation": "[texto explicativo]",
  "visualization": null o {...},
  "context_update": {}
}
```

**Si Falla**: Capturar logs en tiempo real:
```bash
# Terminal 1: Ver logs
docker logs musicai-reasoning --follow

# Terminal 2: Hacer request
curl -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{"message": "puedes hablarme sobre una cadencia conclusiva?", "conversation_history": []}'
```

#### Test 2.3: Probar LLM Client Directamente
```bash
# Entrar al contenedor
docker exec -it musicai-reasoning bash

# Ejecutar prueba Python interactiva
python3 << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/app/src')

from neural.llm_client import OllamaClient, Message

async def test_llm():
    client = OllamaClient(
        base_url="http://host.docker.internal:11434",
        model="qwen2.5:7b",
        temperature=0.7,
        max_tokens=500,
        timeout=120
    )

    messages = [
        Message(role="system", content="Eres un profesor de música."),
        Message(role="user", content="¿Qué es una cadencia conclusiva?")
    ]

    try:
        response = await client.chat(messages)
        print("✅ SUCCESS")
        print(f"Response: {response.content[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

asyncio.run(test_llm())
EOF
```

**Resultado Esperado**: Imprime "✅ SUCCESS" con contenido de respuesta.

**Si Falla**:
- Verificar URL de Ollama en variables de entorno
- Verificar timeout
- Verificar que el modelo está disponible

---

### CAPA 3: Backend MusicAI (Opcional)
**Objetivo**: Si el frontend está configurado para usar el backend en lugar del reasoning directo.

#### Test 3.1: Health Check del Backend
```bash
curl http://localhost:8000/health
```

#### Test 3.2: Probar Endpoint de Chat
```bash
curl -X POST http://localhost:8000/api/v1/music/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "puedes hablarme sobre una cadencia conclusiva?",
    "userId": "test-user"
  }'
```

---

### CAPA 4: Frontend
**Objetivo**: Verificar que el frontend está configurado correctamente.

#### Test 4.1: Verificar Variables de Entorno
```bash
# Ver configuración del frontend
docker exec musicai-chat-frontend env | grep VITE

# Revisar archivo .env si existe
cat musicai-frontend/.env
```

**Resultado Esperado**:
```
VITE_USE_REASONING_SERVICE=true
VITE_REASONING_API_URL=http://localhost:8004
VITE_API_BASE_URL=http://localhost:8000
```

#### Test 4.2: Verificar Detección de Preguntas de Teoría
```bash
# Revisar el código de detección
cat musicai-frontend/src/components/MusicGenerationChat.tsx | grep -A 20 "detectTheoryQuestion"
```

#### Test 4.3: Inspeccionar Network Calls en el Navegador
1. Abrir http://localhost:5173
2. Abrir DevTools (F12) → Network tab
3. Enviar mensaje: "puedes hablarme sobre una cadencia conclusiva?"
4. Verificar:
   - ✅ Request URL: `http://localhost:8004/api/v1/chat-teacher`
   - ✅ Status Code: 200
   - ✅ Response Body contiene `explanation`
   - ❌ Si hay error 500, revisar response details

#### Test 4.4: Revisar Console Logs
```
Abrir DevTools → Console
Buscar errores o warnings relacionados con:
- Network errors
- CORS errors
- API response parsing errors
```

---

### CAPA 5: Integración End-to-End
**Objetivo**: Verificar el flujo completo.

#### Test 5.1: Prueba Manual Completa
1. **Abrir Frontend**: http://localhost:5173
2. **Enviar mensaje simple**: "Hola"
   - ✅ Debe responder
3. **Enviar pregunta de teoría**: "¿Qué es una escala mayor?"
   - ✅ Debe responder con explicación
   - ✅ Opcionalmente con visualización
4. **Enviar pregunta problemática**: "puedes hablarme sobre una cadencia conclusiva?"
   - ✅ Debe responder con explicación sobre cadencias
   - ❌ Si da error, capturar mensaje exacto

#### Test 5.2: Verificar Logs de Todos los Servicios
```bash
# Ver logs de todos los servicios relacionados
docker logs musicai-reasoning --tail 50
docker logs musicai-chat-backend --tail 50
docker logs musicai-chat-frontend --tail 50

# Seguir logs en tiempo real
docker-compose logs -f reasoning musicai-backend musicai-frontend
```

---

## 🔧 Scripts de Diagnóstico Automatizado

### Script 1: Diagnóstico Completo
```bash
#!/bin/bash
# test-musicai-stack.sh

echo "=== MusicAI Stack Diagnostic Tool ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function test_section() {
    echo -e "${YELLOW}>>> $1${NC}"
}

function test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

function test_fail() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Docker containers
test_section "Test 1: Docker Containers Status"
if docker ps --filter "name=musicai" --format "{{.Names}}" | grep -q musicai; then
    test_pass "MusicAI containers are running"
    docker ps --filter "name=musicai" --format "table {{.Names}}\t{{.Status}}"
else
    test_fail "No MusicAI containers found"
fi
echo ""

# Test 2: Ollama on host
test_section "Test 2: Ollama Service on Host"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    test_pass "Ollama is running on localhost:11434"

    # Check for model
    if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
        test_pass "Model qwen2.5:7b is installed"
    else
        test_fail "Model qwen2.5:7b is NOT installed"
        echo "   Run: ollama pull qwen2.5:7b"
    fi
else
    test_fail "Ollama is NOT accessible on localhost:11434"
    echo "   Run: ollama serve"
fi
echo ""

# Test 3: Reasoning service health
test_section "Test 3: Reasoning Service Health"
REASONING_HEALTH=$(curl -s http://localhost:8004/api/v1/health 2>/dev/null)
if [ $? -eq 0 ]; then
    test_pass "Reasoning service is responding"
    echo "$REASONING_HEALTH" | jq '.' 2>/dev/null || echo "$REASONING_HEALTH"
else
    test_fail "Reasoning service is NOT responding"
fi
echo ""

# Test 4: Chat teacher health
test_section "Test 4: Chat Teacher Health"
CHAT_HEALTH=$(curl -s http://localhost:8004/api/v1/chat-teacher/health 2>/dev/null)
if [ $? -eq 0 ]; then
    test_pass "Chat teacher endpoint is responding"
    echo "$CHAT_HEALTH" | jq '.' 2>/dev/null || echo "$CHAT_HEALTH"
else
    test_fail "Chat teacher endpoint is NOT responding"
fi
echo ""

# Test 5: Ollama connectivity from container
test_section "Test 5: Ollama Connectivity from Reasoning Container"
if docker exec musicai-reasoning curl -s -f http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then
    test_pass "Reasoning container CAN reach Ollama via host.docker.internal"
else
    test_fail "Reasoning container CANNOT reach Ollama via host.docker.internal"

    # Test host connectivity
    if docker exec musicai-reasoning ping -c 1 host.docker.internal > /dev/null 2>&1; then
        test_pass "host.docker.internal resolves"
    else
        test_fail "host.docker.internal does NOT resolve"
    fi
fi
echo ""

# Test 6: Chat teacher with simple message
test_section "Test 6: Chat Teacher - Simple Message"
SIMPLE_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "conversation_history": []}' 2>/dev/null)

if echo "$SIMPLE_RESPONSE" | grep -q "explanation"; then
    test_pass "Chat teacher responds to simple message"
else
    test_fail "Chat teacher failed to respond"
    echo "Response: $SIMPLE_RESPONSE"
fi
echo ""

# Test 7: Chat teacher with theory question
test_section "Test 7: Chat Teacher - Theory Question (Cadencia Conclusiva)"
THEORY_RESPONSE=$(curl -s -X POST http://localhost:8004/api/v1/chat-teacher \
  -H "Content-Type: application/json" \
  -d '{"message": "puedes hablarme sobre una cadencia conclusiva?", "conversation_history": []}' 2>/dev/null)

if echo "$THEORY_RESPONSE" | grep -q "explanation"; then
    test_pass "Chat teacher responds to theory question"
    echo "Explanation preview:"
    echo "$THEORY_RESPONSE" | jq -r '.explanation' 2>/dev/null | head -n 3
else
    test_fail "Chat teacher failed to respond to theory question"
    echo "Response: $THEORY_RESPONSE"
fi
echo ""

# Test 8: Frontend configuration
test_section "Test 8: Frontend Configuration"
if docker exec musicai-chat-frontend env 2>/dev/null | grep -q "VITE_USE_REASONING_SERVICE=true"; then
    test_pass "Frontend is configured to use reasoning service"
else
    test_fail "Frontend is NOT configured to use reasoning service"
fi
echo ""

# Test 9: Backend health
test_section "Test 9: Backend Health"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    test_pass "Backend is responding"
else
    test_fail "Backend is NOT responding"
fi
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "Next steps if tests failed:"
echo "1. Check Ollama: ollama serve && ollama pull qwen2.5:7b"
echo "2. Check logs: docker logs musicai-reasoning --tail 100"
echo "3. Restart services: docker-compose restart reasoning"
echo "4. Check network: docker exec musicai-reasoning curl http://host.docker.internal:11434/api/tags"
```

### Script 2: Test Interactivo del LLM
```bash
#!/bin/bash
# test-llm-interactive.sh

echo "=== Interactive LLM Test ==="
echo "This script tests the LLM client inside the reasoning container"
echo ""

docker exec -it musicai-reasoning python3 << 'EOF'
import asyncio
import sys
import os
sys.path.insert(0, '/app/src')

from neural.llm_client import OllamaClient, Message

async def test_llm():
    # Get config from environment
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
    model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')

    print(f"Testing LLM Client:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print("")

    client = OllamaClient(
        base_url=base_url,
        model=model,
        temperature=0.7,
        max_tokens=500,
        timeout=120
    )

    # Test 1: Simple greeting
    print("Test 1: Simple greeting")
    messages1 = [
        Message(role="system", content="Eres un profesor de música."),
        Message(role="user", content="Hola")
    ]

    try:
        response1 = await client.chat(messages1)
        print(f"✅ SUCCESS")
        print(f"Response: {response1.content[:150]}...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("")

    # Test 2: Theory question
    print("Test 2: Theory question about cadence")
    messages2 = [
        Message(role="system", content="Eres un profesor de música experto."),
        Message(role="user", content="¿Puedes hablarme sobre una cadencia conclusiva?")
    ]

    try:
        response2 = await client.chat(messages2)
        print(f"✅ SUCCESS")
        print(f"Response: {response2.content[:200]}...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("Starting async test...")
asyncio.run(test_llm())
print("\nTest complete!")
EOF
```

### Script 3: Monitor de Logs en Tiempo Real
```bash
#!/bin/bash
# monitor-logs.sh

echo "=== MusicAI Logs Monitor ==="
echo "Monitoring reasoning, backend, and frontend logs"
echo "Press Ctrl+C to stop"
echo ""

docker-compose logs -f --tail=50 reasoning musicai-backend musicai-frontend
```

---

## 📊 Checklist de Diagnóstico

### ✅ Pre-requisitos
- [ ] Docker y Docker Compose instalados
- [ ] Ollama instalado en el host
- [ ] Modelo qwen2.5:7b descargado
- [ ] Puertos disponibles: 5173, 8000, 8004, 11434

### ✅ Capa 1: Infraestructura
- [ ] Todos los contenedores corriendo (docker ps)
- [ ] Ollama accesible en localhost:11434
- [ ] Modelo qwen2.5:7b instalado
- [ ] host.docker.internal resuelve desde contenedor

### ✅ Capa 2: Reasoning Service
- [ ] Health check: /api/v1/health responde
- [ ] Chat teacher health: /api/v1/chat-teacher/health todos true
- [ ] Endpoint responde a mensaje simple
- [ ] Endpoint responde a pregunta de teoría
- [ ] LLM client puede conectar con Ollama

### ✅ Capa 3: Backend (Opcional)
- [ ] Health check responde
- [ ] Endpoint de chat funciona

### ✅ Capa 4: Frontend
- [ ] VITE_USE_REASONING_SERVICE=true
- [ ] VITE_REASONING_API_URL correcto
- [ ] No hay errores CORS
- [ ] Network calls llegan al endpoint correcto

### ✅ Capa 5: End-to-End
- [ ] Mensaje simple funciona
- [ ] Pregunta de teoría funciona
- [ ] "Cadencia conclusiva" funciona
- [ ] Visualización se genera correctamente

---

## 🐛 Problemas Comunes y Soluciones

### Problema 1: "Lo siento, estoy teniendo problemas para procesar tu pregunta"

**Causa**: Error en `_generate_explanation()` (chat_teacher.py:288)

**Diagnóstico**:
```bash
# Ver logs del reasoning service
docker logs musicai-reasoning --tail 100

# Buscar errores específicos
docker logs musicai-reasoning 2>&1 | grep -i "error\|exception\|timeout"
```

**Soluciones**:
1. **Ollama no accesible**:
   ```bash
   # Verificar Ollama
   curl http://localhost:11434/api/tags

   # Iniciar Ollama si no está corriendo
   ollama serve
   ```

2. **Modelo no instalado**:
   ```bash
   ollama pull qwen2.5:7b
   ```

3. **Problema de conectividad desde contenedor**:
   ```bash
   # Probar desde el contenedor
   docker exec musicai-reasoning curl http://host.docker.internal:11434/api/tags

   # Si falla, verificar extra_hosts en docker-compose.yml
   # Debe tener: extra_hosts: - "host.docker.internal:host-gateway"
   ```

4. **Timeout de Ollama**:
   - Aumentar `OLLAMA_TIMEOUT` en docker-compose.yml
   - Verificar recursos del sistema (RAM, CPU)

### Problema 2: Contenedor reasoning no está healthy

**Diagnóstico**:
```bash
docker ps -a | grep reasoning
docker logs musicai-reasoning
```

**Soluciones**:
```bash
# Reiniciar servicio
docker-compose restart reasoning

# Reconstruir si es necesario
docker-compose up -d --build reasoning
```

### Problema 3: Frontend no detecta pregunta de teoría

**Diagnóstico**:
- Revisar DevTools → Console
- Verificar que el mensaje tiene palabras clave musicales

**Solución**:
- Verificar `detectTheoryQuestion()` en MusicGenerationChat.tsx
- Asegurarse que la pregunta contiene términos como "cadencia", "escala", etc.

### Problema 4: CORS Errors

**Síntoma**: Error en navegador sobre CORS

**Solución**:
```bash
# Verificar configuración CORS en reasoning service
# Verificar que frontend usa http://localhost:8004 (no 127.0.0.1)
```

### Problema 5: "Components not initialized"

**Síntoma**: Error 500 "Chat teacher components not initialized"

**Diagnóstico**:
```bash
curl http://localhost:8004/api/v1/chat-teacher/health
```

**Solución**:
```bash
# Verificar que main.py inicializa componentes correctamente
docker logs musicai-reasoning | grep "initialized"

# Reiniciar servicio
docker-compose restart reasoning
```

---

## 📝 Logging y Debugging

### Habilitar Logging Detallado
```bash
# Modificar docker-compose.yml para reasoning service
environment:
  LOG_LEVEL: debug  # Cambiar de info a debug
```

### Logs Útiles
```bash
# Ver logs en tiempo real
docker logs musicai-reasoning --follow

# Filtrar solo errores
docker logs musicai-reasoning 2>&1 | grep -i error

# Ver últimas 100 líneas
docker logs musicai-reasoning --tail 100

# Guardar logs a archivo
docker logs musicai-reasoning > reasoning_logs.txt 2>&1
```

### Debugging Interactivo
```bash
# Entrar al contenedor
docker exec -it musicai-reasoning bash

# Verificar variables de entorno
env | grep OLLAMA

# Probar conexión manual
curl http://host.docker.internal:11434/api/tags

# Ejecutar código Python
python3
>>> import sys
>>> sys.path.insert(0, '/app/src')
>>> from neural.llm_client import OllamaClient
>>> # ... test code
```

---

## 🚀 Comandos Rápidos de Recuperación

```bash
# Reiniciar solo reasoning service
docker-compose restart reasoning

# Reiniciar todo el stack
docker-compose restart

# Reconstruir reasoning service
docker-compose up -d --build reasoning

# Ver estado de salud
docker ps --format "table {{.Names}}\t{{.Status}}"

# Purgar y reiniciar todo (CUIDADO: elimina datos)
docker-compose down -v
docker-compose up -d --build

# Ver uso de recursos
docker stats musicai-reasoning
```

---

## 📞 Próximos Pasos

Después de ejecutar los tests:

1. **Si todos los tests pasan**: El problema está en el frontend o en la lógica de negocio
2. **Si falla Test 2 (Ollama)**: Instalar/configurar Ollama correctamente
3. **Si falla Test 5 (Conectividad)**: Verificar networking de Docker
4. **Si falla Test 7 (Teoría)**: Revisar pattern parser y LLM client
5. **Si falla intermitentemente**: Problema de timeout o recursos

**Ejecutar primero**:
```bash
# Hacer ejecutables los scripts
chmod +x test-musicai-stack.sh test-llm-interactive.sh monitor-logs.sh

# Ejecutar diagnóstico completo
./test-musicai-stack.sh

# Si hay problemas con LLM, ejecutar test interactivo
./test-llm-interactive.sh

# Monitorear logs mientras pruebas manualmente
./monitor-logs.sh
```

---

## 📚 Referencias

- **Arquitectura**: Ver documentación de exploración (Agent a270182)
- **Código clave**: `reasoning/src/api/rest/chat_teacher.py`
- **Configuración**: `docker-compose.yml`, `.env`
- **Frontend**: `musicai-frontend/src/components/MusicGenerationChat.tsx`
