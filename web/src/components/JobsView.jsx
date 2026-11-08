import React from 'react';
import { ListTodo } from 'lucide-react';
import { JobRow, Empty } from './Common.jsx';

export default function JobsView({ jobs, onCancelJob }) {
  return (
    <section className="page-content">
      <div className="section-heading">
        <h2>处理记录</h2>
        <span>任务依次执行，避免同时占用转写或模型资源</span>
      </div>
      {jobs.length ? (
        <div className="job-list">
          {jobs.map((job) => (
            <JobRow key={job.id} job={job} onCancel={onCancelJob} />
          ))}
        </div>
      ) : (
        <Empty
          icon={ListTodo}
          title="还没有任务"
          text="连接抖音、同步列表、转写视频或生成卡片后，可在这里查看进度。"
        />
      )}
    </section>
  );
}
