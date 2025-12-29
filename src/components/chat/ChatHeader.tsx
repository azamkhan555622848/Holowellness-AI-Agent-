import { Moon, Sun, Settings, Menu, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface ChatHeaderProps {
  onToggleSidebar: () => void;
  isDarkMode: boolean;
  onToggleTheme: () => void;
  model: string;
  onModelChange: (model: string) => void;
  englishOnly: boolean;
  onLanguageToggle: (englishOnly: boolean) => void;
  fontSize: 'small' | 'medium' | 'large';
  onFontSizeChange: (size: 'small' | 'medium' | 'large') => void;
  highContrast: boolean;
  onHighContrastChange: (enabled: boolean) => void;
}

export function ChatHeader({
  onToggleSidebar,
  isDarkMode,
  onToggleTheme,
  model,
  onModelChange,
  englishOnly,
  onLanguageToggle,
  fontSize,
  onFontSizeChange,
  highContrast,
  onHighContrastChange,
}: ChatHeaderProps) {
  return (
    <header className="h-16 border-b border-border bg-card px-4 flex items-center justify-between gap-4 shrink-0">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleSidebar}
          className="lg:hidden"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-soft">
            <Activity className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="hidden sm:block">
            <h1 className="font-display font-bold text-lg text-foreground leading-tight">
              HoloWellness
            </h1>
            <p className="text-xs text-muted-foreground">AI Fitness Assistant</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Model Selector */}
        <Select value={model} onValueChange={onModelChange}>
          <SelectTrigger className="w-[180px] hidden md:flex">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="deepseek/deepseek-r1-distill-qwen-14b">
              DeepSeek 14B
            </SelectItem>
            <SelectItem value="deepseek/deepseek-r1-distill-qwen-32b">
              DeepSeek 32B
            </SelectItem>
          </SelectContent>
        </Select>

        {/* Language Toggle */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted">
          <span className={`text-xs font-medium ${!englishOnly ? 'text-foreground' : 'text-muted-foreground'}`}>
            中文
          </span>
          <Switch
            checked={englishOnly}
            onCheckedChange={onLanguageToggle}
            aria-label="Toggle language"
          />
          <span className={`text-xs font-medium ${englishOnly ? 'text-foreground' : 'text-muted-foreground'}`}>
            EN
          </span>
        </div>

        {/* Dark Mode Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleTheme}
          aria-label="Toggle dark mode"
        >
          {isDarkMode ? (
            <Sun className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
          ) : (
            <Moon className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
          )}
        </Button>

        {/* Settings Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Settings">
              <Settings className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>Accessibility</DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            <div className="px-2 py-2">
              <Label className="text-xs text-muted-foreground mb-2 block">
                Font Size
              </Label>
              <div className="flex gap-1">
                {(['small', 'medium', 'large'] as const).map((size) => (
                  <Button
                    key={size}
                    variant={fontSize === size ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => onFontSizeChange(size)}
                    className="flex-1 capitalize"
                  >
                    {size}
                  </Button>
                ))}
              </div>
            </div>

            <DropdownMenuSeparator />
            
            <div className="px-2 py-2 flex items-center justify-between">
              <Label className="text-sm">High Contrast</Label>
              <Switch
                checked={highContrast}
                onCheckedChange={onHighContrastChange}
              />
            </div>

            <DropdownMenuSeparator />

            {/* Mobile-only options */}
            <div className="md:hidden">
              <DropdownMenuLabel>Model</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => onModelChange('deepseek/deepseek-r1-distill-qwen-14b')}>
                DeepSeek 14B {model.includes('14b') && '✓'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onModelChange('deepseek/deepseek-r1-distill-qwen-32b')}>
                DeepSeek 32B {model.includes('32b') && '✓'}
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <div className="px-2 py-2 flex items-center justify-between sm:hidden">
                <Label className="text-sm">English Only</Label>
                <Switch
                  checked={englishOnly}
                  onCheckedChange={onLanguageToggle}
                />
              </div>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
