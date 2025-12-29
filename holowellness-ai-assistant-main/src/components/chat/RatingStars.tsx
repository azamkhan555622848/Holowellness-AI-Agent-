import { useState } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RatingStarsProps {
  rating?: number;
  onRate: (rating: number) => void;
  disabled?: boolean;
}

export function RatingStars({ rating, onRate, disabled }: RatingStarsProps) {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div className="flex items-center gap-0.5" role="group" aria-label="Rate this response">
      {[1, 2, 3, 4, 5].map((star) => {
        const isFilled = rating ? star <= rating : hovered ? star <= hovered : false;
        
        return (
          <button
            key={star}
            onClick={() => !disabled && onRate(star)}
            onMouseEnter={() => !disabled && setHovered(star)}
            onMouseLeave={() => setHovered(null)}
            disabled={disabled}
            className={cn(
              'p-0.5 transition-all duration-150',
              disabled ? 'cursor-default' : 'cursor-pointer hover:scale-110',
              isFilled ? 'text-yellow-500' : 'text-muted-foreground/40'
            )}
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            <Star
              className={cn('h-4 w-4 transition-all', isFilled && 'fill-current')}
            />
          </button>
        );
      })}
    </div>
  );
}
