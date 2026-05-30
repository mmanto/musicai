export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  musicxmlUrl?: string
  midiUrl?: string
  audioUrl?: string
  pieceId?: string
  showSheetMusic?: boolean
  explanationText?: string
  isHybrid?: boolean
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
}

export interface GpSection {
  label: string
  startMeasure: number
  endMeasure: number
}

export interface GpTrack {
  index: number
  name: string
  shortName: string
}

export interface MusicFile {
  id: string
  fileName: string
  fileType: 'xml' | 'gp'
  content: string | null
  gpContent: ArrayBuffer | null
  gpSections: GpSection[] | null
  gpTracks: GpTrack[] | null
}

export interface Theme {
  id: string
  title: string
  musicFiles: MusicFile[]
  conversations: Conversation[]
  createdAt: number
}

export type ChatStatus = 'idle' | 'streaming' | 'error'
