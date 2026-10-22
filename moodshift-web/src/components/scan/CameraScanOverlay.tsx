import React from 'react';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { EmotionLabel } from '../../types/mood';
import { X, Camera, Sparkles, Check, Smile, Frown, Meh, Flame, Zap } from 'lucide-react';

export interface CameraScanOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyEmotion: (emotion: EmotionLabel) => void;
  detectedEmotion: EmotionLabel;
  detectedConfidence: number;
  isStreaming: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onRequestCamera: () => Promise<boolean>;
}

export const CameraScanOverlay: React.FC<CameraScanOverlayProps> = ({
  isOpen,
  onClose,
  onApplyEmotion,
  detectedEmotion,
  detectedConfidence,
  isStreaming,
  videoRef,
  onRequestCamera
}) => {
  if (!isOpen) return null;

  const emotionList: { label: EmotionLabel; icon: React.ReactNode; color: string }[] = [
    { label: EmotionLabel.HAPPY, icon: <Smile className="w-4 h-4" />, color: '#10B981' },
    { label: EmotionLabel.NEUTRAL, icon: <Meh className="w-4 h-4" />, color: '#06B6D4' },
    { label: EmotionLabel.SAD, icon: <Frown className="w-4 h-4" />, color: '#6366F1' },
    { label: EmotionLabel.SURPRISED, icon: <Zap className="w-4 h-4" />, color: '#F59E0B' },
    { label: EmotionLabel.ANGRY, icon: <Flame className="w-4 h-4" />, color: '#EF4444' }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <GlassCard className="w-full max-w-xl p-6 space-y-5 border border-cyan-500/30 shadow-2xl relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Manual Mood Diagnostic Scan</h3>
              <p className="text-xs text-slate-400">TFLite FER model + Personal Calibration Pipeline</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Viewfinder */}
        <div className="relative aspect-video rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
          {isStreaming ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover transform -scale-x-100"
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-slate-500 gap-2 p-6 text-center">
              <Camera className="w-10 h-10 text-slate-600 mb-1" />
              <Button variant="outline" size="sm" onClick={onRequestCamera}>
                Enable Live Camera
              </Button>
            </div>
          )}

          {/* Sensed Emotion Tag overlay */}
          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs font-bold text-white uppercase">{detectedEmotion}</span>
            <span className="text-xs text-cyan-300 font-mono">({(detectedConfidence * 100).toFixed(0)}%)</span>
          </div>
        </div>

        {/* Expression Simulator Quick Toggles */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1">
            <span>Simulate / Force Sensed Expression:</span>
            <span>Instant Preview</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {emotionList.map(item => (
              <button
                key={item.label}
                onClick={() => onApplyEmotion(item.label)}
                className={`touch-target-48 p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  detectedEmotion === item.label
                    ? 'bg-cyan-500/20 border-cyan-400 text-white shadow-md shadow-cyan-500/20'
                    : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850'
                }`}
              >
                <span style={{ color: item.color }}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
          <Button variant="ghost" size="md" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            icon={<Check className="w-4 h-4" />}
            onClick={onClose}
          >
            Apply Sensed Mood
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
