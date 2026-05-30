# Estrategia de Configuración Centralizada - Estado Final

## ✅ Objetivo Completado

Un **único archivo `.env` en la raíz** (`/home/mmanto/Projects/agileteam-core/musicai/.env`) establece todas las variables de entorno necesarias para el proyecto MusicAI.

## 📋 Estructura Actual

```
musicai/
├── .env                          ✅ CENTRALIZADO - Única fuente de verdad
├── docker-compose.yml            ✅ Carga .env (env_file: .env)
├── reasoning/
│   ├── .env                      ℹ️ Heredado (ignorado, mantener para referencia)
│   └── docker-compose.yml        ✅ Carga ../.env
├── rlhf/
│   ├── .env                      ℹ️ Heredado (ignorado)
│   └── docker-compose.yml        ✅ Carga ../.env
├── model-base/
│   ├── .env                      ℹ️ No existe (no necesario)
│   └── docker-compose.yml        ✅ Carga ../.env
├── preprocessing/
│   ├── .env                      ℹ️ No existe (no necesario)
│   └── docker-compose.yml        ✅ Carga ../.env
├── knowledge-graph/
│   ├── .env                      ℹ️ No existe (no necesario)
│   └── docker-compose.yml        ✅ Sin carga especial
├── musicai-backend/
│   ├── .env                      ℹ️ Heredado (ignorado)
│   └── docker-compose.yml        ✅ Carga .env
└── musicai-frontend/
    ├── .env                      ℹ️ Heredado (ignorado)
    └── docker-compose.yml        ✅ Carga .env
```

## 🔧 Variables Centralizadas

El archivo `.env` raíz contiene **todas** las variables compartidas:

### Ollama (LLM)
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qcwind/qwen3-8b-instruct-Q4-K-M:latest
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT=120
```

### RabbitMQ
```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
```

### Redis
```env
REDIS_HOST=redis
REDIS_PORT=6379
```

### Neo4j
```env
NEO4J_USER=neo4j
NEO4J_PASSWORD=musicai_password
NEO4J_HOST=neo4j
NEO4J_URI=bolt://neo4j:7687
```

## 🚀 Cómo Usan los Servicios el `.env`

### Desde docker-compose.yml (Raíz)

```yaml
services:
  reasoning:
    env_file: .env                    # ✅ Carga el archivo
    environment:
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}   # ✅ Referencia la variable
      RABBITMQ_HOST: ${RABBITMQ_HOST}
```

### Desde reasoning/docker-compose.yml (Subdirectorio)

```yaml
services:
  reasoning:
    env_file: ../.env                 # ✅ Carga desde padre
    environment:
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
```

### Variables Específicas del Servicio

```yaml
services:
  reasoning:
    env_file: ../.env                 # Variables globales
    environment:
      SERVICE_NAME: reasoning         # Específico del servicio
      REST_PORT: 8004                 # Específico del servicio
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}  # Del .env
```

## ✅ Funcionalidad Verificada

| Servicio | Status | Ollama | RabbitMQ | Neo4j |
|----------|--------|--------|-----------|-------|
| reasoning | ✅ Healthy | ✅ Conecta | ✅ Conecta | - |
| backend | ✅ Healthy | ✅ Conecta | - | - |
| neo4j | ✅ Healthy | - | - | N/A |
| rabbitmq | ✅ Healthy | - | N/A | - |
| redis | ✅ Healthy | - | - | - |

## 🔄 Modificar Configuración

Para cambiar cualquier variable global:

### 1. Editar `.env` raíz
```bash
vim /home/mmanto/Projects/agileteam-core/musicai/.env
```

### 2. Reiniciar servicios
```bash
docker compose up -d
```

**Ejemplo:** Cambiar modelo de Ollama
```env
# ANTES
OLLAMA_MODEL=qcwind/qwen3-8b-instruct-Q4-K-M:latest

# DESPUÉS
OLLAMA_MODEL=mistral:7b
```

Todos los servicios (`reasoning`, `backend`) usarán automáticamente el nuevo modelo.

## 📝 Archivos de Configuración Heredados

Existen archivos `.env` en subdirectorios que **ya no se usan**:

```
reasoning/.env          ← Heredado, ignorado por docker-compose
rlhf/.env              ← Heredado, ignorado por docker-compose
musicai-backend/.env   ← Heredado, ignorado por docker-compose
musicai-frontend/.env  ← Heredado, ignorado por docker-compose
```

Estos pueden **removerse opcionalmente**:
```bash
rm reasoning/.env rlhf/.env musicai-backend/.env musicai-frontend/.env
```

O mantenerlos como referencia de configuración histórica.

## 🎯 Configuración del Host vs Docker

### Ollama en HOST (Actual ✅)
```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```
- Ollama corre en `localhost:11434`
- Contenedores acceden via `host.docker.internal`
- Comparte recursos del host

### Ollama en Docker (Alternativa)
Para correr Ollama en Docker:
1. Descomenta servicio `ollama` en `docker-compose.yml`
2. Cambia `.env` a:
   ```env
   OLLAMA_BASE_URL=http://ollama:11434
   ```
3. Ejecuta: `docker compose up -d ollama reasoning`

## 📊 Ventajas de Esta Arquitectura

✅ **Una única fuente de verdad** - Variables centralizadas en `.env`
✅ **Sin duplicación** - No repites valores en múltiples archivos
✅ **Fácil de modificar** - Cambia una variable, afecta todos los servicios
✅ **Compatible con CI/CD** - Variables listos para inyectar en producción
✅ **Mantenible** - Estructura clara y documentada
✅ **Escalable** - Agregar nuevos servicios es simple

## 🔐 Seguridad para Producción

Para entornos de producción, considera:

1. **Valores sensibles en secretos, no en `.env`**:
   ```bash
   # En CI/CD o Docker Secret
   echo "musicai_secure_password" | docker secret create neo4j_password -
   ```

2. **Variables en `.env.production`** (no en git):
   ```bash
   docker compose --env-file .env.production up
   ```

3. **Validación de variables**:
   ```bash
   docker compose config  # Muestra configuración final
   ```

## 📚 Documentos Relacionados

- [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md) - Configuración detallada
- [NEO4J_FIX.md](NEO4J_FIX.md) - Solución de problemas Neo4j
- [OLLAMA_CONNECTION_FIX.md](OLLAMA_CONNECTION_FIX.md) - Solución de conectividad Ollama

## ✅ Checklist Final

- ✅ Único `.env` en raíz con todas las variables
- ✅ Todos los docker-compose cargan `.env` (local o padre)
- ✅ Variables referenciadas explícitamente con `${VAR_NAME}`
- ✅ Sin duplicación de configuración
- ✅ Todos los servicios conectan correctamente
- ✅ Documentación actualizada
