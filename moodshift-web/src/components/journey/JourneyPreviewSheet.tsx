import React from 'react';
import { MoodJourney } from '../../types/journey';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import {
  Play,
  X,
  Compass,
  Sparkles,
  RefreshCw,
  Music,
  ArrowRight,
  Disc3,
  Clock,
  Layers
} from 'lucide-react';

interface JourneyPreviewSheetProps {
  journey: MoodJourney;
  onStartJourney: () => void;
  onRegenerate: () => void;
  onClose: () => void;
}

export const JourneyPreviewSheet: React.FC<JourneyPreviewSheetProps> = ({
  journey,
  onStartJourney,
  onRegenerate,
  onClose
}) => {
  const totalDurationMs = journey.phases.reduce((acc, phase) => {
    return acc + phase.tracks.reduce((tAcc, t) => tAcc + t.track.durationMs, 0);
  }, 0);

  const totalMinutes = Math.round(totalDurationMs / 60000);
  const totalTracks = journey.phases.reduce((acc, p) => acc + p.tracks.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <GlassCard className="w-full max-w-3xl max-h-[92vh] flex flex-col p-6 shadow-2xl border-white/10 overflow-hidden" variant="elevated">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-white/10 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="cyan" size="sm">
                3-Phase Transition Plan
              </Badge>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                ~{totalMinutes} min • {totalTracks} tracks
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
              <span>{journey.startMood.dominantEmotion || 'Current Mood'}</span>
              <ArrowRight className="w-5 h-5 text-cyan-400" />
              <span className="text-cyan-400">{journey.targetMood.name}</span>
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close journey preview"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Phases list */}
        <div className="flex-1 overflow-y-auto py-4 space-y-6 pr-1">
          {journey.phases.map((phase, pIndex) => (
            <div key={phase.id} className="space-y-3">
              {/* Phase Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center border border-cyan-500/30">
                    {phase.phaseNumber}
                  </span>
                  <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
                    {phase.name}
                  </h3>
                </div>
                <span className="text-xs text-slate-400">
                  Target Energy: {Math.round(phase.targetEnergyRange[0] * 100)}% - {Math.round(phase.targetEnergyRange[1] * 100)}%
                </span>
              </div>

              {/* Tracks in Phase */}
              <div className="space-y-2">
                {phase.tracks.map((jTrack, tIndex) => {
                  const tempoShift = Math.round((jTrack.targetTempoMultiplier - 1.0) * 100);
                  const tempoLabel = tempoShift > 0 ? `+${tempoShift}%` : tempoShift < 0 ? `${tempoShift}%` : 'Normal';

                  return (
                    <div
                      key={jTrack.track.id + tIndex}
                      className="p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 flex items-center justify-between gap-3 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {jTrack.track.artworkUrl ? (
                          <img
                            src={jTrack.track.artworkUrl}
                            alt={jTrack.track.title}
                            className="w-12 h-12 rounded-lg object-cover shrink-0 border border-white/10"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 text-slate-400 border border-white/5">
                            <Disc3 className="w-6 h-6" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-white truncate">
                            {jTrack.track.title}
                          </h4>
                          <p className="text-xs text-slate-400 truncate">
                            {jTrack.track.artist}
                          </p>
                          <p className="text-[11px] text-cyan-400/80 truncate mt-0.5">
                            {jTrack.reason}
                          </p>
                        </div>
                      </div>

                      {/* Badges / Metrics */}
                      <div className="flex items-center gap-2 shrink-0">
                        {jTrack.track.camelotCode && (
                          <Badge variant="purple" size="sm">
                            {jTrack.track.camelotCode}
                          </Badge>
                        )}
                        {jTrack.track.tempoBpm && (
                          <span className="text-xs font-mono text-slate-400">
                            {Math.round(jTrack.track.tempoBpm)} BPM
                          </span>
                        )}
                        <Badge
                          variant={tempoShift > 0 ? 'emerald' : tempoShift < 0 ? 'amber' : 'neutral'}
                          size="sm"
                        >
                          {tempoLabel} ({jTrack.targetTempoMultiplier.toFixed(2)}x)
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Footer actions */}
        <div className="pt-4 border-t border-white/10 flex items-center justify-between shrink-0">
          <Button
            variant="ghost"
            onClick={onRegenerate}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Regenerate Chaining
          </Button>

          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onStartJourney}
              icon={<Play className="w-4 h-4 fill-current" />}
            >
              Embark Journey
            </Button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
