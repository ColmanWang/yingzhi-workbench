import React from 'react';
import { Link, Info } from 'lucide-react';

export default function SettingsView({
  data,
  ready,
  analysisConfigured,
  settingsForm,
  setSettingsForm,
  handleProviderChange,
  handleSaveSettings,
  handleTestLlm,
  savingSettings,
  testingLlm,
  testResult,
  hasBusy,
  posting,
  submit,
  transForm,
  setTransForm,
  handleSaveTransSettings,
  savingTrans,
}) {
  const currentEngine = transForm?.engine || 'local_whisper';
  const currentModel = transForm?.model || 'medium';
  const isSenseVoice = currentEngine === 'siliconflow';

  return (
    <section className="page-content settings-page">
      <div className="settings-section">
        <h2>语音转写引擎与模型</h2>
        <p>短视频语音转为逐字稿的计算引擎与识别模型规格。</p>
        <div className="setting-row" style={{ marginBottom: 12 }}>
          <div>
            <strong>
              {isSenseVoice
                ? '云端 SenseVoice'
                : `Whisper ${currentModel}`}
            </strong>
            <span>
              {isSenseVoice
                ? '阿里 FunAudioLLM 架构 · 针对短视频 BGM 及中文发音强化'
                : `本地语音模型 · CPU 转写 · ${currentModel === 'medium' ? 'medium 精准推荐' : 'small 轻量快速'}`}
            </span>
          </div>
          <span className={`status ${ready || isSenseVoice ? 'status-success' : 'status-failed'}`}>
            {ready || isSenseVoice ? '已就绪' : '需要配置'}
          </span>
        </div>

        <form className="settings-form" onSubmit={handleSaveTransSettings}>
          <div className="form-grid">
            <div className="form-group">
              <label>转写引擎与模型选择</label>
              <select
                value={`${currentEngine}:${currentModel}`}
                onChange={(e) => {
                  const [eng, mod] = e.target.value.split(':');
                  setTransForm?.({ engine: eng, model: mod });
                }}
              >
                <option value="local_whisper:medium">
                  本地 Whisper - medium 模型（推荐：中文断句准，错别字显著减少）
                </option>
                <option value="local_whisper:small">
                  本地 Whisper - small 模型（极轻量：占用低、启动最快）
                </option>
                <option value="siliconflow:FunAudioLLM/SenseVoiceSmall">
                  云端 SenseVoice - 极速高精（阿里 FunAudioLLM，抗 BGM 强，需在下方配置 SiliconFlow Key）
                </option>
              </select>
            </div>
          </div>

          <div className="form-hint" style={{ marginTop: 4, marginBottom: 12 }}>
            💡 已自动开启「中文普通话提示词」、「规范标点诱导」与「防 BGM 串扰死循环」专项优化。
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="button primary"
              disabled={savingTrans}
            >
              {savingTrans ? '保存中…' : '保存转写配置'}
            </button>
          </div>
        </form>

        {!ready && !isSenseVoice && (
          <p className="setting-warning" style={{ marginTop: 12 }}>
            {data.settings.transcription?.missing?.join('、') ||
              '请检查本地语音转写依赖（ffmpeg / faster-whisper）。'}
          </p>
        )}
      </div>

      <div className="settings-section">
        <h2>AI 总结与卡片生成</h2>
        <p>配置大语言模型（LLM），将逐字稿结构化提炼为知识卡片。</p>
        <div className="setting-row" style={{ marginBottom: 12 }}>
          <div>
            <strong>总结服务</strong>
            <span>
              {analysisConfigured
                ? `已配置 (${settingsForm.provider || '自定义'})`
                : '当前不会调用付费 API，也不会自动运行 Codex。'}
            </span>
          </div>
          <span
            className={`status ${
              analysisConfigured ? 'status-success' : 'status-pending'
            }`}
          >
            {analysisConfigured ? '已就绪' : '暂未接入'}
          </span>
        </div>

        <form className="settings-form" onSubmit={handleSaveSettings}>
          <div className="form-grid">
            <div className="form-group">
              <label>模型服务商</label>
              <select
                value={settingsForm.provider}
                onChange={handleProviderChange}
              >
                <option value="siliconflow">SiliconFlow (硅基流动)</option>
                <option value="ollama">Ollama (本地离线免费)</option>
                <option value="deepseek">DeepSeek 官方 API</option>
                <option value="custom">自定义 OpenAI 兼容接口</option>
              </select>
            </div>
            <div className="form-group">
              <label>模型名称 (Model)</label>
              <input
                value={settingsForm.model}
                onChange={(e) =>
                  setSettingsForm({ ...settingsForm, model: e.target.value })
                }
                placeholder="例如 Qwen/Qwen2.5-7B-Instruct 或 deepseek-chat"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>API 接口端点 (Chat Completions URL)</label>
            <input
              value={settingsForm.endpoint}
              onChange={(e) =>
                setSettingsForm({ ...settingsForm, endpoint: e.target.value })
              }
              placeholder="https://api.siliconflow.cn/v1/chat/completions"
              required
            />
            <span className="form-hint">
              兼容任何 OpenAI 规范的 /v1/chat/completions 接口。本地 Ollama
              通常为 http://localhost:11434/v1/chat/completions
            </span>
          </div>

          <div className="form-group">
            <label>API 密钥 (API Key)</label>
            <input
              type="password"
              value={settingsForm.api_key}
              onChange={(e) =>
                setSettingsForm({ ...settingsForm, api_key: e.target.value })
              }
              placeholder={
                data.settings?.analysis?.has_key
                  ? `已配置密钥 (${data.settings.analysis.masked_key})，如不修改请留空`
                  : '输入 API Key (本地 Ollama 可留空)'
              }
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="button primary"
              disabled={savingSettings || testingLlm}
            >
              {savingSettings ? '保存中…' : '保存设置'}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={savingSettings || testingLlm}
              onClick={handleTestLlm}
            >
              {testingLlm ? '测试中…' : '测试连接'}
            </button>
            {testResult && (
              <span
                style={{
                  fontSize: 12,
                  color: testResult.ok ? '#2f6c4d' : '#a85849',
                }}
              >
                {testResult.ok
                  ? '✓ 连接正常'
                  : `✕ 失败: ${testResult.error || '无法连通'}`}
              </span>
            )}
          </div>
        </form>
      </div>

      <div className="settings-section">
        <h2>抖音连接</h2>
        <p>在独立浏览器中登录，授权状态仅保存在本机。</p>
        <div className="setting-row">
          <div>
            <strong>专用浏览器</strong>
            <span>
              登录窗口成功后会自动关闭。能否读取列表，以任务结果为准。
            </span>
          </div>
          <button
            className="button secondary"
            disabled={hasBusy || posting}
            onClick={() => submit('login')}
          >
            <Link size={16} />连接抖音
          </button>
        </div>
      </div>

      <div className="privacy-note">
        <Info size={17} />
        <div>
          <strong>隐私与安全准则：</strong>
          工作台设计为仅限本机单机使用（127.0.0.1）。严禁通过端口映射、内网穿透或公网 IP 开放给外部网络，以防大模型 API Key 盗刷或个人收藏泄露。
        </div>
      </div>
    </section>
  );
}
