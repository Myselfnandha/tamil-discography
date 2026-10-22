/**
 * Camelot Harmonic Mixing & Circle-of-Fifths Engine
 * Maps Spotify key (0-11) & mode (0-1) to Camelot wheel positions (1A - 12B)
 * and calculates harmonic transition affinity between consecutive tracks.
 */

// Spotify key (0-11) to Camelot number mapping
const MAJOR_CAMELOT: Record<number, number> = {
  0: 8,   // C Major = 8B
  1: 3,   // C# Major = 3B
  2: 10,  // D Major = 10B
  3: 5,   // Eb Major = 5B
  4: 12,  // E Major = 12B
  5: 7,   // F Major = 7B
  6: 2,   // F# Major = 2B
  7: 9,   // G Major = 9B
  8: 4,   // Ab Major = 4B
  9: 11,  // A Major = 11B
  10: 6,  // Bb Major = 6B
  11: 1   // B Major = 1B
};

const MINOR_CAMELOT: Record<number, number> = {
  0: 5,   // C Minor = 5A
  1: 12,  // C# Minor = 12A
  2: 7,   // D Minor = 7A
  3: 2,   // Eb Minor = 2A
  4: 9,   // E Minor = 9A
  5: 4,   // F Minor = 4A
  6: 11,  // F# Minor = 11A
  7: 6,   // G Minor = 6A
  8: 1,   // Ab Minor = 1A
  9: 8,   // A Minor = 8A
  10: 3,  // Bb Minor = 3A
  11: 10  // B Minor = 10A
};

export const PITCH_NAMES = ['C', 'C♯', 'D', 'E♭', 'E', 'F', 'F♯', 'G', 'A♭', 'A', 'B♭', 'B'];

export class CamelotHarmonicEngine {
  /**
   * Converts pitch class and mode to Camelot Code (e.g. 8B, 5A)
   */
  public toCamelot(key: number | null | undefined, mode: number | null | undefined): string | null {
    if (key == null || mode == null || key < 0 || key > 11) return null;
    const isMajor = mode === 1;
    const num = isMajor ? MAJOR_CAMELOT[key] : MINOR_CAMELOT[key];
    const letter = isMajor ? 'B' : 'A';
    return `${num}${letter}`;
  }

  /**
   * Parses a Camelot code string (e.g. "8B" -> { num: 8, letter: 'B' })
   */
  public parseCamelot(code: string): { num: number; letter: 'A' | 'B' } | null {
    const match = code.trim().toUpperCase().match(/^(\d{1,2})([AB])$/);
    if (!match) return null;
    const num = parseInt(match[1], 10);
    const letter = match[2] as 'A' | 'B';
    if (num < 1 || num > 12) return null;
    return { num, letter };
  }

  /**
   * Calculates harmonic compatibility bonus between consecutive songs in a journey.
   * Bonus values:
   * +0.15: Exact key match (e.g. 8B -> 8B)
   * +0.10: Adjacent Circle-of-Fifths step (e.g. 8B -> 9B or 8B -> 7B)
   * +0.10: Relative Major <-> Minor (e.g. 8B <-> 8A)
   * +0.05: Diagonal shift (e.g. 8B -> 9A)
   *  0.00: Clashing / distant key or unknown metadata
   */
  public calculateHarmonicBonus(fromCode: string | null | undefined, toCode: string | null | undefined): number {
    if (!fromCode || !toCode) return 0.0; // Unknown: neutral pass

    const from = this.parseCamelot(fromCode);
    const to = this.parseCamelot(toCode);
    if (!from || !to) return 0.0;

    // 1. Exact match
    if (from.num === to.num && from.letter === to.letter) {
      return 0.15;
    }

    // 2. Relative Major <-> Minor (same number, different letter: 8B <-> 8A)
    if (from.num === to.num && from.letter !== to.letter) {
      return 0.10;
    }

    // Circular adjacent distance on 12-hour wheel
    const stepDiff = Math.abs(from.num - to.num);
    const isAdjacent = stepDiff === 1 || stepDiff === 11; // 12 is adjacent to 1

    // 3. Adjacent Circle-of-Fifths step in same mode (e.g. 8B -> 9B or 12B -> 1B)
    if (isAdjacent && from.letter === to.letter) {
      return 0.10;
    }

    // 4. Diagonal harmonic step (adjacent number, cross mode: 8B -> 9A)
    if (isAdjacent && from.letter !== to.letter) {
      return 0.05;
    }

    return 0.0;
  }

  public getTonalityLabel(key: number | null | undefined, mode: number | null | undefined): string {
    if (key == null || mode == null || key < 0 || key > 11) return 'Unknown Key';
    const note = PITCH_NAMES[key];
    const modeName = mode === 1 ? 'Major' : 'Minor';
    const camelot = this.toCamelot(key, mode);
    return `${note} ${modeName} (${camelot})`;
  }
}

export const camelotEngine = new CamelotHarmonicEngine();
