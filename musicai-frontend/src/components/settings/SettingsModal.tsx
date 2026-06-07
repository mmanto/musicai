import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  X, Upload, Plus, Trash2, FileText, Loader2, BookOpen,
  ChevronDown, AlertCircle, CheckCircle2,
} from 'lucide-react'
import {
  listKnowledgeDocuments,
  addKnowledgeDocument,
  uploadKnowledgeDocument,
  deleteKnowledgeDocument,
  type KnowledgeDocument,
} from '../../services/api'

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: 'scales',     label: 'Escalas' },
  { value: 'chords',     label: 'Acordes' },
  { value: 'theory',     label: 'Teoría' },
  { value: 'harmony',    label: 'Armonía' },
  { value: 'technique',  label: 'Técnica' },
  { value: 'notation',   label: 'Notación' },
  { value: 'production', label: 'Producción' },
  { value: 'edition',    label: 'Edición' },
  { value: 'general',    label: 'General' },
]

const DIFFICULTIES = [
  { value: 'beginner',     label: 'Principiante' },
  { value: 'intermediate', label: 'Intermedio' },
  { value: 'advanced',     label: 'Avanzado' },
]

const CATEGORY_COLORS: Record<string, string> = {
  scales:     'bg-blue-500/15 text-blue-400 border-blue-500/20',
  chords:     'bg-purple-500/15 text-purple-400 border-purple-500/20',
  theory:     'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  harmony:    'bg-orange-500/15 text-orange-400 border-orange-500/20',
  technique:  'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
  notation:   'bg-slate-500/15 text-slate-400 border-slate-500/20',
  production: 'bg-rose-500/15 text-rose-400 border-rose-500/20',
  edition:    'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
  general:    'bg-muted/50 text-muted-foreground border-border',
}

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner:     'text-emerald-400',
  intermediate: 'text-yellow-400',
  advanced:     'text-rose-400',
}

function categoryLabel(v: string) {
  return CATEGORIES.find((c) => c.value === v)?.label ?? v
}
function difficultyLabel(v: string) {
  return DIFFICULTIES.find((d) => d.value === v)?.label ?? v
}
function sourceLabel(v: string) {
  if (v === 'kb') return 'KB'
  if (v === 'manual') return 'Manual'
  if (v.startsWith('upload:')) return v.split(':')[1].toUpperCase()
  return v
}
function categoryColor(v: string) {
  return CATEGORY_COLORS[v] ?? CATEGORY_COLORS.general
}

// ── Sub-forms ─────────────────────────────────────────────────────────────────

interface UploadFormProps {
  onDone: () => void
  onCancel: () => void
}

function UploadForm({ onDone, onCancel }: UploadFormProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('general')
  const [difficulty, setDifficulty] = useState('intermediate')
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      uploadKnowledgeDocument(file!, { title: title || undefined, category, difficulty }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge-docs'] })
      onDone()
    },
  })

  return (
    <div className="border border-border rounded-lg p-4 bg-muted/30 flex flex-col gap-3">
      <p className="text-xs font-medium text-foreground">Subir archivo</p>

      <div
        className="border-2 border-dashed border-border rounded-lg p-4 text-center cursor-pointer hover:border-primary/50 transition-colors"
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) { setFile(f); setTitle(f.name.replace(/\.[^.]+$/, '')) }
          }}
        />
        {file ? (
          <div className="flex items-center justify-center gap-2 text-sm text-foreground">
            <FileText className="h-4 w-4 text-primary" />
            {file.name}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 text-muted-foreground">
            <Upload className="h-5 w-5" />
            <span className="text-xs">TXT · MD · PDF</span>
          </div>
        )}
      </div>

      <input
        className="w-full text-xs rounded-md border border-border bg-background px-3 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground"
        placeholder="Título del documento"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />

      <div className="flex gap-2">
        <select
          className="flex-1 text-xs rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select
          className="flex-1 text-xs rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground"
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value)}
        >
          {DIFFICULTIES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>
      </div>

      {mutation.isError && (
        <p className="text-xs text-destructive flex items-center gap-1">
          <AlertCircle className="h-3 w-3 shrink-0" />
          {(mutation.error as any)?.response?.data?.detail ?? 'Error al subir el archivo'}
        </p>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 transition-opacity flex items-center justify-center gap-1"
          disabled={!file || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
          Subir
        </button>
        <button
          className="text-xs px-3 py-2 rounded-md border border-border text-muted-foreground hover:bg-secondary transition-colors"
          onClick={onCancel}
          disabled={mutation.isPending}
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

interface ManualFormProps {
  onDone: () => void
  onCancel: () => void
}

function ManualForm({ onDone, onCancel }: ManualFormProps) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [category, setCategory] = useState('general')
  const [difficulty, setDifficulty] = useState('intermediate')
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => addKnowledgeDocument({ title, content, category, difficulty }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge-docs'] })
      onDone()
    },
  })

  return (
    <div className="border border-border rounded-lg p-4 bg-muted/30 flex flex-col gap-3">
      <p className="text-xs font-medium text-foreground">Agregar texto</p>

      <input
        className="w-full text-xs rounded-md border border-border bg-background px-3 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground"
        placeholder="Título *"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        className="w-full text-xs rounded-md border border-border bg-background px-3 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground resize-none min-h-[100px]"
        placeholder="Contenido del documento *"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={5}
      />

      <div className="flex gap-2">
        <select
          className="flex-1 text-xs rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select
          className="flex-1 text-xs rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground"
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value)}
        >
          {DIFFICULTIES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>
      </div>

      {mutation.isError && (
        <p className="text-xs text-destructive flex items-center gap-1">
          <AlertCircle className="h-3 w-3 shrink-0" />
          {(mutation.error as any)?.response?.data?.detail ?? 'Error al guardar'}
        </p>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 transition-opacity flex items-center justify-center gap-1"
          disabled={!title.trim() || !content.trim() || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
          Agregar
        </button>
        <button
          className="text-xs px-3 py-2 rounded-md border border-border text-muted-foreground hover:bg-secondary transition-colors"
          onClick={onCancel}
          disabled={mutation.isPending}
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// ── Document row ──────────────────────────────────────────────────────────────

function DocRow({ doc }: { doc: KnowledgeDocument }) {
  const [expanded, setExpanded] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const qc = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => deleteKnowledgeDocument(doc.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge-docs'] }),
  })

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="flex items-start gap-2 px-3 py-2.5">
        <button
          className="mt-0.5 shrink-0 text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => setExpanded((v) => !v)}
          title={expanded ? 'Colapsar' : 'Ver contenido'}
        >
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`}
          />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${categoryColor(doc.category)}`}>
              {categoryLabel(doc.category)}
            </span>
            <span className="text-xs font-medium text-foreground truncate">{doc.title}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-[10px] ${DIFFICULTY_COLORS[doc.difficulty] ?? 'text-muted-foreground'}`}>
              {difficultyLabel(doc.difficulty)}
            </span>
            <span className="text-[10px] text-muted-foreground/60">·</span>
            <span className="text-[10px] font-mono text-muted-foreground/60">{sourceLabel(doc.source_type)}</span>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-1">
          {confirmDelete ? (
            <>
              <button
                className="text-[10px] px-2 py-1 rounded bg-destructive text-destructive-foreground disabled:opacity-50 flex items-center gap-0.5"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate()}
              >
                {deleteMutation.isPending
                  ? <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  : <CheckCircle2 className="h-2.5 w-2.5" />}
                Eliminar
              </button>
              <button
                className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:bg-secondary"
                onClick={() => setConfirmDelete(false)}
              >
                Cancelar
              </button>
            </>
          ) : (
            <button
              className="p-1 rounded hover:bg-secondary transition-colors text-muted-foreground hover:text-destructive"
              onClick={() => setConfirmDelete(true)}
              title="Eliminar documento"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {expanded && doc.content_preview && (
        <div className="border-t border-border bg-muted/20 px-3 py-2">
          <p className="text-[10px] text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {doc.content_preview}
            {doc.content_preview.length >= 300 && '…'}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────

interface SettingsModalProps {
  onClose: () => void
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
  const [addMode, setAddMode] = useState<'none' | 'upload' | 'manual'>('none')
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('all')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['knowledge-docs'],
    queryFn: listKnowledgeDocuments,
    staleTime: 30_000,
  })

  const docs = (data?.documents ?? []).filter((d) => {
    const matchSearch = !search || d.title.toLowerCase().includes(search.toLowerCase())
    const matchCat = filterCategory === 'all' || d.category === filterCategory
    return matchSearch && matchCat
  })

  return (
    <div
      className="fixed inset-0 z-[500] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="relative w-full max-w-2xl mx-4 bg-background border border-border rounded-xl shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <h2 className="text-sm font-semibold text-foreground">Ajustes</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-secondary transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-5">

          {/* Section title */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Base de conocimiento</h3>
            </div>
            <p className="text-xs text-muted-foreground">
              Documentos de teoría musical, producción y edición que alimentan el contexto del modelo.
            </p>
          </div>

          {/* Add actions */}
          {addMode === 'none' && (
            <div className="flex gap-2">
              <button
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-md border border-border hover:bg-secondary transition-colors"
                onClick={() => setAddMode('upload')}
              >
                <Upload className="h-3.5 w-3.5" />
                Subir archivo
              </button>
              <button
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-md border border-border hover:bg-secondary transition-colors"
                onClick={() => setAddMode('manual')}
              >
                <Plus className="h-3.5 w-3.5" />
                Agregar texto
              </button>
            </div>
          )}

          {addMode === 'upload' && (
            <UploadForm onDone={() => setAddMode('none')} onCancel={() => setAddMode('none')} />
          )}
          {addMode === 'manual' && (
            <ManualForm onDone={() => setAddMode('none')} onCancel={() => setAddMode('none')} />
          )}

          {/* Filters */}
          <div className="flex gap-2">
            <input
              className="flex-1 text-xs rounded-md border border-border bg-background px-3 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground"
              placeholder="Buscar por título…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="text-xs rounded-md border border-border bg-background px-2 py-2 outline-none focus:ring-1 focus:ring-ring text-foreground"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="all">Todas las categorías</option>
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>

          {/* Document list */}
          {isLoading && (
            <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-xs">Cargando documentos…</span>
            </div>
          )}

          {isError && (
            <div className="flex items-center gap-2 text-xs text-destructive py-4">
              <AlertCircle className="h-4 w-4 shrink-0" />
              No se pudo conectar con el backend.
            </div>
          )}

          {!isLoading && !isError && docs.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-8">
              {search || filterCategory !== 'all' ? 'Sin resultados para los filtros aplicados.' : 'No hay documentos cargados.'}
            </p>
          )}

          {!isLoading && !isError && docs.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-[10px] text-muted-foreground">
                {docs.length} documento{docs.length !== 1 ? 's' : ''}
                {data && data.total !== docs.length ? ` de ${data.total}` : ''}
              </p>
              {docs.map((doc) => <DocRow key={doc.id} doc={doc} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
