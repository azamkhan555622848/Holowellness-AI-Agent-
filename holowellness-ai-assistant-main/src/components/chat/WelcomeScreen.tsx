import { Activity, MessageSquare, Image, Sparkles } from 'lucide-react';

const features = [
  {
    icon: MessageSquare,
    title: 'Ask Anything',
    description: 'Get answers about fitness, nutrition, and wellness',
  },
  {
    icon: Image,
    title: 'Image Analysis',
    description: 'Upload images for posture analysis and feedback',
  },
  {
    icon: Sparkles,
    title: 'Personalized Advice',
    description: 'Receive tailored recommendations for your goals',
  },
];

const quickStarts = [
  'How can I improve my posture?',
  'What exercises help with lower back pain?',
  'Create a beginner workout routine',
  'Tips for better sleep quality',
];

interface WelcomeScreenProps {
  onQuickStart: (message: string) => void;
}

export function WelcomeScreen({ onQuickStart }: WelcomeScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
      {/* Logo */}
      <div className="w-20 h-20 rounded-2xl gradient-primary flex items-center justify-center shadow-medium mb-6">
        <Activity className="h-10 w-10 text-primary-foreground" />
      </div>

      {/* Title */}
      <h2 className="font-display text-2xl md:text-3xl font-bold text-foreground mb-2">
        Welcome to <span className="gradient-text">HoloWellness</span>
      </h2>
      <p className="text-muted-foreground max-w-md mb-8">
        Your AI-powered fitness and wellness assistant. Ask me anything about health, exercise, and nutrition.
      </p>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mb-8">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="p-4 rounded-xl bg-card border border-border shadow-soft"
          >
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mx-auto mb-3">
              <feature.icon className="h-5 w-5 text-primary" />
            </div>
            <h3 className="font-semibold text-foreground mb-1">{feature.title}</h3>
            <p className="text-sm text-muted-foreground">{feature.description}</p>
          </div>
        ))}
      </div>

      {/* Quick Starts */}
      <div className="w-full max-w-2xl">
        <p className="text-sm text-muted-foreground mb-3">Try asking:</p>
        <div className="flex flex-wrap justify-center gap-2">
          {quickStarts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onQuickStart(prompt)}
              className="px-4 py-2 text-sm rounded-full bg-muted hover:bg-muted/80 text-foreground transition-colors border border-border"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
