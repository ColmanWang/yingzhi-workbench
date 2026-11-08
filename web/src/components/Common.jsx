import React from 'react';
import { LoaderCircle, Check, AudioLines, X } from 'lucide-react';
import { statusText, jobText, kindText, sourceText } from '../api.js';

export const busyStates = new Set(['queued', 'running']);

export function Status({ status }) {
  return (
    <span className={`status status-${status}`}>
      {statusText[status] || status || '待转写'}
    </span>
  );
}

export function Empty({ icon: Icon, title, text }) {
  return (
    <div className="empty-state">
      <Icon size={30} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export function JobRow({ job, compact = false, onCancel }) {
  const total = Number(job.total) || 0;
  const done = Math.max(0, Number(job.done) || 0);
  const busy = busyStates.has(job.status);

  return (
    <article className={`job-row ${compact ? 'compact-job' : ''}`}>
      <div className="job-icon">
        {busy ? (
          <LoaderCircle size={21} className="spin" />
        ) : job.status === 'completed' ? (
          <Check size={21} />
        ) : (
          <AudioLines size={21} />
        )}
      </div>
      <div className="job-description">
        <strong>
          {kindText[job.kind] || job.kind}
          <span>{sourceText[job.source] || ''}</span>
        </strong>
        <p>{job.message || jobText[job.status] || job.status}</p>
      </div>
      <div className="job-progress">
        {total > 0 ? (
          <>
            <progress
              value={Math.min(done, total)}
              max={total}
              aria-label="任务进度"
            />
            <span>
              {done} / {total}
            </span>
          </>
        ) : (
          <span className="no-total">
            {busy ? '等待任务返回进度' : ''}
          </span>
        )}
      </div>
      <span className={`job-status job-status-${job.status}`}>
        {jobText[job.status] || job.status}
      </span>
      {busy && onCancel && (
        <button
          className="icon-button"
          aria-label="取消任务"
          title="中止当前任务"
          onClick={() => onCancel(job.id)}
          style={{ marginLeft: 8 }}
        >
          <X size={15} />
        </button>
      )}
    </article>
  );
}
