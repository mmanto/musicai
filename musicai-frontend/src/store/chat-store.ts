import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { Message, Conversation, Theme, ChatStatus, MusicFile, GpSection, GpTrack } from '../types/chat'

function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i])
  return btoa(binary)
}

function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

// Serializes ArrayBuffer → tagged object so JSON.stringify can handle it,
// and revives it back on load.
const persistStorage = createJSONStorage(() => localStorage, {
  replacer: (_key, value) => {
    if (value instanceof ArrayBuffer) {
      return { __ab__: arrayBufferToBase64(value) }
    }
    return value
  },
  reviver: (_key, value) => {
    if (value && typeof value === 'object' && '__ab__' in (value as object)) {
      return base64ToArrayBuffer((value as { __ab__: string }).__ab__)
    }
    return value
  },
})

export type SelectedView =
  | { type: 'conversation'; themeId: string; conversationId: string }
  | { type: 'score'; themeId: string; fileId: string; trackIndex?: number; startMeasure?: number }
  | { type: 'map'; themeId: string; fileId: string }
  | null

export interface RightConversation {
  themeId: string
  conversationId: string
}

interface ChatStore {
  themes: Theme[]
  selected: SelectedView
  rightConversation: RightConversation | null
  streamingContent: string
  status: ChatStatus
  error: string | null

  currentTheme: () => Theme | null
  currentConversation: () => Conversation | null

  startTheme: () => void
  renameTheme: (themeId: string, title: string) => void
  deleteTheme: (themeId: string) => void

  addMusicFile: (themeId: string, file: Omit<MusicFile, 'id'>) => string
  removeMusicFile: (themeId: string, fileId: string) => void
  setMusicFileSections: (themeId: string, fileId: string, sections: GpSection[]) => void
  setMusicFileTracks: (themeId: string, fileId: string, tracks: GpTrack[]) => void
  updateMusicFileScoreId: (themeId: string, fileId: string, scoreId: string) => void
  updateMusicFileUploadStatus: (themeId: string, fileId: string, status: 'pending' | 'done' | 'error') => void

  addConversationToTheme: (themeId: string) => void
  selectConversation: (themeId: string, conversationId: string) => void
  setRightConversation: (conv: RightConversation | null) => void
  closeChatPanel: () => void
  selectScore: (themeId: string, fileId: string, trackIndex?: number, startMeasure?: number) => void
  selectMap: (themeId: string, fileId: string) => void
  deleteConversation: (themeId: string, conversationId: string) => void

  addMessage: (themeId: string, conversationId: string, message: Message) => void
  appendStream: (chunk: string) => void
  finalizeStream: (themeId: string, conversationId: string, extras?: Partial<Message>) => void
  setStatus: (status: ChatStatus) => void
  setError: (error: string | null) => void
}

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function newConversation(): Conversation {
  return { id: uid(), title: 'Nueva conversación', messages: [], createdAt: Date.now() }
}

function newTheme(index: number): Theme {
  return {
    id: uid(),
    title: `Tema ${index}`,
    musicFiles: [],
    conversations: [],
    createdAt: Date.now(),
  }
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      themes: [],
      selected: null,
      rightConversation: null,
      streamingContent: '',
      status: 'idle',
      error: null,

      currentTheme: () => {
        const { selected, themes } = get()
        if (!selected) return null
        return themes.find((t) => t.id === selected.themeId) ?? null
      },

      currentConversation: () => {
        const { selected, themes } = get()
        if (!selected || selected.type !== 'conversation') return null
        const theme = themes.find((t) => t.id === selected.themeId)
        return theme?.conversations.find((c) => c.id === selected.conversationId) ?? null
      },

      startTheme: () => {
        const { themes } = get()
        const theme = newTheme(themes.length + 1)
        set({ themes: [theme, ...themes], selected: null })
      },

      renameTheme: (themeId, title) => {
        set((s) => ({
          themes: s.themes.map((t) => (t.id === themeId ? { ...t, title } : t)),
        }))
      },

      deleteTheme: (themeId) => {
        set((s) => {
          const themes = s.themes.filter((t) => t.id !== themeId)
          const gone = s.selected?.themeId === themeId
          const fallback: SelectedView = (() => {
            const first = themes.find((t) => t.conversations.length > 0)
            if (first) return { type: 'conversation', themeId: first.id, conversationId: first.conversations[0].id }
            return null
          })()
          const rcGone = s.rightConversation?.themeId === themeId
          return { themes, selected: gone ? fallback : s.selected, rightConversation: rcGone ? null : s.rightConversation }
        })
      },

      addMusicFile: (themeId, file) => {
        const id = uid()
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : { ...t, musicFiles: [...(t.musicFiles ?? []), { ...file, id }] }
          ),
        }))
        return id
      },

      removeMusicFile: (themeId, fileId) => {
        set((s) => {
          const gone =
            (s.selected?.type === 'score' || s.selected?.type === 'map') &&
            s.selected.themeId === themeId &&
            s.selected.fileId === fileId
          const theme = s.themes.find((t) => t.id === themeId)
          const remaining = (theme?.musicFiles ?? []).filter((f) => f.id !== fileId)
          const fallback: SelectedView = remaining[0]
            ? { type: 'score', themeId, fileId: remaining[0].id }
            : theme?.conversations[0]
            ? { type: 'conversation', themeId, conversationId: theme.conversations[0].id }
            : null
          return {
            themes: s.themes.map((t) => (t.id !== themeId ? t : { ...t, musicFiles: remaining })),
            selected: gone ? fallback : s.selected,
          }
        })
      },

      setMusicFileSections: (themeId, fileId, sections) => {
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : {
              ...t,
              musicFiles: (t.musicFiles ?? []).map((f) =>
                f.id !== fileId ? f : { ...f, gpSections: sections }
              ),
            }
          ),
        }))
      },

      setMusicFileTracks: (themeId, fileId, tracks) => {
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : {
              ...t,
              musicFiles: (t.musicFiles ?? []).map((f) =>
                f.id !== fileId ? f : { ...f, gpTracks: tracks }
              ),
            }
          ),
        }))
      },

      updateMusicFileScoreId: (themeId, fileId, scoreId) => {
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : {
              ...t,
              musicFiles: (t.musicFiles ?? []).map((f) =>
                f.id !== fileId ? f : { ...f, scoreId }
              ),
            }
          ),
        }))
      },

      updateMusicFileUploadStatus: (themeId, fileId, status) => {
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : {
              ...t,
              musicFiles: (t.musicFiles ?? []).map((f) =>
                f.id !== fileId ? f : { ...f, scoreUploadStatus: status }
              ),
            }
          ),
        }))
      },

      addConversationToTheme: (themeId) => {
        const conv = newConversation()
        set((s) => {
          const sel = s.selected
          const sameThemeScoreOrMap =
            sel && (sel.type === 'score' || sel.type === 'map') && sel.themeId === themeId
          if (sameThemeScoreOrMap) {
            return {
              themes: s.themes.map((t) =>
                t.id !== themeId ? t : { ...t, conversations: [conv, ...t.conversations] }
              ),
              rightConversation: { themeId, conversationId: conv.id },
              streamingContent: '',
              status: 'idle' as ChatStatus,
              error: null,
            }
          }
          return {
            themes: s.themes.map((t) =>
              t.id !== themeId ? t : { ...t, conversations: [conv, ...t.conversations] }
            ),
            selected: { type: 'conversation' as const, themeId, conversationId: conv.id },
            streamingContent: '',
            status: 'idle' as ChatStatus,
            error: null,
          }
        })
      },

      selectConversation: (themeId, conversationId) => {
        set((s) => {
          const sel = s.selected
          const sameThemeScoreOrMap =
            sel && (sel.type === 'score' || sel.type === 'map') && sel.themeId === themeId
          if (sameThemeScoreOrMap) {
            return { rightConversation: { themeId, conversationId }, streamingContent: '', status: 'idle' as ChatStatus, error: null }
          }
          return { selected: { type: 'conversation' as const, themeId, conversationId }, rightConversation: null, streamingContent: '', status: 'idle' as ChatStatus, error: null }
        })
      },

      setRightConversation: (conv) => set({ rightConversation: conv }),

      closeChatPanel: () => {
        set((s) => {
          const rc = s.rightConversation
          if (!rc) return {}
          // If no score/map is currently selected, restore conversation as full-screen
          const sel = s.selected
          if (!sel || sel.type === 'conversation') {
            return { rightConversation: null, selected: { type: 'conversation' as const, themeId: rc.themeId, conversationId: rc.conversationId } }
          }
          return { rightConversation: null }
        })
      },

      selectScore: (themeId, fileId, trackIndex, startMeasure) => {
        set((s) => {
          const newSelected = { type: 'score' as const, themeId, fileId, trackIndex, startMeasure }

          // navegación dentro del mismo archivo (secciones/pistas) — no tocar rightConversation
          const prev = s.selected
          if (prev?.type === 'score' && prev.themeId === themeId && prev.fileId === fileId) {
            return { selected: newSelected }
          }

          // ya hay panel de chat para este tema — mantenerlo
          if (s.rightConversation?.themeId === themeId) {
            return { selected: newSelected }
          }

          // abrir (o crear) conversación en el panel derecho
          const theme = s.themes.find((t) => t.id === themeId)
          if (!theme) return { selected: newSelected }

          if (theme.conversations.length > 0) {
            return {
              selected: newSelected,
              rightConversation: { themeId, conversationId: theme.conversations[0].id },
            }
          }

          const conv = newConversation()
          return {
            themes: s.themes.map((t) =>
              t.id !== themeId ? t : { ...t, conversations: [conv, ...t.conversations] }
            ),
            selected: newSelected,
            rightConversation: { themeId, conversationId: conv.id },
          }
        })
      },

      selectMap: (themeId, fileId) => {
        set((s) => {
          const newSelected = { type: 'map' as const, themeId, fileId }

          const prev = s.selected
          if (prev?.type === 'map' && prev.themeId === themeId && prev.fileId === fileId) {
            return { selected: newSelected }
          }

          if (s.rightConversation?.themeId === themeId) {
            return { selected: newSelected }
          }

          const theme = s.themes.find((t) => t.id === themeId)
          if (!theme) return { selected: newSelected }

          if (theme.conversations.length > 0) {
            return {
              selected: newSelected,
              rightConversation: { themeId, conversationId: theme.conversations[0].id },
            }
          }

          const conv = newConversation()
          return {
            themes: s.themes.map((t) =>
              t.id !== themeId ? t : { ...t, conversations: [conv, ...t.conversations] }
            ),
            selected: newSelected,
            rightConversation: { themeId, conversationId: conv.id },
          }
        })
      },

      deleteConversation: (themeId, conversationId) => {
        set((s) => {
          const themes = s.themes.map((t) => {
            if (t.id !== themeId) return t
            return { ...t, conversations: t.conversations.filter((c) => c.id !== conversationId) }
          })
          const gone = s.selected?.type === 'conversation' && s.selected.conversationId === conversationId
          const rcGone = s.rightConversation?.conversationId === conversationId && s.rightConversation?.themeId === themeId
          const theme = themes.find((t) => t.id === themeId)
          const fallback: SelectedView = (() => {
            if (theme?.conversations[0]) return { type: 'conversation', themeId, conversationId: theme.conversations[0].id }
            const other = themes.find((t) => t.conversations.length > 0)
            if (other) return { type: 'conversation', themeId: other.id, conversationId: other.conversations[0].id }
            return null
          })()
          return { themes, selected: gone ? fallback : s.selected, rightConversation: rcGone ? null : s.rightConversation }
        })
      },

      addMessage: (themeId, conversationId, message) => {
        set((s) => ({
          themes: s.themes.map((t) => {
            if (t.id !== themeId) return t
            return {
              ...t,
              conversations: t.conversations.map((c) => {
                if (c.id !== conversationId) return c
                const messages = [...c.messages, message]
                const title =
                  c.title === 'Nueva conversación' && message.role === 'user'
                    ? message.content.slice(0, 48)
                    : c.title
                return { ...c, messages, title }
              }),
            }
          }),
        }))
      },

      appendStream: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),

      finalizeStream: (themeId, conversationId, extras) => {
        const { streamingContent } = get()
        if (!streamingContent && !extras?.musicxmlUrl) return
        const message: Message = {
          id: uid(),
          role: 'assistant',
          content: streamingContent,
          timestamp: Date.now(),
          ...extras,
        }
        set((s) => ({
          themes: s.themes.map((t) => {
            if (t.id !== themeId) return t
            return {
              ...t,
              conversations: t.conversations.map((c) =>
                c.id !== conversationId ? c : { ...c, messages: [...c.messages, message] }
              ),
            }
          }),
          streamingContent: '',
          status: 'idle',
        }))
      },

      setStatus: (status) => set({ status }),
      setError: (error) => set({ error, status: 'error' }),
    }),
    {
      name: 'musicai-chat',
      storage: persistStorage,
      partialize: (s) => ({
        themes: s.themes.map((t) => ({
          ...t,
          musicFiles: (t.musicFiles ?? []).map((f) => ({
            ...f,
            gpContent: null, // never persist binary GP data to localStorage (quota risk)
          })),
        })),
        selected: s.selected,
        rightConversation: s.rightConversation,
      }),
    }
  )
)
