import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageSquare, X, Send, Square, Trash2, ChevronRight } from 'lucide-react'

const OLLAMA_MODEL = import.meta.env.VITE_OLLAMA_MODEL ?? 'qwen3-8b'

interface Msg {
  role: 'user' | 'assistant'
  content: string
  id: string
}

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export function OllamaPanel() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [input])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
  }, [])

  const send = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || streaming) return

    const userMsg: Msg = { role: 'user', content: trimmed, id: uid() }
    const assistantId = uid()

    setMessages((prev) => [
      ...prev,
      userMsg,
      { role: 'assistant', content: '', id: assistantId },
    ])
    setInput('')
    setStreaming(true)

    const history = [...messages, userMsg].map(({ role, content }) => ({ role, content }))
    const controller = new AbortController()
    abortRef.current = controller

    try {
      // Calls via Vite proxy (/api/ollama → http://localhost:11434/api/chat)
      const res = await fetch('/api/ollama', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: OLLAMA_MODEL,
          stream: true,
          messages: history,
        }),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let rafId: ReturnType<typeof requestAnimationFrame> | null = null
      let pendingText = ''

      const flush = () => {
        rafId = null
        if (!pendingText) return
        const chunk = pendingText
        pendingText = ''
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + chunk } : m
          )
        )
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          if (!trimmedLine) continue

          let obj: { message?: { content?: string }; done?: boolean; error?: string }
          try { obj = JSON.parse(trimmedLine) } catch { continue }

          if (obj.error) throw new Error(obj.error)

          const text = obj.message?.content
          if (text) {
            pendingText += text
            if (rafId === null) rafId = requestAnimationFrame(flush)
          }
          if (obj.done) break
        }
      }

      if (rafId !== null) cancelAnimationFrame(rafId)
      if (pendingText) {
        const last = pendingText
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + last } : m
          )
        )
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      const msg = err instanceof Error ? err.message : 'Error de conexión'
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `❌ ${msg}` }
            : m
        )
      )
    } finally {
      abortRef.current = null
      setStreaming(false)
    }
  }, [input, streaming, messages])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <>
      {/* Toggle pill */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex flex-col items-center justify-center gap-1 bg-background border border-border border-r-0 rounded-l-lg px-1.5 py-3 shadow-md hover:bg-secondary transition-colors"
          title="Abrir chat IA"
        >
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <ChevronRight className="h-3 w-3 text-muted-foreground rotate-180" />
        </button>
      )}

      {/* Panel */}
      {open && (
        <aside className="fixed right-0 top-12 bottom-0 w-72 z-50 flex flex-col border-l border-border bg-background shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border shrink-0">
            <MessageSquare className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-foreground">IA Chat</p>
              <p className="text-[10px] text-muted-foreground font-mono truncate" title={OLLAMA_MODEL}>
                {OLLAMA_MODEL}
              </p>
            </div>
            <button
              onClick={() => setMessages([])}
              title="Limpiar conversación"
              className="p-1 rounded hover:text-destructive transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
            <button
              onClick={() => setOpen(false)}
              title="Cerrar panel"
              className="p-1 rounded hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
            {messages.length === 0 && (
              <p className="text-xs text-muted-foreground text-center mt-8 px-4 leading-relaxed">
                Iniciá una conversación con <span className="font-mono">{OLLAMA_MODEL}</span>
              </p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap break-words ${
                    msg.role === 'user'
                      ? 'bg-secondary text-secondary-foreground'
                      : 'bg-muted text-foreground'
                  }`}
                >
                  {msg.content || (
                    <span className="inline-flex gap-0.5 items-center">
                      <span className="w-1 h-1 rounded-full bg-current animate-bounce [animation-delay:0ms]" />
                      <span className="w-1 h-1 rounded-full bg-current animate-bounce [animation-delay:150ms]" />
                      <span className="w-1 h-1 rounded-full bg-current animate-bounce [animation-delay:300ms]" />
                    </span>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border p-3 shrink-0">
            <div className="flex gap-2 items-end rounded-lg border border-border bg-background shadow-sm focus-within:ring-1 focus-within:ring-ring px-2.5 py-1.5">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escribí tu mensaje..."
                rows={1}
                disabled={streaming}
                className="flex-1 resize-none bg-transparent text-xs outline-none placeholder:text-muted-foreground disabled:opacity-50 leading-relaxed py-0.5 text-foreground"
              />
              <button
                className="h-7 w-7 shrink-0 rounded-md bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 transition-opacity"
                disabled={!input.trim() && !streaming}
                onClick={streaming ? stop : send}
                title={streaming ? 'Detener' : 'Enviar'}
              >
                {streaming ? <Square className="h-3 w-3" /> : <Send className="h-3 w-3" />}
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground text-center mt-1">
              Enter para enviar · Shift+Enter nueva línea
            </p>
          </div>
        </aside>
      )}
    </>
  )
}
