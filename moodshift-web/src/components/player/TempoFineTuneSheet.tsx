import React from 'react';
import { GlassCard } from '../common/GlassCard';
import { Slider } from '../common/Slider';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { JourneyTrack } from '../../types/track';
import { TargetMood } from '../../types/mood';
import {
  Gauge,
  Sliders,
  X,
  RotateCcw,
  ShieldCheck,
  Zap,
  Info
} from 'lucide-react';

interface TempoFineTuneSheetProps {
  currentTrack: JourneyTrack | null;
  targetMood: TargetMood;
  effectiveTempo: number;
  manualTempo: number | null;
  isTempoTuned: boolean;
  onSetManualTempo: (tempo: number | null) => void;
  onToggleTempoTuned: () => void;
  onClose: () => void;
}

export const TempoFineTuneSheet: React.FC<TempoFineTuneSheetProps> = ({
  currentTrack,
  targetMood,
  effectiveTempo,
  manualTempo,
  isTempoTuned,
  onSetManualTempo,
  onToggleTempoTuned,
  onClose
}) => {
  const nativeBpm = currentTrack?.track.tempoBpm || 110;
  const shiftedBpm = Math.round(nativeBpm * effectiveTempo);
  const tempoPercent = Math.round((effectiveTempo - 1.0) * 100);
  const tempoSign = tempoPercent > 0 ? `+${tempoPercent}%` : tempoPercent < 0 ? `${tempoPercent}%` : '0%';

  const isGuardrailed =
    (nativeBpm > 130 && targetMood.baseTempoMultiplier > 1.0) ||
    (nativeBpm < 70 && targetMood.baseTempoMultiplier < 1.0);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <GlassCard className="w-full max-w-lg p-6 flex flex-col gap-5 rounded-t-[32px] sm:rounded-2xl border-white/10 shadow-2xl pb-[max(env(safe-area-inset-bottom,0px),20px)]" variant="elevated">
        {/* Android Pull/Drag Handle */}
        <div className="pt-1 pb-1 flex justify-center cursor-grab -mt-2 sm:hidden">
          <div className="w-12 h-1.5 rounded-full bg-slate-600/70" />
        </div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
              <Gauge className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Tempo Modulation Fine-Tune
              </h3>
              <p className="text-xs text-slate-400">
                Subtle entrainment modulation (0.96x – 1.04x)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close tempo fine tune"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Pitch Lock Invariant Notice */}
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-xs text-emerald-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Pitch Invariant Locked at 1.0x: </span>
            Browser time-stretches tempo without altering musical key, chord harmonies, or vocal pitch.
          </div>
        </div>

        {/* Live Values */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-white/5 border border-white/5">
            <span className="text-[11px] uppercase tracking-wider text-slate-400">Current Tempo</span>
            <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">
              {effectiveTempo.toFixed(2)}x
              <span className="text-xs text-slate-400 font-sans ml-1.5">({tempoSign})</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-white/5 border border-white/5">
            <span className="text-[11px] uppercase tracking-wider text-slate-400">Effective Pace</span>
            <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
              {shiftedBpm} BPM
              <span className="text-xs text-slate-400 font-sans ml-1.5">(was {Math.round(nativeBpm)})</span>
            </div>
          </div>
        </div>

        {/* Guardrail status */}
        {isGuardrailed && (
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center gap-2 text-xs text-amber-300">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Dynamic Guardrail Active: Song native BPM is {Math.round(nativeBpm)}. Tempo boost dampened to prevent unnatural rushing.
            </span>
          </div>
        )}

        {/* Slider */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span>Relaxed (0.96x)</span>
            <span className="font-semibold text-white">Modulation Slider</span>
            <span>Energized (1.04x)</span>
          </div>

          <Slider
            min={0.96}
            max={1.04}
            step={0.01}
            value={effectiveTempo}
            onChange={(val) => onSetManualTempo(val)}
            formatValue={(v) => `${v.toFixed(2)}x`}
          />
        </div>

        {/* Action Controls */}
        <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSetManualTempo(null)}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
            disabled={manualTempo === null}
          >
            Reset to Target ({targetMood.baseTempoMultiplier.toFixed(2)}x)
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={onClose}
          >
            Done
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
