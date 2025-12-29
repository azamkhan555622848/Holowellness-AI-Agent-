import { Bot } from 'lucide-react';

export function ThinkingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
        <Bot className="h-4 w-4 text-secondary-foreground" />
      </div>

      {/* Thinking Animation */}
      <div className="bg-chat-ai border border-border rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full bg-primary animate-typing"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
          <span className="text-sm text-muted-foreground animate-pulse-subtle">
            Thinking...
          </span>
        </div>
      </div>
    </div>
  );
}

