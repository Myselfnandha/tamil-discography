import React from 'react';
import { MoodSnapshot, TargetMood } from '../../types/mood';
import { MoodOrb } from '../common/MoodOrb';
import { Play, SlidersHorizontal, RefreshCw, Zap, Waves, Sun, Target, Shield, Droplets, Moon, Sparkles, ChevronRight } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface FixMyMoodCardProps {
  currentMood: MoodSnapshot;
  recommendedTarget: TargetMood;
  isAutoSensing: boolean;
  onStartJourney: (target: TargetMood) => void;
  onChangeTarget: () => void;
  onOpenCorrection: () => void;
  onRefreshSense: () => void;
}

export const FixMyMoodCard: React.FC<FixMyMoodCardProps> = ({
  currentMood,
  recommendedTarget,
  isAutoSensing,
  onStartJourney,
  onChangeTarget,
  onOpenCorrection,
  onRefreshSense
}) => {
  // Render target icon
  const renderTargetIcon = (iconName: string) => {
    switch (iconName.toLowerCase()) {
      case 'zap': return <Zap className="w-5 h-5 text-red-400" />;
      case 'waves': return <Waves className="w-5 h-5 text-cyan-400" />;
      case 'sun': return <Sun className="w-5 h-5 text-amber-400" />;
      case 'target': return <Target className="w-5 h-5 text-violet-400" />;
      case 'shield': return <Shield className="w-5 h-5 text-emerald-400" />;
      case 'droplets': return <Droplets className="w-5 h-5 text-indigo-400" />;
      case 'moon': return <Moon className="w-5 h-5 text-slate-400" />;
      default: return <Zap className="w-5 h-5 text-cyan-400" />;
    }
  };

  const getMoodHeadline = () => {
    if (currentMood.energy < 0.35) return 'Low energy & depleted';
    if (currentMood.valence < 0.35) return 'Reflective or melancholic';
    if (currentMood.arousal > 0.7) return 'High tension or restlessness';
    if (currentMood.energy > 0.65 && currentMood.valence > 0.65) return 'Vibrant energy & high spirits';
    return 'Balanced, resting state';
  };

  return (
    <div
      className="relative overflow-hidden rounded-3xl border border-white/10 shadow-2xl p-5 select-none transition-all"
      style={{
        background: `radial-gradient(ellipse at top center, ${recommendedTarget.colorAccent}22 0%, rgba(19, 25, 43, 0.95) 75%)`
      }}
    >
      {/* Top Status & Sensor Badge */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            <span className={`w-2 h-2 rounded-full ${isAutoSensing ? 'bg-cyan-400 animate-ping' : 'bg-cyan-400'}`} />
            {isAutoSensing ? 'Scanning ambient...' : 'Real-time State Sensed'}
          </span>
          {currentMood.isPersonalized && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
              Personalized
            </span>
          )}
        </div>

        <button
          onClick={() => {
            triggerHaptic('light');
            onRefreshSense();
          }}
          className="w-8 h-8 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-cyan-300 flex items-center justify-center transition-colors active:scale-95"
          title="Re-sense ambient signals"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isAutoSensing ? 'animate-spin text-cyan-400' : ''}`} />
        </button>
      </div>

      {/* Living Mood Orb Centerpiece */}
      <div className="flex flex-col items-center justify-center py-3">
        <div
          onClick={() => {
            triggerHaptic('medium');
            onOpenCorrection();
          }}
          className="relative cursor-pointer active:scale-95 transition-transform"
        >
          <MoodOrb
            energy={currentMood.energy}
            valence={currentMood.valence}
            arousal={currentMood.arousal}
            size="lg"
          />
          <div className="absolute inset-0 rounded-full border-2 border-cyan-400/20 pointer-events-none" />
        </div>

        {/* Emotion Headline */}
        <h2 className="text-lg sm:text-xl font-extrabold text-white tracking-tight text-center mt-3 mb-1">
          {getMoodHeadline()}
        </h2>

        {/* Energy & Valence Chips */}
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-900/80 text-cyan-300 border border-slate-800">
            Energy: {(currentMood.energy * 100).toFixed(0)}%
          </span>
          <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-900/80 text-emerald-300 border border-slate-800">
            Valence: {(currentMood.valence * 100).toFixed(0)}%
          </span>
          <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-900/80 text-slate-300 border border-slate-800">
            {(currentMood.confidence * 100).toFixed(0)}% Match
          </span>
        </div>
      </div>

      {/* Recommended Destination Card */}
      <div
        onClick={() => {
          triggerHaptic('light');
          onChangeTarget();
        }}
        className="mt-4 p-3.5 rounded-2xl bg-slate-900/85 hover:bg-slate-850 border border-slate-800/90 transition-all cursor-pointer active:scale-[0.98] group"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 border"
              style={{
                backgroundColor: `${recommendedTarget.colorAccent}20`,
                borderColor: `${recommendedTarget.colorAccent}50`
              }}
            >
              {renderTargetIcon(recommendedTarget.icon)}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-400 font-medium">Destination:</span>
                <span className="text-sm font-extrabold text-white">{recommendedTarget.name}</span>
              </div>
              <p className="text-[11px] text-slate-300 truncate mt-0.5 m-0">
                {recommendedTarget.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-cyan-950 text-cyan-300 border border-cyan-800/40">
              {recommendedTarget.baseTempoMultiplier.toFixed(2)}x
            </span>
            <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-colors" />
          </div>
        </div>
      </div>

      {/* Main Action: Primary Full-Width Button */}
      <div className="mt-4 space-y-2">
        <button
          onClick={() => {
            triggerHaptic('success');
            onStartJourney(recommendedTarget);
          }}
          className="w-full h-14 rounded-2xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-black text-sm tracking-wider uppercase flex items-center justify-center gap-2 shadow-xl shadow-cyan-400/25 active:scale-[0.98] transition-transform"
        >
          <Play className="w-5 h-5 fill-current" />
          START SHIFT JOURNEY
        </button>

        {/* Secondary Sub-actions */}
        <div className="flex items-center justify-between pt-1 px-1">
          <button
            onClick={() => {
              triggerHaptic('light');
              onChangeTarget();
            }}
            className="text-xs text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Change Target</span>
          </button>

          <button
            onClick={() => {
              triggerHaptic('light');
              onOpenCorrection();
            }}
            className="text-xs text-slate-400 hover:text-cyan-300 transition-colors"
          >
            Correct Sensed Mood ›
          </button>
        </div>
      </div>
    </div>
  );
};
