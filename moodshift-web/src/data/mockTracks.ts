import { Track } from '../types/track';
import { camelotEngine } from '../domain/CamelotHarmonicEngine';

function createTrack(
  id: string,
  title: string,
  artist: string,
  bpm: number,
  key: number,
  mode: number,
  energy: number,
  valence: number,
  album?: string,
  artworkUrl?: string
): Track {
  const camelot = camelotEngine.toCamelot(key, mode);
  return {
    id,
    title,
    artist,
    album: album || 'Single Release',
    durationMs: 210000,
    artworkUrl: artworkUrl || `https://images.unsplash.com/photo-${1514525253161 + (key * 1000)}?w=300&h=300&fit=crop`,
    spotifyUri: `spotify:track:${id}`,
    tempoBpm: bpm,
    musicalKey: key,
    musicalMode: mode,
    camelotCode: camelot,
    energy,
    valence,
    playCount: Math.floor(Math.random() * 20) + 1
  };
}

export const MOCK_TRACK_LIBRARY: Track[] = [
  // Low Energy / Relaxed (Calm & Wind Down, 55 - 80 BPM)
  createTrack('t1', 'Midnight Breeze', 'Santhosh & Leon', 65, 0, 1, 0.22, 0.65, 'Nocturne Whispers'), // C Maj (8B)
  createTrack('t2', 'Echoes of Rain', 'Anoushka Shankar', 68, 9, 0, 0.18, 0.55, 'Land of Gold'),       // A Min (8A)
  createTrack('t3', 'Still Water Drift', 'Kavita Thomas', 62, 7, 1, 0.15, 0.60, 'Ambient Madras'),     // G Maj (9B)
  createTrack('t4', 'Stars Over Ooty', 'Sean Roldan Trio', 72, 2, 0, 0.25, 0.50, 'Hillside Acoustic'), // D Min (7A)
  createTrack('t5', 'Lullaby for Sleepers', 'Pradeep Kumar', 58, 4, 0, 0.10, 0.45, 'Aasai'),           // E Min (9A)
  createTrack('t6', 'Dew on Jasmine', 'Bombay Jayashri', 70, 5, 1, 0.28, 0.70, 'Morning Ragas'),       // F Maj (7B)

  // Reflective & Cathartic (70 - 95 BPM, Minor keys)
  createTrack('t7', 'Poove Sempoove (Lofi Re-imagined)', 'Ilayaraja & Sid', 76, 2, 0, 0.38, 0.28, 'Retro Rewind'), // D Min (7A)
  createTrack('t8', 'Marakkuma Nenjam (Strings)', 'A.R. Rahman', 84, 0, 0, 0.42, 0.32, 'Vendhu Thanindhathu Kaadu'), // C Min (5A)
  createTrack('t9', 'Kadavul Amaitha Medai', 'Govind Vasantha', 80, 5, 0, 0.35, 0.25, '96 Sessions'),                // F Min (4A)
  createTrack('t10', 'Silent Shadows', 'Dhibu Ninan Thomas', 88, 7, 0, 0.45, 0.30, 'Kanaa Acoustic'),               // G Min (6A)
  createTrack('t11', 'Kanave Kanave', 'Anirudh Ravichander', 92, 9, 0, 0.48, 0.35, 'David'),                        // A Min (8A)

  // Focus & Flow State (90 - 115 BPM, balanced modality)
  createTrack('t12', 'Synthetic Dawn', 'Tenma & The Casteless', 98, 0, 1, 0.52, 0.50, 'Casteless Collective'),  // C Maj (8B)
  createTrack('t13', 'Bespoke Motion', 'Siddharth Vipin', 104, 7, 1, 0.55, 0.52, 'Studio Chronicles'),          // G Maj (9B)
  createTrack('t14', 'Monsoon Transit', 'Sanjeev T', 100, 2, 1, 0.48, 0.55, 'St. Thomas Road'),                 // D Maj (10B)
  createTrack('t15', 'Subtle Waves', 'Sandunes', 110, 9, 1, 0.54, 0.48, 'Downstream'),                           // A Maj (11B)
  createTrack('t16', 'Marina Sunrise', 'Karthik Raja', 102, 5, 1, 0.50, 0.58, 'Chennai Beats'),                 // F Maj (7B)

  // Confident & Driving (110 - 125 BPM, Major keys)
  createTrack('t17', 'Vathi Raid (Groove Edit)', 'Anirudh Ravichander', 116, 2, 1, 0.72, 0.74, 'Master'),       // D Maj (10B)
  createTrack('t18', 'Aalaporaan Thamizhan', 'A.R. Rahman & Kailash', 118, 9, 1, 0.75, 0.72, 'Mersal'),         // A Maj (11B)
  createTrack('t19', 'Karuppu Perazhaga', 'D. Imman', 122, 4, 1, 0.70, 0.68, 'Kacheri Arambam'),              // E Maj (12B)
  createTrack('t20', 'Unakku Thaan', 'Santhosh Narayanan & Dhee', 112, 0, 1, 0.68, 0.75, 'Chithha'),           // C Maj (8B)

  // Uplift & Buoyant (115 - 128 BPM, Strict Major)
  createTrack('t21', 'Enna Sona (Uplift Mix)', 'A.R. Rahman', 120, 0, 1, 0.65, 0.85, 'OK Jaanu'),                // C Maj (8B)
  createTrack('t22', 'Hayyoda (Sun Drenched)', 'Anirudh Ravichander', 124, 7, 1, 0.68, 0.82, 'Jawan'),          // G Maj (9B)
  createTrack('t23', 'Bodhai Kaname', 'Anirudh & Shashaa', 118, 2, 1, 0.62, 0.80, 'Oh Manapenne'),               // D Maj (10B)
  createTrack('t24', 'Neeyum Naanum', 'Harris Jayaraj', 122, 9, 1, 0.66, 0.78, 'Naanum Rowdy Dhaan'),            // A Maj (11B)

  // Energized & Electric (125 - 142 BPM, Strict Major & High Energy)
  createTrack('t25', 'Naa Ready (High Volt)', 'Anirudh & Vijay', 132, 2, 1, 0.92, 0.75, 'Leo'),                 // D Maj (10B)
  createTrack('t26', 'Arabic Kuthu', 'Anirudh & Jonita', 130, 7, 1, 0.88, 0.82, 'Beast'),                       // G Maj (9B)
  createTrack('t27', 'Badass', 'Anirudh Ravichander', 136, 0, 1, 0.95, 0.68, 'Leo OST'),                        // C Maj (8B)
  createTrack('t28', 'Rowdy Baby (Turbo)', 'Yuvan Shankar Raja', 138, 9, 1, 0.90, 0.86, 'Maari 2'),             // A Maj (11B)
  createTrack('t29', 'Vaathi Coming', 'Anirudh Ravichander', 134, 4, 1, 0.94, 0.84, 'Master'),                   // E Maj (12B)
  createTrack('t30', 'Jalabulajangu', 'Anirudh Ravichander', 140, 2, 1, 0.96, 0.78, 'Don')                      // D Maj (10B)
];

export const MOCK_TRACKS: Track[] = MOCK_TRACK_LIBRARY;
