const {test} = require('node:test');
const assert = require('node:assert/strict');
const runtime = require('../dist/catalog-runtime.js');

test('missing ratings never become generated scores', () => {
  assert.equal(runtime.score({slug:'frieren'}), null);
  assert.equal(runtime.score({averageScore:92}), 92);
  assert.equal(runtime.score({averageScore:101}), null);
});
test('untrusted HTML and image URLs are escaped', () => {
  assert.equal(runtime.escapeHtml('<img src=x onerror="x">'), '&lt;img src=x onerror=&quot;x&quot;&gt;');
  assert.equal(runtime.imageUrl('javascript:alert(1)','fallback'), 'fallback');
  assert.equal(runtime.imageUrl('https://example.com/" onerror="x','fallback'), 'fallback');
});
test('downloads use manifest rows without inventing episodes or formats', () => {
  assert.deepEqual(runtime.episodes({translated_episodes:[1,264],episodes:29}), []);
  const rows = runtime.episodes({subtitles:[{episode:264, files:{srt:'https://example.com/a.srt', vtt:null}}]});
  assert.equal(rows.length,1);
  assert.equal(rows[0].episode,264);
  assert.deepEqual(Object.keys(rows[0].files), ['srt']);
});
test('download URLs reject executable protocols', () => {
  const rows = runtime.episodes({subtitles:[{episode:1,files:{srt:'javascript:alert(1)',vtt:'https://example.com/a.vtt'}}]});
  assert.deepEqual(Object.keys(rows[0].files),['vtt']);
});
test('release metadata is safe for template rendering', () => {
  const item = runtime.release({slug:'demo',title:{english:'A & B'},format:'<img onerror=x>',seasonYear:'<img>',averageScore:200,coverImage:'javascript:alert(1)',genres:['Fantasy',3],available_episodes_count:'<img>'});
  assert.equal(item.title.english,'A & B');
  assert.equal(item.format,null);
  assert.equal(item.seasonYear,null);
  assert.equal(item.averageScore,null);
  assert.equal(item.coverImage,'');
  assert.equal(item.available_episodes_count,0);
  assert.deepEqual(item.genres,['Fantasy']);
  assert.equal(runtime.release({slug:"demo');alert(1)"}),null);
});
