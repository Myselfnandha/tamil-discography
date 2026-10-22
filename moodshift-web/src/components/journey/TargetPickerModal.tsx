import React, { useEffect } from 'react';
import { TargetMood, ModeConstraint } from '../../types/mood';
import { DEFAULT_TARGET_MOODS } from '../../data/defaultTargetMoods';
import {
  Waves,
  Target,
  Sun,
  Zap,
  Shield,
  Droplets,
  Moon,
  X,
  Gauge,
  Music2,
  Check
} from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface TargetPickerModalProps {
  selectedMoodId?: string;
  onSelectMood: (mood: TargetMood) => void;
  onClose: () => void;
}

const ICONS_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Waves,
  Target,
  Sun,
  Zap,
  Shield,
  Droplets,
  Moon
};

export const TargetPickerModal: React.FC<TargetPickerModalProps> = ({
  selectedMoodId,
  onSelectMood,
  onClose
}) => {
  useEffect(() => {
    triggerHaptic('light');
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

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

      {/* Android Bottom Sheet */}
      <div className="relative z-10 w-full max-w-lg mx-auto bg-[#13192B]/95 backdrop-blur-2xl border-t border-white/10 rounded-t-[32px] shadow-2xl flex flex-col max-h-[88vh] pb-[max(env(safe-area-inset-bottom,0px),16px)] animate-in slide-in-from-bottom duration-300">
        {/* Android Pull/Drag Handle */}
        <div className="pt-3 pb-1 flex justify-center cursor-grab">
          <div className="w-12 h-1.5 rounded-full bg-slate-600/70" />
        </div>

        {/* Sheet Header */}
        <div className="flex items-center justify-between px-5 py-2.5 border-b border-white/5 shrink-0">
          <div>
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2 m-0">
              <Target className="w-4 h-4 text-cyan-400" />
              Target Mood Destination
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5 m-0">
              Harmonic keys & pitch-locked tempo curve
            </p>
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

        {/* Scrollable Mood List (Optimized for Mobile Thumb Scrolling) */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
          {DEFAULT_TARGET_MOODS.map((mood) => {
            const IconComponent = ICONS_MAP[mood.icon] || Target;
            const isSelected = selectedMoodId === mood.id;

            return (
              <div
                key={mood.id}
                onClick={() => {
                  triggerHaptic('medium');
                  onSelectMood(mood);
                }}
                className={`relative p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer flex items-center justify-between gap-3 active:scale-[0.98] ${
                  isSelected
                    ? 'bg-slate-800/90 border-cyan-400/80 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-400/40'
                    : 'bg-slate-900/60 hover:bg-slate-800/70 border-white/5 hover:border-white/10'
                }`}
              >
                {/* Left: Icon & Text */}
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div
                    className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 border transition-transform duration-200"
                    style={{
                      backgroundColor: `${mood.colorAccent}18`,
                      borderColor: `${mood.colorAccent}40`
                    }}
                  >
                    <span style={{ color: mood.colorAccent }}>
                      <IconComponent className="w-5 h-5" />
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white tracking-tight leading-tight m-0 truncate">
                        {mood.name}
                      </h3>
                      {isSelected && (
                        <span className="w-4 h-4 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center shrink-0">
                          <Check className="w-2.5 h-2.5 stroke-[3]" />
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-1 leading-snug mt-0.5 m-0">
                      {mood.description}
                    </p>

                    {/* Metadata Pills */}
                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-950/60 text-slate-300 border border-slate-800/60 flex items-center gap-1">
                        <Gauge className="w-2.5 h-2.5 text-cyan-400" />
                        {mood.baseTempoMultiplier.toFixed(2)}x
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-950/60 text-slate-300 border border-slate-800/60">
                        {mood.idealBpmRange[0]}–{mood.idealBpmRange[1]} BPM
                      </span>
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                          mood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR
                            ? 'bg-amber-950/40 text-amber-300 border-amber-600/30'
                            : mood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR
                            ? 'bg-indigo-950/40 text-indigo-300 border-indigo-600/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {mood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR
                          ? 'Major Key'
                          : mood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR
                          ? 'Minor Key'
                          : 'Modal'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
