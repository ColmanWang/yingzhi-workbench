import React from 'react';
import { ChevronRight } from 'lucide-react';

export default function Sidebar({ navs, view, setView, onSelectNav }) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#"
        onClick={(e) => {
          e.preventDefault();
          setView('library');
          onSelectNav?.();
        }}
      >
        映知<span className="brand-dot">.</span>
      </a>
      <nav aria-label="主导航">
        {navs.map(([key, label, Icon]) => (
          <button
            key={key}
            aria-label={label}
            className={`nav-item ${view === key ? 'active' : ''}`}
            onClick={() => {
              setView(key);
              onSelectNav?.();
            }}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="local-indicator">
        <span />
        <span>本地运行</span>
        <ChevronRight size={15} />
      </div>
    </aside>
  );
}
