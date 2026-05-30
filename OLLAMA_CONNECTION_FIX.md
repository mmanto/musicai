# Solución - Reasoning no conectaba a Ollama

## Problema

```
musicai-reasoning | 2026-05-21 11:15:44,978 - src.neural.llm_client - ERROR - Ollama service check failed: [Errno -2] Name or service not known
```

El servicio `reasoning` no podía conectarse a Ollama.

## Causa Raíz

La variable `OLLAMA_BASE_URL` en `.env` estaba configurada a:
```env
OLLAMA_BASE_URL=http://ollama:11434
```

Esto asume que Ollama es un **servicio en la red Docker**, pero en realidad Ollama estaba corriendo en el **host local** en `localhost:11434`.

Cuando un contenedor Docker intenta conectarse a `http://ollama:11434`, busca un servicio llamado `ollama` en la red Docker, lo que falla si Ollama no es un servicio Docker.

## Solución

Cambiar la URL de Ollama a `http://host.docker.internal:11434` en `.env`:

```env
# ANTES
OLLAMA_BASE_URL=http://ollama:11434

# DESPUÉS
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

`host.docker.internal` es un alias especial que Docker proporciona para acceder al host desde un contenedor.

## Cambios Realizados

### 1. **`.env` centralizado** 
Actualizado con URL correcta de Ollama:
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qcwind/qwen3-8b-instruct-Q4-K-M:latest
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT=120
```

### 2. **`reasoning/docker-compose.yml`**
- ✅ Agregadas variables de Ollama explícitamente en `environment:`
- ✅ Actualizado comando de Ollama para usar `${OLLAMA_MODEL}` en lugar de hardcodear `llama3.1:8b`

**Antes:**
```yaml
environment:
  # Ollama vars NO estaban aquí
  
command:
  ollama pull llama3.1:8b  # ❌ Hardcodeado
```

**Después:**
```yaml
environment:
  OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
  OLLAMA_MODEL: ${OLLAMA_MODEL}
  OLLAMA_TEMPERATURE: ${OLLAMA_TEMPERATURE}
  OLLAMA_MAX_TOKENS: ${OLLAMA_MAX_TOKENS}
  OLLAMA_TIMEOUT: ${OLLAMA_TIMEOUT}

command:
  ollama pull ${OLLAMA_MODEL}  # ✅ Usa variable
```

## Verificación

✅ **Servicio Reasoning** ahora se inicia correctamente:
```
2026-05-21 11:17:47,467 - src.neural.llm_client - INFO - Ollama client initialized with model: qcwind/qwen3-8b-instruct-Q4-K-M:latest
2026-05-21 11:17:51,526 - src.neural.llm_client - INFO - Ollama service is healthy
```

✅ **Conectividad con Ollama** confirmada:
```
HTTP Request: GET http://host.docker.internal:11434/api/tags "HTTP/1.1 200 OK"
```

## Opciones de Configuración

### Opción A: Ollama en HOST (Actual ✅)
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```
**Ventajas:**
- Ollama comparte recursos del host
- Configuración centralizada en el host
- Fácil de debuggear localmente

**Cuándo usar:**
- Desarrollo local
- Ollama ya está corriendo en el host

### Opción B: Ollama en Docker
```yaml
ollama:
  image: ollama/ollama:latest
  container_name: musicai-ollama
  ports:
    - "11434:11434"
  environment:
    OLLAMA_BASE_URL=http://ollama:11434
```
**Ventajas:**
- Stack completamente containerizado
- Reproducible en cualquier máquina

**Cuándo usar:**
- Producción
- CI/CD pipelines
- Ambientes aislados

## Archivos Modificados

1. `/home/mmanto/Projects/agileteam-core/musicai/.env`
   - Actualizado `OLLAMA_BASE_URL` a `http://host.docker.internal:11434`

2. `/home/mmanto/Projects/agileteam-core/musicai/reasoning/docker-compose.yml`
   - Agregadas variables de Ollama en `environment:`
   - Actualizado comando para usar `${OLLAMA_MODEL}`
   - Agregado `env_file: ../.env` a servicio ollama

3. `/home/mmanto/Projects/agileteam-core/musicai/docker-compose.yml`
   - Variables de Ollama ya estaban en `environment:` (sin cambios)

## Status Actual

```
musicai-reasoning:
  STATUS: Up 28 seconds (healthy)
  OLLAMA: ✅ Connected to host.docker.internal:11434
  MODEL: ✅ qcwind/qwen3-8b-instruct-Q4-K-M:latest

musicai-chat-backend:
  STATUS: Up 5 minutes (healthy)
```

## Lecciones Aprendidas

1. **`host.docker.internal` es clave** - Para acceder a servicios del host desde Docker
2. **Variables vs Hardcoding** - Mantener configuraciones en variables, no en comandos
3. **Documentar ambiente de ejecución** - Saber dónde corre cada servicio (host vs Docker)
