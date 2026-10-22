import React, { useEffect, useState } from 'react';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { Shield, Sparkles, X, Check, Camera, RefreshCw } from 'lucide-react';

export interface FaceCalibrationModalProps {
  isOpen: boolean;
  step: number;
  onAdvance: () => void;
  onCancel: () => void;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isStreaming: boolean;
  onRequestCamera: () => Promise<boolean>;
}

export const FaceCalibrationModal: React.FC<FaceCalibrationModalProps> = ({
  isOpen,
  step,
  onAdvance,
  onCancel,
  videoRef,
  isStreaming,
  onRequestCamera
}) => {
  const [countdown, setCountdown] = useState(3);
  const [capturing, setCapturing] = useState(false);

  const stepDetails = [
    {
      step: 1,
      title: 'Neutral Resting Baseline',
      desc: 'Relax your facial muscles completely and look naturally at the ring. This is your personal baseline.',
      duration: 3
    },
    {
      step: 2,
      title: 'Genuine Smile Expression',
      desc: 'Give us your natural, genuine smile. Capturing your unique cheek and eye curvature.',
      duration: 3
    },
    {
      step: 3,
      title: 'Low Energy & Tired Expression',
      desc: 'Think of something draining or relaxing after a long day. Helps calibrate low-energy states.',
      duration: 3
    },
    {
      step: 4,
      title: 'High Arousal & Surprised',
      desc: 'Open your eyes wide and look surprised! Captures elevated arousal landmarks.',
      duration: 3
    },
    {
      step: 5,
      title: '3D Head Geometry & Mesh',
      desc: 'Slowly rotate your head in a small circle to map 468 3D facial landmarks.',
      duration: 5
    }
  ];

  const currentStepInfo = stepDetails[step - 1] || stepDetails[0];

  useEffect(() => {
    if (isOpen && !isStreaming) {
      onRequestCamera();
    }
  }, [isOpen, isStreaming, onRequestCamera]);

  useEffect(() => {
    if (isOpen) {
      setCountdown(currentStepInfo.duration);
      setCapturing(true);
      const interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(interval);
            setCapturing(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isOpen, step, currentStepInfo.duration]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <GlassCard className="w-full max-w-lg p-6 space-y-5 border border-cyan-500/30 shadow-2xl shadow-cyan-950/40 relative">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Let's Learn Your Face</h3>
              <p className="text-xs text-slate-400">Step {step} of 5 · Boosts detection to ~90%+ accuracy</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Camera Viewfinder with 3D Guide Ring */}
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
              <Camera className="w-10 h-10 text-slate-600" />
              <p className="text-xs">Camera preview active in privacy-first local mode</p>
            </div>
          )}

          {/* Alignment Target Ring */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className={`w-44 h-56 rounded-[48%] border-2 transition-all duration-500 flex items-center justify-center ${
              capturing ? 'border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.5)]' : 'border-emerald-400'
            }`}>
              {capturing && (
                <div className="text-2xl font-mono font-bold text-cyan-300 bg-slate-950/70 px-3 py-1 rounded-full border border-cyan-500/40">
                  {countdown}s
                </div>
              )}
            </div>
          </div>

          {/* Privacy Badge */}
          <div className="absolute bottom-2 left-2 text-[10px] font-medium bg-black/70 text-slate-300 px-2.5 py-1 rounded-md border border-white/10 flex items-center gap-1.5 backdrop-blur-sm">
            <Shield className="w-3 h-3 text-emerald-400" />
            <span>Zero Cloud Upload · On-Device Only</span>
          </div>
        </div>

        {/* Step Instructions */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1 text-center">
          <h4 className="text-sm font-bold text-white">{currentStepInfo.title}</h4>
          <p className="text-xs text-slate-300">{currentStepInfo.desc}</p>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-1">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Skip for Now
          </Button>
          <Button
            variant="primary"
            size="md"
            icon={step === 5 ? <Check className="w-4 h-4" /> : <RefreshCw className="w-4 h-4" />}
            onClick={onAdvance}
          >
            {step === 5 ? 'Complete Calibration' : 'Next Expression →'}
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
