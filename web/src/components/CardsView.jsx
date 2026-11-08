import React, { useState } from 'react';
import { BookOpen, FileText, ExternalLink, Download, Archive } from 'lucide-react';
import { sourceText, safeFile } from '../api.js';
import { Empty } from './Common.jsx';

const THEME_NAMES = {
  classic: '经典墨绿',
  minimal: '极简纸白',
  dark: '暗黑极客',
  xiaohongshu: '手账高赞',
};

export default function CardsView({ cards, onExportZip, exportingZip }) {
  const [themeFilter, setThemeFilter] = useState('all');

  const filteredCards = cards.filter(
    (c) => themeFilter === 'all' || (c.theme || 'classic') === themeFilter
  );

  return (
    <section className="page-content">
      <div className="section-heading">
        <div>
          <h2>已生成的卡片</h2>
          <span style={{ display: 'block', marginTop: 4 }}>
            {filteredCards.length} 张卡片 · 支持多主题与离线归档
          </span>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select
            value={themeFilter}
            onChange={(e) => setThemeFilter(e.target.value)}
            style={{
              padding: '6px 10px',
              fontSize: 12,
              borderRadius: 6,
              border: '1px solid #dce2e0',
            }}
          >
            <option value="all">全部主题</option>
            <option value="classic">经典墨绿</option>
            <option value="minimal">极简纸白</option>
            <option value="dark">暗黑极客</option>
            <option value="xiaohongshu">手账高赞</option>
          </select>
          {cards.length > 0 && (
            <button
              className="button compact secondary"
              disabled={exportingZip}
              onClick={() => onExportZip?.(filteredCards.map((c) => c.item_id))}
              title="打包所有卡片及逐字稿为 ZIP 归档文件"
            >
              <Archive size={14} />
              {exportingZip ? '打包中…' : '批量导出 ZIP'}
            </button>
          )}
        </div>
      </div>

      {filteredCards.length ? (
        <div className="cards-grid">
          {filteredCards.map((card) => (
            <article className="knowledge-card" key={card.id}>
              <div className="card-preview">
                {safeFile(card.png_url) ? (
                  <img
                    src={safeFile(card.png_url)}
                    alt={`${card.title}知识卡片`}
                    loading="lazy"
                  />
                ) : (
                  <FileText size={44} />
                )}
              </div>
              <div className="card-caption">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="card-source">
                    {sourceText[card.source] || '本地卡片'}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: '#6e7d75',
                      background: '#edf2ee',
                      padding: '2px 6px',
                      borderRadius: 4,
                    }}
                  >
                    {THEME_NAMES[card.theme] || '经典墨绿'}
                  </span>
                </div>
                <h3>{card.title}</h3>
                <p>{card.author || '未知作者'}</p>
                <div className="card-links">
                  {safeFile(card.html_url) && (
                    <a
                      href={safeFile(card.html_url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      打开卡片
                      <ExternalLink size={14} />
                    </a>
                  )}
                  {safeFile(card.png_url) && (
                    <a href={safeFile(card.png_url)} download>
                      <Download size={14} />下载图片
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          icon={BookOpen}
          title="还没有知识卡片"
          text="在资料库选择已转写的条目，点击“生成卡片”即可将逐字稿自动提炼排版成卡片。"
        />
      )}
    </section>
  );
}
