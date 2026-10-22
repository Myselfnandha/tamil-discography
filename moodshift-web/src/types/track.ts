export enum PlaybackSource {
  SPOTIFY_DEEPLINK = 'SPOTIFY_DEEPLINK',
  YOUTUBE_STREAM = 'YOUTUBE_STREAM',
  LOCAL_SYNTH = 'LOCAL_SYNTH'
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  album?: string;
  durationMs: number;
  artworkUrl?: string;
  spotifyUri?: string;
  youtubeId?: string;
  audioUrl?: string;          // Direct stream or synthesized preview
  tempoBpm?: number | null;   // Native BPM from Spotify features (used for guardrails)
  musicalKey?: number | null; // 0 = C, 1 = C#, ..., 11 = B
  musicalMode?: number | null;// 1 = Major, 0 = Minor
  camelotCode?: string | null;// e.g. "8B" (C Major), "8A" (A Minor)
  energy: number;             // 0.0 - 1.0
  valence: number;            // 0.0 - 1.0
  userVibeTag?: string;
  playCount: number;
  lastPlayedAt?: string;
}

export interface JourneyTrack {
  track: Track;
  source: PlaybackSource;
  estimatedEnergy: number;
  estimatedValence: number;
  targetTempoMultiplier: number; // Dynamically computed [0.96 .. 1.04]
  reason: string;                // e.g. "Familiar comfort track", "Camelot 8B -> 9B step", "Phase 3 Major mode anchor"
}
