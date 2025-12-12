import assert from 'node:assert/strict';
import test from 'node:test';

import { computeGroupHue } from '../../src/terrarium/static/color.js';

test('returns hue within [0, 360) for typical ids', () => {
  assert.equal(computeGroupHue(0), 0);
  assert.equal(computeGroupHue(1), 47);
  assert.equal(computeGroupHue(2), 94);
  assert.equal(computeGroupHue(8), 16);
});

test('wraps negative ids into the positive range', () => {
  assert.equal(computeGroupHue(-1), 313);
  assert.equal(computeGroupHue(-5), 125);
});

test('normalizes very large ids deterministically', () => {
  assert.equal(computeGroupHue(100), 20);
  assert.equal(computeGroupHue(1000000), computeGroupHue(1000000 + 360));
});

test('falls back to zero hue for non-finite values', () => {
  assert.equal(computeGroupHue(NaN), 0);
  assert.equal(computeGroupHue(Infinity), 0);
});
