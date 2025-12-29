import { useState, useEffect, useCallback } from 'react';

type FontSize = 'small' | 'medium' | 'large';

interface AccessibilitySettings {
  fontSize: FontSize;
  highContrast: boolean;
  reduceMotion: boolean;
}

const fontSizeMap: Record<FontSize, string> = {
  small: '14px',
  medium: '16px',
  large: '18px',
};

export function useAccessibility() {
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('holowellness_accessibility');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch (e) {
          console.error('Failed to parse accessibility settings:', e);
        }
      }
    }
    return {
      fontSize: 'medium',
      highContrast: false,
      reduceMotion: false,
    };
  });

  useEffect(() => {
    const root = document.documentElement;
    
    // Apply font size
    root.style.fontSize = fontSizeMap[settings.fontSize];
    
    // Apply high contrast
    if (settings.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
    
    // Apply reduce motion
    if (settings.reduceMotion) {
      root.classList.add('reduce-motion');
    } else {
      root.classList.remove('reduce-motion');
    }

    // Save to localStorage
    localStorage.setItem('holowellness_accessibility', JSON.stringify(settings));
  }, [settings]);

  const setFontSize = useCallback((fontSize: FontSize) => {
    setSettings(prev => ({ ...prev, fontSize }));
  }, []);

  const setHighContrast = useCallback((highContrast: boolean) => {
    setSettings(prev => ({ ...prev, highContrast }));
  }, []);

  const setReduceMotion = useCallback((reduceMotion: boolean) => {
    setSettings(prev => ({ ...prev, reduceMotion }));
  }, []);

  return {
    ...settings,
    setFontSize,
    setHighContrast,
    setReduceMotion,
  };
}
