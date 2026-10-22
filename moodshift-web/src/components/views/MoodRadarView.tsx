import React from 'react';
import { MoodSnapshot, EmotionLabel } from '../../types/mood';
import { PersonalFaceProfile } from '../../types/face';
import { Activity, Camera, ShieldCheck, UserCheck, RefreshCw, Sparkles } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface MoodRadarViewProps {
  currentMood: MoodSnapshot;
  personalProfile: PersonalFaceProfile | null;
  onOpenSelfReportWheel: () => void;
  onOpenManualScan: () => void;
  onOpenCalibration: () => void;
  onRefreshSense: () => void;
  isAutoSensing: boolean;
}

export const MoodRadarView: React.FC<MoodRadarViewProps> = ({
  currentMood,
  personalProfile,
  onOpenSelfReportWheel,
  onOpenManualScan,
  onOpenCalibration,
  onRefreshSense,
  isAutoSensing
}) => {
  // Determine Quadrant
  const getQuadrant = (valence: number, energy: number) => {
    if (energy >= 0.5 && valence >= 0.5) return { name: 'Vibrant & Energized', color: 'text-amber-400', bg: 'bg-amber-950/30' };
    if (energy < 0.5 && valence >= 0.5) return { name: 'Calm & Restorative', color: 'text-cyan-400', bg: 'bg-cyan-950/30' };
    if (energy >= 0.5 && valence < 0.5) return { name: 'High Tension / Restless', color: 'text-rose-400', bg: 'bg-rose-950/30' };
    return { name: 'Depleted / Melancholic', color: 'text-indigo-400', bg: 'bg-indigo-950/30' };
  };

  const quad = getQuadrant(currentMood.valence, currentMood.energy);

  return (
    <div className="space-y-5 pb-36 animate-in fade-in duration-300">
      {/* Title & Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-950/60 via-slate-900/90 to-[#0E1526] p-5 border border-white/10 shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight m-0">Emotion & Sensor Radar</h2>
              <p className="text-[11px] text-slate-400 m-0">Multi-signal psychological state fusion</p>
            </div>
          </div>

          <button
            onClick={() => {
              triggerHaptic('light');
              onRefreshSense();
            }}
            className="w-8 h-8 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300 hover:text-cyan-300 flex items-center justify-center transition-colors active:scale-95"
            title="Refresh Ambient Signal"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAutoSensing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>

        {/* Quadrant Classification */}
        <div className="mt-3 p-3 rounded-2xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs text-slate-400 font-medium">State:</span>
            <span className={`text-xs font-bold ${quad.color}`}>{quad.name}</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
            {(currentMood.dominantEmotion || 'neutral').toUpperCase()}
          </span>
        </div>
      </div>

      {/* Interactive 2D Quadrant Radar Preview Card */}
      <div className="p-5 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider m-0">
            2D Valence–Energy Coordinate Space
          </h3>
          <span className="text-[10px] font-mono text-cyan-400 font-bold">
            ({currentMood.valence.toFixed(2)}, {currentMood.energy.toFixed(2)})
          </span>
        </div>

        {/* 2D Plane Box */}
        <div
          onClick={() => {
            triggerHaptic('medium');
            onOpenSelfReportWheel();
          }}
          className="relative w-full aspect-square max-w-[280px] mx-auto rounded-2xl bg-slate-950/90 border border-slate-800/80 p-3 flex items-center justify-center cursor-pointer group active:scale-[0.98] transition-transform"
        >
          {/* Axis Crosshairs */}
          <div className="absolute inset-x-3 top-1/2 h-[1px] bg-slate-800 pointer-events-none" />
          <div className="absolute inset-y-3 left-1/2 w-[1px] bg-slate-800 pointer-events-none" />

          {/* Quadrant Background Accents */}
          <div className="absolute top-3 right-3 text-[9px] font-bold text-amber-500/40 uppercase">Joy / Energy</div>
          <div className="absolute bottom-3 right-3 text-[9px] font-bold text-cyan-500/40 uppercase">Calm / Peace</div>
          <div className="absolute top-3 left-3 text-[9px] font-bold text-rose-500/40 uppercase">Tension</div>
          <div className="absolute bottom-3 left-3 text-[9px] font-bold text-indigo-500/40 uppercase">Melancholy</div>

          {/* Sensed Mood Coordinate Indicator */}
          <div
            className="absolute w-7 h-7 rounded-full bg-cyan-400/30 border-2 border-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-400/50 transition-all duration-700 pointer-events-none"
            style={{
              left: `calc(${currentMood.valence * 80 + 10}% - 14px)`,
              bottom: `calc(${currentMood.energy * 80 + 10}% - 14px)`
            }}
          >
            <div className="w-2.5 h-2.5 rounded-full bg-white shadow-sm" />
          </div>

          <span className="absolute bottom-1.5 inset-x-0 text-center text-[10px] text-slate-500 font-medium group-hover:text-cyan-400 transition-colors">
            Tap to open interactive self-report wheel ›
          </span>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2 text-center pt-1">
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <span className="text-[10px] text-slate-400 block">Valence</span>
            <span className="text-sm font-bold font-mono text-cyan-300">
              {(currentMood.valence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <span className="text-[10px] text-slate-400 block">Energy</span>
            <span className="text-sm font-bold font-mono text-emerald-300">
              {(currentMood.energy * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
            <span className="text-[10px] text-slate-400 block">Confidence</span>
            <span className="text-sm font-bold font-mono text-white">
              {(currentMood.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Sensor Tools Grid */}
      <div className="grid grid-cols-2 gap-3">
        {/* Camera Face Diagnostic */}
        <button
          onClick={() => {
            triggerHaptic('medium');
            onOpenManualScan();
          }}
          className="p-4 rounded-3xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800/80 text-left transition-all active:scale-95 space-y-2 group"
        >
          <div className="w-9 h-9 rounded-2xl bg-cyan-500/15 text-cyan-400 flex items-center justify-center border border-cyan-500/30 group-hover:scale-110 transition-transform">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white m-0">Camera Face Scan</h4>
            <p className="text-[10px] text-slate-400 leading-tight mt-1 m-0">
              Private on-device expression estimation.
            </p>
          </div>
        </button>

        {/* Face Calibration Profile */}
        <button
          onClick={() => {
            triggerHaptic('medium');
            onOpenCalibration();
          }}
          className="p-4 rounded-3xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800/80 text-left transition-all active:scale-95 space-y-2 group"
        >
          <div className="w-9 h-9 rounded-2xl bg-purple-500/15 text-purple-400 flex items-center justify-center border border-purple-500/30 group-hover:scale-110 transition-transform">
            {personalProfile ? <ShieldCheck className="w-4 h-4 text-emerald-400" /> : <UserCheck className="w-4 h-4 text-purple-400" />}
          </div>
          <div>
            <h4 className="text-xs font-bold text-white m-0">Personal Profile</h4>
            <p className="text-[10px] text-slate-400 leading-tight mt-1 m-0">
              {personalProfile ? 'Profile Calibrated (90%+)' : 'Calibrate your resting baseline.'}
            </p>
          </div>
        </button>
      </div>
    </div>
  );
};
