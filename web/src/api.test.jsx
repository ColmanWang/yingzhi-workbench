import {afterEach,describe,expect,it,vi} from 'vitest';
import {request,safeFile,safeSource} from './api.js';
afterEach(()=>vi.unstubAllGlobals());
describe('API安全边界',()=>{
 it('拒绝协议与域名伪装的原视频链接',()=>{
  for(const value of ['javascript:alert(1)','https://douyin.com.evil.test/','https://user:pass@www.douyin.com/video/1','not a url'])expect(safeSource(value)).toBeNull();
  expect(safeSource('https://www.douyin.com/video/1')).toBe('https://www.douyin.com/video/1');
 });
 it('仅接受本机卡片地址',()=>{
  expect(safeFile('/files/cards/example.png')).toBe('/files/cards/example.png');
  for(const value of ['https://evil.test/card.png','/files/cards/../../secret',null])expect(safeFile(value)).toBeNull();
 });
 it('将服务失败转换成可读错误',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>({success:false,error:{message:'任务仍在执行'}})})));
  await expect(request('/api/jobs')).rejects.toThrow('任务仍在执行');
 });
 it('处理非JSON错误响应和未知错误',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>{throw new Error('invalid')}})));
  await expect(request('/api/bootstrap')).rejects.toThrow('无法读取');
  fetch.mockResolvedValue({ok:false,json:async()=>({success:false})});
  await expect(request('/api/jobs')).rejects.toThrow('操作未完成');
 });
});
