import React from 'react';
import { TargetMood, ModeConstraint } from '../../types/mood';
import { DEFAULT_TARGET_MOODS } from '../../data/defaultTargetMoods';
import { GlassCard } from '../common/GlassCard';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
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

interface TargetPickerModalProps {
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <GlassCard className="w-full max-w-4xl max-h-[90vh] flex flex-col p-6 shadow-2xl border-white/10 overflow-hidden" variant="elevated">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10 shrink-0">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Target className="w-5 h-5 text-cyan-400" />
              Choose Your Target Emotional State
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select your goal. MoodShift modulates tempo (0.96x – 1.04x) with pitch locked at 1.0x and harmonic Camelot key transitions.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close target mood picker"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mood Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 py-4 overflow-y-auto pr-1">
          {DEFAULT_TARGET_MOODS.map((mood) => {
            const IconComponent = ICONS_MAP[mood.icon] || Target;
            const isSelected = selectedMoodId === mood.id;
            const tempoPercent = Math.round((mood.baseTempoMultiplier - 1.0) * 100);
            const tempoSign = tempoPercent > 0 ? `+${tempoPercent}%` : tempoPercent < 0 ? `${tempoPercent}%` : 'Normal';

            return (
              <div
                key={mood.id}
                onClick={() => onSelectMood(mood)}
                className={`group relative p-4 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col justify-between gap-3 ${
                  isSelected
                    ? 'bg-white/10 border-cyan-400/80 shadow-[0_0_20px_rgba(6,182,212,0.25)] ring-1 ring-cyan-400/50'
                    : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.07] hover:border-white/20'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between mb-2">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center border"
                      style={{
                        backgroundColor: `${mood.colorAccent}20`,
                        borderColor: `${mood.colorAccent}40`,
                        color: mood.colorAccent
                      }}
                    >
                      <IconComponent className="w-5 h-5" />
                    </div>
                    {isSelected && (
                      <div className="w-6 h-6 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center">
                        <Check className="w-4 h-4 stroke-[3]" />
                      </div>
                    )}
                  </div>

                  <h3 className="text-base font-semibold text-white tracking-tight group-hover:text-cyan-300 transition-colors">
                    {mood.name}
                  </h3>
                  <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                    {mood.description}
                  </p>
                </div>

                {/* Technical / Audio Characteristics */}
                <div className="pt-2 border-t border-white/5 flex flex-col gap-1.5 text-[11px]">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1">
                      <Gauge className="w-3.5 h-3.5 text-slate-500" />
                      Tempo Shift
                    </span>
                    <span className="font-mono font-medium text-white">
                      {tempoSign} ({mood.baseTempoMultiplier.toFixed(2)}x)
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1">
                      <Music2 className="w-3.5 h-3.5 text-slate-500" />
                      Ideal BPM
                    </span>
                    <span className="font-mono text-slate-300">
                      {mood.idealBpmRange[0]}-{mood.idealBpmRange[1]} BPM
                    </span>
                  </div>

                  <div className="flex items-center justify-between mt-1">
                    <Badge
                      variant={
                        mood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR
                          ? 'emerald'
                          : mood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR
                          ? 'purple'
                          : 'neutral'
                      }
                      size="sm"
                    >
                      {mood.phase3ModeConstraint === ModeConstraint.STRICT_MAJOR
                        ? 'Phase 3: Strict Major'
                        : mood.phase3ModeConstraint === ModeConstraint.STRICT_MINOR
                        ? 'Phase 3: Strict Minor'
                        : 'Phase 3: Flexible Mode'}
                    </Badge>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-white/10 flex items-center justify-between shrink-0">
          <div className="text-[11px] text-slate-500 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Zero pitch alteration (Web Audio preserves 1.0x key pitch)
          </div>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
