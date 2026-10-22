import React from 'react';

export interface SliderProps {
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  label?: string;
  valueDisplay?: string | number;
  formatValue?: (value: number) => string;
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  min,
  max,
  step = 0.01,
  value,
  onChange,
  label,
  valueDisplay,
  formatValue,
  className = ''
}) => {
  const percentage = ((value - min) / (max - min)) * 100;
  const displayVal = formatValue ? formatValue(value) : valueDisplay !== undefined ? valueDisplay : value;

  return (
    <div className={`w-full flex flex-col gap-2 ${className}`}>
      {(label || valueDisplay !== undefined || formatValue !== undefined) && (
        <div className="flex items-center justify-between text-xs font-medium text-slate-300">
          <span>{label}</span>
          <span className="font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
            {displayVal}
          </span>
        </div>
      )}
      <div className="relative flex items-center h-6 select-none touch-none">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={e => onChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
          style={{
            background: `linear-gradient(to right, #06B6D4 0%, #06B6D4 ${percentage}%, #1E293B ${percentage}%, #1E293B 100%)`
          }}
        />
      </div>
    </div>
  );
};
