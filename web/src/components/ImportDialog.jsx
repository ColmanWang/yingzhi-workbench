import React, { useState } from 'react';
import { X, Plus, LoaderCircle, CheckCircle } from 'lucide-react';

export default function ImportDialog({ open, onClose, onImport, importing }) {
  const [url, setUrl] = useState('');
  const [source, setSource] = useState('collection');
  const [error, setError] = useState('');

  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!url.trim()) {
      setError('请输入或粘贴抖音链接');
      return;
    }
    setError('');
    try {
      await onImport(url.trim(), source);
      setUrl('');
      onClose();
    } catch (err) {
      setError(err.message || '导入失败，请检查链接有效性');
    }
  }

  return (
    <div
      className="reader-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="reader-dialog"
        style={{
          width: 'min(540px, 92vw)',
          height: 'auto',
          minHeight: 'auto',
          borderRadius: 12,
          padding: 24,
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 16,
          }}
        >
          <h2 id="import-title" style={{ fontSize: 18, margin: 0, fontWeight: 650 }}>
            快捷导入单条抖音视频
          </h2>
          <button className="icon-button" aria-label="关闭" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label>抖音分享文本或链接</label>
            <textarea
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="直接粘贴手机端复制的完整分享口令或网址，例如：https://v.douyin.com/xxx/ 或包含口令的整段文本"
              rows={4}
              style={{
                width: '100%',
                border: '1px solid #dce2e0',
                borderRadius: 6,
                padding: '10px 12px',
                fontSize: 13,
                resize: 'none',
              }}
              required
            />
            <span className="form-hint">
              系统将自动提取其中的短链接并自动追踪真实视频 ID，无需全量同步。
            </span>
          </div>

          <div className="form-group" style={{ marginBottom: 20 }}>
            <label>归属来源</label>
            <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input
                  type="radio"
                  name="importSource"
                  value="collection"
                  checked={source === 'collection'}
                  onChange={() => setSource('collection')}
                />
                收藏列表
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input
                  type="radio"
                  name="importSource"
                  value="like"
                  checked={source === 'like'}
                  onChange={() => setSource('like')}
                />
                喜欢列表
              </label>
            </div>
          </div>

          {error && (
            <div
              style={{
                color: '#a85849',
                fontSize: 12,
                background: '#fff6f4',
                padding: '8px 12px',
                borderRadius: 6,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button
              type="button"
              className="button secondary"
              onClick={onClose}
              disabled={importing}
            >
              取消
            </button>
            <button
              type="submit"
              className="button primary"
              disabled={importing}
            >
              {importing ? (
                <>
                  <LoaderCircle size={15} className="spin" /> 解析中…
                </>
              ) : (
                <>
                  <Plus size={15} /> 立即解析导入
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
