import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'musicai-chat-panel-width'
const DEFAULT_WIDTH = 380
const MIN_WIDTH = 260
const MAX_RATIO = 0.65

interface SplitViewProps {
  left: ReactNode
  right: ReactNode
}

export default function SplitView({ left, right }: SplitViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [chatWidth, setChatWidth] = useState<number>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? Number(stored) : DEFAULT_WIDTH
  })
  const dragging = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    startX.current = e.clientX
    startWidth.current = chatWidth
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [chatWidth])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const delta = startX.current - e.clientX
      const containerW = containerRef.current.offsetWidth
      const maxWidth = Math.floor(containerW * MAX_RATIO)
      const next = Math.min(maxWidth, Math.max(MIN_WIDTH, startWidth.current + delta))
      setChatWidth(next)
    }
    const onMouseUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      setChatWidth((w) => {
        localStorage.setItem(STORAGE_KEY, String(w))
        return w
      })
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  return (
    <div ref={containerRef} className="flex-1 flex overflow-hidden">
      {/* Left panel — score/map viewer */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {left}
      </div>

      {/* Drag handle */}
      <div
        className="w-1 shrink-0 bg-border hover:bg-primary/40 cursor-col-resize transition-colors select-none"
        onMouseDown={onMouseDown}
      />

      {/* Right panel — chat */}
      <div
        className="shrink-0 flex flex-col overflow-hidden border-l border-border"
        style={{ width: chatWidth }}
      >
        {right}
      </div>
    </div>
  )
}
