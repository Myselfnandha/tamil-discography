import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Triggers subtle tactile mobile feedback via navigator.vibrate if supported on Android.
 */
export function triggerHaptic(type: 'light' | 'medium' | 'success' | 'warning' = 'light') {
  if (typeof window !== 'undefined' && 'vibrate' in navigator) {
    try {
      switch (type) {
        case 'light':
          navigator.vibrate(8);
          break;
        case 'medium':
          navigator.vibrate(18);
          break;
        case 'success':
          navigator.vibrate([12, 40, 15]);
          break;
        case 'warning':
          navigator.vibrate([25, 50, 25]);
          break;
      }
    } catch {
      // Ignore vibration errors if blocked by platform policy
    }
  }
}
