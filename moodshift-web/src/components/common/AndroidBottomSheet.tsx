import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface AndroidBottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  maxHeight?: string;
}

export const AndroidBottomSheet: React.FC<AndroidBottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxHeight = 'max-h-[85vh]'
}) => {
  useEffect(() => {
    if (isOpen) {
      triggerHaptic('light');
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
        onClick={() => {
          triggerHaptic('light');
          onClose();
        }}
      />

      {/* Sheet Container */}
      <div
        className={`relative z-10 w-full max-w-lg mx-auto bg-[#13192B]/95 backdrop-blur-2xl border-t border-white/10 rounded-t-[32px] shadow-2xl flex flex-col ${maxHeight} pb-[max(env(safe-area-inset-bottom,0px),16px)] animate-in slide-in-from-bottom duration-300 overscroll-contain`}
      >
        {/* Android Pull/Drag Handle */}
        <div className="pt-3 pb-1 cursor-grab active:cursor-grabbing flex justify-center">
          <div className="w-12 h-1.5 rounded-full bg-slate-600/70 active:bg-slate-500 transition-colors" />
        </div>

        {/* Header if title provided */}
        {(title || subtitle) && (
          <div className="flex items-center justify-between px-6 py-2.5 border-b border-white/5">
            <div>
              {title && <h3 className="text-lg font-bold text-white tracking-tight m-0">{title}</h3>}
              {subtitle && <p className="text-xs text-slate-400 font-medium m-0">{subtitle}</p>}
            </div>
            <button
              onClick={() => {
                triggerHaptic('light');
                onClose();
              }}
              className="w-8 h-8 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Scrollable Sheet Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {children}
        </div>
      </div>
    </div>
  );
};
