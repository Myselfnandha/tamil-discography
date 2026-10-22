import React from 'react';
import { FlowMode } from '../../types/mood';
import { PersonalFaceProfile } from '../../types/face';
import { Sparkles, Scan, UserCheck, ShieldCheck } from 'lucide-react';

export interface TopHeaderProps {
  flowMode: FlowMode;
  onFlowModeChange: (mode: FlowMode) => void;
  personalProfile: PersonalFaceProfile | null;
  onOpenCalibration: () => void;
  onOpenManualScan: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  flowMode,
  onFlowModeChange,
  personalProfile,
  onOpenCalibration,
  onOpenManualScan
}) => {
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    if (hour < 21) return 'Good Evening';
    return 'Peaceful Night';
  };

  return (
    <header className="w-full flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4 px-2 select-none">
      {/* Brand & Greeting */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white m-0">MoodShift</h1>
            <span className="text-[10px] tracking-wider uppercase px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 font-mono border border-cyan-800/40">
              Web OS
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium m-0">{getGreeting()} · Adaptive Music Journeys</p>
        </div>
      </div>

      {/* Right Action Cluster: Flow Mode + Calibration + Scan */}
      <div className="flex items-center flex-wrap gap-2.5">
        {/* Flow Mode Switcher */}
        <div className="flex items-center bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => onFlowModeChange(FlowMode.AUTO)}
            className={`text-xs px-2.5 py-1.5 rounded-lg transition-all font-medium ${
              flowMode === FlowMode.AUTO
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Auto Mode: Open & play immediately without decisions"
          >
            Auto
          </button>
          <button
            onClick={() => onFlowModeChange(FlowMode.GUIDED)}
            className={`text-xs px-2.5 py-1.5 rounded-lg transition-all font-medium ${
              flowMode === FlowMode.GUIDED
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Guided Mode: Ambient card with 1-tap start (Default)"
          >
            Guided
          </button>
          <button
            onClick={() => onFlowModeChange(FlowMode.MANUAL)}
            className={`text-xs px-2.5 py-1.5 rounded-lg transition-all font-medium ${
              flowMode === FlowMode.MANUAL
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Manual Mode: Full diagnostic camera and mood selection"
          >
            Manual
          </button>
        </div>

        {/* Face Calibration Pill */}
        <button
          onClick={onOpenCalibration}
          className={`touch-target-48 text-xs px-3 py-1.5 rounded-xl border transition-all flex items-center gap-1.5 cursor-pointer ${
            personalProfile
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/50'
              : 'bg-slate-900/70 border-slate-700 text-slate-300 hover:border-slate-500 hover:text-white'
          }`}
          title="On-device personal face enrollment"
        >
          {personalProfile ? (
            <>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Face Calibrated (90%+)</span>
            </>
          ) : (
            <>
              <UserCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>Calibrate Face</span>
            </>
          )}
        </button>

        {/* Diagnostic Scan CTA */}
        <button
          onClick={onOpenManualScan}
          className="touch-target-48 text-xs px-3 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-750 text-slate-200 hover:text-white border border-slate-700/80 transition-all flex items-center gap-1.5 cursor-pointer"
        >
          <Scan className="w-3.5 h-3.5 text-cyan-400" />
          <span>Scan</span>
        </button>
      </div>
    </header>
  );
};
