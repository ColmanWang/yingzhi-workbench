import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Play, ListTodo, BookOpen, Settings, Info, Check, X, LoaderCircle } from 'lucide-react';
import {
  request,
  postJob,
  saveSettings,
  testLlm,
  cancelJob,
  importVideoUrl,
  downloadZipExport,
  createEventSource,
  kindText,
} from './api.js';

import Sidebar from './components/Sidebar.jsx';
import PageHeader from './components/PageHeader.jsx';
import LibraryView from './components/LibraryView.jsx';
import Inspector from './components/Inspector.jsx';
import JobsView from './components/JobsView.jsx';
import CardsView from './components/CardsView.jsx';
import SettingsView from './components/SettingsView.jsx';
import TaskDock from './components/TaskDock.jsx';
import ImportDialog from './components/ImportDialog.jsx';
import { busyStates } from './components/Common.jsx';

const navs = [
  ['library', '视频资料库', Play],
  ['jobs', '任务中心', ListTodo],
  ['cards', '知识卡片', BookOpen],
  ['settings', '设置', Settings],
];

const emptyData = { items: [], jobs: [], cards: [], settings: {}, csrf_token: '' };

const PROVIDER_DEFAULTS = {
  siliconflow: {
    endpoint: 'https://api.siliconflow.cn/v1/chat/completions',
    model: 'Qwen/Qwen2.5-7B-Instruct',
  },
  ollama: {
    endpoint: 'http://localhost:11434/v1/chat/completions',
    model: 'qwen2.5:7b',
  },
  deepseek: {
    endpoint: 'https://api.deepseek.com/v1/chat/completions',
    model: 'deepseek-chat',
  },
  custom: {
    endpoint: '',
    model: '',
  },
};

export default function App() {
  const [data, setData] = useState(emptyData);
  const [view, setView] = useState('library');
  const [source, setSource] = useState('collection');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [detailTab, setDetailTab] = useState('transcript');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const [limit, setLimit] = useState(3);
  const [notice, setNotice] = useState('');
  const [mobileDetail, setMobileDetail] = useState(false);

  // Phase 3 states
  const [cardTheme, setCardTheme] = useState('classic');
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exportingZip, setExportingZip] = useState(false);

  // Settings form state
  const [settingsForm, setSettingsForm] = useState({
    provider: 'siliconflow',
    endpoint: 'https://api.siliconflow.cn/v1/chat/completions',
    api_key: '',
    model: 'Qwen/Qwen2.5-7B-Instruct',
    enabled: true,
  });
  const [testingLlm, setTestingLlm] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);

  // Transcription settings state
  const [transForm, setTransForm] = useState({
    engine: 'local_whisper',
    model: 'medium',
  });
  const [savingTrans, setSavingTrans] = useState(false);

  const refresh = useCallback(async (silent = false) => {
    try {
      const incoming = await request('/api/bootstrap');
      setData({ ...emptyData, ...incoming });
      setLoading(false);
      if (!silent) setError('');
    } catch (e) {
      setLoading(false);
      setError(e.message);
    }
  }, []);

  // Initialize and connect SSE
  useEffect(() => {
    refresh();

    let es = null;
    let fallbackTimer = null;

    es = createEventSource(
      (event) => {
        if (event.type === 'job_updated' || event.type === 'job_submitted') {
          const updatedJob = event.data;
          setData((old) => {
            const exists = old.jobs.some((j) => j.id === updatedJob.id);
            const nextJobs = exists
              ? old.jobs.map((j) => (j.id === updatedJob.id ? { ...j, ...updatedJob } : j))
              : [updatedJob, ...old.jobs];
            return { ...old, jobs: nextJobs };
          });
          if (['completed', 'failed', 'cancelled'].includes(updatedJob.status)) {
            refresh(true);
          }
        } else if (event.type === 'settings_updated') {
          setData((old) => ({ ...old, settings: event.data }));
        } else if (event.type === 'item_imported') {
          const item = event.data;
          setData((old) => ({
            ...old,
            items: [item, ...old.items.filter((x) => x.id !== item.id)],
          }));
        }
      },
      () => {
        if (!fallbackTimer) {
          fallbackTimer = setInterval(() => refresh(true), 10000);
        }
      }
    );

    return () => {
      es?.close();
      if (fallbackTimer) clearInterval(fallbackTimer);
    };
  }, [refresh]);

  useEffect(() => {
    if (data.settings?.analysis) {
      const a = data.settings.analysis;
      setSettingsForm((prev) => ({
        ...prev,
        provider: a.provider || 'siliconflow',
        endpoint: a.endpoint || PROVIDER_DEFAULTS.siliconflow.endpoint,
        model: a.model || PROVIDER_DEFAULTS.siliconflow.model,
        enabled: a.enabled ?? false,
      }));
    }
    if (data.settings?.transcription) {
      const t = data.settings.transcription;
      setTransForm((prev) => ({
        ...prev,
        engine: t.engine || 'local_whisper',
        model: t.model || 'medium',
      }));
    }
  }, [data.settings?.analysis, data.settings?.transcription]);

  const items = data.items || [];
  const jobs = data.jobs || [];
  const cards = data.cards || [];

  const filtered = useMemo(() => {
    return items.filter(
      (x) =>
        (source === 'all' || x.source === source) &&
        `${x.title} ${x.author}`.toLowerCase().includes(query.toLowerCase()) &&
        (statusFilter === 'all' ||
          (statusFilter === 'success'
            ? ['success', 'transcribed'].includes(x.status)
            : statusFilter === 'image'
            ? x.media_kind === 'image'
            : statusFilter === 'attention'
            ? ['failed', 'interrupted', 'no_speech', 'unavailable'].includes(x.status)
            : x.status === statusFilter))
    );
  }, [items, source, query, statusFilter]);

  const active = filtered.find((x) => x.id === activeId) || filtered[0] || null;
  const activeCards = cards.filter((x) => x.item_id === active?.id);
  const currentJob = jobs.find((x) => busyStates.has(x.status)) || jobs[0];
  const hasBusy = jobs.some((x) => busyStates.has(x.status));
  const ready = data.settings.transcription?.ready ?? data.settings.asr_ready ?? false;
  const analysisConfigured = Boolean(
    data.settings?.analysis?.configured || data.settings?.analysis_enabled
  );

  const pickable = filtered.filter(
    (x) => x.media_kind !== 'image' && x.status !== 'skipped_image' && x.status !== 'transcribing'
  );
  const allPicked = pickable.length > 0 && pickable.every((x) => selected.includes(x.id));

  async function submit(kind, explicitSource, ids, chosenTheme) {
    if (posting || hasBusy) return;
    const chosen = explicitSource || (source === 'all' ? 'collection' : source);
    setPosting(true);
    setError('');
    setNotice('');
    try {
      const body = {
        kind,
        source: chosen,
        ...(kind === 'collect' ? { limit: Number(limit) } : {}),
        ...(kind === 'transcribe' || kind === 'summarize' ? { ids } : {}),
        ...(kind === 'summarize' ? { theme: chosenTheme || cardTheme } : {}),
      };
      const job = await postJob(body, data.csrf_token);
      setData((old) => ({
        ...old,
        jobs: [job, ...old.jobs.filter((x) => x.id !== job.id)],
      }));
      setNotice(`${kindText[kind] || '任务'}已加入任务`);
      if (kind === 'transcribe' || kind === 'summarize') setSelected([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setPosting(false);
    }
  }

  async function handleCancelJob(jobId) {
    try {
      await cancelJob(jobId, data.csrf_token);
      setData((old) => ({
        ...old,
        jobs: old.jobs.map((j) => (j.id === jobId ? { ...j, status: 'cancelled', message: '已取消' } : j)),
      }));
      setNotice('任务已取消');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleImportUrl(url, importSource) {
    setImporting(true);
    try {
      const newItem = await importVideoUrl(url, importSource, data.csrf_token);
      setData((old) => ({
        ...old,
        items: [newItem, ...old.items.filter((x) => x.id !== newItem.id)],
      }));
      setActiveId(newItem.id);
      setNotice('视频已成功导入！可立即发起转写或提炼卡片。');
    } finally {
      setImporting(false);
    }
  }

  async function handleExportZip(ids) {
    if (!ids?.length) return;
    setExportingZip(true);
    try {
      await downloadZipExport(ids, data.csrf_token);
      setNotice(`已成功打包导出 ${ids.length} 张卡片及逐字稿！`);
    } catch (err) {
      setError(err.message || '导出 ZIP 失败');
    } finally {
      setExportingZip(false);
    }
  }

  function transcribeSelected() {
    const picked = items.filter(
      (x) => selected.includes(x.id) && x.media_kind !== 'image' && x.status !== 'skipped_image'
    );
    const sources = [...new Set(picked.map((x) => x.source))];
    if (sources.length !== 1) {
      setError('请按收藏或喜欢分组选择视频后转写。');
      return;
    }
    submit('transcribe', sources[0], picked.map((x) => x.id));
  }

  function summarizeSelected() {
    const picked = items.filter((x) => selected.includes(x.id));
    const sources = [...new Set(picked.map((x) => x.source))];
    if (sources.length !== 1) {
      setError('请按收藏或喜欢分组选择视频后生成卡片。');
      return;
    }
    submit('summarize', sources[0], picked.map((x) => x.id), cardTheme);
  }

  function toggle(id) {
    setSelected((old) => (old.includes(id) ? old.filter((x) => x !== id) : [...old, id]));
  }

  function chooseSource(value) {
    setSource(value);
    setSelected([]);
    setActiveId(null);
  }

  function openItem(item) {
    setActiveId(item.id);
    setDetailTab('transcript');
    setMobileDetail(true);
  }

  function handleProviderChange(e) {
    const p = e.target.value;
    const defaults = PROVIDER_DEFAULTS[p] || PROVIDER_DEFAULTS.custom;
    setSettingsForm((prev) => ({
      ...prev,
      provider: p,
      endpoint: defaults.endpoint || prev.endpoint,
      model: defaults.model || prev.model,
    }));
  }

  async function handleSaveSettings(e) {
    e?.preventDefault();
    setSavingSettings(true);
    setError('');
    try {
      const updated = await saveSettings({ ...settingsForm, enabled: true }, data.csrf_token);
      setData((old) => ({ ...old, settings: updated }));
      setNotice('AI 总结与模型配置已保存');
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleSaveTransSettings(e) {
    e?.preventDefault();
    setSavingTrans(true);
    setError('');
    try {
      const updated = await saveSettings({ transcription: transForm }, data.csrf_token);
      setData((old) => ({ ...old, settings: updated }));
      setNotice('语音转写配置已保存');
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingTrans(false);
    }
  }

  async function handleTestLlm() {
    setTestingLlm(true);
    setTestResult(null);
    try {
      const res = await testLlm(settingsForm, data.csrf_token);
      setTestResult(res);
      if (res.ok) {
        setNotice('大模型测试连接成功！');
      } else {
        setError(`模型连接测试失败: ${res.error || '未知错误'}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setTestingLlm(false);
    }
  }

  const headerTitle = navs.find((x) => x[0] === view)[1];

  return (
    <div className="app-shell">
      <Sidebar
        navs={navs}
        view={view}
        setView={setView}
        onSelectNav={() => setMobileDetail(false)}
      />

      <div className="workspace">
        <PageHeader
          title={headerTitle}
          view={view}
          posting={posting}
          hasBusy={hasBusy}
          onLogin={() => submit('login')}
          onCollect={() => submit('collect')}
          onOpenImport={() => setImportOpen(true)}
        />

        {error && (
          <div className="banner error" role="alert">
            <Info size={18} />
            <span>{error}</span>
            <button onClick={() => refresh()} className="text-button">
              重新连接
            </button>
            <button
              aria-label="关闭错误"
              onClick={() => setError('')}
              className="icon-button"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {notice && (
          <div className="banner success" role="status">
            <Check size={17} />
            <span>{notice}</span>
            <button
              aria-label="关闭提示"
              onClick={() => setNotice('')}
              className="icon-button"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {loading ? (
          <div className="loading-state">
            <LoaderCircle className="spin" />正在读取本地资料…
          </div>
        ) : (
          <>
            {view === 'library' && (
              <div className={`library-layout ${mobileDetail ? 'show-detail' : ''}`}>
                <LibraryView
                  source={source}
                  chooseSource={chooseSource}
                  query={query}
                  setQuery={setQuery}
                  statusFilter={statusFilter}
                  setStatusFilter={setStatusFilter}
                  limit={limit}
                  setLimit={setLimit}
                  selected={selected}
                  setSelected={setSelected}
                  toggle={toggle}
                  pickable={pickable}
                  allPicked={allPicked}
                  filtered={filtered}
                  active={active}
                  openItem={openItem}
                  transcribeSelected={transcribeSelected}
                  summarizeSelected={summarizeSelected}
                  cardTheme={cardTheme}
                  setCardTheme={setCardTheme}
                  ready={ready}
                  analysisConfigured={analysisConfigured}
                  hasBusy={hasBusy}
                  posting={posting}
                />
                <Inspector
                  item={active}
                  cards={activeCards}
                  tab={detailTab}
                  setTab={setDetailTab}
                  onBack={() => setMobileDetail(false)}
                  onGenerateCard={(id, s, customTheme) => submit('summarize', s, [id], customTheme || cardTheme)}
                  cardTheme={cardTheme}
                  setCardTheme={setCardTheme}
                  analysisConfigured={analysisConfigured}
                  hasBusy={hasBusy}
                  posting={posting}
                />
              </div>
            )}

            {view === 'jobs' && (
              <JobsView jobs={jobs} onCancelJob={handleCancelJob} />
            )}

            {view === 'cards' && (
              <CardsView
                cards={cards}
                onExportZip={handleExportZip}
                exportingZip={exportingZip}
              />
            )}

            {view === 'settings' && (
              <SettingsView
                data={data}
                ready={ready}
                analysisConfigured={analysisConfigured}
                settingsForm={settingsForm}
                setSettingsForm={setSettingsForm}
                handleProviderChange={handleProviderChange}
                handleSaveSettings={handleSaveSettings}
                handleTestLlm={handleTestLlm}
                savingSettings={savingSettings}
                testingLlm={testingLlm}
                testResult={testResult}
                hasBusy={hasBusy}
                posting={posting}
                submit={submit}
                transForm={transForm}
                setTransForm={setTransForm}
                handleSaveTransSettings={handleSaveTransSettings}
                savingTrans={savingTrans}
              />
            )}
          </>
        )}
      </div>

      <TaskDock currentJob={currentJob} onCancelJob={handleCancelJob} />

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImport={handleImportUrl}
        importing={importing}
      />
    </div>
  );
}
