import { useState, useCallback, useEffect } from 'react';
import { Message, Conversation, ChatApiRequest, ChatApiResponse } from '@/types/chat';

const API_BASE = '/api';
const USER_ID = '68368fff90e7c4615a08a719';
const MAX_RETRIES = 3;
const RETRY_DELAY = 2000;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState('deepseek/deepseek-r1-distill-qwen-14b');
  const [englishOnly, setEnglishOnly] = useState(false);

  // Load session from localStorage
  useEffect(() => {
    const storedSessionId = localStorage.getItem('holowellness_session_id');
    const storedConversations = localStorage.getItem('holowellness_conversations');
    
    if (storedSessionId) {
      setSessionId(storedSessionId);
    }
    
    if (storedConversations) {
      try {
        setConversations(JSON.parse(storedConversations));
      } catch (e) {
        console.error('Failed to parse stored conversations:', e);
      }
    }
  }, []);

  // Save session to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('holowellness_session_id', sessionId);
    }
  }, [sessionId]);

  // Save conversations to localStorage
  useEffect(() => {
    localStorage.setItem('holowellness_conversations', JSON.stringify(conversations));
  }, [conversations]);

  const sendMessage = useCallback(async (
    text: string,
    imageBase64?: string
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage: Message = {
      text,
      isUser: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      imageUrl: imageBase64 ? `data:image/jpeg;base64,${imageBase64}` : undefined,
    };
    setMessages(prev => [...prev, userMessage]);

    const payload: ChatApiRequest = {
      query: text,
      user_id: USER_ID,
      session_id: sessionId || undefined,
      translate: !englishOnly,
      model,
      image_base64: imageBase64,
    };

    let retries = 0;
    let success = false;

    while (retries < MAX_RETRIES && !success) {
      try {
        const response = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (response.status === 502 || response.status === 504) {
          retries++;
          if (retries < MAX_RETRIES) {
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
            continue;
          }
          throw new Error('Server is temporarily unavailable. Please try again.');
        }

        if (!response.ok) {
          throw new Error(`Request failed: ${response.statusText}`);
        }

        const data: ChatApiResponse = await response.json();
        
        // Update session ID
        if (data.session_id && data.session_id !== sessionId) {
          setSessionId(data.session_id);
          
          // Add to conversations list
          const newConversation: Conversation = {
            id: data.session_id,
            title: text.slice(0, 50) + (text.length > 50 ? '...' : ''),
            preview: data.response.slice(0, 100),
            timestamp: new Date().toISOString(),
            messageCount: 2,
          };
          setConversations(prev => [newConversation, ...prev.slice(0, 19)]);
        }

        // Add AI message
        const aiMessage: Message = {
          _id: data.message_id,
          text: data.response,
          isUser: false,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          thinking: data.thinking,
          retrievedContext: data.retrieved_context,
        };
        setMessages(prev => [...prev, aiMessage]);
        success = true;

      } catch (err) {
        if (retries >= MAX_RETRIES - 1) {
          const errorMessage = err instanceof Error ? err.message : 'An error occurred';
          setError(errorMessage);
          
          // Add error message
          const errorMsg: Message = {
            text: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
            isUser: false,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages(prev => [...prev, errorMsg]);
        }
        retries++;
      }
    }

    setIsLoading(false);
  }, [sessionId, model, englishOnly]);

  const rateMessage = useCallback(async (messageId: string, rating: number) => {
    try {
      await fetch(`${API_BASE}/chat/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, rating }),
      });

      setMessages(prev =>
        prev.map(msg =>
          msg._id === messageId ? { ...msg, rating } : msg
        )
      );
    } catch (err) {
      console.error('Failed to rate message:', err);
    }
  }, []);

  const clearSession = useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/memory/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (err) {
      console.error('Failed to clear session:', err);
    }

    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('holowellness_session_id');
  }, [sessionId]);

  const startNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('holowellness_session_id');
  }, []);

  const loadConversation = useCallback((conversationId: string) => {
    setSessionId(conversationId);
    setMessages([]);
    // Note: In a real implementation, you'd fetch the conversation history here
  }, []);

  return {
    messages,
    conversations,
    isLoading,
    error,
    model,
    englishOnly,
    sessionId,
    setModel,
    setEnglishOnly,
    sendMessage,
    rateMessage,
    clearSession,
    startNewChat,
    loadConversation,
  };
}

