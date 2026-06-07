import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Music2, User, X } from 'lucide-react';
import {
  generateMusic,
  generatePattern,
  getJobStatus,
  chatWithTeacher,
  chatWithTeacherStream,
  processMessage,
  type MusicGenerationRequest,
  type PatternGenerationRequest,
  type JobStatus,
  type ChatRequest,
  type ProcessResponse,
} from '../services/api';
import {
  chatWithReasoningTeacher,
  submitCorrection,
  type ChatTeacherRequest,
  type CorrectionRequest,
} from '../services/reasoningApi';
import { useChatStore } from '../store/chat-store';
import type { Message } from '../types/chat';
import SheetMusicViewer from './sheet-music/SheetMusicViewer';
import MusicAwareText from './MusicAwareText';
import './sheet-music/sheet-music.css';
import './InlineNotation.css';

const USE_REASONING_SERVICE =
  import.meta.env.VITE_USE_REASONING_SERVICE === 'true' || false;

// Derive a short display name from the raw model string, e.g.
// "qcwind/qwen3-8b-instruct-Q4-K-M:latest" → "qwen3-8b"
function deriveModelShortName(raw: string | undefined): string {
  if (!raw) return 'IA'
  const withoutTag = raw.split(':')[0]
  const name = withoutTag.split('/').pop() ?? withoutTag
  return name.replace(/-instruct.*$/i, '').replace(/-chat.*$/i, '')
}

const MODEL_SHORT_NAME = deriveModelShortName(import.meta.env.VITE_OLLAMA_MODEL as string | undefined)

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

const GREETING: Message = {
  id: 'greeting',
  role: 'assistant',
  content:
    '¡Hola! Soy MusicAI. Puedo ayudarte de dos formas:\n\n' +
    '🎼 **Patrones musicales exactos** (RECOMENDADO para teoría musical):\n' +
    '   • "escala de do mayor"\n' +
    '   • "acorde de La menor"\n' +
    '   • "arpegio de Sol mayor"\n\n' +
    '🎵 **Música creativa con IA** (experimental, resultados variables):\n' +
    '   • Sé MUY específico: instrumentos, ritmo, melodía, tempo\n\n' +
    '💬 **Preguntas sobre teoría musical**:\n' +
    '   • "¿Qué es una escala pentatónica?"\n' +
    '   • "Esa escala debe comenzar con la tónica en la"\n\n' +
    '¿Qué te gustaría crear?',
  timestamp: 0,
};

interface Props {
  themeId?: string
  conversationId?: string
  onClose?: () => void
}

// Stable empty array to avoid new reference on every render in Zustand selectors
const EMPTY_MESSAGES: Message[] = [];

export default function MusicGenerationChat({ themeId: propThemeId, conversationId: propConversationId, onClose }: Props = {}) {
  const selected = useChatStore((s) => s.selected);
  const themeId = propThemeId ?? selected?.themeId ?? '';
  const conversationId = propConversationId ?? (selected?.type === 'conversation' ? selected.conversationId : '');

  const storedMessages = useChatStore((s) => {
    // Use prop values when in panel mode (avoids relying on selected.type)
    const tid = propThemeId ?? (s.selected?.themeId ?? '');
    const cid = propConversationId ?? (s.selected?.type === 'conversation' ? s.selected.conversationId : '');
    if (!tid || !cid) return EMPTY_MESSAGES;
    const theme = s.themes.find((t) => t.id === tid);
    return theme?.conversations.find((c) => c.id === cid)?.messages ?? EMPTY_MESSAGES;
  });

  const streamingContent = useChatStore((s) => s.streamingContent);
  const storeAddMessage = useChatStore((s) => s.addMessage);
  const storeAppendStream = useChatStore((s) => s.appendStream);
  const storeFinalizeStream = useChatStore((s) => s.finalizeStream);

  // Use conversation ID as backend session ID
  const sessionId = conversationId;

  // Derive the active score_id: prefer currently viewed score file, fallback to last uploaded
  const activeScoreId = useChatStore((s) => {
    // When in panel mode the main view is the score — use it directly
    const tid = propThemeId ?? s.selected?.themeId;
    const theme = s.themes.find((t) => t.id === tid);
    if (!theme) return null;
    const files = theme.musicFiles ?? [];
    if (s.selected?.type === 'score' && s.selected.themeId === tid) {
      const viewed = files.find((f) => f.id === (s.selected as { fileId: string }).fileId);
      if (viewed?.scoreId) return viewed.scoreId;
    }
    for (let i = files.length - 1; i >= 0; i--) {
      if (files[i].scoreId) return files[i].scoreId;
    }
    return null;
  });

  const activeFileName = useChatStore((s) => {
    const tid = propThemeId ?? s.selected?.themeId;
    const theme = s.themes.find((t) => t.id === tid);
    if (!theme) return null;
    const files = theme.musicFiles ?? [];
    if (s.selected?.type === 'score' && s.selected.themeId === tid) {
      const viewed = files.find((f) => f.id === (s.selected as { fileId: string }).fileId);
      if (viewed) return viewed.fileName;
    }
    for (let i = files.length - 1; i >= 0; i--) {
      if (files[i].scoreId) return files[i].fileName;
    }
    return null;
  });

  // Messages displayed = greeting (if empty) + stored + live streaming
  const messages: Message[] =
    storedMessages.length === 0 ? [GREETING] : storedMessages;

  const [input, setInput] = useState('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [sessionContext, setSessionContext] = useState<Record<string, unknown> | null>(null);
  const [correctingMessageId, setCorrectingMessageId] = useState<string | null>(null);
  const [correctionText, setCorrectionText] = useState('');
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingMusicData, setPendingMusicData] = useState<Partial<Message> | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [storedMessages, streamingContent]);

  useEffect(() => {
    if (!correctingMessageId) inputRef.current?.focus();
  }, [storedMessages, correctingMessageId]);

  // Reset local state when conversation changes
  useEffect(() => {
    setInput('');
    setActiveJobId(null);
    setSessionContext(null);
    setCorrectingMessageId(null);
    setCorrectionText('');
    setIsStreaming(false);
    setPendingMusicData(null);
  }, [conversationId]);

  const { data: jobStatus } = useQuery<JobStatus>({
    queryKey: ['jobStatus', activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: activeJobId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.status === 'completed' || data.status === 'failed') return false;
      return 2000;
    },
  });

  useEffect(() => {
    if (!jobStatus || !activeJobId) return;
    if (jobStatus.status === 'completed' && jobStatus.piece_id) {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const abs = (url?: string) =>
        url ? (url.startsWith('http') ? url : `${baseUrl}${url}`) : undefined;
      const musicData: Partial<Message> = {
        musicxmlUrl: abs((jobStatus as any).musicxml_url),
        midiUrl: abs((jobStatus as any).midi_url),
        audioUrl: abs(jobStatus.audio_url),
        pieceId: jobStatus.piece_id,
        showSheetMusic: !!(jobStatus as any).midi_url || !!(jobStatus as any).musicxml_url,
      };
      // If there's a pending hybrid message (streaming already finalized), add it
      // If streaming is done, attach to the last message via a system-level update
      // For simplicity: add as a standalone assistant message
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        ...musicData,
      });
      setActiveJobId(null);
    } else if (jobStatus.status === 'failed') {
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'system',
        content: `❌ Error al generar la música: ${jobStatus.error || 'Error desconocido'}`,
        timestamp: Date.now(),
      });
      setActiveJobId(null);
    }
  }, [jobStatus, activeJobId, themeId, conversationId, storeAddMessage]);

  const generateMutation = useMutation({
    mutationFn: (request: MusicGenerationRequest) => generateMusic(request),
    onSuccess: (data) => setActiveJobId(data.job_id),
    onError: (error: any) => {
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'system',
        content: `❌ Error: ${error.response?.data?.detail || error.message}`,
        timestamp: Date.now(),
      });
    },
  });

  const patternMutation = useMutation({
    mutationFn: (request: PatternGenerationRequest) => generatePattern(request),
    onSuccess: (data) => setActiveJobId(data.job_id),
    onError: (error: any) => {
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'system',
        content: `❌ Error: ${error.response?.data?.detail || error.message}`,
        timestamp: Date.now(),
      });
    },
  });

  const chatMutation = useMutation({
    mutationFn: async (request: ChatRequest | ChatTeacherRequest) => {
      if (USE_REASONING_SERVICE) {
        const reasoningRequest: ChatTeacherRequest = {
          message: request.message,
          conversation_history:
            'conversation_history' in request
              ? (request.conversation_history ?? [])
              : storedMessages
                  .filter((m) => m.role !== 'system')
                  .slice(-6)
                  .map((m) => ({
                    role: m.role === 'user' ? ('user' as const) : ('assistant' as const),
                    content: m.content || '',
                  })),
          session_id: sessionId,
          session_context: sessionContext ?? undefined,
        };
        return chatWithReasoningTeacher(reasoningRequest);
      } else {
        return chatWithTeacher(request as ChatRequest);
      }
    },
    onSuccess: (data: any) => {
      if (USE_REASONING_SERVICE) {
        if (data.type === 'text') {
          storeAddMessage(themeId, conversationId, {
            id: uid(),
            role: 'assistant',
            content: data.explanation || '',
            timestamp: Date.now(),
          });
        } else if (data.type === 'hybrid' && data.visualization) {
          storeAddMessage(themeId, conversationId, {
            id: uid(),
            role: 'assistant',
            content: data.explanation || '',
            explanationText: data.explanation,
            isHybrid: true,
            showSheetMusic: true,
            musicxmlUrl: data.musicxmlUrl,
            midiUrl: data.midiUrl,
            timestamp: Date.now(),
          });
        }
        if (data.context_update) setSessionContext(data.context_update);
      } else {
        if (data.type === 'text') {
          storeAddMessage(themeId, conversationId, {
            id: uid(),
            role: 'assistant',
            content: data.content || '',
            timestamp: Date.now(),
          });
        } else if (data.type === 'hybrid' && data.job_id) {
          storeAddMessage(themeId, conversationId, {
            id: uid(),
            role: 'assistant',
            content: data.content || 'Generando visualización...',
            explanationText: data.content,
            isHybrid: true,
            timestamp: Date.now(),
          });
          setActiveJobId(data.job_id);
        } else if (data.type === 'pattern_redirect' || data.type === 'creative_redirect') {
          storeAddMessage(themeId, conversationId, {
            id: uid(),
            role: 'assistant',
            content: data.content || 'Procesando solicitud...',
            timestamp: Date.now(),
          });
        }
      }
    },
    onError: (error: any) => {
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'system',
        content: `❌ Error: ${error.response?.data?.detail || error.message}`,
        timestamp: Date.now(),
      });
    },
  });

  const handleStreamingChat = async (message: string) => {
    setIsStreaming(true);
    setPendingMusicData(null);
    try {
      const request = {
        message,
        conversation_history: storedMessages
          .filter((m) => m.role !== 'system')
          .slice(-6)
          .map((m) => ({
            role: m.role === 'user' ? ('user' as const) : ('assistant' as const),
            content: m.content,
          })),
        session_id: sessionId,
        score_id: activeScoreId ?? undefined,
      };
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      for await (const chunk of chatWithTeacherStream(request)) {
        if (chunk.pattern) {
          const p = chunk.pattern as {
            job_id: string; piece_id: string; midi_url: string;
            musicxml_url: string; audio_url?: string;
          };
          setPendingMusicData({
            isHybrid: true,
            showSheetMusic: true,
            midiUrl: `${baseUrl}${p.midi_url}`,
            musicxmlUrl: `${baseUrl}${p.musicxml_url}`,
            audioUrl: p.audio_url ? `${baseUrl}${p.audio_url}` : undefined,
          });
        }
        if (chunk.token) {
          storeAppendStream(chunk.token);
          scrollToBottom();
        }
        if (chunk.error) {
          storeAppendStream(`\n❌ Error: ${chunk.error}`);
        }
      }
    } catch (error: any) {
      storeAppendStream(`\n❌ Error: ${error.message}`);
    } finally {
      setIsStreaming(false);
      storeFinalizeStream(themeId, conversationId, pendingMusicData ?? undefined);
      setPendingMusicData(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isPending) return;

    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };
    storeAddMessage(themeId, conversationId, userMsg);
    const trimmedInput = input.trim();
    setInput('');

    try {
      const processResult: ProcessResponse = await processMessage({
        message: trimmedInput,
        conversation_history: storedMessages
          .filter((m) => m.role !== 'system')
          .slice(-6)
          .map((m) => ({
            role: m.role === 'user' ? ('user' as const) : ('assistant' as const),
            content: m.content,
          })),
        session_id: sessionId,
      });

      switch (processResult.intent) {
        case 'pattern':
          if (processResult.pattern_data) {
            patternMutation.mutate({
              pattern_type: processResult.pattern_data.pattern_type,
              tonic: processResult.pattern_data.tonic,
              scale_type: processResult.pattern_data.scale_type,
              chord_type: processResult.pattern_data.chord_type,
              chord_symbols: processResult.pattern_data.chord_symbols,
              octaves: processResult.pattern_data.octaves,
              tempo: processResult.pattern_data.tempo,
              duration: processResult.pattern_data.duration,
              clef: processResult.pattern_data.clef as 'treble' | 'bass' | 'alto' | 'tenor',
            });
          }
          break;
        default:
          handleStreamingChat(trimmedInput);
      }
    } catch {
      handleStreamingChat(trimmedInput);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSubmitCorrection = async (originalContent: string) => {
    if (!correctionText.trim() || isSubmittingCorrection) return;
    setIsSubmittingCorrection(true);
    try {
      const request: CorrectionRequest = {
        session_id: sessionId,
        original_response: originalContent,
        user_correction: correctionText.trim(),
        concept_type: 'general',
        concept_details: sessionContext ?? {},
      };
      const response = await submitCorrection(request);
      if (response.success) {
        storeAddMessage(themeId, conversationId, {
          id: uid(),
          role: 'system',
          content: `✅ ${response.message}`,
          timestamp: Date.now(),
        });
      }
      setCorrectingMessageId(null);
      setCorrectionText('');
    } catch (error: any) {
      storeAddMessage(themeId, conversationId, {
        id: uid(),
        role: 'system',
        content: `❌ Error al guardar la corrección: ${error.message}`,
        timestamp: Date.now(),
      });
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  const isPending =
    generateMutation.isPending ||
    patternMutation.isPending ||
    activeJobId !== null ||
    isStreaming;

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Panel header — only shown in split-view mode */}
      {onClose && (
        <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0 gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <Music2 size={12} className="text-muted-foreground shrink-0" />
            <span className="text-xs font-semibold text-foreground shrink-0">{MODEL_SHORT_NAME}</span>
            {activeFileName && (
              <>
                <span className="text-muted-foreground/40 shrink-0">·</span>
                <span className="text-xs text-muted-foreground truncate" title={activeFileName}>
                  {activeFileName}
                </span>
              </>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-secondary transition-colors shrink-0"
            title="Cerrar panel de chat"
          >
            <X size={14} className="text-muted-foreground" />
          </button>
        </div>
      )}
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-6">
          {messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="flex justify-end gap-2.5">
                  <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-2.5 text-sm leading-relaxed">
                    <MusicAwareText text={msg.content} />
                  </div>
                  <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <User size={14} className="text-primary" />
                  </div>
                </div>
              );
            }

            if (msg.role === 'system') {
              return (
                <div key={msg.id} className="text-xs text-muted-foreground bg-muted/50 rounded-lg px-4 py-2.5 text-center max-w-[80%] mx-auto">
                  {msg.content}
                </div>
              );
            }

            return (
              <div key={msg.id} className="flex gap-2.5">
                <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center shrink-0 mt-0.5">
                  <Music2 size={14} className="text-secondary-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  {msg.isHybrid && msg.explanationText ? (
                    <>
                      <MusicAwareText text={msg.explanationText} markdown />
                      {msg.musicxmlUrl && <hr className="border-border my-4" />}
                    </>
                  ) : (
                    <MusicAwareText text={msg.content} markdown />
                  )}

                  {msg.showSheetMusic && msg.musicxmlUrl && (
                    <SheetMusicViewer
                      musicxmlUrl={msg.musicxmlUrl}
                      midiUrl={msg.midiUrl}
                      audioUrl={msg.audioUrl}
                      pieceId={msg.pieceId}
                    />
                  )}

                  {msg.id !== 'greeting' && (
                    <div className="mt-3 pt-3 border-t border-border/50">
                      {correctingMessageId === msg.id ? (
                        <div className="flex flex-col gap-2">
                          <textarea
                            className="w-full text-xs rounded-lg border border-border bg-background px-3 py-2 outline-none focus:ring-1 focus:ring-ring resize-none min-h-[60px] text-foreground placeholder:text-muted-foreground"
                            placeholder="Escribe la corrección aquí..."
                            value={correctionText}
                            onChange={(e) => setCorrectionText(e.target.value)}
                            rows={2}
                            disabled={isSubmittingCorrection}
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground disabled:opacity-50 transition-opacity"
                              onClick={() => handleSubmitCorrection(msg.content)}
                              disabled={!correctionText.trim() || isSubmittingCorrection}
                            >
                              {isSubmittingCorrection ? '⏳ Guardando...' : '✅ Enviar corrección'}
                            </button>
                            <button
                              type="button"
                              className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:bg-secondary transition-colors"
                              onClick={() => { setCorrectingMessageId(null); setCorrectionText('') }}
                              disabled={isSubmittingCorrection}
                            >
                              ❌ Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="text-xs px-2.5 py-1 rounded-md border border-border text-muted-foreground hover:bg-secondary transition-colors"
                          onClick={() => setCorrectingMessageId(msg.id)}
                          title="Corregir esta respuesta"
                        >
                          ✏️ Corregir
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Live streaming message */}
          {(isStreaming || streamingContent) && (
            <div className="flex gap-2.5">
              <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center shrink-0 mt-0.5">
                <Music2 size={14} className="text-secondary-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                {streamingContent ? (
                  <MusicAwareText text={streamingContent} markdown />
                ) : (
                  <div className="flex items-center gap-1.5 py-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Job pending indicator (pattern generation) */}
          {activeJobId && !isStreaming && (
            <div className="flex gap-2.5">
              <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center shrink-0">
                <Music2 size={14} className="text-secondary-foreground" />
              </div>
              <div className="flex items-center gap-1.5 py-2">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border bg-background px-4 py-3 shrink-0">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit}>
            <div className="flex gap-2 items-end rounded-xl border border-border bg-background shadow-sm focus-within:ring-1 focus-within:ring-ring px-3 py-2">
              <textarea
                ref={inputRef}
                className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground leading-relaxed py-0.5 max-h-48 text-foreground"
                placeholder='Ej: "escala de do mayor" o "¿qué es una escala pentatónica?"'
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                rows={2}
                disabled={isPending}
              />
              <button
                type="submit"
                className="h-8 w-8 shrink-0 rounded-md bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 transition-opacity"
                disabled={!input.trim() || isPending}
              >
                <Send size={14} />
              </button>
            </div>
          </form>
          <p className="text-[0.65rem] text-muted-foreground mt-1.5 text-center">
            Enter para enviar · Shift+Enter nueva línea
          </p>
        </div>
      </div>
    </div>
  );
}
