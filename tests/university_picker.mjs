import assert from 'node:assert/strict';
import { test } from 'node:test';
import mountPicker from '../assets/university-picker.mjs';

test('directory cache, deadline, and manual fallback', async t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  const element = () => ({
    children: [], setAttribute() {}, removeAttribute() {}, scrollIntoView() {},
    replaceChildren() { this.children = []; },
    append(child) { this.children.push(child); },
  });
  globalThis.document = {createElement: element};
  const input = element(), list = element(), status = element(), choices = [];
  const parentElement = {
    getRootNode: () => ({}),
    querySelector: selector => ({'.uni-input': input, '.uni-list': list, '.uni-status': status})[selector],
  };
  let calls = 0, stalled = false;
  t.mock.method(globalThis, 'fetch', async (_url, {signal}) => {
    calls++;
    if (stalled) return new Promise((_, reject) => signal.addEventListener('abort', () => reject(signal.reason)));
    return {ok: true, json: async () => ({items: []})};
  });
  const dispose = mountPicker({data: {}, parentElement, setStateValue: (_, value) => choices.push(value)});
  const tick = async ms => {
    t.mock.timers.tick(ms);
    await new Promise(resolve => setImmediate(resolve));
  };
  const type = async name => { input.value = name; input.oninput(); await tick(250); };
  await type('Demo University');
  await type('DEMO  university');
  assert.equal(calls, 1);
  assert.match(status.textContent, /No directory match/);
  await tick(600001);
  stalled = true;
  await type('Demo University');
  assert.equal(calls, 2);
  await tick(8000);
  assert.match(status.textContent, /unavailable/);
  input.onkeydown({key: 'Enter', preventDefault() {}});
  assert.deepEqual(choices, [{name: 'Demo University', source: 'typed'}]);
  stalled = false;
  await type('Demo University');
  assert.equal(calls, 3);
  assert.match(status.textContent, /No directory match/);
  dispose();
});
