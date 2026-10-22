import React from 'react';
import { GlassCard } from '../common/GlassCard';
import { Button } from '../common/Button';
import { AlertCircle, ExternalLink, Volume2, X } from 'lucide-react';
import { Track } from '../../types/track';

interface SpotifyFallbackAlertProps {
  track: Track | null;
  onConfirmOpenSpotify: () => void;
  onStayInApp: () => void;
  onClose: () => void;
}

export const SpotifyFallbackAlert: React.FC<SpotifyFallbackAlertProps> = ({
  track,
  onConfirmOpenSpotify,
  onStayInApp,
  onClose
}) => {
  if (!track) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <GlassCard className="w-full max-w-md p-6 flex flex-col gap-5 shadow-2xl border-white/10" variant="elevated">
        <div className="flex items-start justify-between">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
            <AlertCircle className="w-6 h-6" />
          </div>
          <button
            onClick={onClose}
            aria-label="Close Spotify alert"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">
            DSP Notice: External Spotify Playback
          </h3>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed">
            Spotify's native application does not support MoodShift's real-time Web Audio DSP pipeline.
          </p>
          <div className="p-3 mt-3 rounded-xl bg-white/5 border border-white/5 text-xs text-slate-400 space-y-1">
            <p>• <span className="text-white font-medium">In MoodShift:</span> Dynamic tempo modulation (0.96x – 1.04x) with pitch locked at 1.0x.</p>
            <p>• <span className="text-white font-medium">In Spotify App:</span> Standard 1.00x speed without entrainment modulation.</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-2.5 pt-2">
          <Button
            variant="primary"
            fullWidth
            onClick={onStayInApp}
            icon={<Volume2 className="w-4 h-4" />}
          >
            Stay in MoodShift
          </Button>

          <Button
            variant="ghost"
            fullWidth
            onClick={onConfirmOpenSpotify}
            icon={<ExternalLink className="w-4 h-4" />}
          >
            Open Spotify
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
