export interface Message {
  _id?: string;
  text: string;
  isUser: boolean;
  timestamp: string;
  rating?: number;
  thinking?: string;
  retrievedContext?: string;
  imageUrl?: string;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  messageCount: number;
}

export interface ChatSettings {
  model: string;
  englishOnly: boolean;
  fontSize: 'small' | 'medium' | 'large';
  highContrast: boolean;
}

export interface ChatApiRequest {
  query: string;
  user_id: string;
  session_id?: string;
  translate: boolean;
  model: string;
  image_base64?: string;
  metrics?: Record<string, unknown>;
}

export interface ChatApiResponse {
  response: string;
  session_id: string;
  message_id: string;
  thinking?: string;
  retrieved_context?: string;
  rag_metadata?: {
    reranked: boolean;
    num_sources: number;
  };
}

