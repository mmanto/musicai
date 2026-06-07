/**
 * MusicAI API Client
 *
 * Axios-based client for communicating with the MusicAI backend API.
 */

import axios, { AxiosError } from 'axios';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_V1_PREFIX = '/api/v1';

// Create axios instance
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_V1_PREFIX}`,
  timeout: 60000, // 60 seconds for generation requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available (future)
    // const token = localStorage.getItem('auth_token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle common errors
    if (error.response) {
      const status = error.response.status;
      const detail = (error.response.data as any)?.detail || 'Unknown error';

      console.error(`API Error [${status}]:`, detail);

      // Handle specific status codes
      switch (status) {
        case 401:
          // Unauthorized - redirect to login (future)
          break;
        case 404:
          console.error('Resource not found');
          break;
        case 500:
          console.error('Server error:', detail);
          break;
      }
    } else if (error.request) {
      console.error('Network error: No response from server');
    } else {
      console.error('Request error:', error.message);
    }

    return Promise.reject(error);
  }
);

// ==================== Type Definitions ====================

export interface MusicGenerationRequest {
  prompt: string;
  duration?: number;
  temperature?: number;
  guidance_scale?: number;
  title?: string;
  melody_file?: File;
}

export interface MusicGenerationResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  piece_id?: string;
  audio_url?: string;
  created_at: string;
  completed_at?: string;
  error?: string;
  progress?: number;
}

export interface GenerationJob {
  job_id: string;
  prompt: string;
  duration: number;
  status: string;
  piece_id?: string;
  audio_url?: string;
  created_at: string;
  completed_at?: string;
}

export interface MusicAnalysisRequest {
  piece_id?: string;
  generate_explanation?: boolean;
}

export interface MusicAnalysis {
  key?: string;
  tempo?: number;
  time_signature?: string;
  duration?: number;
  chords?: string[];
  note_count?: number;
  pitch_range?: {
    lowest: number;
    highest: number;
  };
  [key: string]: any;
}

export interface MusicAnalysisResponse {
  piece_id: string;
  analysis: MusicAnalysis;
  explanation?: string;
}

export interface TransformationRequest {
  piece_id: string;
  transformation_type: 'transpose' | 'augment' | 'change_tempo';
  semitones?: number;
  factor?: number;
  tempo?: number;
}

export interface TransformationResponse {
  original_piece_id: string;
  new_piece_id: string;
  transformation_applied: string;
  message: string;
}

export interface HealthResponse {
  status: string;
  services: {
    music21: boolean;
    musicgen: boolean;
    audio_to_midi: boolean;
    ollama: boolean;
  };
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
  session_id?: string;
  score_id?: string;
}

export interface ScoreUploadResponse {
  score_id: string;
  analysis: Record<string, unknown>;
  context_summary: string;
}

export interface PatternData {
  pattern_type: 'scale' | 'chord' | 'arpeggio';
  tonic?: string;
  scale_type?: string;
  chord_symbols?: string[];
  chord_type?: string;
  octaves?: number;
  tempo?: number;
  duration?: number;
}

export interface ChatResponse {
  type: 'text' | 'music' | 'hybrid' | 'pattern_redirect' | 'creative_redirect';
  content?: string;
  job_id?: string;
  patterns?: PatternData[];
}

// Process endpoint types
export interface ProcessRequest {
  message: string;
  conversation_history?: ChatMessage[];
  session_id?: string;
}

export interface ProcessPatternData {
  pattern_type: 'scale' | 'chord' | 'arpeggio';
  tonic?: string;
  scale_type?: string;
  chord_type?: string;
  chord_symbols?: string;
  octaves: number;
  tempo: number;
  duration: number;
  clef: string;
}

export interface ProcessResponse {
  intent: 'pattern' | 'theory' | 'validation' | 'creative' | 'chat';
  should_stream: boolean;
  pattern_data?: ProcessPatternData;
  confidence: number;
  detected_keywords: string[];
}

// ==================== API Functions ====================

/**
 * Health Check
 */
export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
};

/**
 * Music Generation
 */
export const generateMusic = async (
  request: MusicGenerationRequest
): Promise<MusicGenerationResponse> => {
  const formData = new FormData();

  formData.append('prompt', request.prompt);
  if (request.duration !== undefined) formData.append('duration', request.duration.toString());
  if (request.temperature !== undefined) formData.append('temperature', request.temperature.toString());
  if (request.guidance_scale !== undefined) formData.append('guidance_scale', request.guidance_scale.toString());
  if (request.title) formData.append('title', request.title);
  if (request.melody_file) formData.append('melody_file', request.melody_file);

  const response = await apiClient.post('/music/generate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Generate Musical Pattern (scales, chords, arpeggios)
 */
export interface PatternGenerationRequest {
  pattern_type: 'scale' | 'chord' | 'arpeggio';
  tonic?: string;
  scale_type?: string;
  chord_symbols?: string;
  chord_type?: string;
  octaves?: number;
  tempo?: number;
  duration?: number;
  clef?: 'treble' | 'bass' | 'alto' | 'tenor';
  title?: string;
}

export const generatePattern = async (
  request: PatternGenerationRequest
): Promise<MusicGenerationResponse> => {
  console.log('DEBUG - generatePattern request:', JSON.stringify(request, null, 2));

  const formData = new FormData();

  formData.append('pattern_type', request.pattern_type);
  if (request.tonic) formData.append('tonic', request.tonic);
  if (request.scale_type) formData.append('scale_type', request.scale_type);
  if (request.chord_symbols) formData.append('chord_symbols', request.chord_symbols);
  if (request.chord_type) formData.append('chord_type', request.chord_type);
  if (request.octaves !== undefined) formData.append('octaves', request.octaves.toString());
  if (request.tempo !== undefined) formData.append('tempo', request.tempo.toString());
  if (request.duration !== undefined) formData.append('duration', request.duration.toString());
  if (request.clef) formData.append('clef', request.clef);
  if (request.title) formData.append('title', request.title);

  const response = await apiClient.post('/music/pattern', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
  });

  return response.data;
};

/**
 * Get Job Status
 */
export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response = await apiClient.get(`/music/status/${jobId}`);
  return response.data;
};

/**
 * List All Jobs
 */
export const listJobs = async (): Promise<GenerationJob[]> => {
  const response = await apiClient.get('/music/jobs');
  return response.data;
};

/**
 * Analyze Music (by piece_id)
 */
export const analyzeMusic = async (
  request: MusicAnalysisRequest
): Promise<MusicAnalysisResponse> => {
  const response = await apiClient.post('/music/analyze', request);
  return response.data;
};

/**
 * Analyze Uploaded File
 */
export const analyzeUpload = async (
  file: File,
  generateExplanation: boolean = false
): Promise<MusicAnalysisResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('generate_explanation', generateExplanation.toString());

  const response = await apiClient.post('/music/analyze/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Transform Music
 */
export const transformMusic = async (
  request: TransformationRequest
): Promise<TransformationResponse> => {
  const response = await apiClient.post('/music/transform', request);
  return response.data;
};

/**
 * Download File
 */
export const downloadFile = async (
  pieceId: string,
  format: 'audio' | 'midi' | 'musicxml' | 'abc'
): Promise<Blob> => {
  const response = await apiClient.get(`/music/download/${pieceId}/${format}`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Get Audio URL
 */
export const getAudioUrl = (pieceId: string): string => {
  return `${API_BASE_URL}${API_V1_PREFIX}/music/download/${pieceId}/audio`;
};

/**
 * Get MIDI URL
 */
export const getMidiUrl = (pieceId: string): string => {
  return `${API_BASE_URL}${API_V1_PREFIX}/music/download/${pieceId}/midi`;
};

/**
 * Chat with Music Teacher
 */
export const chatWithTeacher = async (
  request: ChatRequest
): Promise<ChatResponse> => {
  const response = await apiClient.post('/music/chat', request);
  return response.data;
};

/**
 * Process Message (Unified Intent Analysis)
 * Analyzes user input and returns intent with extracted parameters
 */
export const processMessage = async (
  request: ProcessRequest
): Promise<ProcessResponse> => {
  const response = await apiClient.post('/music/process', request);
  return response.data;
};

/**
 * Chat with Music Teacher (Streaming)
 * Returns an async generator that yields tokens as they're received
 */
export async function* chatWithTeacherStream(
  request: ChatRequest
): AsyncGenerator<{
  token?: string;
  done?: boolean;
  error?: string;
  full_response?: string;
  pattern?: {
    job_id: string;
    piece_id: string;
    midi_url: string;
    musicxml_url: string;
    audio_url?: string;
  };
}> {
  const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/music/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete SSE messages
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || ''; // Keep incomplete message in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6); // Remove 'data: ' prefix
        try {
          const data = JSON.parse(jsonStr);
          yield data;
        } catch (e) {
          console.error('Error parsing SSE data:', e);
        }
      }
    }
  }
}

/**
 * Upload a music score file to the backend for analysis.
 * Returns a score_id that can be passed in chat requests.
 */
export const uploadScore = async (
  file: Blob,
  fileName: string,
  fileType: 'xml' | 'gp',
  options?: { tracksJson?: string; sectionsJson?: string }
): Promise<ScoreUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file, fileName);
  formData.append('file_name', fileName);
  formData.append('file_type', fileType);
  if (options?.tracksJson) formData.append('tracks_json', options.tracksJson);
  if (options?.sectionsJson) formData.append('sections_json', options.sectionsJson);

  const response = await apiClient.post('/music/score/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
    // Accept both 200 (full analysis) and 206 (metadata only)
    validateStatus: (s) => s === 200 || s === 206,
  });
  return response.data;
};

/**
 * Link a score to a session so the backend can look up context by session_id.
 */
export const linkScoreToSession = async (
  sessionId: string,
  scoreId: string
): Promise<void> => {
  await apiClient.post('/music/score/link-session', { session_id: sessionId, score_id: scoreId });
};

// ==================== Knowledge Base API ====================

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: string;
  difficulty: string;
  source_type: string;
  added_at: string | null;
  content_preview: string;
}

export interface KnowledgeListResponse {
  documents: KnowledgeDocument[];
  total: number;
}

export const listKnowledgeDocuments = async (): Promise<KnowledgeListResponse> => {
  const response = await apiClient.get('/knowledge/documents');
  return response.data;
};

export const addKnowledgeDocument = async (data: {
  title: string;
  content: string;
  category: string;
  difficulty: string;
}): Promise<{ doc_id: string; status: string }> => {
  const response = await apiClient.post('/knowledge/documents', data);
  return response.data;
};

export const uploadKnowledgeDocument = async (
  file: File,
  meta: { title?: string; category: string; difficulty: string }
): Promise<{ doc_id: string; status: string; chars: number; title: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  if (meta.title) formData.append('title', meta.title);
  formData.append('category', meta.category);
  formData.append('difficulty', meta.difficulty);
  const response = await apiClient.post('/knowledge/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  });
  return response.data;
};

export const deleteKnowledgeDocument = async (docId: string): Promise<void> => {
  await apiClient.delete(`/knowledge/documents/${docId}`);
};

export default apiClient;
