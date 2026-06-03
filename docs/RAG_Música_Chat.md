# RAG para Música y Chat — Diseño e Implementación

## Objetivo

Transformar el sistema de chat de MusicAI en un agente que **aprende de forma continua** a partir de dos fuentes:

1. **Archivos de música subidos** (MusicXML, MIDI, GP): cada partitura analizada se vectoriza y persiste en ChromaDB.
2. **Interacciones del chat**: cada turno usuario/asistente se almacena semánticamente para que futuros chats se beneficien de conversaciones anteriores.

El resultado es un ciclo virtuoso donde cuanto más se usa el sistema, más contexto rico tiene disponible para el modelo.

---

## Arquitectura antes vs. después

### Antes

```
Usuario pregunta
    → RAG consulta únicamente: music_theory_kb (estática, JSON)
    → LLM responde
    → La interacción se descarta
```

### Después

```
Usuario sube partitura
    → music21 analiza → ScoreAnalysis
    → ScoreStore.save()             [memoria de sesión, efímera]
    → RAG.add_score()               [ChromaDB music_scores, persistente] ◄ NUEVO

Usuario hace pregunta
    → RAG.get_context_for_query(msg, session_id)
         ├── music_theory        (base estática de teoría)
         ├── music_scores        (análisis de archivos subidos) ◄ NUEVO
         └── chat_interactions   (historial de conversaciones) ◄ NUEVO
    → LLM recibe contexto enriquecido → respuesta mejor
    → RAG.add_interaction()         [persistir Q&A] ◄ NUEVO
```

---

## Colecciones ChromaDB

### `music_theory` (existente, sin cambios)

Base de conocimiento estática cargada desde `music_theory_kb.json`.

| Campo | Descripción |
|---|---|
| `id` | `concept_N` |
| `document` | `título + descripción + ejemplos + conceptos relacionados` |
| `metadata.category` | Categoría: `"scales"`, `"chords"`, `"harmony"`, etc. |
| `metadata.difficulty` | `"beginner"` / `"intermediate"` / `"advanced"` |

### `music_scores` (nueva)

Un documento por cada partitura subida y analizada.

| Campo | Descripción |
|---|---|
| `id` | `score_id` (e.g. `score_abc123`) — seguro para upsert |
| `document` | `context_summary` generado por `ScoreAnalysis.build_summary()` |
| `metadata.key` | Tonalidad, e.g. `"A minor"` |
| `metadata.tempo` | BPM |
| `metadata.file_type` | `"xml"` o `"gp"` |
| `metadata.created_at` | Timestamp ISO 8601 |

**Ejemplo de documento:**
```
Partitura: "Bohemian Rhapsody.gp5"
Tonalidad: B minor
Tempo: 76 BPM
Compás: 4/4
Acordes principales: Bm, G, D, A, F#m
Total de notas: 1243
Secciones: Intro, Verse, Chorus, Solo
Instrumentos/pistas: Guitar 1, Guitar 2, Bass, Drums
```

### `chat_interactions` (nueva)

Un documento por cada turno completado de chat.

| Campo | Descripción |
|---|---|
| `id` | `chat_` + SHA-1(session_id + timestamp + msg_prefix)[:16] |
| `document` | `"Usuario: ...\nAsistente: ..."` |
| `metadata.session_id` | ID de conversación del frontend |
| `metadata.timestamp` | Timestamp ISO 8601 |

---

## Archivos modificados

### `app/infrastructure/knowledge/rag_service.py`

**Cambios principales:**
- Migración de `chromadb.Client(Settings(...))` (API deprecada) a `chromadb.PersistentClient(path=...)`.
- Tres colecciones inicializadas en el constructor: `music_theory`, `music_scores`, `chat_interactions`.
- `get_rag_service()` ahora usa `settings.chroma_persist_directory` (`/app/chromadb_data`) en vez del fallback a `/tmp/`. Esto garantiza que los datos sobrevivan reinicios del contenedor Docker.
- **Métodos nuevos:**
  - `add_score(score_analysis)` — upsert de una partitura analizada.
  - `add_interaction(session_id, user_msg, assistant_response)` — almacena un turno de chat.
  - `search_scores(query)` — búsqueda semántica en partituras.
  - `search_interactions(query, session_id=None)` — búsqueda en historial.
  - `_format_results(results)` — helper de formateo compartido.
- `get_context_for_query(query, n_results, session_id=None)` — ahora agrega resultados de las 3 colecciones en secciones etiquetadas.

### `app/presentation/api/score_routes.py`

Después de `score_store.save(score)`, se llama `get_rag_service().add_score(score)` con un try/except que evita que un fallo de RAG rompa la respuesta al frontend.

### `app/infrastructure/ai/ollama_service.py`

`chat_music_teacher()` y `chat_music_teacher_stream()` reciben el parámetro opcional `session_id: Optional[str] = None`, que se pasa a `get_context_for_query()` para permitir búsqueda de interacciones previas de esa misma sesión.

### `app/presentation/api/generation_routes.py`

- **Helper `_store_interaction(session_id, user_msg, response_text)`** a nivel de módulo: wrappea `get_rag_service().add_interaction()` con manejo de errores no-fatal.
- **Endpoint `/music/chat`**: llama a `_store_interaction()` antes de cada `return ChatResponse(...)` con texto final. Pasa `session_id` a `chat_music_teacher()`.
- **Endpoint `/music/chat/stream`**: al recibir el evento `'done'`, usa `run_in_executor()` para offloadear la escritura a ChromaDB al thread pool sin bloquear el streaming SSE. Pasa `session_id` a `chat_music_teacher_stream()`.

---

## Persistencia Docker

No se requieren cambios en `docker-compose.yml`. El volumen y variable de entorno ya estaban configurados:

```yaml
environment:
  CHROMA_PERSIST_DIRECTORY: /app/chromadb_data
volumes:
  - chat_chromadb:/app/chromadb_data
```

La corrección en `get_rag_service()` hace que ahora este valor sea efectivamente utilizado, permitiendo que las tres colecciones persistan entre reinicios.

---

## Flujo completo de aprendizaje

```
1. Usuario sube "mi_canción.musicxml"
   → music21 analiza tonalidad, tempo, acordes
   → Se guarda en ScoreStore (memoria de sesión)
   → Se vectoriza y persiste en ChromaDB[music_scores]

2. Usuario pregunta "¿qué escala usa la canción que subí?"
   → RAG busca en las 3 colecciones con la pregunta
   → Encuentra la partitura en music_scores
   → LLM recibe: contexto de teoría + descripción de la partitura
   → Responde con información específica del archivo
   → La respuesta se guarda en ChromaDB[chat_interactions]

3. En otra sesión, usuario pregunta algo similar sobre escalas
   → RAG encuentra la interacción anterior como contexto relevante
   → LLM puede referenciar el ejemplo concreto de la canción anterior
```

---

## Diseño de degradación graceful

En todos los puntos de integración con ChromaDB se aplica el patrón:

```python
try:
    get_rag_service().add_score(score)
except Exception as rag_err:
    logger.warning(f"RAG indexing failed (non-fatal): {rag_err}")
```

Si ChromaDB no está disponible (no instalado, ruta no escribible, fallo de inicialización), el sistema continúa operando normalmente — upload, chat y streaming siguen funcionando. Las secciones `PARTITURAS ANALIZADAS RELEVANTES` e `INTERACCIONES PREVIAS RELEVANTES` simplemente no aparecen en el prompt.

---

## Verificación

### Test de integración: upload + chat

```bash
# 1. Subir una partitura
curl -X POST http://localhost:8000/api/v1/music/score/upload \
  -F "file=@mi_cancion.xml" \
  -F "file_name=mi_cancion.xml" \
  -F "file_type=xml"
# → Observar en logs: "Upserted score 'mi_cancion.xml' ... into music_scores"

# 2. Chat sobre la partitura
curl -X POST http://localhost:8000/api/v1/music/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "explica la tonalidad de la pieza", "session_id": "test-session"}'
# → En logs debe aparecer: "PARTITURAS ANALIZADAS RELEVANTES"
```

### Test de memoria de interacciones

```bash
# Hacer 2 preguntas en la misma sesión, luego una tercera similar a la primera
# En logs de la tercera debe aparecer: "INTERACCIONES PREVIAS RELEVANTES"
```

### Test de persistencia

```bash
docker compose restart musicai-backend
# Luego verificar que ChromaDB retiene los documentos:
# GET http://localhost:8000/api/v1/music/score/<score_id_previo>
# (ScoreStore es efímero, pero ChromaDB persiste — el score ya no está en memoria
#  pero sí en el RAG para búsquedas semánticas)
```

### Test de degradación

```bash
# En docker-compose, cambiar CHROMA_PERSIST_DIRECTORY a /root/nonexistent
# Reiniciar y verificar que upload y chat siguen respondiendo 200
```
