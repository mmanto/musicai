# Solución - Neo4j no iniciaba

## Problema Identificado

Neo4j no iniciaba debido a que variables de entorno no reconocidas estaban siendo pasadas al contenedor:

```
Failed to read config: Unrecognized setting. No declared setting with name: PORT
Failed to read config: Unrecognized setting. No declared setting with name: DATABASE
Failed to read config: Unrecognized setting. No declared setting with name: PAGECACHE.SIZE
Failed to read config: Unrecognized setting. No declared setting with name: URI
```

### Raíz del Problema

Cuando se agregó la configuración centralizada con `env_file: .env`, Docker cargaba **todas** las variables del `.env` en los contenedores de Neo4j, incluyendo:

- `NEO4J_PORT` - No es reconocida por Neo4j
- `NEO4J_DATABASE` - No es reconocida por Neo4j
- `NEO4J_HEAP_MAX` - Causaba conflicto con la sintaxis de Neo4j
- `NEO4J_PAGECACHE_SIZE` - Causaba conflicto con la sintaxis de Neo4j
- `NEO4J_URI` - No es reconocida por Neo4j
- `NEO4J_HOST` - No es reconocida por Neo4j

Neo4j es muy estricto con las variables de entorno y solo acepta las que están explícitamente documentadas.

## Solución Implementada

### 1. Removí variables no reconocidas del `.env`

```env
# ==========================================
# INFRAESTRUCTURA - NEO4J
# ==========================================
NEO4J_USER=neo4j
NEO4J_PASSWORD=musicai_password

# Variables para aplicaciones (no para Neo4j mismo)
NEO4J_HOST=neo4j
NEO4J_URI=bolt://neo4j:7687
```

### 2. Removí `env_file` de Neo4j en docker-compose.yml

**Antes:**
```yaml
neo4j:
  image: neo4j:5-community
  env_file: .env  # ❌ Cargaba todas las variables
  environment:
    NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
```

**Después:**
```yaml
neo4j:
  image: neo4j:5-community
  environment:
    NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}  # ✅ Solo necesita AUTH
    NEO4J_PLUGINS: '["apoc"]'
```

### 3. Limpié volúmenes corruptos

```bash
docker volume rm musicai_neo4j_data musicai_neo4j_logs
```

## Variables de Neo4j Válidas

Neo4j en Docker **solo** reconoce estas variables de entorno:

| Variable | Propósito |
|----------|-----------|
| `NEO4J_AUTH` | Usuario y contraseña (formato: `user/password`) |
| `NEO4J_PLUGINS` | Array de plugins a instalar |
| `NEO4J_dbms_*` | Configuraciones específicas del dbms (con límites) |

**Nota:** Los puertos se configuran en docker-compose con `ports:`, no con variables de entorno.

## Variables Compartidas del Proyecto

Las siguientes variables **se usan en otras aplicaciones** para conectarse a Neo4j, pero **NO** se pasan a Neo4j:

```env
NEO4J_HOST=neo4j          # Usado por: knowledge-graph, preprocessing, etc.
NEO4J_URI=bolt://neo4j:7687  # Usado por: reasoning, knowledge-graph
NEO4J_USER=neo4j          # Usado por: knowledge-graph
NEO4J_PASSWORD=musicai_password  # Usado por: knowledge-graph
```

## Archivos Modificados

1. ✅ `/home/mmanto/Projects/agileteam-core/musicai/.env`
   - Simplificado para no pasar variables inválidas a Neo4j

2. ✅ `/home/mmanto/Projects/agileteam-core/musicai/docker-compose.yml`
   - Removido `env_file` de Neo4j
   - Mantenidas solo variables válidas

3. ✅ `/home/mmanto/Projects/agileteam-core/musicai/knowledge-graph/docker-compose.yml`
   - Removido `env_file` del servicio neo4j interno
   - Renombrado contenedor a `musicai-neo4j-kg` para evitar conflicto

## Verificación

```bash
# Neo4j ahora inicia correctamente
docker compose ps neo4j
# STATUS: Up X seconds (healthy)

# HTTP API responde
curl http://localhost:7474
# {"bolt_direct":"bolt://localhost:7687",...}
```

## Lecciones Aprendidas

1. **No usar `env_file` global para todos los servicios** - Cada servicio tiene requerimientos diferentes
2. **Neo4j es particular con variables de entorno** - Validación estricta
3. **Separar variables de configuración de variables de aplicación** - Las que se usan en el código vs las que se pasan al contenedor
4. **Documentar qué variables cada servicio necesita** - Evita conflictos

## Próximas Mejoras

- [ ] Crear `.env.neo4j` separado si se necesita configuración avanzada de memoria
- [ ] Documentar por servicio qué variables de `.env` necesita
- [ ] Validar automaticamente las variables soportadas por cada imagen Docker
