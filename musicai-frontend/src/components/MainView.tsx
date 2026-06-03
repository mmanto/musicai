import { useMemo } from 'react'
import { Music2, FileMusic } from 'lucide-react'
import { useChatStore } from '../store/chat-store'
import MusicGenerationChat from './MusicGenerationChat'
import { AlphaTabViewer } from './score/AlphaTabViewer'
import { ScoreViewer } from './score/ScoreViewer'
import { MapViewer } from './score/MapViewer'
import { GpMapViewer } from './score/GpMapViewer'
import SplitView from './layout/SplitView'

export default function MainView() {
  const themes = useChatStore((s) => s.themes)
  const selected = useChatStore((s) => s.selected)
  const rightConversation = useChatStore((s) => s.rightConversation)
  const closeChatPanel = useChatStore((s) => s.closeChatPanel)
  const startTheme = useChatStore((s) => s.startTheme)

  const activeTheme = useMemo(
    () => themes.find((t) => t.id === selected?.themeId) ?? null,
    [themes, selected]
  )

  const trackIndex = selected?.type === 'score' ? selected.trackIndex : undefined
  const trackIndexes = useMemo(
    () => (trackIndex !== undefined ? [trackIndex] : undefined),
    [trackIndex]
  )

  // ── Empty state ────────────────────────────────────────────────────────────────

  if (!selected) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center px-8 bg-background">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
          <Music2 size={28} className="text-primary" />
        </div>
        <div>
          <p className="font-semibold text-foreground text-lg">MusicAI</p>
          <p className="text-sm text-muted-foreground mt-2 max-w-sm leading-relaxed">
            Generá música, explorá teoría musical y visualizá partituras.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-center max-w-md">
          {[
            'escala de do mayor',
            'acorde de La menor',
            '¿qué es una escala pentatónica?',
            'arpegio de Sol mayor',
          ].map((s) => (
            <button
              key={s}
              className="text-xs px-3 py-1.5 rounded-full border border-border bg-secondary/50 hover:bg-secondary text-secondary-foreground transition-colors"
              onClick={() => startTheme()}
            >
              {s}
            </button>
          ))}
        </div>
        <p className="text-[0.65rem] text-muted-foreground">
          Creá un tema en el panel lateral para comenzar
        </p>
      </div>
    )
  }

  // ── Score view ─────────────────────────────────────────────────────────────────

  if (selected.type === 'score') {
    const mf = activeTheme?.musicFiles?.find((f) => f.id === selected.fileId)
    const hasRightChat = !!(rightConversation && rightConversation.themeId === selected.themeId)

    const scoreContent = mf?.fileType === 'gp' && mf.gpContent ? (
      <div className="flex-1 flex flex-col overflow-hidden">
        <AlphaTabViewer
          content={mf.gpContent}
          fileName={mf.fileName}
          trackIndexes={trackIndexes}
          startMeasure={selected.startMeasure}
        />
      </div>
    ) : mf?.fileType === 'xml' && mf.content ? (
      <div className="flex-1 flex flex-col overflow-hidden">
        <ScoreViewer content={mf.content} fileName={mf.fileName} />
      </div>
    ) : (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-8 text-muted-foreground">
        <FileMusic className="h-10 w-10 opacity-20" />
        <p className="text-sm">No hay partitura cargada en este tema</p>
        <p className="text-xs opacity-60">
          El contenido del archivo no está disponible. Volvé a cargarlo desde el panel lateral.
        </p>
      </div>
    )

    if (hasRightChat) {
      return (
        <SplitView
          left={scoreContent}
          right={
            <MusicGenerationChat
              themeId={rightConversation!.themeId}
              conversationId={rightConversation!.conversationId}
              onClose={closeChatPanel}
            />
          }
        />
      )
    }

    return scoreContent
  }

  // ── Map view ───────────────────────────────────────────────────────────────────

  if (selected.type === 'map') {
    const mf = activeTheme?.musicFiles?.find((f) => f.id === selected.fileId)
    const hasRightChat = !!(rightConversation && rightConversation.themeId === selected.themeId)

    const mapContent = mf?.fileType === 'gp' && mf.gpContent ? (
      <div className="flex-1 flex flex-col overflow-hidden">
        <GpMapViewer content={mf.gpContent} fileName={mf.fileName} />
      </div>
    ) : mf?.fileType === 'xml' && mf.content ? (
      <div className="flex-1 flex flex-col overflow-hidden">
        <MapViewer content={mf.content} fileName={mf.fileName} />
      </div>
    ) : (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-8 text-muted-foreground">
        <FileMusic className="h-10 w-10 opacity-20" />
        <p className="text-sm">No hay partitura cargada en este tema</p>
      </div>
    )

    if (hasRightChat) {
      return (
        <SplitView
          left={mapContent}
          right={
            <MusicGenerationChat
              themeId={rightConversation!.themeId}
              conversationId={rightConversation!.conversationId}
              onClose={closeChatPanel}
            />
          }
        />
      )
    }

    return mapContent
  }

  // ── Conversation view ──────────────────────────────────────────────────────────

  return <MusicGenerationChat />
}
