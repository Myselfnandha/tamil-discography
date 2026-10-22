import React from 'react';
import { MoodSnapshot, TargetMood } from '../../types/mood';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { MoodOrb } from '../common/MoodOrb';
import { Play, SlidersHorizontal, RefreshCw, Zap, Waves, Sun, Target, Shield, Droplets, Moon } from 'lucide-react';

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

  // Convert float 0-1 to dots
  const renderDots = (value: number) => {
    const totalDots = 5;
    const filledDots = Math.round(value * totalDots);
    return (
      <span className="inline-flex gap-1 items-center font-mono text-sm tracking-tighter">
        {Array.from({ length: totalDots }).map((_, i) => (
          <span
            key={i}
            className={`w-2 h-2 rounded-full transition-colors ${
              i < filledDots ? 'bg-cyan-400 shadow-sm shadow-cyan-400/50' : 'bg-slate-700'
            }`}
          />
        ))}
      </span>
    );
  };

  const getMoodHeadline = () => {
    if (currentMood.energy < 0.35) return 'You seem low energy & depleted';
    if (currentMood.valence < 0.35) return 'Feeling reflective or melancholic';
    if (currentMood.arousal > 0.7) return 'Sensing restlessness or high tension';
    if (currentMood.energy > 0.65 && currentMood.valence > 0.65) return 'Vibrant energy & high spirits detected';
    return 'Balanced, resting state observed';
  };

  return (
    <GlassCard
      className="relative overflow-hidden border border-white/10 shadow-2xl shadow-cyan-950/20"
      style={{
        background: `radial-gradient(ellipse at top right, ${recommendedTarget.colorAccent}15 0%, rgba(26, 31, 46, 0.85) 60%)`
      }}
    >
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
        {/* Left Section: Mood Diagnosis */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              <span className={`w-2 h-2 rounded-full ${isAutoSensing ? 'bg-cyan-400 animate-ping' : 'bg-cyan-400'}`} />
              {isAutoSensing ? 'Sensing ambient signals...' : '✨ Mood Sensed'}
            </span>
            <button
              onClick={onRefreshSense}
              className="text-slate-400 hover:text-cyan-300 p-1 rounded-lg hover:bg-slate-800/60 transition-colors"
              title="Re-sense ambient signals"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isAutoSensing ? 'animate-spin' : ''}`} />
            </button>
            {currentMood.isPersonalized && (
              <Badge variant="emerald" size="sm">
                Personalized
              </Badge>
            )}
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {getMoodHeadline()}
          </h2>

          {/* Gauges */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 font-medium">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Energy:</span>
              {renderDots(currentMood.energy)}
              <span className="text-slate-400 font-mono text-[11px]">({(currentMood.energy * 100).toFixed(0)}%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Valence:</span>
              {renderDots(currentMood.valence)}
              <span className="text-slate-400 font-mono text-[11px]">({(currentMood.valence * 100).toFixed(0)}%)</span>
            </div>
            <div className="text-slate-400 text-[11px]">
              Confidence: <span className="text-white font-mono">{(currentMood.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Recommended Target Box */}
          <div className="pt-2">
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border"
                  style={{
                    backgroundColor: `${recommendedTarget.colorAccent}15`,
                    borderColor: `${recommendedTarget.colorAccent}40`
                  }}
                >
                  {renderTargetIcon(recommendedTarget.icon)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 font-medium">Recommended Destination:</span>
                    <span className="text-sm font-bold text-white">{recommendedTarget.name}</span>
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-1">{recommendedTarget.description}</p>
                </div>
              </div>

              {/* Tonality & Tempo Badges */}
              <div className="flex items-center gap-2 shrink-0">
                <Badge variant="cyan" size="sm">
                  Tempo {recommendedTarget.baseTempoMultiplier.toFixed(2)}x
                </Badge>
                <Badge variant="outline" size="sm">
                  {recommendedTarget.idealBpmRange[0]}–{recommendedTarget.idealBpmRange[1]} BPM
                </Badge>
              </div>
            </div>
          </div>

          {/* CTAs */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="primary"
              size="lg"
              icon={<Play className="w-5 h-5 fill-current" />}
              onClick={() => onStartJourney(recommendedTarget)}
              className="shadow-xl shadow-cyan-500/25"
            >
              START JOURNEY (2-TAPS)
            </Button>

            <Button
              variant="outline"
              size="md"
              icon={<SlidersHorizontal className="w-4 h-4" />}
              onClick={onChangeTarget}
            >
              Change Destination
            </Button>

            <button
              onClick={onOpenCorrection}
              className="text-xs text-slate-400 hover:text-cyan-300 hover:underline transition-colors ml-auto sm:ml-0"
            >
              Not feeling this? Tap to correct ›
            </button>
          </div>
        </div>

        {/* Right Section: Living Dynamic Orb */}
        <div className="flex flex-col items-center justify-center shrink-0 w-full md:w-auto pt-2 md:pt-0">
          <MoodOrb
            energy={currentMood.energy}
            valence={currentMood.valence}
            arousal={currentMood.arousal}
            size="lg"
            className="cursor-pointer"
          />
          <span className="text-[11px] text-slate-400 font-medium mt-2">Living Mood Resonance</span>
        </div>
      </div>
    </GlassCard>
  );
};
