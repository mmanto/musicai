import { useEffect, useRef, useState } from 'react'
import { FileMusic, Music, Repeat2, BookOpen } from 'lucide-react'

interface ScorePart { id: number; name: string; shortName: string }
interface Section {
  label: string; startMeasure: number; endMeasure: number
  tempo?: string; repeatStart?: boolean; repeatEnd?: boolean
}
interface ScoreMap {
  title: string; composer: string; artist: string; tempo: number
  parts: ScorePart[]; totalMeasures: number; sections: Section[]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildMapFromScore(score: any): ScoreMap {
  const totalMeasures: number = score.masterBars.length
  const rawSections: Array<{
    label: string; measure: number; tempo?: string; repeatStart?: boolean; repeatEnd?: boolean
  }> = []

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const mb of score.masterBars as any[]) {
    const barNum: number = mb.index + 1
    const tempoAuto = mb.tempoAutomations?.[0]
    const tempoStr = tempoAuto?.value ? `♩= ${Math.round(tempoAuto.value)}` : undefined
    if (mb.section) {
      rawSections.push({
        label: mb.section.text || mb.section.marker || `Sección ${barNum}`,
        measure: barNum, tempo: tempoStr,
        repeatStart: mb.isRepeatStart || false, repeatEnd: mb.isRepeatEnd || false,
      })
    } else if (mb.isRepeatStart || mb.isRepeatEnd) {
      rawSections.push({
        label: `c.${barNum}`, measure: barNum,
        repeatStart: mb.isRepeatStart || false, repeatEnd: mb.isRepeatEnd || false,
      })
    }
  }

  const seen = new Set<number>()
  const unique = rawSections
    .filter((s) => { if (seen.has(s.measure)) return false; seen.add(s.measure); return true })
    .sort((a, b) => a.measure - b.measure)

  const sections: Section[] = unique.map((s, i) => ({
    label: s.label, startMeasure: s.measure,
    endMeasure: unique[i + 1] ? unique[i + 1].measure - 1 : totalMeasures,
    tempo: s.tempo, repeatStart: s.repeatStart, repeatEnd: s.repeatEnd,
  }))

  if (sections.length === 0 && totalMeasures > 0) {
    sections.push({ label: 'Completo', startMeasure: 1, endMeasure: totalMeasures })
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const parts: ScorePart[] = (score.tracks as any[]).map((t) => ({
    id: t.index as number,
    name: (t.name as string) || `Track ${t.index + 1}`,
    shortName: (t.shortName as string) || '',
  }))

  return {
    title: (score.title as string) || 'Sin título',
    composer: (score.music as string) || '',
    artist: (score.artist as string) || '',
    tempo: score.tempo as number,
    parts, totalMeasures, sections,
  }
}

const SECTION_COLORS = [
  'bg-blue-100 border-blue-300 text-blue-800', 'bg-violet-100 border-violet-300 text-violet-800',
  'bg-emerald-100 border-emerald-300 text-emerald-800', 'bg-amber-100 border-amber-300 text-amber-800',
  'bg-rose-100 border-rose-300 text-rose-800', 'bg-cyan-100 border-cyan-300 text-cyan-800',
  'bg-orange-100 border-orange-300 text-orange-800', 'bg-pink-100 border-pink-300 text-pink-800',
]
const SECTION_HUES = [
  'bg-blue-300', 'bg-violet-300', 'bg-emerald-300', 'bg-amber-300',
  'bg-rose-300', 'bg-cyan-300', 'bg-orange-300', 'bg-pink-300',
]
const SECTION_HUES_LIGHT = [
  'bg-blue-200', 'bg-violet-200', 'bg-emerald-200', 'bg-amber-200',
  'bg-rose-200', 'bg-cyan-200', 'bg-orange-200', 'bg-pink-200',
]

interface Props { content: ArrayBuffer; fileName: string }

export function GpMapViewer({ content, fileName }: Props) {
  const hiddenRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<ScoreMap | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hiddenRef.current || !content) return
    let cancelled = false
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let api: any = null

    import('@coderline/alphatab').then((alphaTab) => {
      if (cancelled || !hiddenRef.current) return
      try {
        api = new alphaTab.AlphaTabApi(hiddenRef.current, {
          core: { fontDirectory: '/alphatab/font/' },
          player: { enablePlayer: false },
        })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        api.scoreLoaded.on((score: any) => {
          if (cancelled) return
          try { setMap(buildMapFromScore(score)) }
          catch { setError('No se pudo analizar la estructura del archivo.') }
          setLoading(false)
          try { api?.destroy() } catch { /* noop */ }
          api = null
        })
        api.error.on((err: Error) => {
          if (!cancelled) { setError(err?.message ?? 'Error al analizar'); setLoading(false) }
        })
        api.load(content.slice(0))
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Error al inicializar')
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
      if (api) { try { api.destroy() } catch { /* noop */ }; api = null }
    }
  }, [content])

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-destructive bg-destructive/10 rounded-lg mx-4 my-3">
        <FileMusic className="h-4 w-4 shrink-0" />
        <span>No se pudo analizar <strong>{fileName}</strong>: {error}</span>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto px-6 py-6 relative">
      <div
        ref={hiddenRef}
        style={{ position: 'absolute', left: '-9999px', top: 0, width: '600px', height: '400px', overflow: 'hidden', visibility: 'hidden' }}
      />

      {loading ? (
        <div className="flex items-center justify-center py-24 text-sm text-muted-foreground">
          <Music className="h-4 w-4 animate-pulse mr-2" />Analizando estructura…
        </div>
      ) : !map ? (
        <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
          No se pudo analizar el archivo.
        </div>
      ) : (
        <>
          <div className="mb-6">
            <h1 className="text-xl font-semibold text-foreground">{map.title}</h1>
            {(map.composer || map.artist) && (
              <p className="text-sm text-muted-foreground mt-0.5">{map.composer || map.artist}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Music className="h-3.5 w-3.5" />{map.totalMeasures} compases</span>
              {map.tempo > 0 && <span className="font-mono">♩= {map.tempo}</span>}
              <span className="flex items-center gap-1"><BookOpen className="h-3.5 w-3.5" />{map.parts.length} {map.parts.length === 1 ? 'pista' : 'pistas'}</span>
              <span className="font-mono opacity-60">{fileName}</span>
            </div>
          </div>

          <div className="mb-8">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Estructura</h2>
            <div className="flex flex-wrap gap-2 items-end">
              {map.sections.map((sec, i) => {
                const width = map.totalMeasures > 0
                  ? Math.max(4, Math.round(((sec.endMeasure - sec.startMeasure + 1) / map.totalMeasures) * 100))
                  : 10
                return (
                  <div key={i} className="flex flex-col items-center gap-1" style={{ minWidth: `${Math.max(width, 6)}%` }}>
                    <div className={`w-full rounded-lg border-2 px-3 py-2.5 text-center ${SECTION_COLORS[i % SECTION_COLORS.length]}`}>
                      <div className="flex items-center justify-center gap-1">
                        {sec.repeatStart && <Repeat2 className="h-3 w-3 opacity-60" />}
                        <span className="font-semibold text-sm">{sec.label}</span>
                        {sec.repeatEnd && <Repeat2 className="h-3 w-3 opacity-60 scale-x-[-1]" />}
                      </div>
                      {sec.tempo && <div className="text-xs opacity-70 mt-0.5">{sec.tempo}</div>}
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                      {sec.startMeasure === sec.endMeasure ? `c.${sec.startMeasure}` : `c.${sec.startMeasure}–${sec.endMeasure}`}
                    </span>
                  </div>
                )
              })}
            </div>
            <div className="mt-4 h-2 rounded-full bg-muted overflow-hidden flex">
              {map.sections.map((sec, i) => {
                const pct = map.totalMeasures > 0 ? ((sec.endMeasure - sec.startMeasure + 1) / map.totalMeasures) * 100 : 0
                return (
                  <div key={i} className={`${SECTION_HUES[i % SECTION_HUES.length]} h-full`}
                    style={{ width: `${pct}%` }} title={`${sec.label}: c.${sec.startMeasure}–${sec.endMeasure}`} />
                )
              })}
            </div>
          </div>

          {map.parts.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Pistas / Instrumentos</h2>
              <div className="flex flex-col gap-2">
                {map.parts.map((part, i) => (
                  <div key={part.id} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-6 text-right shrink-0">{i + 1}.</span>
                    <div className="flex-1 flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2">
                      <Music className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span className="text-sm font-medium">{part.name}</span>
                      {part.shortName && part.shortName !== part.name && (
                        <span className="text-xs text-muted-foreground font-mono">({part.shortName})</span>
                      )}
                    </div>
                    <div className="w-32 h-3 rounded-full bg-muted overflow-hidden flex shrink-0">
                      {map.sections.map((sec, si) => {
                        const pct = map.totalMeasures > 0 ? ((sec.endMeasure - sec.startMeasure + 1) / map.totalMeasures) * 100 : 0
                        return <div key={si} className={`${SECTION_HUES_LIGHT[si % SECTION_HUES_LIGHT.length]} h-full`} style={{ width: `${pct}%` }} />
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
