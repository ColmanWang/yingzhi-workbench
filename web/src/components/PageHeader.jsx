import React from 'react';
import { Link, RefreshCw, Plus } from 'lucide-react';

const SUBTITLES = {
  library: '从喜欢和收藏中，留下值得回看的内容。',
  jobs: '每一步处理，都有可追踪的进度。',
  cards: '把视频里的收获，留在手边。',
  settings: '让工作台按你的方式运行。',
};

export default function PageHeader({ title, view, posting, hasBusy, onLogin, onCollect, onOpenImport }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{SUBTITLES[view] || ''}</p>
      </div>
      <div className="header-actions">
        <button
          className="button secondary"
          disabled={posting || hasBusy}
          onClick={onOpenImport}
          title="直接粘贴单条抖音分享链接或口令"
        >
          <Plus size={17} />导入链接
        </button>
        <button
          className="button secondary"
          disabled={posting || hasBusy}
          onClick={onLogin}
        >
          <Link size={17} />连接抖音
        </button>
        <button
          className="button primary"
          disabled={posting || hasBusy}
          onClick={onCollect}
        >
          <RefreshCw size={17} className={posting ? 'spin' : ''} />同步列表
        </button>
      </div>
    </header>
  );
}
