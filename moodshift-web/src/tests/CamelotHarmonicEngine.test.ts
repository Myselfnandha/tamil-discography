import { describe, it, expect } from 'vitest';
import { camelotEngine } from '../domain/CamelotHarmonicEngine';

describe('CamelotHarmonicEngine', () => {
  it('correctly maps pitch class and mode to Camelot codes', () => {
    // C Major (key 0, mode 1) -> 8B
    expect(camelotEngine.toCamelot(0, 1)).toBe('8B');
    // A Minor (key 9, mode 0) -> 8A
    expect(camelotEngine.toCamelot(9, 0)).toBe('8A');
    // G Major (key 7, mode 1) -> 9B
    expect(camelotEngine.toCamelot(7, 1)).toBe('9B');
    // E Minor (key 4, mode 0) -> 9A
    expect(camelotEngine.toCamelot(4, 0)).toBe('9A');
    // B Major (key 11, mode 1) -> 1B
    expect(camelotEngine.toCamelot(11, 1)).toBe('1B');
    // F# Minor (key 6, mode 0) -> 11A
    expect(camelotEngine.toCamelot(6, 0)).toBe('11A');
  });

  it('handles invalid or null inputs gracefully with null', () => {
    expect(camelotEngine.toCamelot(null, 1)).toBeNull();
    expect(camelotEngine.toCamelot(0, null)).toBeNull();
    expect(camelotEngine.toCamelot(-1, 1)).toBeNull();
    expect(camelotEngine.toCamelot(12, 1)).toBeNull();
  });

  it('awards +0.15 harmonic bonus for exact key match', () => {
    expect(camelotEngine.calculateHarmonicBonus('8B', '8B')).toBe(0.15);
    expect(camelotEngine.calculateHarmonicBonus('5A', '5A')).toBe(0.15);
  });

  it('awards +0.10 harmonic bonus for relative Major <-> Minor', () => {
    expect(camelotEngine.calculateHarmonicBonus('8B', '8A')).toBe(0.10);
    expect(camelotEngine.calculateHarmonicBonus('8A', '8B')).toBe(0.10);
    expect(camelotEngine.calculateHarmonicBonus('12A', '12B')).toBe(0.10);
  });

  it('awards +0.10 harmonic bonus for adjacent Circle-of-Fifths steps', () => {
    // 8B -> 9B
    expect(camelotEngine.calculateHarmonicBonus('8B', '9B')).toBe(0.10);
    // 8B -> 7B
    expect(camelotEngine.calculateHarmonicBonus('8B', '7B')).toBe(0.10);
    // Wraparound: 12B -> 1B and 1B -> 12B
    expect(camelotEngine.calculateHarmonicBonus('12B', '1B')).toBe(0.10);
    expect(camelotEngine.calculateHarmonicBonus('1B', '12B')).toBe(0.10);
  });

  it('awards +0.05 harmonic bonus for diagonal steps', () => {
    // 8B -> 9A (adjacent number, cross mode)
    expect(camelotEngine.calculateHarmonicBonus('8B', '9A')).toBe(0.05);
    // 12A -> 1B
    expect(camelotEngine.calculateHarmonicBonus('12A', '1B')).toBe(0.05);
  });

  it('awards 0.00 bonus for clashing / distant keys', () => {
    // 8B -> 2B (distant step)
    expect(camelotEngine.calculateHarmonicBonus('8B', '2B')).toBe(0.0);
    // Missing metadata
    expect(camelotEngine.calculateHarmonicBonus(null, '8B')).toBe(0.0);
  });

  it('provides human-readable tonality labels', () => {
    expect(camelotEngine.getTonalityLabel(0, 1)).toBe('C Major (8B)');
    expect(camelotEngine.getTonalityLabel(9, 0)).toBe('A Minor (8A)');
  });
});
