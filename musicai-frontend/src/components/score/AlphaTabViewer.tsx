import { useEffect, useRef, useState } from 'react'
import { FileMusic, Music, Play, Pause, Square } from 'lucide-react'

interface Props {
  content: ArrayBuffer
  fileName: string
  trackIndexes?: number[]
  startMeasure?: number
}

export function AlphaTabViewer({ content, fileName, trackIndexes, startMeasure }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [progress, setProgress] = useState(0)
  const [trackName, setTrackName] = useState<string | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const apiRef = useRef<any>(null)
  const startMeasureRef = useRef(startMeasure)
  startMeasureRef.current = startMeasure
  // Keep latest trackIndexes accessible without triggering re-init
  const trackIndexesRef = useRef(trackIndexes)
  trackIndexesRef.current = trackIndexes

  // ── Initialize AlphaTab only when file content changes ───────────────────────
  useEffect(() => {
    if (!containerRef.current || !content) return

    const el = containerRef.current
    setError(null)
    setLoading(true)
    setIsPlaying(false)
    setIsReady(false)
    setProgress(0)
    setTrackName(null)

    let cancelled = false

    import('@coderline/alphatab').then((alphaTab) => {
      if (cancelled || !containerRef.current) return

      try {
        const api = new alphaTab.AlphaTabApi(el, {
          core: { fontDirectory: '/alphatab/font/' },
          player: {
            enablePlayer: true,
            enableCursor: true,
            enableAnimatedBeatCursor: true,
            soundFont: 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/soundfont/sonivox.sf2',
          },
        })

        apiRef.current = api

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        api.scoreLoaded.on((score: any) => {
          if (cancelled) return
          setLoading(false)

          // Apply track filter if one is already selected
          const currentIndexes = trackIndexesRef.current
          if (currentIndexes && currentIndexes.length > 0) {
            const tracks = currentIndexes
              .map((i) => score?.tracks?.[i])
              .filter(Boolean)
            if (tracks.length > 0) {
              try { api.renderTracks(tracks) } catch { /* noop */ }
            }
          }

          // Track name display
          const firstIdx = currentIndexes?.[0] ?? 0
          const name: string | undefined = score?.tracks?.[firstIdx]?.name
          setTrackName(name ?? null)

          // Navigate to startMeasure if provided
          const m = startMeasureRef.current
          if (m === undefined || score?.masterBars?.[m - 1] == null) return
          try { api.tickPosition = score.masterBars[m - 1].start } catch { /* noop */ }

          const scrollOnce = () => {
            if (cancelled) return
            api.postRenderFinished.off(scrollOnce)
            requestAnimationFrame(() => {
              const cursor =
                containerRef.current?.querySelector<HTMLElement>('.at-cursor-beat') ??
                containerRef.current?.querySelector<HTMLElement>('.at-cursor-bar')
              cursor?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
            })
          }
          api.postRenderFinished.on(scrollOnce)
        })

        api.playerStateChanged.on((args: { state: number }) => {
          if (cancelled) return
          setIsPlaying(args.state === 1)
          if (args.state !== 1) setProgress(0)
        })

        api.playerPositionChanged.on((args: { currentTime: number; endTime: number }) => {
          if (!cancelled && args.endTime > 0) setProgress(args.currentTime / args.endTime)
        })

        api.soundFontLoaded.on(() => {
          if (!cancelled) setIsReady(true)
        })

        api.error.on((err: Error) => {
          if (!cancelled) {
            setError(err?.message ?? 'Error al cargar el archivo')
            setLoading(false)
          }
        })

        // Load all tracks; renderTracks() handles which ones are visible
        api.load(content.slice(0))
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Error al inicializar AlphaTab')
          setLoading(false)
        }
      }
    }).catch((err: unknown) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : 'Error al cargar AlphaTab')
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
      if (apiRef.current) {
        try { apiRef.current.destroy() } catch { /* noop */ }
        apiRef.current = null
      }
    }
  }, [content]) // ← only re-init when the file itself changes

  // ── Switch tracks without reinitializing the API ─────────────────────────────
  useEffect(() => {
    const api = apiRef.current
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allTracks = (api?.score as any)?.tracks
    if (!allTracks) return

    if (trackIndexes && trackIndexes.length > 0) {
      const tracks = trackIndexes.map((i) => allTracks[i]).filter(Boolean)
      if (tracks.length > 0) {
        try {
          api.renderTracks(tracks)
          setTrackName(allTracks[trackIndexes[0]]?.name ?? null)
        } catch { /* noop */ }
      }
    } else {
      // No specific track — show all
      try {
        api.renderTracks(allTracks)
        setTrackName(null)
      } catch { /* noop */ }
    }
  }, [trackIndexes])

  // ── Navigate to a specific measure and stop playback ────────────────────────
  useEffect(() => {
    const api = apiRef.current
    if (!api?.score) return
    const container = containerRef.current
    if (!container) return

    // Stop playback — cursor must rest at the target position
    try {
      api.stop()
      setIsPlaying(false)
      setProgress(0)
    } catch { /* noop */ }

    if (startMeasure === undefined) {
      try {
        api.tickPosition = 0
        container.scrollTo({ top: 0, left: 0, behavior: 'smooth' })
      } catch { /* noop */ }
      return
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const bar = (api.score as any)?.masterBars?.[startMeasure - 1]
    if (!bar) return
    try { api.tickPosition = bar.start } catch { return }

    let rafId = 0
    let timerId: ReturnType<typeof setTimeout>

    const doScroll = () => {
      // Prefer the beat cursor for precise positioning, fall back to bar cursor
      const cursor =
        container.querySelector<HTMLElement>('.at-cursor-beat') ??
        container.querySelector<HTMLElement>('.at-cursor-bar')
      cursor?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
    }

    // Watch for the cursor DOM update triggered by tickPosition change
    const observer = new MutationObserver((mutations) => {
      const moved = mutations.some((m) => {
        const el = m.target as Element
        return el.classList?.contains('at-cursor-beat') || el.classList?.contains('at-cursor-bar')
      })
      if (!moved) return
      observer.disconnect()
      clearTimeout(timerId)
      rafId = requestAnimationFrame(doScroll)
    })

    observer.observe(container, { attributes: true, subtree: true, attributeFilter: ['style'] })
    // Fallback scroll if mutation never fires (e.g. cursor already at position)
    timerId = setTimeout(() => { observer.disconnect(); doScroll() }, 300)

    return () => {
      observer.disconnect()
      clearTimeout(timerId)
      cancelAnimationFrame(rafId)
    }
  }, [startMeasure])

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-destructive bg-destructive/10 rounded-lg mx-4 my-3">
        <FileMusic className="h-4 w-4 shrink-0" />
        <span>No se pudo renderizar <strong>{fileName}</strong>: {error}</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-0 h-full">
      {!loading && (
        <div className="flex items-center justify-end gap-1 px-3 py-1.5 border-b border-border bg-muted/30 shrink-0">
          {trackName && (
            <span className="text-xs text-muted-foreground/70 mr-auto truncate">{trackName}</span>
          )}
          <button
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-secondary transition-colors disabled:opacity-40"
            disabled={!isReady}
            onClick={() => apiRef.current?.playPause()}
            title={isPlaying ? 'Pausar' : 'Reproducir'}
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>
          <button
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-secondary transition-colors disabled:opacity-40"
            disabled={!isReady}
            onClick={() => apiRef.current?.stop()}
            title="Detener"
          >
            <Square className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {!loading && (
        <div className="h-0.5 bg-muted shrink-0">
          <div
            className="h-full bg-primary transition-[width] duration-100 ease-linear"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center gap-4 py-12 bg-white flex-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Music className="h-5 w-5 animate-pulse" />
            <span className="text-sm">Cargando partitura…</span>
          </div>
          <div className="w-48 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-primary animate-[indeterminate_1.5s_ease-in-out_infinite] w-1/3" />
          </div>
        </div>
      )}

      {/* Container always in DOM — never hidden — so AlphaTab has valid dimensions */}
      <div className={`flex-1 overflow-auto bg-white isolate ${loading ? 'invisible' : ''}`}>
        <div ref={containerRef} />
      </div>
    </div>
  )
}
