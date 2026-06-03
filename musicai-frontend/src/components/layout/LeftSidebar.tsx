import { useEffect, useRef, useState } from 'react'
import {
  Plus, Trash2, MessageSquare, ChevronDown, ChevronRight, ChevronLeft,
  FolderOpen, FileMusic, X, PanelLeftOpen, Settings, LogOut, User,
  Map, Hash, Music2, Loader2, Link2, AlertCircle,
} from 'lucide-react'
// ChevronRight is used inside the themes list (expand/collapse) — keep it
import { useChatStore } from '../../store/chat-store'
import type { GpSection, GpTrack } from '../../types/chat'
import { uploadScore } from '../../services/api'

// ── GP parsing helpers (ported from music-ui/ConversationSidebar) ──────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildScoreData(score: any): { sections: GpSection[]; tracks: GpTrack[] } {
  const totalMeasures: number = score.masterBars.length
  const rawSections: Array<{ label: string; measure: number }> = []

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const mb of score.masterBars as any[]) {
    if (mb.section) {
      const label: string = mb.section.text || mb.section.marker || `Sección ${mb.index + 1}`
      rawSections.push({ label, measure: mb.index + 1 })
    }
  }

  const seen = new Set<number>()
  const unique = rawSections
    .filter((s) => { if (seen.has(s.measure)) return false; seen.add(s.measure); return true })
    .sort((a, b) => a.measure - b.measure)

  const sections: GpSection[] = unique.map((s, i) => ({
    label: s.label,
    startMeasure: s.measure,
    endMeasure: unique[i + 1] ? unique[i + 1].measure - 1 : totalMeasures,
  }))

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tracks: GpTrack[] = (score.tracks as any[]).map((t: any) => ({
    index: t.index,
    name: t.name || `Pista ${t.index + 1}`,
    shortName: t.shortName || t.name || `P${t.index + 1}`,
  }))

  return { sections, tracks }
}

async function parseGpFile(
  content: ArrayBuffer
): Promise<{ sections: GpSection[]; tracks: GpTrack[]; midiBytes: Uint8Array | null }> {
  const mountEl = document.createElement('div')
  mountEl.style.cssText = 'position:absolute;left:-9999px;top:0;width:600px;height:400px;overflow:hidden;visibility:hidden'
  document.body.appendChild(mountEl)
  try {
    const alphaTab = await import('@coderline/alphatab')
    return await new Promise((resolve) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let api: any = null
      let scoreMeta: { sections: GpSection[]; tracks: GpTrack[] } | null = null
      let midiBytes: Uint8Array | null = null
      let midiDone = false

      function tryResolve() {
        if (scoreMeta && midiDone) {
          resolve({ ...scoreMeta, midiBytes })
          try { api?.destroy() } catch { /* noop */ }
        }
      }

      // Fallback: resolve after 5s even if midiLoad never fires
      const fallbackTimer = setTimeout(() => {
        if (scoreMeta) resolve({ ...scoreMeta, midiBytes })
        else resolve({ sections: [], tracks: [], midiBytes: null })
        try { api?.destroy() } catch { /* noop */ }
      }, 5000)

      try {
        api = new alphaTab.AlphaTabApi(mountEl, {
          core: { fontDirectory: '/alphatab/font/' },
          // enablePlayer: true so midiLoad fires (no audio output without a sound font)
          player: { enablePlayer: true, soundFont: '' },
        })

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        api.midiLoad.on((midiFile: any) => {
          try { midiBytes = midiFile.toBinary() } catch { /* noop */ }
          midiDone = true
          clearTimeout(fallbackTimer)
          tryResolve()
        })

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        api.scoreLoaded.on((score: any) => {
          try { scoreMeta = buildScoreData(score) } catch { scoreMeta = { sections: [], tracks: [] } }
          tryResolve()
        })

        api.error.on(() => {
          clearTimeout(fallbackTimer)
          try { api?.destroy() } catch { /* noop */ }
          resolve({ sections: [], tracks: [], midiBytes: null })
        })

        api.load(content)
      } catch {
        clearTimeout(fallbackTimer)
        try { api?.destroy() } catch { /* noop */ }
        resolve({ sections: [], tracks: [], midiBytes: null })
      }
    })
  } catch {
    return { sections: [], tracks: [], midiBytes: null }
  } finally {
    document.body.removeChild(mountEl)
  }
}

// ── Score upload helpers ────────────────────────────────────────────────────────

type UploadCallbacks = {
  updateScoreId: (scoreId: string) => void
  updateStatus: (status: 'pending' | 'done' | 'error') => void
}

async function uploadXmlScore(
  fileName: string,
  xmlContent: string,
  cb: UploadCallbacks
) {
  cb.updateStatus('pending')
  try {
    const blob = new Blob([xmlContent], { type: 'application/xml' })
    const result = await uploadScore(blob, fileName, 'xml')
    cb.updateScoreId(result.score_id)
    cb.updateStatus('done')
  } catch (err) {
    console.warn('[LeftSidebar] XML score upload failed (non-blocking):', err)
    cb.updateStatus('error')
  }
}

async function uploadGpScore(
  fileName: string,
  midiBytes: Uint8Array | null,
  sections: GpSection[],
  tracks: GpTrack[],
  cb: UploadCallbacks,
  gpFallbackBuffer?: ArrayBuffer,
) {
  cb.updateStatus('pending')
  try {
    let blob: Blob
    let uploadName: string

    if (midiBytes && midiBytes.length > 0) {
      // Preferred path: AlphaTab extracted MIDI → full music21 analysis
      blob = new Blob([midiBytes], { type: 'audio/midi' })
      uploadName = fileName.replace(/\.[^.]+$/, '.mid')
    } else if (gpFallbackBuffer && gpFallbackBuffer.byteLength > 0) {
      // Fallback: send the original GP file so the backend parses it natively
      blob = new Blob([gpFallbackBuffer], { type: 'application/octet-stream' })
      uploadName = fileName          // keep original .gp5/.gp4/etc. extension
    } else {
      throw new Error('No usable data for upload (no MIDI and no GP bytes)')
    }

    const result = await uploadScore(blob, uploadName, 'gp', {
      tracksJson: JSON.stringify(tracks),
      sectionsJson: JSON.stringify(sections),
    })
    cb.updateScoreId(result.score_id)
    cb.updateStatus('done')
  } catch (err) {
    console.warn('[LeftSidebar] GP score upload failed (non-blocking):', err)
    cb.updateStatus('error')
  }
}

// ── Component ──────────────────────────────────────────────────────────────────

interface LeftSidebarProps {
  open: boolean
  onToggle: () => void
}

export default function LeftSidebar({ open, onToggle }: LeftSidebarProps) {
  const themes = useChatStore((s) => s.themes)
  const selected = useChatStore((s) => s.selected)
  const rightConversation = useChatStore((s) => s.rightConversation)
  const startTheme = useChatStore((s) => s.startTheme)
  const renameTheme = useChatStore((s) => s.renameTheme)
  const addMusicFile = useChatStore((s) => s.addMusicFile)
  const removeMusicFile = useChatStore((s) => s.removeMusicFile)
  const setMusicFileSections = useChatStore((s) => s.setMusicFileSections)
  const setMusicFileTracks = useChatStore((s) => s.setMusicFileTracks)
  const updateMusicFileScoreId = useChatStore((s) => s.updateMusicFileScoreId)
  const updateMusicFileUploadStatus = useChatStore((s) => s.updateMusicFileUploadStatus)
  const addConversationToTheme = useChatStore((s) => s.addConversationToTheme)
  const selectConversation = useChatStore((s) => s.selectConversation)
  const selectScore = useChatStore((s) => s.selectScore)
  const selectMap = useChatStore((s) => s.selectMap)
  const deleteThemeStore = useChatStore((s) => s.deleteTheme)
  const deleteConversation = useChatStore((s) => s.deleteConversation)

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [editingThemeId, setEditingThemeId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [addMenuThemeId, setAddMenuThemeId] = useState<string | null>(null)
  const [addMenuPos, setAddMenuPos] = useState<{ top: number; left: number } | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pendingThemeId = useRef<string | null>(null)

  // Close add-menu on outside click
  useEffect(() => {
    if (!addMenuThemeId) return
    const handler = () => { setAddMenuThemeId(null); setAddMenuPos(null) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [addMenuThemeId])

  function toggleTheme(themeId: string) {
    setCollapsed((prev) => ({ ...prev, [themeId]: !prev[themeId] }))
  }

  function startEditing(themeId: string, currentTitle: string) {
    setEditingThemeId(themeId)
    setEditingTitle(currentTitle)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  function commitEdit() {
    if (editingThemeId) {
      const trimmed = editingTitle.trim()
      if (trimmed) renameTheme(editingThemeId, trimmed)
    }
    setEditingThemeId(null)
  }

  function openFilePicker(themeId: string) {
    pendingThemeId.current = themeId
    setAddMenuThemeId(null)
    fileInputRef.current?.click()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    const themeId = pendingThemeId.current
    if (!file || !themeId) return

    const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
    const isGp = ['gp', 'gp3', 'gp4', 'gp5', 'gpx'].includes(ext)

    const reader = new FileReader()
    if (isGp) {
      reader.onload = (ev) => {
        const buffer = ev.target?.result as ArrayBuffer
        const fileId = addMusicFile(themeId, {
          fileName: file.name, fileType: 'gp',
          content: null, gpContent: buffer, gpSections: null, gpTracks: null,
        })
        selectScore(themeId, fileId)
        parseGpFile(buffer.slice(0)).then(({ sections, tracks, midiBytes }) => {
          if (sections.length > 0) setMusicFileSections(themeId, fileId, sections)
          if (tracks.length > 0) setMusicFileTracks(themeId, fileId, tracks)
          uploadGpScore(file.name, midiBytes, sections, tracks, {
            updateScoreId: (id) => updateMusicFileScoreId(themeId, fileId, id),
            updateStatus: (s) => updateMusicFileUploadStatus(themeId, fileId, s),
          }, buffer)
        })
      }
      reader.readAsArrayBuffer(file)
    } else {
      reader.onload = (ev) => {
        const xmlContent = ev.target?.result as string
        const fileId = addMusicFile(themeId, {
          fileName: file.name, fileType: 'xml',
          content: xmlContent, gpContent: null, gpSections: null, gpTracks: null,
        })
        selectScore(themeId, fileId)
        uploadXmlScore(file.name, xmlContent, {
          updateScoreId: (id) => updateMusicFileScoreId(themeId, fileId, id),
          updateStatus: (s) => updateMusicFileUploadStatus(themeId, fileId, s),
        })
      }
      reader.readAsText(file)
    }
    e.target.value = ''
  }

  const scoreActive = (fileId: string) =>
    selected?.type === 'score' && selected.fileId === fileId

  const trackActive = (fileId: string, trackIndex: number) =>
    selected?.type === 'score' && selected.fileId === fileId &&
    (selected as { trackIndex?: number }).trackIndex === trackIndex

  const mapActive = (fileId: string) =>
    selected?.type === 'map' && selected.fileId === fileId

  const convActive = (convId: string) =>
    selected?.type === 'conversation' && selected.conversationId === convId

  const convInPanel = (convId: string) =>
    rightConversation?.conversationId === convId

  // ── Minimized strip ───────────────────────────────────────────────────────────

  if (!open) {
    return (
      <div className="w-9 shrink-0 flex flex-col items-center border-r border-border bg-background pt-3 gap-3">
        <button
          onClick={onToggle}
          title="Abrir panel de temas"
          className="p-1.5 rounded hover:bg-secondary transition-colors"
        >
          <PanelLeftOpen className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>
    )
  }

  // ── Full sidebar ──────────────────────────────────────────────────────────────

  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-border bg-background overflow-hidden">
      <input
        ref={fileInputRef}
        type="file"
        accept=".musicxml,.xml,.gp,.gp3,.gp4,.gp5,.gpx"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Header */}
      <div className="p-3 border-b border-border flex gap-2 shrink-0">
        <button
          className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium border border-border rounded-md px-2 py-1.5 hover:bg-secondary transition-colors"
          onClick={() => startTheme()}
        >
          <Plus className="h-3.5 w-3.5" />
          Nuevo tema
        </button>
        <button
          onClick={onToggle}
          title="Minimizar panel"
          className="p-1.5 rounded border border-border hover:bg-secondary transition-colors"
        >
          <ChevronLeft className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </div>

      {/* Themes list */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
        {themes.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-6 px-3">
            Creá tu primer tema para empezar
          </p>
        )}

        {themes.map((theme) => {
          const isOpen = !collapsed[theme.id]
          const isEditing = editingThemeId === theme.id

          return (
            <div key={theme.id}>
              {/* Theme row */}
              <div className="group flex items-center gap-1 rounded-md px-1.5 py-1.5 hover:bg-secondary/50 transition-colors">
                <button className="shrink-0" onClick={() => !isEditing && toggleTheme(theme.id)}>
                  {isOpen
                    ? <ChevronDown className="h-3 w-3 text-muted-foreground" />
                    : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                </button>
                <FolderOpen className="h-3 w-3 shrink-0 text-muted-foreground" />

                {isEditing ? (
                  <input
                    ref={inputRef}
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitEdit()
                      if (e.key === 'Escape') setEditingThemeId(null)
                    }}
                    className="flex-1 min-w-0 text-xs font-medium bg-background border border-border rounded px-1 py-0 outline-none focus:ring-1 focus:ring-ring"
                  />
                ) : (
                  <span
                    className="flex-1 min-w-0 text-xs font-medium text-foreground truncate cursor-text"
                    onDoubleClick={() => startEditing(theme.id, theme.title)}
                    title="Doble click para editar"
                  >
                    {theme.title}
                  </span>
                )}

                {!isEditing && (
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                      className="p-0.5 rounded hover:text-primary"
                      title="Agregar al tema"
                      onClick={(e) => {
                        e.stopPropagation()
                        if (addMenuThemeId === theme.id) {
                          setAddMenuThemeId(null)
                          setAddMenuPos(null)
                        } else {
                          const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
                          setAddMenuPos({ top: rect.bottom + 4, left: rect.left })
                          setAddMenuThemeId(theme.id)
                        }
                      }}
                    >
                      <Plus className="h-3 w-3" />
                    </button>
                    {addMenuThemeId === theme.id && addMenuPos && (
                      <div
                        className="fixed bg-card border border-border rounded-md shadow-lg z-[200] min-w-[170px] overflow-hidden"
                        style={{ top: addMenuPos.top, left: addMenuPos.left }}
                        onMouseDown={(e) => e.stopPropagation()}
                      >
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-secondary transition-colors text-left"
                          onClick={() => {
                            addConversationToTheme(theme.id)
                            setCollapsed((p) => ({ ...p, [theme.id]: false }))
                            setAddMenuThemeId(null)
                            setAddMenuPos(null)
                          }}
                        >
                          <MessageSquare className="h-3.5 w-3.5" />
                          Nueva conversación
                        </button>
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-secondary transition-colors text-left border-t border-border"
                          onClick={() => {
                            openFilePicker(theme.id)
                            setCollapsed((p) => ({ ...p, [theme.id]: false }))
                            setAddMenuThemeId(null)
                            setAddMenuPos(null)
                          }}
                        >
                          <FileMusic className="h-3.5 w-3.5" />
                          Agregar partitura
                        </button>
                      </div>
                    )}
                    <button
                      onClick={() => deleteThemeStore(theme.id)}
                      className="p-0.5 rounded hover:text-destructive"
                      title="Eliminar tema"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>

              {/* Music files */}
              {isOpen && (theme.musicFiles ?? []).length > 0 && (
                <div className="ml-4 mt-0.5 mb-1 flex flex-col gap-0.5">
                  {(theme.musicFiles ?? []).map((mf) => (
                    <div key={mf.id}>
                      {/* File row */}
                      <div
                        className={`group/file flex items-center gap-1 rounded-md px-2 py-1.5 cursor-pointer transition-colors ${
                          scoreActive(mf.id)
                            ? 'bg-secondary text-secondary-foreground'
                            : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
                        }`}
                        onClick={() => selectScore(theme.id, mf.id)}
                      >
                        <FileMusic className={`h-3 w-3 shrink-0 ${scoreActive(mf.id) ? 'text-primary' : 'text-primary/60'}`} />
                        <span className="flex-1 text-[0.65rem] font-mono truncate">{mf.fileName}</span>
                        {/* Score upload status indicator */}
                        {mf.scoreUploadStatus === 'pending' && (
                          <Loader2 className="h-3 w-3 shrink-0 text-muted-foreground animate-spin" title="Vinculando al chat..." />
                        )}
                        {mf.scoreUploadStatus === 'done' && (
                          <Link2 className="h-3 w-3 shrink-0 text-green-500" title="Partitura vinculada al chat" />
                        )}
                        {mf.scoreUploadStatus === 'error' && (
                          <AlertCircle className="h-3 w-3 shrink-0 text-amber-500" title="No se pudo vincular al backend" />
                        )}
                        <div className="flex items-center gap-0.5 opacity-0 group-hover/file:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => { e.stopPropagation(); selectMap(theme.id, mf.id) }}
                            className={`p-0.5 rounded transition-colors ${mapActive(mf.id) ? 'text-primary' : 'hover:text-primary'}`}
                            title="Ver mapa de estructura"
                          >
                            <Map className="h-3 w-3" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); removeMusicFile(theme.id, mf.id) }}
                            className="p-0.5 rounded hover:text-destructive"
                            title="Quitar partitura"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      </div>

                      {/* GP sections */}
                      {mf.fileType === 'gp' && mf.gpSections && mf.gpSections.length > 0 && (
                        <div className="ml-3 flex flex-col gap-0.5 mb-0.5">
                          {mf.gpSections.map((sec, i) => {
                            const currentTrack = selected?.type === 'score' && selected.fileId === mf.id
                              ? (selected as { trackIndex?: number }).trackIndex
                              : undefined
                            return (
                              <button
                                key={i}
                                className="flex items-center gap-1.5 rounded-md px-2 py-1 text-left hover:bg-secondary/50 transition-colors group/sec"
                                onClick={() => selectScore(theme.id, mf.id, currentTrack, sec.startMeasure)}
                                title={`c.${sec.startMeasure}–${sec.endMeasure}`}
                              >
                                <Hash className="h-2.5 w-2.5 shrink-0 text-muted-foreground/60" />
                                <span className="flex-1 text-xs text-muted-foreground group-hover/sec:text-foreground truncate">{sec.label}</span>
                                <span className="text-[10px] font-mono text-muted-foreground/50 shrink-0">{sec.startMeasure}</span>
                              </button>
                            )
                          })}
                        </div>
                      )}

                      {/* GP tracks */}
                      {mf.fileType === 'gp' && mf.gpTracks && mf.gpTracks.length > 0 && (
                        <div className="ml-3 flex flex-col gap-0.5 mb-0.5">
                          <div className="mx-2 my-1 border-t border-border" />
                          {mf.gpTracks.map((track) => (
                            <div
                              key={track.index}
                              className={`flex items-center gap-1.5 rounded-md px-2 py-1 cursor-pointer transition-colors ${
                                trackActive(mf.id, track.index)
                                  ? 'bg-secondary text-secondary-foreground'
                                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
                              }`}
                              title={track.name}
                              onClick={() => {
                                const currentMeasure = selected?.type === 'score' && selected.fileId === mf.id
                                  ? (selected as { startMeasure?: number }).startMeasure
                                  : undefined
                                selectScore(theme.id, mf.id, track.index, currentMeasure)
                              }}
                            >
                              <Music2 className="h-2.5 w-2.5 shrink-0 text-muted-foreground/60" />
                              <span className="flex-1 text-xs truncate">{track.name}</span>
                              <span className="text-[10px] font-mono text-muted-foreground/40 shrink-0">{track.index + 1}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Conversations */}
              {isOpen && (
                <div className="ml-4 flex flex-col gap-0.5">
                  {theme.conversations.map((conv) => {
                    const isActive = convActive(conv.id)
                    const isInPanel = convInPanel(conv.id)
                    return (
                      <div
                        key={conv.id}
                        className={`group flex items-center gap-1 rounded-md pl-2 pr-1 py-1.5 cursor-pointer transition-colors ${
                          isActive
                            ? 'bg-secondary text-secondary-foreground'
                            : isInPanel
                            ? 'bg-primary/8 text-foreground border border-primary/20'
                            : 'hover:bg-secondary/50 text-muted-foreground hover:text-foreground'
                        }`}
                        onClick={() => selectConversation(theme.id, conv.id)}
                      >
                        <MessageSquare className={`h-3 w-3 shrink-0 ${isInPanel && !isActive ? 'text-primary/60' : 'opacity-60'}`} />
                        <span className="flex-1 text-xs truncate">{conv.title}</span>
                        {isInPanel && !isActive && (
                          <span title="Abierto en panel derecho">
                            <PanelLeftOpen className="h-3 w-3 shrink-0 text-primary/50" />
                          </span>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteConversation(theme.id, conv.id) }}
                          className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-destructive transition-opacity"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* User footer */}
      <div className="border-t border-border p-2 shrink-0 relative">
        <button
          className="w-full flex items-center gap-2.5 rounded-md px-2 py-2 hover:bg-secondary/50 transition-colors text-left"
          onClick={() => setShowUserMenu((v) => !v)}
        >
          <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <User className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground truncate">MusicAI</p>
            <p className="text-[10px] text-muted-foreground truncate">Sesión activa</p>
          </div>
        </button>

        {showUserMenu && (
          <div className="absolute bottom-full left-2 right-2 mb-1 bg-card border border-border rounded-md shadow-lg overflow-hidden z-10">
            <button className="w-full flex items-center gap-2 px-3 py-2.5 text-xs hover:bg-secondary transition-colors text-left">
              <Settings className="h-3.5 w-3.5" />
              Ajustes
            </button>
            <div className="border-t border-border" />
            <button className="w-full flex items-center gap-2 px-3 py-2.5 text-xs hover:bg-secondary transition-colors text-left text-destructive">
              <LogOut className="h-3.5 w-3.5" />
              Cerrar sesión
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
