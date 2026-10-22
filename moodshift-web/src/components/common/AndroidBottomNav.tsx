import React from 'react';
import { Compass, Activity, Disc3, Sliders } from 'lucide-react';
import { triggerHaptic } from '../../lib/utils';

export type AndroidNavTab = 'journey' | 'radar' | 'harmonic' | 'dsp';

export interface AndroidBottomNavProps {
  activeTab: AndroidNavTab;
  onTabChange: (tab: AndroidNavTab) => void;
  targetAccentColor?: string;
  hasActivePlayback?: boolean;
}

export const AndroidBottomNav: React.FC<AndroidBottomNavProps> = ({
  activeTab,
  onTabChange,
  targetAccentColor = '#06B6D4',
  hasActivePlayback = false
}) => {
  const tabs = [
    {
      id: 'journey' as const,
      label: 'Journey',
      icon: Compass,
      description: 'Mood Shift'
    },
    {
      id: 'radar' as const,
      label: 'Radar',
      icon: Activity,
      description: 'Emotion Scan'
    },
    {
      id: 'harmonic' as const,
      label: 'Harmonic',
      icon: Disc3,
      description: 'Camelot Keys'
    },
    {
      id: 'dsp' as const,
      label: 'DSP & Audio',
      icon: Sliders,
      description: 'Pitch & Tempo'
    }
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-[#0A0E1A]/95 backdrop-blur-2xl border-t border-white/10 px-3 pt-2 pb-[max(env(safe-area-inset-bottom,0px),10px)] select-none">
      <div className="max-w-md mx-auto flex items-center justify-around">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              onClick={() => {
                triggerHaptic('light');
                onTabChange(tab.id);
              }}
              className="flex flex-col items-center justify-center flex-1 py-1 px-1 transition-all group active:scale-90"
            >
              {/* Material You Pill Indicator */}
              <div
                className={`relative px-4 py-1 rounded-full transition-all duration-300 flex items-center justify-center ${
                  isActive
                    ? 'shadow-md shadow-cyan-500/20'
                    : 'hover:bg-slate-800/40'
                }`}
                style={{
                  backgroundColor: isActive ? `${targetAccentColor}28` : 'transparent'
                }}
              >
                <Icon
                  className={`w-5 h-5 transition-transform duration-200 ${
                    isActive ? 'scale-110' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                  style={{
                    color: isActive ? targetAccentColor : undefined
                  }}
                />
              </div>

              {/* Tab Label */}
              <span
                className={`text-[11px] font-semibold mt-1 tracking-tight transition-colors duration-200 ${
                  isActive ? 'text-white font-bold' : 'text-slate-400'
                }`}
              >
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
