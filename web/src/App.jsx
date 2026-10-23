import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, ListTodo, BookOpen, Settings, Link, RefreshCw, Search, AudioLines, ExternalLink, ChevronRight, ArrowLeft, Download, Check, Info, X, LoaderCircle, Image, FileText, Video } from 'lucide-react';
import { request, postJob, statusText, jobText, kindText, sourceText, safeSource, safeFile } from './api.js';
const navs=[['library','视频资料库',Play],['jobs','任务中心',ListTodo],['cards','知识卡片',BookOpen],['settings','设置',Settings]];
const emptyData={items:[],jobs:[],cards:[],settings:{},csrf_token:''};
const busyStates=new Set(['queued','running']);
export default function App(){
 const [data,setData]=useState(emptyData),[view,setView]=useState('library'),[source,setSource]=useState('collection'),[query,setQuery]=useState(''),[statusFilter,setStatusFilter]=useState('all'),[selected,setSelected]=useState([]),[activeId,setActiveId]=useState(null),[detailTab,setDetailTab]=useState('transcript'),[error,setError]=useState(''),[loading,setLoading]=useState(true),[posting,setPosting]=useState(false),[limit,setLimit]=useState(3),[notice,setNotice]=useState(''),[mobileDetail,setMobileDetail]=useState(false);
 const refresh=useCallback(async(silent=false)=>{
  try {const incoming=await request('/api/bootstrap');setData({...emptyData,...incoming});setLoading(false);if(!silent)setError('');}
  catch(e){setLoading(false);setError(e.message);}
 },[]);
 useEffect(()=>{refresh();const timer=setInterval(()=>refresh(true),2500);return()=>clearInterval(timer);},[refresh]);
 const items=data.items||[],jobs=data.jobs||[],cards=data.cards||[];
 const filtered=useMemo(()=>items.filter(x=>(source==='all'||x.source===source)&&`${x.title} ${x.author}`.toLowerCase().includes(query.toLowerCase())&&(statusFilter==='all'||(statusFilter==='success'?['success','transcribed'].includes(x.status):statusFilter==='image'?x.media_kind==='image':statusFilter==='attention'?['failed','interrupted','no_speech','unavailable'].includes(x.status):x.status===statusFilter))),[items,source,query,statusFilter]);
 const active=filtered.find(x=>x.id===activeId)||filtered[0]||null;
 const activeCards=cards.filter(x=>x.item_id===active?.id);
 const currentJob=jobs.find(x=>busyStates.has(x.status))||jobs[0];
 const hasBusy=jobs.some(x=>busyStates.has(x.status));
 const ready=data.settings.transcription?.ready??data.settings.asr_ready??false;
 const pickable=filtered.filter(x=>x.media_kind!=='image'&&x.status!=='skipped_image'&&x.status!=='transcribing');
 const allPicked=pickable.length>0&&pickable.every(x=>selected.includes(x.id));
 async function submit(kind,explicitSource,ids){
  if(posting||hasBusy)return;
  const chosen=explicitSource||(source==='all'?'collection':source);
  setPosting(true);setError('');setNotice('');
  try{
   const body={kind,source:chosen,...(kind==='collect'?{limit:Number(limit)}:{}),...(kind==='transcribe'?{ids}: {})};
   const job=await postJob(body,data.csrf_token);
   setData(old=>({...old,jobs:[job,...old.jobs.filter(x=>x.id!==job.id)]}));setNotice(`${kindText[kind]}已加入任务`);
   if(kind==='transcribe')setSelected([]);
  }catch(e){setError(e.message);}finally{setPosting(false);}
 }
 function transcribeSelected(){
  const picked=items.filter(x=>selected.includes(x.id)&&x.media_kind!=='image'&&x.status!=='skipped_image');
  const sources=[...new Set(picked.map(x=>x.source))];
  if(sources.length!==1){setError('请按收藏或喜欢分组选择视频后转写。');return;}
  submit('transcribe',sources[0],picked.map(x=>x.id));
 }
 function toggle(id){setSelected(old=>old.includes(id)?old.filter(x=>x!==id):[...old,id]);}
 function chooseSource(value){setSource(value);setSelected([]);setActiveId(null);}
 function openItem(item){setActiveId(item.id);setDetailTab('transcript');setMobileDetail(true);}
 const headerTitle=navs.find(x=>x[0]===view)[1];
 return <div className="app-shell">
  <aside className="sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();setView('library');}}>映知<span className="brand-dot">.</span></a><nav aria-label="主导航">{navs.map(([key,label,Icon])=><button key={key} aria-label={label} className={`nav-item ${view===key?'active':''}`} onClick={()=>{setView(key);setMobileDetail(false);}}><Icon size={20}/><span>{label}</span></button>)}</nav><div className="local-indicator"><span/><span>本地运行</span><ChevronRight size={15}/></div></aside>
  <div className="workspace"><header className="page-header"><div><h1>{headerTitle}</h1><p>{view==='library'?'从喜欢和收藏中，留下值得回看的内容。':view==='jobs'?'每一步处理，都有可追踪的进度。':view==='cards'?'把视频里的收获，留在手边。':'让工作台按你的方式运行。'}</p></div><div className="header-actions"><button className="button secondary" disabled={posting||hasBusy} onClick={()=>submit('login')}><Link size={17}/>连接抖音</button><button className="button primary" disabled={posting||hasBusy} onClick={()=>submit('collect')}><RefreshCw size={17} className={posting?'spin':''}/>同步列表</button></div></header>
   {error&&<div className="banner error" role="alert"><Info size={18}/><span>{error}</span><button onClick={()=>refresh()} className="text-button">重新连接</button><button aria-label="关闭错误" onClick={()=>setError('')} className="icon-button"><X size={16}/></button></div>}
   {notice&&<div className="banner success" role="status"><Check size={17}/><span>{notice}</span><button aria-label="关闭提示" onClick={()=>setNotice('')} className="icon-button"><X size={16}/></button></div>}
   {loading?<div className="loading-state"><LoaderCircle className="spin"/>正在读取本地资料…</div>:<>
    {view==='library'&&<div className={`library-layout ${mobileDetail?'show-detail':''}`}><section className="library-main"><div className="library-toolbar"><div className="source-tabs" role="tablist" aria-label="来源">{['collection','like','all'].map(s=><button role="tab" aria-selected={source===s} className={source===s?'selected':''} key={s} onClick={()=>chooseSource(s)}>{sourceText[s]}</button>)}</div><label className="search"><Search size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索标题或作者" aria-label="搜索标题或作者"/>{query&&<button aria-label="清空搜索" className="icon-button" onClick={()=>setQuery('')}><X size={14}/></button>}</label></div>
     <div className="selection-toolbar"><span>{selected.length?`已选择 ${selected.length} 条`:`${filtered.length} 条资料`}</span><div className="selection-actions"><label className="status-filter">状态<select aria-label="状态筛选" value={statusFilter} onChange={e=>{setStatusFilter(e.target.value);setSelected([]);}}><option value="all">全部状态</option><option value="pending">待转写</option><option value="success">已转写</option><option value="attention">需处理</option><option value="image">图文内容</option></select></label><label>同步数量<select aria-label="同步数量" value={limit} onChange={e=>setLimit(Number(e.target.value))}>{[3,10,20,50,100].map(x=><option key={x} value={x}>{x} 条</option>)}</select></label><button className="button compact secondary" disabled={!selected.length||!ready||hasBusy||posting} onClick={transcribeSelected}><AudioLines size={16}/>本地转写</button></div></div>
     <div className="video-table"><div className="table-heading"><input type="checkbox" aria-label="选择全部视频" checked={allPicked} onChange={()=>setSelected(allPicked?[]:pickable.map(x=>x.id))}/><span>视频</span><span>来源</span><span>状态</span></div>{filtered.length?filtered.map(item=><div key={item.id} className={`video-row ${active?.id===item.id?'current':''}`}><input aria-label={`选择 ${item.title||'未命名视频'}`} type="checkbox" checked={selected.includes(item.id)} disabled={item.media_kind==='image'||item.status==='skipped_image'||item.status==='transcribing'} onChange={()=>toggle(item.id)}/><button className="video-title" aria-label={`查看 ${item.title||'未命名视频'}`} onClick={()=>openItem(item)}><span className="video-icon">{item.media_kind==='image'?<Image size={21}/>:<Video size={21}/>}</span><span><strong>{item.title||'未命名视频'}</strong><small>{item.author||'未知作者'}</small></span></button><span className="source-cell">{sourceText[item.source]||item.source}</span><Status status={item.status}/></div>):<Empty icon={Search} title={query?'没有找到匹配的资料':'这里还没有视频'} text={query?'试试其他关键词，或切换来源。':'连接抖音后，点击“同步列表”读取收藏或喜欢。'}/>}</div>
     <p className="library-footnote"><Info size={14}/>{source==='all'?'同步默认读取收藏；转写请按单个来源勾选。':'同步只读取列表，勾选后再开始本地转写。'}图文识别和 AI 总结稍后配置。</p>
    </section><Inspector item={active} cards={activeCards} tab={detailTab} setTab={setDetailTab} onBack={()=>setMobileDetail(false)}/></div>}
    {view==='jobs'&&<section className="page-content"><div className="section-heading"><h2>处理记录</h2><span>任务依次执行，避免同时占用浏览器或转写资源</span></div>{jobs.length?<div className="job-list">{jobs.map(job=><JobRow key={job.id} job={job}/>)}</div>:<Empty icon={ListTodo} title="还没有任务" text="连接抖音、同步列表或转写视频后，可在这里查看进度。"/>}</section>}
    {view==='cards'&&<section className="page-content"><div className="section-heading"><h2>已生成的卡片</h2><span>{cards.length} 张 · 来自本地文件</span></div>{cards.length?<div className="cards-grid">{cards.map(card=><article className="knowledge-card" key={card.id}><div className="card-preview">{safeFile(card.png_url)?<img src={safeFile(card.png_url)} alt={`${card.title}知识卡片`} loading="lazy"/>:<FileText size={44}/>}</div><div className="card-caption"><span className="card-source">{sourceText[card.source]||'本地卡片'}</span><h3>{card.title}</h3><p>{card.author||'未知作者'}</p><div className="card-links">{safeFile(card.html_url)&&<a href={safeFile(card.html_url)} target="_blank" rel="noreferrer">打开卡片<ExternalLink size={14}/></a>}{safeFile(card.png_url)&&<a href={safeFile(card.png_url)} download><Download size={14}/>下载图片</a>}</div></div></article>)}</div>:<Empty icon={BookOpen} title="还没有知识卡片" text="已有卡片会在这里展示。AI 总结服务暂未接入，转写不会自动生成新卡片。"/>}</section>}
    {view==='settings'&&<section className="page-content settings-page"><div className="settings-section"><h2>本地转写</h2><p>视频音频在你的 Mac 上转成文字。</p><div className="setting-row"><div><strong>Whisper small</strong><span>本地语音模型 · CPU 转写</span></div><span className={`status ${ready?'status-success':'status-failed'}`}>{ready?'已就绪':'需要配置'}</span></div>{!ready&&<p className="setting-warning">{data.settings.transcription?.missing?.join('、')||'请检查语音转写依赖。'}</p>}</div><div className="settings-section"><h2>AI 总结</h2><p>完成转写后，再选择适合的总结方式。</p><div className="setting-row"><div><strong>总结服务</strong><span>当前不会调用付费 API，也不会自动运行 Codex。</span></div><span className="status status-pending">暂未接入</span></div></div><div className="settings-section"><h2>抖音连接</h2><p>在独立浏览器中登录，授权状态仅保存在本机。</p><div className="setting-row"><div><strong>专用浏览器</strong><span>登录窗口成功后会自动关闭。能否读取列表，以任务结果为准。</span></div><button className="button secondary" disabled={hasBusy||posting} onClick={()=>submit('login')}><Link size={16}/>连接抖音</button></div></div><div className="privacy-note"><Info size={17}/>工作台只在本机开放。自动采集和定时任务均未启用。</div></section>}
   </>}
  </div><footer className="task-dock"><span className="dock-label">最近任务</span>{currentJob?<JobRow job={currentJob} compact/>:<div className="dock-idle"><AudioLines size={21}/><div><strong>准备就绪</strong><span>选择视频后开始本地转写，进度会显示在这里。</span></div></div>}</footer>
 </div>;
}
function Status({status}){return <span className={`status status-${status}`}>{statusText[status]||status||'待转写'}</span>;}
function Empty({icon:Icon,title,text}){return <div className="empty-state"><Icon size={30}/><h3>{title}</h3><p>{text}</p></div>;}
function DetailTabs({tab,setTab,cards,label='资料详情'}){
 return <div className="detail-tabs" role="tablist" aria-label={label}><button role="tab" aria-selected={tab==='transcript'} onClick={()=>setTab('transcript')}>逐字稿</button><button role="tab" aria-selected={tab==='card'} onClick={()=>setTab('card')}>卡片{cards.length>0&&<span>{cards.length}</span>}</button></div>;
}
function DetailContent({item,cards,tab}){
 const card=cards[0];
 return <>{tab==='transcript'?(item.transcript?<div className="transcript">{item.transcript}</div>:<div className="detail-empty"><FileText size={26}/><p>{item.media_kind==='image'||item.status==='skipped_image'?'这是图文内容，需图片文字识别；当前不会进行语音转写。':['no_speech','unavailable'].includes(item.status)?'本次没有识别到语音，可核对原视频后再决定是否重试。':item.status==='transcribing'?'本地转写正在进行，完成后会自动显示逐字稿。':item.error||'还没有逐字稿。勾选视频后点击“本地转写”。'}</p></div>):card?(<div className="detail-card">{safeFile(card.png_url)?<img src={safeFile(card.png_url)} alt={`${card.title}知识卡片`}/>:<p>卡片已保存为 HTML。</p>}<div className="card-links">{safeFile(card.html_url)&&<a href={safeFile(card.html_url)} target="_blank" rel="noreferrer">打开卡片<ExternalLink size={14}/></a>}{safeFile(card.png_url)&&<a href={safeFile(card.png_url)} download><Download size={14}/>下载图片</a>}</div></div>):<div className="detail-empty"><BookOpen size={26}/><p>这条资料还没有卡片。AI 总结服务尚未接入。</p></div>}</>;
}
function Reader({item,cards,tab,setTab,onClose}){
 const panel=useRef(null);
 useEffect(()=>{
  const previous=document.activeElement,overflow=document.body.style.overflow;
  document.body.style.overflow='hidden';panel.current.querySelector('button')?.focus();
  function keydown(event){
   if(event.key==='Escape'){event.preventDefault();onClose();}
   if(event.key==='Tab'){
    const targets=[...panel.current.querySelectorAll('button,a[href]')],first=targets[0],last=targets[targets.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
   }
  }
  document.addEventListener('keydown',keydown);
  return()=>{document.body.style.overflow=overflow;document.removeEventListener('keydown',keydown);previous?.focus();};
 },[onClose]);
 return <div className="reader-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}><section ref={panel} className="reader-dialog" role="dialog" aria-modal="true" aria-labelledby="reader-title"><header className="reader-header"><div><span className="reader-eyebrow">展开阅读 · {sourceText[item.source]} · {item.author||'未知作者'}</span><h2 id="reader-title">{item.title||'未命名视频'}</h2></div><button className="button secondary" aria-label="关闭阅读" onClick={onClose}><X size={18}/>关闭</button></header><DetailTabs tab={tab} setTab={setTab} cards={cards} label="展开阅读内容"/><div className="reader-body"><DetailContent item={item} cards={cards} tab={tab}/></div></section></div>;
}
function Inspector({item,cards,tab,setTab,onBack}){
 const [expanded,setExpanded]=useState(false);
 const closeReader=useCallback(()=>setExpanded(false),[]);
 useEffect(()=>setExpanded(false),[item?.id]);
 if(!item)return <aside className="inspector"><Empty icon={FileText} title="选择一条资料" text="在这里查看逐字稿、原视频和已有卡片。"/><div className="analysis-note"><p><Info size={17}/>尚未配置 AI 总结功能</p></div></aside>;
 const link=safeSource(item.source_url);
 return <><aside className="inspector"><button className="mobile-back text-button" onClick={onBack}><ArrowLeft size={16}/>返回列表</button><div className="inspector-head"><h2 title={item.title}>{item.title||'未命名视频'}</h2><dl><div><dt>作者</dt><dd>{item.author||'未知作者'}</dd></div><div><dt>来源</dt><dd>{sourceText[item.source]||item.source}</dd></div><div><dt>状态</dt><dd><Status status={item.status}/></dd></div></dl><div className="inspector-actions">{link&&<a className="original-link" href={link} target="_blank" rel="noreferrer"><ExternalLink size={15}/>查看原视频</a>}<button className="button compact secondary" onClick={()=>setExpanded(true)}><BookOpen size={15}/>展开阅读</button></div></div><DetailTabs tab={tab} setTab={setTab} cards={cards}/><div className="detail-body"><DetailContent item={item} cards={cards} tab={tab}/></div><div className="analysis-note"><p><Info size={15}/>尚未配置 AI 总结功能</p></div></aside>{expanded&&<Reader item={item} cards={cards} tab={tab} setTab={setTab} onClose={closeReader}/>}</>;
}

function JobRow({job,compact=false}){
 const total=Number(job.total)||0,done=Math.max(0,Number(job.done)||0),busy=busyStates.has(job.status);
 return <article className={`job-row ${compact?'compact-job':''}`}><div className="job-icon">{busy?<LoaderCircle size={21} className="spin"/>:job.status==='completed'?<Check size={21}/>:<AudioLines size={21}/>}</div><div className="job-description"><strong>{kindText[job.kind]||job.kind}<span>{sourceText[job.source]||''}</span></strong><p>{job.message||jobText[job.status]||job.status}</p></div><div className="job-progress">{total>0?<><progress value={Math.min(done,total)} max={total} aria-label="任务进度"/><span>{done} / {total}</span></>:<span className="no-total">{busy?'等待任务返回进度':''}</span>}</div><span className={`job-status job-status-${job.status}`}>{jobText[job.status]||job.status}</span></article>;
}
