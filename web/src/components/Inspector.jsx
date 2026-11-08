import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FileText,
  BookOpen,
  ArrowLeft,
  ExternalLink,
  Download,
  X,
  Info,
  Sparkles,
} from 'lucide-react';
import { sourceText, safeSource, safeFile } from '../api.js';
import { Status, Empty } from './Common.jsx';

export function DetailTabs({ tab, setTab, cards, label = '资料详情' }) {
  return (
    <div className="detail-tabs" role="tablist" aria-label={label}>
      <button
        role="tab"
        aria-selected={tab === 'transcript'}
        onClick={() => setTab('transcript')}
      >
        逐字稿
      </button>
      <button
        role="tab"
        aria-selected={tab === 'card'}
        onClick={() => setTab('card')}
      >
        卡片{cards.length > 0 && <span>{cards.length}</span>}
      </button>
    </div>
  );
}

export function DetailContent({
  item,
  cards,
  tab,
  onGenerateCard,
  cardTheme,
  setCardTheme,
  hasBusy,
  posting,
}) {
  const card = cards[0];
  const canSummarize =
    item.transcript || (item.media_kind === 'image' && item.status === 'success');

  return (
    <>
      {tab === 'transcript' ? (
        item.transcript ? (
          <div className="transcript">
            {cards.length === 0 && (
              <div className="generate-card-bar">
                <span>逐字稿已就绪，可一键提炼卡片</span>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <select
                    value={cardTheme || 'classic'}
                    onChange={(e) => setCardTheme?.(e.target.value)}
                    style={{ fontSize: 11, padding: '4px 6px', borderRadius: 4, border: '1px solid #c9d9cf' }}
                    title="选择卡片视觉主题"
                  >
                    <option value="classic">经典墨绿</option>
                    <option value="minimal">极简纸白</option>
                    <option value="dark">暗黑极客</option>
                    <option value="xiaohongshu">手账高赞</option>
                  </select>
                  <button
                    className="button compact sparkle"
                    disabled={hasBusy || posting}
                    onClick={() => onGenerateCard?.(item.id, item.source, cardTheme)}
                  >
                    <Sparkles size={14} /> 一键提炼卡片
                  </button>
                </div>
              </div>
            )}
            {item.transcript}
          </div>
        ) : (
          <div className="detail-empty">
            <FileText size={26} />
            <p>
              {item.media_kind === 'image' || item.status === 'skipped_image'
                ? '这是图文内容，需图片文字识别；当前不会进行语音转写。'
                : ['no_speech', 'unavailable'].includes(item.status)
                ? '本次没有识别到语音，可核对原视频后再决定是否重试。'
                : item.status === 'transcribing'
                ? '本地转写正在进行，完成后会自动显示逐字稿。'
                : item.error || '还没有逐字稿。勾选视频后点击“本地转写”。'}
            </p>
          </div>
        )
      ) : card ? (
        <div className="detail-card">
          {safeFile(card.png_url) ? (
            <img src={safeFile(card.png_url)} alt={`${card.title}知识卡片`} />
          ) : (
            <p>卡片已保存为 HTML。</p>
          )}
          <div className="card-links">
            {safeFile(card.html_url) && (
              <a href={safeFile(card.html_url)} target="_blank" rel="noreferrer">
                打开卡片
                <ExternalLink size={14} />
              </a>
            )}
            {safeFile(card.png_url) && (
              <a href={safeFile(card.png_url)} download>
                <Download size={14} />下载图片
              </a>
            )}
            <button
              className="text-button"
              style={{ fontSize: 12, color: '#3b6a55', cursor: 'pointer' }}
              disabled={hasBusy || posting}
              onClick={() => onGenerateCard?.(item.id, item.source, cardTheme)}
              title="使用新主题重新渲染卡片"
            >
              <Sparkles size={13} style={{ marginRight: 3 }} />重置卡片风格
            </button>
          </div>
        </div>
      ) : (
        <div className="detail-empty">
          <BookOpen size={26} />
          <p>
            这条资料还没有卡片。
            {canSummarize ? '可直接点击“生成卡片”进行提炼。' : 'AI 总结服务尚未接入。'}
          </p>
          {canSummarize && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 12 }}>
              <select
                value={cardTheme || 'classic'}
                onChange={(e) => setCardTheme?.(e.target.value)}
                style={{ fontSize: 11, padding: '4px 6px', borderRadius: 4, border: '1px solid #c9d9cf' }}
              >
                <option value="classic">经典墨绿</option>
                <option value="minimal">极简纸白</option>
                <option value="dark">暗黑极客</option>
                <option value="xiaohongshu">手账高赞</option>
              </select>
              <button
                className="button compact sparkle"
                disabled={hasBusy || posting}
                onClick={() => onGenerateCard?.(item.id, item.source, cardTheme)}
              >
                <Sparkles size={14} /> 立即生成卡片
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}

export function Reader({
  item,
  cards,
  tab,
  setTab,
  onClose,
  onGenerateCard,
  cardTheme,
  setCardTheme,
  hasBusy,
  posting,
}) {
  const panel = useRef(null);

  useEffect(() => {
    const previous = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current?.querySelector('button')?.focus();

    function keydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
      if (event.key === 'Tab') {
        const targets = [...(panel.current?.querySelectorAll('button,a[href]') || [])];
        const first = targets[0];
        const last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener('keydown', keydown);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener('keydown', keydown);
      previous?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="reader-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        ref={panel}
        className="reader-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reader-title"
      >
        <header className="reader-header">
          <div>
            <span className="reader-eyebrow">
              展开阅读 · {sourceText[item.source]} · {item.author || '未知作者'}
            </span>
            <h2 id="reader-title">{item.title || '未命名视频'}</h2>
          </div>
          <button
            className="button secondary"
            aria-label="关闭阅读"
            onClick={onClose}
          >
            <X size={18} />关闭
          </button>
        </header>
        <DetailTabs
          tab={tab}
          setTab={setTab}
          cards={cards}
          label="展开阅读内容"
        />
        <div className="reader-body">
          <DetailContent
            item={item}
            cards={cards}
            tab={tab}
            onGenerateCard={onGenerateCard}
            cardTheme={cardTheme}
            setCardTheme={setCardTheme}
            hasBusy={hasBusy}
            posting={posting}
          />
        </div>
      </section>
    </div>
  );
}

export default function Inspector({
  item,
  cards,
  tab,
  setTab,
  onBack,
  onGenerateCard,
  cardTheme,
  setCardTheme,
  analysisConfigured,
  hasBusy,
  posting,
}) {
  const [expanded, setExpanded] = useState(false);
  const closeReader = useCallback(() => setExpanded(false), []);

  useEffect(() => setExpanded(false), [item?.id]);

  if (!item)
    return (
      <aside className="inspector">
        <Empty
          icon={FileText}
          title="选择一条资料"
          text="在这里查看逐字稿、原视频和已有卡片。"
        />
        <div className="analysis-note">
          <p>
            <Info size={17} />尚未配置 AI 总结功能
          </p>
        </div>
      </aside>
    );

  const link = safeSource(item.source_url);

  return (
    <>
      <aside className="inspector">
        <button className="mobile-back text-button" onClick={onBack}>
          <ArrowLeft size={16} />返回列表
        </button>
        <div className="inspector-head">
          <h2 title={item.title}>{item.title || '未命名视频'}</h2>
          <dl>
            <div>
              <dt>作者</dt>
              <dd>{item.author || '未知作者'}</dd>
            </div>
            <div>
              <dt>来源</dt>
              <dd>{sourceText[item.source] || item.source}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>
                <Status status={item.status} />
              </dd>
            </div>
          </dl>
          <div className="inspector-actions">
            {link && (
              <a
                className="original-link"
                href={link}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={15} />查看原视频
              </a>
            )}
            <button
              className="button compact secondary"
              onClick={() => setExpanded(true)}
            >
              <BookOpen size={15} />展开阅读
            </button>
          </div>
        </div>
        <DetailTabs tab={tab} setTab={setTab} cards={cards} />
        <div className="detail-body">
          <DetailContent
            item={item}
            cards={cards}
            tab={tab}
            onGenerateCard={onGenerateCard}
            cardTheme={cardTheme}
            setCardTheme={setCardTheme}
            hasBusy={hasBusy}
            posting={posting}
          />
        </div>
        <div className="analysis-note">
          <p>
            <Info size={15} />
            {analysisConfigured ? '已配置 AI 总结提炼服务' : '尚未配置 AI 总结功能'}
          </p>
        </div>
      </aside>
      {expanded && (
        <Reader
          item={item}
          cards={cards}
          tab={tab}
          setTab={setTab}
          onClose={closeReader}
          onGenerateCard={onGenerateCard}
          cardTheme={cardTheme}
          setCardTheme={setCardTheme}
          hasBusy={hasBusy}
          posting={posting}
        />
      )}
    </>
  );
}
