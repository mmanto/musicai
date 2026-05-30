import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Message, Conversation, Theme, ChatStatus, MusicFile, GpSection, GpTrack } from '../types/chat'

export type SelectedView =
  | { type: 'conversation'; themeId: string; conversationId: string }
  | { type: 'score'; themeId: string; fileId: string; trackIndex?: number; startMeasure?: number }
  | { type: 'map'; themeId: string; fileId: string }
  | null

interface ChatStore {
  themes: Theme[]
  selected: SelectedView
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

  addConversationToTheme: (themeId: string) => void
  selectConversation: (themeId: string, conversationId: string) => void
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
          return { themes, selected: gone ? fallback : s.selected }
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

      addConversationToTheme: (themeId) => {
        const conv = newConversation()
        set((s) => ({
          themes: s.themes.map((t) =>
            t.id !== themeId ? t : { ...t, conversations: [conv, ...t.conversations] }
          ),
          selected: { type: 'conversation', themeId, conversationId: conv.id },
          streamingContent: '',
          status: 'idle',
          error: null,
        }))
      },

      selectConversation: (themeId, conversationId) => {
        set({ selected: { type: 'conversation', themeId, conversationId }, streamingContent: '', status: 'idle', error: null })
      },

      selectScore: (themeId, fileId, trackIndex, startMeasure) => {
        set({ selected: { type: 'score', themeId, fileId, trackIndex, startMeasure } })
      },

      selectMap: (themeId, fileId) => {
        set({ selected: { type: 'map', themeId, fileId } })
      },

      deleteConversation: (themeId, conversationId) => {
        set((s) => {
          const themes = s.themes.map((t) => {
            if (t.id !== themeId) return t
            return { ...t, conversations: t.conversations.filter((c) => c.id !== conversationId) }
          })
          const gone = s.selected?.type === 'conversation' && s.selected.conversationId === conversationId
          const theme = themes.find((t) => t.id === themeId)
          const fallback: SelectedView = (() => {
            if (theme?.conversations[0]) return { type: 'conversation', themeId, conversationId: theme.conversations[0].id }
            const other = themes.find((t) => t.conversations.length > 0)
            if (other) return { type: 'conversation', themeId: other.id, conversationId: other.conversations[0].id }
            return null
          })()
          return { themes, selected: gone ? fallback : s.selected }
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
      partialize: (s) => ({
        themes: s.themes.map((t) => ({
          ...t,
          musicFiles: (t.musicFiles ?? []).map((f) => ({
            ...f,
            content: null,
            gpContent: null,
          })),
        })),
        selected: s.selected,
      }),
    }
  )
)
