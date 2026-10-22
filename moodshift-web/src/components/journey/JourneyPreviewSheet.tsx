import React, { useEffect } from 'react';
import { MoodJourney } from '../../types/journey';
import {
  Play,
  X,
  Sparkles,
  RefreshCw,
  Music,
  ArrowRight,
  Disc3,
  Clock,
  Layers,
  ChevronRight
} from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface JourneyPreviewSheetProps {
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
  useEffect(() => {
    triggerHaptic('light');
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const totalDurationMs = journey.phases.reduce((acc, phase) => {
    return acc + phase.tracks.reduce((tAcc, t) => tAcc + t.track.durationMs, 0);
  }, 0);

  const totalMinutes = Math.round(totalDurationMs / 60000);
  const totalTracks = journey.phases.reduce((acc, p) => acc + p.tracks.length, 0);

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
      <div className="relative z-10 w-full max-w-lg mx-auto bg-[#13192B]/95 backdrop-blur-2xl border-t border-white/10 rounded-t-[32px] shadow-2xl flex flex-col max-h-[90vh] pb-[max(env(safe-area-inset-bottom,0px),16px)] animate-in slide-in-from-bottom duration-300">
        {/* Pull Handle */}
        <div className="pt-3 pb-1 flex justify-center cursor-grab">
          <div className="w-12 h-1.5 rounded-full bg-slate-600/70" />
        </div>

        {/* Header */}
        <div className="px-5 py-2.5 border-b border-white/5 flex items-start justify-between shrink-0">
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                3-PHASE TRANSITION
              </span>
              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                ~{totalMinutes} min · {totalTracks} tracks
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2 m-0">
              <span className="capitalize">{journey.startMood.dominantEmotion || 'Current'}</span>
              <ArrowRight className="w-4 h-4 text-cyan-400" />
              <span className="text-cyan-400">{journey.targetMood.name}</span>
            </h2>
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

        {/* Scrollable Phases */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {journey.phases.map((phase) => (
            <div key={phase.phaseNumber} className="space-y-2">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-mono font-bold flex items-center justify-center border border-cyan-500/40">
                    {phase.phaseNumber}
                  </span>
                  <span className="text-xs font-bold text-white tracking-tight">{phase.name}</span>
                </div>
                <span className="text-[10px] text-slate-400 italic line-clamp-1 max-w-[180px]">
                  {phase.description}
                </span>
              </div>

              {/* Tracks in phase */}
              <div className="space-y-1.5">
                {phase.tracks.map((jt) => (
                  <div
                    key={jt.track.id}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/70"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-slate-800 shrink-0 overflow-hidden border border-white/5 relative">
                        {jt.track.artworkUrl ? (
                          <img src={jt.track.artworkUrl} alt={jt.track.title} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center bg-cyan-950/60">
                            <Music className="w-3.5 h-3.5 text-cyan-400" />
                          </div>
                        )}
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-bold text-white truncate m-0 leading-tight">
                          {jt.track.title}
                        </h4>
                        <p className="text-[10px] text-slate-400 truncate mt-0.5 m-0 leading-tight">
                          {jt.track.artist}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/50">
                        {jt.track.camelotCode || '8B'}
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {jt.targetTempoMultiplier.toFixed(2)}x
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Sticky Action Footer */}
        <div className="p-4 border-t border-white/5 bg-[#13192B] flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => {
              triggerHaptic('light');
              onRegenerate();
            }}
            className="w-12 h-12 rounded-2xl bg-slate-800/90 hover:bg-slate-750 text-slate-300 hover:text-cyan-300 border border-slate-700 flex items-center justify-center shrink-0 active:scale-95 transition-all"
            title="Regenerate Journey"
          >
            <RefreshCw className="w-5 h-5" />
          </button>

          <button
            onClick={() => {
              triggerHaptic('success');
              onStartJourney();
            }}
            className="flex-1 h-12 rounded-2xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold text-sm tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-cyan-400/30 active:scale-98 transition-all"
          >
            <Play className="w-4 h-4 fill-current" />
            START JOURNEY NOW
          </button>
        </div>
      </div>
    </div>
  );
};
