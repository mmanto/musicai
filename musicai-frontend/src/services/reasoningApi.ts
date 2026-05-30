/**
 * API client for MusicAI Reasoning Service
 *
 * This service provides communication with the reasoning backend
 * for educational chat with music visualization capabilities.
 */

import axios from 'axios';

// Reasoning service base URL (configurable via environment variable)
const REASONING_BASE_URL = import.meta.env.VITE_REASONING_API_URL || 'http://localhost:8004';

// Create axios instance for reasoning service
const reasoningClient = axios.create({
  baseURL: `${REASONING_BASE_URL}/api/v1`,
  timeout: 60000, // 60 seconds for LLM responses
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// TypeScript Interfaces
// ============================================================================

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatTeacherRequest {
  message: string;
  conversation_history: ConversationMessage[];
  session_id?: string;
  session_context?: Record<string, any>;
}

export interface ConceptVisualization {
  pattern_type: string;
  tonic?: string;
  scale_type?: string;
  chord_symbols?: string[];
  direction?: string;
  musicxml_b64: string;
  midi_b64: string;
  description: string;
}

export interface ChatTeacherResponse {
  type: 'text' | 'hybrid';
  explanation: string;
  visualization?: ConceptVisualization;
  context_update: Record<string, any>;
}

// Extended response with URLs (after base64 conversion)
export interface ChatTeacherResponseWithUrls extends ChatTeacherResponse {
  musicxmlUrl?: string;
  midiUrl?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert base64 string to Blob
 */
function base64ToBlob(base64: string, mimeType: string): Blob {
  try {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);

    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }

    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  } catch (error) {
    console.error('Error converting base64 to blob:', error);
    throw new Error('Failed to decode base64 data');
  }
}

/**
 * Convert base64-encoded files to object URLs
 *
 * This function takes the base64 data from the backend and converts it
 * to temporary browser URLs that can be used by visualizers and players.
 */
function convertBase64ToUrls(visualization: ConceptVisualization): {
  musicxmlUrl: string;
  midiUrl: string;
} {
  // Convert MusicXML
  const musicxmlBlob = base64ToBlob(visualization.musicxml_b64, 'application/xml');
  const musicxmlUrl = URL.createObjectURL(musicxmlBlob);

  // Convert MIDI
  const midiBlob = base64ToBlob(visualization.midi_b64, 'audio/midi');
  const midiUrl = URL.createObjectURL(midiBlob);

  return { musicxmlUrl, midiUrl };
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Send a message to the chat teacher and get a response
 *
 * This function:
 * 1. Sends the user's message to the reasoning service
 * 2. Receives the response (text + optional visualization)
 * 3. If visualization is present, converts base64 to object URLs
 * 4. Returns the complete response ready for UI rendering
 *
 * @param request - Chat request with message and history
 * @returns Response with explanation and optional visualization URLs
 * @throws Error if the request fails
 */
export const chatWithReasoningTeacher = async (
  request: ChatTeacherRequest
): Promise<ChatTeacherResponseWithUrls> => {
  try {
    console.log('[ReasoningAPI] Sending chat request:', {
      message: request.message.substring(0, 100),
      historyLength: request.conversation_history.length,
      hasSessionId: !!request.session_id,
      hasContext: !!request.session_context,
    });

    // Send request to reasoning service
    const response = await reasoningClient.post<ChatTeacherResponse>(
      '/chat-teacher',
      request
    );

    console.log('[ReasoningAPI] Received response:', {
      type: response.data.type,
      explanationLength: response.data.explanation.length,
      hasVisualization: !!response.data.visualization,
    });

    const data = response.data;

    // If visualization present, convert base64 to object URLs
    if (data.visualization) {
      console.log('[ReasoningAPI] Converting visualization base64 to URLs');

      const { musicxmlUrl, midiUrl } = convertBase64ToUrls(data.visualization);

      return {
        ...data,
        musicxmlUrl,
        midiUrl,
      };
    }

    return data;

  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('[ReasoningAPI] Request failed:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
      });

      const message = error.response?.data?.detail || error.message;
      throw new Error(`Chat teacher error: ${message}`);
    }

    console.error('[ReasoningAPI] Unexpected error:', error);
    throw error;
  }
};

/**
 * Check health of the reasoning service
 *
 * @returns Health status of the service
 */
export const checkReasoningHealth = async (): Promise<{
  status: string;
  components: Record<string, boolean>;
}> => {
  try {
    const response = await reasoningClient.get('/chat-teacher/health');
    return response.data;
  } catch (error) {
    console.error('[ReasoningAPI] Health check failed:', error);
    throw error;
  }
};

/**
 * Cleanup object URLs to prevent memory leaks
 *
 * Call this function when a visualization is no longer needed
 * (e.g., when a message is removed from the chat).
 *
 * @param urls - Object containing URLs to revoke
 */
export const cleanupVisualizationUrls = (urls: {
  musicxmlUrl?: string;
  midiUrl?: string;
}) => {
  if (urls.musicxmlUrl) {
    URL.revokeObjectURL(urls.musicxmlUrl);
  }
  if (urls.midiUrl) {
    URL.revokeObjectURL(urls.midiUrl);
  }
};

// ============================================================================
// Correction API
// ============================================================================

export interface CorrectionRequest {
  session_id: string;
  original_response: string;
  user_correction: string;
  concept_type?: string;
  concept_details?: Record<string, any>;
}

export interface CorrectionResponse {
  success: boolean;
  correction_id: string;
  message: string;
}

/**
 * Submit a correction to help the system learn
 *
 * @param request - The correction details
 * @returns Response with success status
 */
export const submitCorrection = async (
  request: CorrectionRequest
): Promise<CorrectionResponse> => {
  try {
    console.log('[ReasoningAPI] Submitting correction:', {
      session_id: request.session_id,
      concept_type: request.concept_type,
    });

    const response = await reasoningClient.post<CorrectionResponse>(
      '/chat-teacher/correction',
      request
    );

    console.log('[ReasoningAPI] Correction submitted:', response.data);
    return response.data;

  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('[ReasoningAPI] Correction failed:', {
        status: error.response?.status,
        data: error.response?.data,
      });
      throw new Error(`Correction error: ${error.response?.data?.detail || error.message}`);
    }
    throw error;
  }
};

/**
 * Get stored corrections
 *
 * @param sessionId - Optional session filter
 * @param conceptType - Optional concept type filter
 * @returns List of corrections
 */
export const getCorrections = async (
  sessionId?: string,
  conceptType?: string
): Promise<{ corrections: any[]; count: number }> => {
  try {
    const params = new URLSearchParams();
    if (sessionId) params.append('session_id', sessionId);
    if (conceptType) params.append('concept_type', conceptType);

    const response = await reasoningClient.get('/chat-teacher/corrections', { params });
    return response.data;
  } catch (error) {
    console.error('[ReasoningAPI] Get corrections failed:', error);
    return { corrections: [], count: 0 };
  }
};

// ============================================================================
// Exports
// ============================================================================

export default {
  chatWithReasoningTeacher,
  checkReasoningHealth,
  cleanupVisualizationUrls,
  submitCorrection,
  getCorrections,
};
