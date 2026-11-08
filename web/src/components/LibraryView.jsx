import React from 'react';
import { Search, X, AudioLines, Sparkles, Image, Video } from 'lucide-react';
import { sourceText } from '../api.js';
import { Status, Empty } from './Common.jsx';

export default function LibraryView({
  source,
  chooseSource,
  query,
  setQuery,
  statusFilter,
  setStatusFilter,
  limit,
  setLimit,
  selected,
  setSelected,
  toggle,
  pickable,
  allPicked,
  filtered,
  active,
  openItem,
  transcribeSelected,
  summarizeSelected,
  cardTheme,
  setCardTheme,
  ready,
  analysisConfigured,
  hasBusy,
  posting,
}) {
  return (
    <section className="library-main">
      <div className="library-toolbar">
        <div className="source-tabs" role="tablist" aria-label="来源">
          {['collection', 'like', 'all'].map((s) => (
            <button
              role="tab"
              aria-selected={source === s}
              className={source === s ? 'selected' : ''}
              key={s}
              onClick={() => chooseSource(s)}
            >
              {sourceText[s]}
            </button>
          ))}
        </div>
        <label className="search">
          <Search size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索标题或作者"
            aria-label="搜索标题或作者"
          />
          {query && (
            <button
              aria-label="清空搜索"
              className="icon-button"
              onClick={() => setQuery('')}
            >
              <X size={14} />
            </button>
          )}
        </label>
      </div>

      <div className="selection-toolbar">
        <span>
          {selected.length ? `已选择 ${selected.length} 条` : `${filtered.length} 条资料`}
        </span>
        <div className="selection-actions">
          <label className="status-filter">
            状态
            <select
              aria-label="状态筛选"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setSelected([]);
              }}
            >
              <option value="all">全部状态</option>
              <option value="pending">待转写</option>
              <option value="success">已转写</option>
              <option value="attention">需处理</option>
              <option value="image">图文内容</option>
            </select>
          </label>
          <label>
            同步数量
            <select
              aria-label="同步数量"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              {[3, 10, 20, 50, 100].map((x) => (
                <option key={x} value={x}>
                  {x} 条
                </option>
              ))}
            </select>
          </label>
          <button
            className="button compact secondary"
            disabled={!selected.length || !ready || hasBusy || posting}
            onClick={transcribeSelected}
          >
            <AudioLines size={16} />本地转写
          </button>
          <select
            value={cardTheme || 'classic'}
            onChange={(e) => setCardTheme?.(e.target.value)}
            style={{ padding: '6px', fontSize: 12, borderRadius: 5, border: '1px solid #e5e9e6', color: '#33413c' }}
            title="选择要生成的卡片视觉主题"
          >
            <option value="classic">经典墨绿</option>
            <option value="minimal">极简纸白</option>
            <option value="dark">暗黑极客</option>
            <option value="xiaohongshu">手账高赞</option>
          </select>
          <button
            className="button compact sparkle"
            disabled={!selected.length || hasBusy || posting}
            onClick={summarizeSelected}
            title={
              !analysisConfigured
                ? '生成前请先在设置中配置大模型'
                : '对选中的内容生成知识卡片'
            }
          >
            <Sparkles size={15} />生成卡片
          </button>
        </div>
      </div>

      <div className="video-table">
        <div className="table-heading">
          <input
            type="checkbox"
            aria-label="选择全部视频"
            checked={allPicked}
            onChange={() => setSelected(allPicked ? [] : pickable.map((x) => x.id))}
          />
          <span>视频</span>
          <span>来源</span>
          <span>状态</span>
        </div>
        {filtered.length ? (
          filtered.map((item) => (
            <div
              key={item.id}
              className={`video-row ${active?.id === item.id ? 'current' : ''}`}
            >
              <input
                aria-label={`选择 ${item.title || '未命名视频'}`}
                type="checkbox"
                checked={selected.includes(item.id)}
                disabled={
                  item.media_kind === 'image' ||
                  item.status === 'skipped_image' ||
                  item.status === 'transcribing'
                }
                onChange={() => toggle(item.id)}
              />
              <button
                className="video-title"
                aria-label={`查看 ${item.title || '未命名视频'}`}
                onClick={() => openItem(item)}
              >
                <span className="video-icon">
                  {item.media_kind === 'image' ? (
                    <Image size={21} />
                  ) : (
                    <Video size={21} />
                  )}
                </span>
                <span>
                  <strong>{item.title || '未命名视频'}</strong>
                  <small>{item.author || '未知作者'}</small>
                </span>
              </button>
              <span className="source-cell">
                {sourceText[item.source] || item.source}
              </span>
              <Status status={item.status} />
            </div>
          ))
        ) : (
          <Empty
            icon={Search}
            title={query ? '没有找到匹配的资料' : '这里还没有视频'}
            text={
              query
                ? '试试其他关键词，或切换来源。'
                : '连接抖音后，点击“同步列表”读取收藏或喜欢。'
            }
          />
        )}
      </div>
      <p className="library-footnote">
        {source === 'all'
          ? '同步默认读取收藏；转写或生成卡片请按单个来源勾选。'
          : '同步只读取列表，勾选后再开始本地转写或 AI 提炼卡片。'}
      </p>
    </section>
  );
}
