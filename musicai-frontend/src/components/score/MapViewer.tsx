import { useMemo } from 'react'
import { Music, Repeat2, BookOpen } from 'lucide-react'

interface ScorePart {
  id: string
  name: string
  abbreviation: string
}

interface Section {
  label: string
  startMeasure: number
  endMeasure: number
  tempo?: string
  repeatStart?: boolean
  repeatEnd?: boolean
}

interface ScoreMap {
  title: string
  composer: string
  parts: ScorePart[]
  totalMeasures: number
  sections: Section[]
}

function parseMusicXml(xml: string): ScoreMap {
  const doc = new DOMParser().parseFromString(xml, 'text/xml')
  const text = (selector: string, root: Element | Document = doc) =>
    root.querySelector(selector)?.textContent?.trim() ?? ''

  const title =
    text('work-title') || text('movement-title') || text('credit-words') || 'Sin título'
  const composer =
    text('creator[type="composer"]') || text('identification creator') || ''

  const parts: ScorePart[] = Array.from(doc.querySelectorAll('score-part')).map((p) => ({
    id: p.getAttribute('id') ?? '',
    name: text('part-name', p) || text('instrument-name', p) || (p.getAttribute('id') ?? ''),
    abbreviation: text('part-abbreviation', p) || '',
  }))

  const firstPartId = parts[0]?.id ?? ''
  const partEl = firstPartId
    ? doc.querySelector(`part[id="${firstPartId}"]`)
    : doc.querySelector('part')

  const measureEls = partEl
    ? Array.from(partEl.querySelectorAll('measure'))
    : Array.from(doc.querySelectorAll('measure'))

  const totalMeasures = measureEls.length

  const rawSections: Array<{
    label: string; measure: number; tempo?: string; repeatStart?: boolean; repeatEnd?: boolean
  }> = []
  let globalTempo = ''

  for (const m of measureEls) {
    const num = parseInt(m.getAttribute('number') ?? '0', 10)
    for (const rehearsal of m.querySelectorAll('rehearsal')) {
      rawSections.push({ label: rehearsal.textContent?.trim() ?? '', measure: num })
    }
    for (const words of m.querySelectorAll('direction-type words')) {
      const txt = words.textContent?.trim() ?? ''
      if (!txt) continue
      if (!globalTempo && /\d+/.test(txt) && txt.length < 6) globalTempo = `♩= ${txt}`
      if (txt.length > 2 && txt.length < 30 && !rawSections.some((s) => s.measure === num)) {
        rawSections.push({ label: txt[0].toUpperCase() + txt.slice(1), measure: num })
      }
    }
    const bpm = m.querySelector('per-minute')?.textContent?.trim()
    if (bpm && !globalTempo) globalTempo = `♩= ${bpm}`
    const hasRepeatFwd = m.querySelector('barline repeat[direction="forward"]') !== null
    const hasRepeatBwd = m.querySelector('barline repeat[direction="backward"]') !== null
    if (hasRepeatFwd || hasRepeatBwd) {
      const existing = rawSections.find((s) => s.measure === num)
      if (existing) {
        existing.repeatStart = existing.repeatStart || hasRepeatFwd
        existing.repeatEnd = existing.repeatEnd || hasRepeatBwd
      } else {
        rawSections.push({ label: `c.${num}`, measure: num, repeatStart: hasRepeatFwd, repeatEnd: hasRepeatBwd })
      }
    }
  }

  const seen = new Set<number>()
  const unique = rawSections
    .filter((s) => { if (seen.has(s.measure)) return false; seen.add(s.measure); return true })
    .sort((a, b) => a.measure - b.measure)

  const sections: Section[] = unique.map((s, i) => ({
    label: s.label,
    startMeasure: s.measure,
    endMeasure: unique[i + 1] ? unique[i + 1].measure - 1 : totalMeasures,
    tempo: s.tempo,
    repeatStart: s.repeatStart,
    repeatEnd: s.repeatEnd,
  }))

  if (sections.length === 0 && totalMeasures > 0) {
    sections.push({ label: 'Completo', startMeasure: 1, endMeasure: totalMeasures })
  }

  return { title, composer, parts, totalMeasures, sections }
}

const SECTION_COLORS = [
  'bg-blue-100 border-blue-300 text-blue-800',
  'bg-violet-100 border-violet-300 text-violet-800',
  'bg-emerald-100 border-emerald-300 text-emerald-800',
  'bg-amber-100 border-amber-300 text-amber-800',
  'bg-rose-100 border-rose-300 text-rose-800',
  'bg-cyan-100 border-cyan-300 text-cyan-800',
  'bg-orange-100 border-orange-300 text-orange-800',
  'bg-pink-100 border-pink-300 text-pink-800',
]

const SECTION_HUES = [
  'bg-blue-300', 'bg-violet-300', 'bg-emerald-300', 'bg-amber-300',
  'bg-rose-300', 'bg-cyan-300', 'bg-orange-300', 'bg-pink-300',
]

const SECTION_HUES_LIGHT = [
  'bg-blue-200', 'bg-violet-200', 'bg-emerald-200', 'bg-amber-200',
  'bg-rose-200', 'bg-cyan-200', 'bg-orange-200', 'bg-pink-200',
]

interface Props { content: string; fileName: string }

export function MapViewer({ content, fileName }: Props) {
  const map = useMemo<ScoreMap | null>(() => {
    try { return parseMusicXml(content) } catch { return null }
  }, [content])

  if (!map) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        No se pudo analizar el archivo MusicXML.
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto px-6 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">{map.title}</h1>
        {map.composer && <p className="text-sm text-muted-foreground mt-0.5">{map.composer}</p>}
        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Music className="h-3.5 w-3.5" />{map.totalMeasures} compases
          </span>
          <span className="flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />{map.parts.length} {map.parts.length === 1 ? 'parte' : 'partes'}
          </span>
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
              <div key={i} className={`${SECTION_HUES[i % SECTION_HUES.length]} h-full`} style={{ width: `${pct}%` }}
                title={`${sec.label}: c.${sec.startMeasure}–${sec.endMeasure}`} />
            )
          })}
        </div>
      </div>

      {map.parts.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Partes / Instrumentos</h2>
          <div className="flex flex-col gap-2">
            {map.parts.map((part, i) => (
              <div key={part.id} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-6 text-right shrink-0">{i + 1}.</span>
                <div className="flex-1 flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2">
                  <Music className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="text-sm font-medium">{part.name}</span>
                  {part.abbreviation && part.abbreviation !== part.name && (
                    <span className="text-xs text-muted-foreground font-mono">({part.abbreviation})</span>
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
    </div>
  )
}
