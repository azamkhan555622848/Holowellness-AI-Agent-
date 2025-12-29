import { useState } from 'react';
import { ChevronDown, Brain, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExpandableSectionProps {
  title: string;
  content: string;
  type: 'thinking' | 'sources';
}

export function ExpandableSection({ title, content, type }: ExpandableSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const Icon = type === 'thinking' ? Brain : BookOpen;
  const bgClass = type === 'thinking' ? 'bg-chat-thinking' : 'bg-chat-sources';

  return (
    <div className={cn('rounded-lg overflow-hidden mt-2', bgClass)}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" />
          <span>{title}</span>
        </div>
        <ChevronDown
          className={cn(
            'h-4 w-4 transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}
        />
      </button>
      
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isExpanded ? 'max-h-96' : 'max-h-0'
        )}
      >
        <div className="px-3 pb-3">
          <div className="text-sm text-muted-foreground whitespace-pre-wrap max-h-64 overflow-y-auto scrollbar-thin">
            {content}
          </div>
        </div>
      </div>
    </div>
  );
}
