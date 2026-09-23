import { describe, it, expect } from 'vitest';
import { activeFace, canStep, cubeRotation, faceAngle, faceDepth, stepForIndex } from './cube';

describe('geometria del cubo', () => {
  it('divide il giro fra le facce', () => {
    expect(faceAngle(4)).toBe(90);
    expect(faceAngle(3)).toBe(120);
  });

  it('con 4 facce la profondita e meta larghezza', () => {
    expect(faceDepth(800, 4)).toBeCloseTo(400, 6);
  });

  it('con 3 facce usa l apotema del prisma', () => {
    expect(faceDepth(800, 3)).toBeCloseTo(400 / Math.tan(Math.PI / 3), 6);
  });
});

describe('indice e rotazione', () => {
  it('ricava la faccia attiva con il modulo, anche per step negativi', () => {
    expect(activeFace(0, 4)).toBe(0);
    expect(activeFace(5, 4)).toBe(1);
    expect(activeFace(-1, 4)).toBe(3);
  });

  it('non riporta l angolo a zero tornando alla prima faccia', () => {
    // Quarta faccia -> prima: la rotazione prosegue invece di tornare indietro di 270 gradi.
    expect(cubeRotation(3, 4)).toBe(-270);
    expect(cubeRotation(4, 4)).toBe(-360);
  });
});

describe('salto diretto a una faccia', () => {
  it('sceglie la strada piu corta quando il loop e attivo', () => {
    // Dalla faccia 0 alla 3 conviene girare indietro di un passo.
    expect(stepForIndex(0, 4, 3, true)).toBe(-1);
    expect(stepForIndex(0, 4, 1, true)).toBe(1);
    expect(activeFace(stepForIndex(8, 4, 2, true), 4)).toBe(2);
  });

  it('senza loop resta nell intervallo delle facce', () => {
    expect(stepForIndex(0, 4, 3, false)).toBe(3);
  });
});

describe('limiti dei pulsanti', () => {
  it('con il loop si puo sempre girare', () => {
    expect(canStep(3, 4, 1, true)).toBe(true);
  });

  it('senza loop i pulsanti si spengono agli estremi', () => {
    expect(canStep(3, 4, 1, false)).toBe(false);
    expect(canStep(0, 4, -1, false)).toBe(false);
    expect(canStep(0, 4, 1, false)).toBe(true);
  });

  it('con una sola faccia non si gira', () => {
    expect(canStep(0, 1, 1, true)).toBe(false);
  });
});
