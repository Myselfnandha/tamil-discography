import React from 'react';
import { FlowMode } from '../../types/mood';
import { PersonalFaceProfile } from '../../types/face';
import { Sparkles, RefreshCw, UserCheck, ShieldCheck, Scan } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export interface AndroidTopBarProps {
  flowMode: FlowMode;
  onFlowModeChange: (mode: FlowMode) => void;
  personalProfile: PersonalFaceProfile | null;
  onOpenCalibration: () => void;
  onOpenManualScan: () => void;
  onRefreshSense: () => void;
  isAutoSensing: boolean;
}

export const AndroidTopBar: React.FC<AndroidTopBarProps> = ({
  flowMode,
  onFlowModeChange,
  personalProfile,
  onOpenCalibration,
  onOpenManualScan,
  onRefreshSense,
  isAutoSensing
}) => {
  return (
    <header className="sticky top-0 z-30 w-full bg-[#0A0E1A]/80 backdrop-blur-xl border-b border-white/5 px-4 pt-[max(env(safe-area-inset-top,0px),10px)] pb-3 select-none">
      <div className="flex items-center justify-between gap-3">
        {/* App Title & Identity */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-600 to-indigo-700 p-0.5 shadow-lg shadow-cyan-500/25 flex items-center justify-center">
            <div className="w-full h-full bg-[#0A0E1A] rounded-[14px] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-base font-extrabold text-white tracking-tight leading-none m-0">MoodShift</h1>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                APP
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium leading-tight mt-0.5">Adaptive Music Journeys</p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          {/* Flow Mode Segmented Pill */}
          <div className="flex items-center p-0.5 bg-slate-900/90 rounded-full border border-slate-800/80 shadow-inner">
            {(['AUTO', 'GUIDED', 'MANUAL'] as const).map((mode) => {
              const isActive = flowMode === mode;
              return (
                <button
                  key={mode}
                  onClick={() => {
                    triggerHaptic('light');
                    onFlowModeChange(mode as FlowMode);
                  }}
                  className={`text-[10px] font-bold px-2 py-1 rounded-full transition-all duration-200 active:scale-95 ${
                    isActive
                      ? 'bg-cyan-500 text-slate-950 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mode === 'AUTO' ? 'Auto' : mode === 'GUIDED' ? 'Guided' : 'Manual'}
                </button>
              );
            })}
          </div>

          {/* Quick Camera Face Scan */}
          <button
            onClick={() => {
              triggerHaptic('medium');
              onOpenManualScan();
            }}
            className="w-8 h-8 rounded-full bg-slate-800/90 border border-slate-700/70 text-slate-200 active:scale-95 flex items-center justify-center transition-all hover:border-cyan-500/50"
            title="Scan Emotion"
          >
            <Scan className="w-3.5 h-3.5 text-cyan-400" />
          </button>

          {/* Calibration Avatar Status */}
          <button
            onClick={() => {
              triggerHaptic('light');
              onOpenCalibration();
            }}
            className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all active:scale-95 ${
              personalProfile
                ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-400'
                : 'bg-slate-800/90 border-slate-700 text-slate-400 hover:text-white'
            }`}
            title={personalProfile ? 'Profile Calibrated' : 'Calibrate Face'}
          >
            {personalProfile ? <ShieldCheck className="w-4 h-4 text-emerald-400" /> : <UserCheck className="w-3.5 h-3.5 text-slate-400" />}
          </button>

          {/* Refresh Sensed Ambient */}
          <button
            onClick={() => {
              triggerHaptic('light');
              onRefreshSense();
            }}
            className="w-8 h-8 rounded-full bg-slate-800/90 border border-slate-700 text-slate-300 hover:text-cyan-300 active:scale-95 flex items-center justify-center transition-colors"
            title="Re-sense Ambient Signals"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isAutoSensing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
