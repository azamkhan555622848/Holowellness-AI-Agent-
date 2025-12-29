import { useState, useRef, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatHeader } from './ChatHeader';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ThinkingIndicator } from './ThinkingIndicator';
import { WelcomeScreen } from './WelcomeScreen';
import { useChat } from '@/hooks/useChat';
import { useTheme } from '@/hooks/useTheme';
import { useAccessibility } from '@/hooks/useAccessibility';

export function ChatContainer() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    conversations,
    isLoading,
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
  } = useChat();

  const { resolvedTheme, toggleTheme } = useTheme();
  const {
    fontSize,
    highContrast,
    setFontSize,
    setHighContrast,
  } = useAccessibility();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleSend = (text: string, imageBase64?: string) => {
    sendMessage(text, imageBase64);
  };

  const handleQuickStart = (prompt: string) => {
    sendMessage(prompt);
  };

  const handleClearAll = () => {
    clearSession();
    localStorage.removeItem('holowellness_conversations');
  };

  return (
    <div className="h-screen flex bg-background">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentSessionId={sessionId}
        onNewChat={startNewChat}
        onSelectConversation={loadConversation}
        onClearAll={handleClearAll}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <ChatHeader
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          isDarkMode={resolvedTheme === 'dark'}
          onToggleTheme={toggleTheme}
          model={model}
          onModelChange={setModel}
          englishOnly={englishOnly}
          onLanguageToggle={setEnglishOnly}
          fontSize={fontSize}
          onFontSizeChange={setFontSize}
          highContrast={highContrast}
          onHighContrastChange={setHighContrast}
        />

        {/* Messages Area */}
        {messages.length === 0 ? (
          <WelcomeScreen onQuickStart={handleQuickStart} />
        ) : (
          <ScrollArea className="flex-1">
            <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
              {messages.map((message, index) => (
                <ChatMessage
                  key={`${message._id || index}-${message.timestamp}`}
                  message={message}
                  onRate={rateMessage}
                />
              ))}
              
              {isLoading && <ThinkingIndicator />}
              
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}

        {/* Input Area */}
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>
    </div>
  );
}

