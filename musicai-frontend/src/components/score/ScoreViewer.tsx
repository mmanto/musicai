import { useEffect, useRef, useState } from 'react'
import { FileMusic, Music } from 'lucide-react'

interface Props {
  content: string
  fileName: string
}

export function ScoreViewer({ content, fileName }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!containerRef.current || !content) return

    const el = containerRef.current
    el.innerHTML = ''
    setError(null)
    setLoading(true)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let osmd: any = null
    let cancelled = false

    import('opensheetmusicdisplay').then(({ OpenSheetMusicDisplay }) => {
      if (cancelled) return
      osmd = new OpenSheetMusicDisplay(el, {
        autoResize: false,
        backend: 'svg',
        drawTitle: true,
        drawComposer: true,
        drawCredits: false,
      })

      osmd
        .load(content)
        .then(() => {
          if (!cancelled) {
            osmd?.render()
            setLoading(false)
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : 'Error al renderizar la partitura')
            setLoading(false)
          }
        })
    })

    return () => {
      cancelled = true
      if (osmd) {
        try { osmd.clear() } catch { /* noop */ }
        osmd = null
      }
      el.innerHTML = ''
    }
  }, [content])

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
      <div className={`flex-1 overflow-auto bg-white ${loading ? 'hidden' : ''}`}>
        <div ref={containerRef} className="min-h-32 px-4 py-2" />
      </div>
    </div>
  )
}
