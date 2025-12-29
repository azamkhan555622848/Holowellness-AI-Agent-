import { User, Bot } from 'lucide-react';
import { Message } from '@/types/chat';
import { RatingStars } from './RatingStars';
import { ExpandableSection } from './ExpandableSection';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: Message;
  onRate?: (messageId: string, rating: number) => void;
}

export function ChatMessage({ message, onRate }: ChatMessageProps) {
  const { text, isUser, timestamp, rating, thinking, retrievedContext, imageUrl, _id } = message;

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
          isUser
            ? 'gradient-primary'
            : 'bg-secondary'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary-foreground" />
        ) : (
          <Bot className="h-4 w-4 text-secondary-foreground" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'flex flex-col max-w-[85%] md:max-w-[75%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Image Preview (if any) */}
        {imageUrl && (
          <div className="mb-2 rounded-lg overflow-hidden border border-border">
            <img
              src={imageUrl}
              alt="Uploaded image"
              className="max-w-xs max-h-48 object-cover"
            />
          </div>
        )}

        {/* Message Bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3 shadow-soft',
            isUser
              ? 'bg-chat-user text-chat-user-foreground rounded-br-md'
              : 'bg-chat-ai text-chat-ai-foreground rounded-bl-md border border-border'
          )}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        </div>

        {/* AI Message Extras */}
        {!isUser && (
          <div className="w-full mt-1 space-y-1">
            {/* Thinking Section */}
            {thinking && (
              <ExpandableSection
                title="How I thought about this"
                content={thinking}
                type="thinking"
              />
            )}

            {/* Sources Section */}
            {retrievedContext && (
              <ExpandableSection
                title="Sources used"
                content={retrievedContext}
                type="sources"
              />
            )}

            {/* Rating and Timestamp */}
            <div className="flex items-center justify-between px-1 mt-2">
              <span className="text-xs text-muted-foreground">{timestamp}</span>
              {_id && onRate && (
                <RatingStars
                  rating={rating}
                  onRate={(r) => onRate(_id, r)}
                />
              )}
            </div>
          </div>
        )}

        {/* User Message Timestamp */}
        {isUser && (
          <span className="text-xs text-muted-foreground mt-1 px-1">
            {timestamp}
          </span>
        )}
      </div>
    </div>
  );
}
