# Configuración Centralizada de Variables de Entorno

## Descripción General

El proyecto MusicAI utiliza un único archivo `.env` en la **raíz del proyecto** para centralizar todas las variables de entorno necesarias. Esto elimina la duplicación y facilita la gestión de configuraciones.

## Estructura

```
musicai/
├── .env                          # Variables centralizadas (COMPARTIDAS POR TODOS)
├── docker-compose.yml            # Stack principal (carga .env)
├── reasoning/
│   ├── docker-compose.yml        # Carga ../.env
│   └── Dockerfile
├── rlhf/
│   ├── docker-compose.yml        # Carga ../.env
│   └── Dockerfile
├── model-base/
│   ├── docker-compose.yml        # Carga ../.env
│   └── Dockerfile
├── preprocessing/
│   ├── docker-compose.yml        # Carga ../.env
│   └── Dockerfile
├── knowledge-graph/
│   ├── docker-compose.yml        # Carga ../.env
│   └── Dockerfile
└── musicai-backend/
    ├── .env                      # (ELIMINADO - usar raíz)
    └── Dockerfile
```

## Funcionamiento

### 1. Archivo `.env` Centralizado

El archivo `.env` en la raíz contiene todas las variables de entorno organizadas por sección:

```env
# OLLAMA - LLM Service
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TEMPERATURE=0.7

# INFRAESTRUCTURA - RABBITMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# INFRAESTRUCTURA - NEO4J
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=musicai_password
```

### 2. Docker-Compose con `env_file`

Cada `docker-compose.yml` **carga automáticamente** el archivo `.env` usando la directiva `env_file`:

#### Desde la Raíz (docker-compose.yml)
```yaml
services:
  reasoning:
    env_file: .env
    environment:
      # Variables específicas del servicio
      SERVICE_NAME: reasoning
      # Variables compartidas (se cargan del .env)
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
      OLLAMA_MODEL: ${OLLAMA_MODEL}
```

#### Desde Subdirectorios (reasoning/docker-compose.yml)
```yaml
services:
  reasoning:
    env_file: ../.env        # Carga desde el padre
    environment:
      SERVICE_NAME: reasoning
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}
      OLLAMA_MODEL: ${OLLAMA_MODEL}
```

### 3. Resolución de Variables

Docker Compose resuelve las variables en este orden:

1. **Variables del `.env`** → Se cargan automáticamente
2. **Variables de `environment`** → Pueden referenciar las del `.env` usando `${VAR_NAME}`
3. **Variables del host** → Si no están definidas en los anteriores

## Variables Compartidas Actuales

### Ollama (LLM)
- `OLLAMA_BASE_URL` - URL del servicio Ollama
- `OLLAMA_MODEL` - Modelo a usar
- `OLLAMA_TEMPERATURE` - Temperatura de generación
- `OLLAMA_MAX_TOKENS` - Tokens máximos
- `OLLAMA_TIMEOUT` - Timeout en segundos

### RabbitMQ (Message Broker)
- `RABBITMQ_HOST` - Host de RabbitMQ
- `RABBITMQ_PORT` - Puerto AMQP
- `RABBITMQ_USER` - Usuario
- `RABBITMQ_PASSWORD` - Contraseña
- `RABBITMQ_VHOST` - Virtual host

### Redis (Cache)
- `REDIS_HOST` - Host de Redis
- `REDIS_PORT` - Puerto de Redis
- `REDIS_DB` - Base de datos por defecto

### Neo4j (Graph Database)
- `NEO4J_URI` - Connection URI (bolt://)
- `NEO4J_USER` - Usuario
- `NEO4J_PASSWORD` - Contraseña
- `NEO4J_DATABASE` - Base de datos
- `NEO4J_dbms_memory_heap_max__size` - Memory heap máximo
- `NEO4J_dbms_memory_pagecache_size` - Page cache size

## Servicios que Usan Variables Centralizadas

| Servicio | Variables del .env |
|----------|-------------------|
| **reasoning** | OLLAMA_*, RABBITMQ_*, NEO4J_* |
| **rlhf** | RABBITMQ_* |
| **model-base** | RABBITMQ_*, REDIS_* |
| **preprocessing** | RABBITMQ_*, REDIS_* |
| **knowledge-graph** | NEO4J_*, RABBITMQ_* |
| **musicai-backend** | OLLAMA_* |
| **musicai-frontend** | VITE_* |

## Modificar Configuración

Para cambiar una variable de entorno:

1. **Editar `/home/mmanto/Projects/agileteam-core/musicai/.env`**
2. **Ejecutar** `docker compose up -d` (cargará automáticamente los cambios)

Ejemplo - Cambiar modelo de Ollama:
```env
# Antes
OLLAMA_MODEL=llama3.1:8b

# Después
OLLAMA_MODEL=llama2:13b
```

Todos los servicios que usan `${OLLAMA_MODEL}` recibirán el nuevo valor.

## Diferencias Entre Servicios

Algunos servicios tienen variables específicas además de las compartidas:

### reasoning/docker-compose.yml
- Variables específicas: `COT_MAX_STEPS`, `MUSIC21_CACHE_DIR`, `QUEUE_REASONING_*`
- Estas se definen directamente en el `environment` del docker-compose

### rlhf/docker-compose.yml
- Variables específicas: `REWARD_MODEL_PATH`, `TRAINING_ALGORITHM`, `LEARNING_RATE`
- Las compartidas (RABBITMQ_*) se cargan del `.env`

## Ciencia Detrás de `env_file`

Docker Compose con `env_file`:

```yaml
env_file: .env              # Carga el archivo
environment:
  VAR1: valor1              # Carga variables específicas
  VAR2: ${VAR1}             # Puede referenciar las del env_file
```

**Ventajas:**
- ✅ Una sola fuente de verdad para variables compartidas
- ✅ Fácil de modificar centralmente
- ✅ No duplicación de valores
- ✅ Compatible con secretos y vault (futuro)

## Próximos Pasos

1. ✅ Centralizar Ollama, RabbitMQ, Redis, Neo4j
2. 🔄 Migrar backends individuales a usar `.env`
3. 🔄 Agregar soporte para `.env.local` (desarrollo local)
4. 🔄 Documentar variables sensibles para producción

## Solución de Problemas

### Las variables no se cargan
- Verificar que `env_file: ../.env` esté al mismo nivel de `services:`
- Ejecutar `docker compose config` para ver la configuración final

### Cambios en .env no se reflejan
- Hacer rebuild: `docker compose up -d --build`
- Remover contenedores y volúmenes: `docker compose down -v`

### Variable no encontrada
- Asegurarse que está definida en `.env`
- Usar `${VARIABLE_NAME}` (con llaves) en docker-compose
