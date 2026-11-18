import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const code = await readFile(new URL('./dashboard.js', import.meta.url));
const {endpoints, load, metric} = await import(`data:text/javascript;base64,${code.toString('base64')}`);

test('missing metrics are distinct from zero', () => {
  for (const value of ['', ' ', null, undefined, false, NaN, {}, 'unknown']) assert.equal(metric(value), 'N/A');
  assert.equal(metric(0, '%'), '0%');
  assert.equal(metric('12', '%'), '12%');
});

test('only same-origin dashboard GETs can be requested', async () => {
  assert.equal(new Set(endpoints).size, endpoints.length);
  for (const name of endpoints) {
    const result = await load(name, async (url, options) => {
      assert.equal(url, `/rest/1.0/dashboard/${name}`);
      assert.equal(options.method, 'GET'); assert.equal(options.mode, 'same-origin');
      return {ok:true, json: async () => ({})};
    });
    assert.deepEqual(result, {});
  }
  await assert.rejects(load('elsewhere', () => assert.fail()), /Unknown panel/);
});

test('failed or malformed responses are not healthy empty results', async () => {
  await assert.rejects(load('events', async () => ({ok:false, status:503})), /503/);
  await assert.rejects(load('nodes', async () => ({ok:true, json: async () => []})), /Invalid response/);
});
