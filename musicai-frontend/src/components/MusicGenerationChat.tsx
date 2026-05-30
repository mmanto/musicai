import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Music2, User } from 'lucide-react';
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

export default function MusicGenerationChat() {
  const selected = useChatStore((s) => s.selected)!;
  const themeId = selected.themeId;
  const conversationId =
    selected.type === 'conversation' ? selected.conversationId : '';

  const storedMessages = useChatStore((s) => {
    if (!s.selected || s.selected.type !== 'conversation') return [];
    const theme = s.themes.find((t) => t.id === s.selected!.themeId);
    return (
      theme?.conversations.find(
        (c) => c.id === (s.selected as { conversationId: string }).conversationId
      )?.messages ?? []
    );
  });

  const streamingContent = useChatStore((s) => s.streamingContent);
  const storeAddMessage = useChatStore((s) => s.addMessage);
  const storeAppendStream = useChatStore((s) => s.appendStream);
  const storeFinalizeStream = useChatStore((s) => s.finalizeStream);

  // Use conversation ID as backend session ID
  const sessionId = conversationId;

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
                      <div className="text-sm text-foreground leading-relaxed">
                        <MusicAwareText text={msg.explanationText} />
                      </div>
                      {msg.musicxmlUrl && <hr className="border-border my-4" />}
                    </>
                  ) : (
                    <div className="text-sm text-foreground leading-relaxed">
                      <MusicAwareText text={msg.content} />
                    </div>
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
              <div className="flex-1 min-w-0 text-sm text-foreground leading-relaxed">
                {streamingContent ? (
                  <MusicAwareText text={streamingContent} />
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
