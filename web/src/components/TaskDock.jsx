import React from 'react';
import { AudioLines } from 'lucide-react';
import { JobRow } from './Common.jsx';

export default function TaskDock({ currentJob, onCancelJob }) {
  return (
    <footer className="task-dock">
      <span className="dock-label">最近任务</span>
      {currentJob ? (
        <JobRow job={currentJob} compact onCancel={onCancelJob} />
      ) : (
        <div className="dock-idle">
          <AudioLines size={21} />
          <div>
            <strong>准备就绪</strong>
            <span>选择视频后开始本地转写或生成卡片，进度会显示在这里。</span>
          </div>
        </div>
      )}
    </footer>
  );
}
