import assert from 'node:assert/strict';
import test from 'node:test';
import { receiverUrl, checkInfo, checkReceipt } from '../harmonyos/entry/src/main/ets/common/Protocol.ts';

test('only explicit private IPv4 receiver addresses may receive pairing credentials', () => {
  assert.equal(receiverUrl('192.168.1.9:8765'), 'http://192.168.1.9:8765');
  assert.equal(receiverUrl('http://10.0.0.2:9000/'), 'http://10.0.0.2:9000');
  for (const address of ['https://example.com', '8.8.8.8:8765', '192.168.1.2:0',
    '192.168.1.256:8765', '192.168.1.2:99999', 'http://a@192.168.1.2:8765',
    'http://192.168.1.2:8765/path', 'http://192.168.1.2:8765?token=x']) {
    assert.throws(() => receiverUrl(address));
  }
});

test('native client rejects old receivers without multipart support', () => {
  assert.throws(() => checkInfo(200, '{"protocol":1,"max_bytes":1024}'));
  assert.throws(() => checkInfo(401, '{"error":"wrong password"}'));
  assert.equal(checkInfo(200, '{"protocol":1,"max_bytes":1073741824,"form_upload":true}').max_bytes, 1073741824);
});

test('only 201 with matching length and digest confirms saved transfer', () => {
  const sha = 'a'.repeat(64);
  const body = JSON.stringify({name:'原图 (1).png', bytes:3, sha256:sha});
  assert.equal(checkReceipt(201, body, 3, sha).name, '原图 (1).png');
  assert.throws(() => checkReceipt(200, body, 3, sha));
  assert.throws(() => checkReceipt(201, body, 4, sha));
  assert.throws(() => checkReceipt(201, body, 3, 'b'.repeat(64)));
  for (const invalid of ['null', '[]', '{}', 'not json', '{"bytes":"3"}']) {
    assert.throws(() => checkReceipt(201, invalid, 3, sha));
  }
});
