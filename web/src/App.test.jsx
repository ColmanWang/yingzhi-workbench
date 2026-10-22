import React from 'react';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';
const items = [
 {id:'collection-1',title:'测试收藏视频',author:'原作者甲',source:'collection',status:'transcribed',media_kind:'video',transcript:'这里是真实逐字稿。',source_url:'https://www.douyin.com/video/1'},
 {id:'like-2',title:'测试喜欢视频',author:'原作者乙',source:'like',status:'pending',media_kind:'video',transcript:'',source_url:'https://www.douyin.com/video/2'},
 {id:'like-3',title:'图文资料',author:'原作者丙',source:'like',status:'skipped_image',media_kind:'image',transcript:'',source_url:'https://www.douyin.com/video/3'},
];
let post;
let extraData;

beforeEach(() => {
 post = vi.fn();extraData={};
 vi.stubGlobal('fetch',vi.fn(async (url, options) => {
  if(options?.method==='POST'){post(JSON.parse(options.body),options.headers); return {ok:true,json:async()=>({success:true,data:{id:'job-1',kind:'collect',status:'queued',source:'collection',done:0,total:3,message:'等待执行'}})};}
  let data = url==='/api/cards'?[]:{items,jobs:[],cards:[],settings:{transcription:{ready:true,missing:[],model:'small'},analysis:{configured:false},local_only:true},csrf_token:'test-token',...extraData};
  return {ok:true,json:async()=>({success:true,data})};
 }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.clearAllMocks();});
describe('工作台真实数据流程',()=>{
 it('加载资料且启动时不自动采集',async()=>{
  render(<App/>);
  for(const label of ['视频资料库','任务中心','知识卡片','设置'])expect(screen.getByRole('button',{name:label})).toHaveAttribute('aria-label',label); expect(await screen.findByRole('button',{name:'查看 测试收藏视频'})).toBeInTheDocument();
  expect(post).not.toHaveBeenCalled();expect(screen.getByText('尚未配置 AI 总结功能')).toBeInTheDocument();
 });
 it('按来源筛选并搜索',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});
  await u.click(screen.getByRole('tab',{name:'喜欢'}));expect(screen.queryByRole('button',{name:'查看 测试收藏视频'})).not.toBeInTheDocument();
  await u.type(screen.getByPlaceholderText('搜索标题或作者'),'乙');expect(screen.getByRole('button',{name:'查看 测试喜欢视频'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'查看 图文资料'})).not.toBeInTheDocument();
 });
 it('只将勾选的视频提交本地转写并携带CSRF',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('tab',{name:'喜欢'}));
  await u.click(screen.getByLabelText('选择 测试喜欢视频'));await u.click(screen.getByRole('button',{name:'本地转写'}));
  await waitFor(()=>expect(post).toHaveBeenCalled());expect(post.mock.calls[0][0]).toEqual({kind:'transcribe',source:'like',ids:['like-2']});expect(post.mock.calls[0][1]['X-CSRF-Token']).toBe('test-token');
 });
 it('点击同步时提交用户选择的范围',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('button',{name:'同步列表'}));
  expect(post.mock.calls[0][0]).toEqual({kind:'collect',source:'collection',limit:3});
 });
 it('展示图文不能语音转写的提示',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('tab',{name:'喜欢'}));await u.click(screen.getByRole('button',{name:'查看 图文资料'}));
  expect(screen.getByText('这是图文内容，需图片文字识别；当前不会进行语音转写。')).toBeInTheDocument();
 });
 it('任务中心显示实际任务空态，设置显示总结待配置',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('button',{name:'任务中心'}));expect(screen.getByText('还没有任务')).toBeInTheDocument();
  await u.click(screen.getByRole('button',{name:'设置'}));expect(screen.getByText('Whisper small')).toBeInTheDocument();expect(screen.getByText('暂未接入')).toBeInTheDocument();
 });
 it('服务不可用时显示可重试错误',async()=>{
  fetch.mockRejectedValue(new Error('offline'));render(<App/>);expect(await screen.findByRole('alert')).toHaveTextContent('无法连接本地工作台');expect(screen.getByRole('button',{name:'重新连接'})).toBeInTheDocument();
 });
 it('筛选状态并全选，搜索后不保留隐藏详情',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});
  await u.click(screen.getByRole('tab',{name:'全部'}));await u.click(screen.getByLabelText('选择全部视频'));
  expect(screen.getByText('已选择 2 条')).toBeInTheDocument();await u.click(screen.getByRole('button',{name:'本地转写'}));
  expect(screen.getByRole('alert')).toHaveTextContent('按收藏或喜欢分组');
  await u.selectOptions(screen.getByLabelText('状态筛选'),'pending');expect(screen.queryByRole('button',{name:'查看 测试收藏视频'})).not.toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'测试喜欢视频'})).toBeInTheDocument();await u.type(screen.getByPlaceholderText('搜索标题或作者'),'没有');expect(screen.getByText('没有找到匹配的资料')).toBeInTheDocument();
  await u.click(screen.getByRole('button',{name:'清空搜索'}));expect(screen.getByRole('button',{name:'查看 测试喜欢视频'})).toBeInTheDocument();
 });
 it('已有卡片支持详情预览与导出，任务显示真实条数',async()=>{
  extraData={cards:[{id:'c1',item_id:'collection-1',title:'卡片一',author:'甲',source:'collection',html_url:'/files/cards/a.html',png_url:'/files/cards/a.png'}],jobs:[{id:'j1',kind:'transcribe',source:'collection',status:'completed',done:2,total:2,message:'完成2条'}]};
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('tab',{name:/卡片/}));
  expect(screen.getByAltText('卡片一知识卡片')).toBeInTheDocument();expect(screen.getByRole('link',{name:/下载图片/})).toHaveAttribute('href','/files/cards/a.png');
  await u.click(screen.getByRole('button',{name:'知识卡片'}));expect(screen.getByRole('heading',{name:'卡片一'})).toBeInTheDocument();
  await u.click(screen.getByRole('button',{name:'任务中心'}));expect(screen.getAllByText('2 / 2')).toHaveLength(2);expect(screen.getAllByText('完成2条')).toHaveLength(2);
 });
 it('待执行任务禁用重复操作，未就绪依赖清楚展示',async()=>{
  extraData={jobs:[{id:'j1',kind:'login',source:'like',status:'running',done:0,total:0}],settings:{transcription:{ready:false,missing:['ffmpeg'],model:'small'},analysis:{configured:false}}};
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});expect(screen.getByRole('button',{name:'同步列表'})).toBeDisabled();
  expect(screen.getByText('等待任务返回进度')).toBeInTheDocument();await u.click(screen.getByRole('button',{name:'设置'}));expect(screen.getByText('ffmpeg')).toBeInTheDocument();expect(screen.getByText('需要配置')).toBeInTheDocument();
 });
 it('任务提交失败不会显示成功，错误可关闭',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});
  fetch.mockImplementation(async (url,options)=> options?.method==='POST'?{ok:false,json:async()=>({success:false,error:{message:'已有任务'}})}:{ok:true,json:async()=>({success:true,data:{items,jobs:[],csrf_token:'token'}})});
  await u.click(screen.getByRole('button',{name:'连接抖音'}));expect(screen.getByRole('alert')).toHaveTextContent('已有任务');await u.click(screen.getByRole('button',{name:'关闭错误'}));expect(screen.queryByRole('alert')).not.toBeInTheDocument();
 });

 it('连接操作显示回执并允许关闭提示和返回资料库',async()=>{
  const u=userEvent.setup();render(<App/>);await screen.findByRole('button',{name:'查看 测试收藏视频'});await u.click(screen.getByRole('button',{name:'查看 测试收藏视频'}));await u.click(screen.getByRole('button',{name:'返回列表'}));
  await u.click(screen.getByRole('button',{name:'连接抖音'}));expect(screen.getByRole('status')).toHaveTextContent('连接抖音已加入任务');await u.click(screen.getByRole('button',{name:'关闭提示'}));expect(screen.queryByRole('status')).not.toBeInTheDocument();
  await u.click(screen.getByRole('button',{name:'知识卡片'}));expect(screen.getByText('还没有知识卡片')).toBeInTheDocument();await u.click(screen.getByRole('link',{name:/映知/}));expect(screen.getByRole('heading',{name:'视频资料库'})).toBeInTheDocument();
 });

});
