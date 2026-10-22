export async function request(path, options = {}) {
  let response;
  try { response = await fetch(path, options); }
  catch { throw new Error('无法连接本地工作台，请确认服务正在运行。'); }
  let result;
  try { result = await response.json(); }
  catch { throw new Error('本地服务返回了无法读取的结果，请重试。'); }
  if (!response.ok || !result.success) throw new Error(result.error?.message || '操作未完成，请重试。');
  return result.data;
}
export function postJob(body, token) {
  return request('/api/jobs', { method: 'POST', headers: { 'Content-Type':'application/json', 'X-CSRF-Token': token }, body: JSON.stringify(body) });
}
export const statusText = {pending:'待转写',transcribing:'转写中',transcribed:'已转写',success:'已转写',skipped_image:'图文内容',no_speech:'未识别到语音',unavailable:'未识别到语音',failed:'转写失败',interrupted:'已中断'};
export const jobText = {queued:'等待执行',running:'进行中',completed:'已完成',failed:'失败',interrupted:'已中断'};
export const kindText = {login:'连接抖音',collect:'同步列表',transcribe:'本地语音转写'};
export const sourceText = {collection:'收藏',like:'喜欢',all:'全部'};
export function safeSource(value) {
  try { const u = new URL(value); return u.protocol === 'https:' && (u.hostname === 'douyin.com' || u.hostname.endsWith('.douyin.com')) && !u.username && !u.password ? u.href : null; }
  catch { return null; }
}
export function safeFile(value) {
  return typeof value === 'string' && value.startsWith('/files/cards/') && !value.includes('..') ? value : null;
}
