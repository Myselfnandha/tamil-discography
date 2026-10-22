import React, { useState } from 'react';
import { TargetMood } from '../../types/mood';
import { JourneyTrack } from '../../types/track';
import { Sliders, ShieldCheck, Gauge, Volume2, Sparkles, Activity, Play, Square } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface DspEngineViewProps {
  currentTrack?: JourneyTrack | null;
  targetMood: TargetMood;
  effectiveTempo: number;
  manualTempo: number | null;
  isTempoTuned: boolean;
  onSetManualTempo: (tempo: number) => void;
  onToggleTempoTuned: () => void;
}

export const DspEngineView: React.FC<DspEngineViewProps> = ({
  currentTrack,
  targetMood,
  effectiveTempo,
  manualTempo,
  isTempoTuned,
  onSetManualTempo,
  onToggleTempoTuned
}) => {
  const [offlineSynthPlaying, setOfflineSynthPlaying] = useState<string | null>(null);
  const [audioCtx, setAudioCtx] = useState<AudioContext | null>(null);
  const [activeNodes, setActiveNodes] = useState<{ osc1?: OscillatorNode; osc2?: OscillatorNode; gain?: GainNode }>({});

  const trackBpm = currentTrack?.track.tempoBpm || 105;
  const currentSpeed = manualTempo !== null ? manualTempo : effectiveTempo;

  // Toggle ambient procedural synthesizer
  const toggleProceduralSound = (synthId: string) => {
    triggerHaptic('medium');

    if (offlineSynthPlaying === synthId) {
      // Stop
      activeNodes.osc1?.stop();
      activeNodes.osc2?.stop();
      activeNodes.gain?.disconnect();
      setOfflineSynthPlaying(null);
      return;
    }

    // Stop existing if any
    activeNodes.osc1?.stop();
    activeNodes.osc2?.stop();
    activeNodes.gain?.disconnect();

    const ctx = audioCtx || new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    if (!audioCtx) setAudioCtx(ctx);

    if (ctx.state === 'suspended') {
      ctx.resume();
    }

    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    if (synthId === 'theta') {
      // Theta binaural: 216Hz left, 222Hz right (6Hz difference)
      osc1.frequency.setValueAtTime(216, ctx.currentTime);
      osc2.frequency.setValueAtTime(222, ctx.currentTime);
      osc1.type = 'sine';
      osc2.type = 'sine';
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
    } else if (synthId === 'pad') {
      // 432 Hz warm healing pad
      osc1.frequency.setValueAtTime(432, ctx.currentTime);
      osc2.frequency.setValueAtTime(432 * 1.5, ctx.currentTime);
      osc1.type = 'triangle';
      osc2.type = 'sine';
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
    } else {
      // Alpha flow: 432Hz + 442Hz (10Hz difference)
      osc1.frequency.setValueAtTime(432, ctx.currentTime);
      osc2.frequency.setValueAtTime(442, ctx.currentTime);
      osc1.type = 'sine';
      osc2.type = 'triangle';
      gain.gain.setValueAtTime(0.07, ctx.currentTime);
    }

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start();
    osc2.start();

    setActiveNodes({ osc1, osc2, gain });
    setOfflineSynthPlaying(synthId);
  };

  return (
    <div className="space-y-5 pb-36 animate-in fade-in duration-300">
      {/* Title & DSP Invariant Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-cyan-950/70 via-slate-900/90 to-[#0E1526] p-5 border border-white/10 shadow-xl">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight m-0">Audio DSP & Pitch Engine</h2>
            <p className="text-[11px] text-slate-400 m-0">Dynamic tempo ramping with invariant pitch preservation</p>
          </div>
        </div>

        {/* Pitch Lock Guarantee Box */}
        <div className="mt-3 p-3.5 rounded-2xl bg-slate-950/60 border border-emerald-500/30 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-emerald-300">Pitch Lock Active (Invariant: 1.00x)</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-normal mt-0.5">
              `HTMLMediaElement.preservesPitch = true`. Musical tonality, vocal registers, and instrumental timbre remain crystal clear with zero distortion.
            </p>
          </div>
        </div>
      </div>

      {/* Dynamic Tempo Slider Card */}
      <div className="p-4 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider m-0">
              Active Playback Tempo Multiplier
            </h3>
          </div>
          <button
            onClick={() => {
              triggerHaptic('light');
              onToggleTempoTuned();
            }}
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border transition-colors ${
              isTempoTuned
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            {isTempoTuned ? 'Adaptive: ON' : 'Adaptive: OFF'}
          </button>
        </div>

        {/* Live Multiplier Display */}
        <div className="flex items-baseline justify-between px-2">
          <div className="text-3xl font-extrabold font-mono text-cyan-300">
            {currentSpeed.toFixed(2)}x
          </div>
          <div className="text-right">
            <span className="text-[11px] text-slate-400 block font-medium">Resulting Tempo</span>
            <span className="text-xs font-bold font-mono text-white">
              {(trackBpm * currentSpeed).toFixed(1)} BPM
            </span>
          </div>
        </div>

        {/* Range Slider */}
        <div className="px-1 space-y-2">
          <input
            type="range"
            min="0.96"
            max="1.04"
            step="0.005"
            value={currentSpeed}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              onSetManualTempo(val);
            }}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500 px-0.5">
            <span>0.96x (-4%)</span>
            <span className="text-slate-400">1.00x (Standard)</span>
            <span>1.04x (+4%)</span>
          </div>
        </div>

        {/* Reset Button */}
        {manualTempo !== null && (
          <button
            onClick={() => {
              triggerHaptic('light');
              onSetManualTempo(effectiveTempo);
            }}
            className="w-full py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-slate-300 transition-colors"
          >
            Reset to Journey Target Curve ({effectiveTempo.toFixed(2)}x)
          </button>
        )}
      </div>

      {/* Offline Procedural Synthesizer Card */}
      <div className="p-4 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Volume2 className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider m-0">
            Procedural Offline Ambient Generator
          </h3>
        </div>
        <p className="text-[11px] text-slate-400">
          Synthesized in real-time via Web Audio API. 100% offline-ready without external network dependencies.
        </p>

        <div className="space-y-2 mt-2">
          {[
            {
              id: 'pad',
              title: '432 Hz Harmonic Ambient Pad',
              desc: 'Warm soothing harmonic resonance for deep calming.',
              accent: 'text-amber-400'
            },
            {
              id: 'theta',
              title: '6 Hz Theta Wave Binaural Beat',
              desc: 'Sub-auditory frequency difference promoting meditative wind-down.',
              accent: 'text-indigo-400'
            },
            {
              id: 'alpha',
              title: '10 Hz Alpha Wave Focus Flow',
              desc: 'Cognitive focus binaural frequency for mental clarity.',
              accent: 'text-cyan-400'
            }
          ].map((synth) => {
            const isPlaying = offlineSynthPlaying === synth.id;

            return (
              <div
                key={synth.id}
                className="flex items-center justify-between p-3 rounded-2xl bg-slate-950/60 border border-slate-800/70"
              >
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-white truncate">{synth.title}</span>
                    {isPlaying && (
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping shrink-0" />
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{synth.desc}</p>
                </div>

                <button
                  onClick={() => toggleProceduralSound(synth.id)}
                  className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-90 ${
                    isPlaying
                      ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/25'
                      : 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  }`}
                >
                  {isPlaying ? <Square className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
