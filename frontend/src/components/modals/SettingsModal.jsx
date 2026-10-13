import React, { useState, useEffect } from 'react';
import { X, Sliders, Brain, Trash2, Plus, Check } from 'lucide-react';
import { api } from '../../services/api';
import { useChat } from '../../contexts/ChatContext';

export function SettingsModal({ isOpen, onClose, theme }) {
  const isLight = theme === 'lavender-glow';
  const { availableModels } = useChat();
  const [activeTab, setActiveTab] = useState('general');
  const [defaultModel, setDefaultModel] = useState('gpt-4o-mini');
  const [temperature, setTemperature] = useState(0.7);
  const [systemInstructions, setSystemInstructions] = useState('');
  const [memories, setMemories] = useState([]);
  const [newMemory, setNewMemory] = useState('');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const fetchSettings = async () => {
      try {
        const s = await api.getSettings();
        if (s) {
          setDefaultModel(s.default_model);
          setTemperature(s.temperature);
          setSystemInstructions(s.system_instructions || '');
        }
        const m = await api.getMemories();
        setMemories(m);
      } catch (err) {
        console.warn('Failed to load settings:', err);
      }
    };
    fetchSettings();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSaveSettings = async () => {
    setLoading(true);
    try {
      await api.updateSettings({
        default_model: defaultModel,
        temperature,
        system_instructions: systemInstructions,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newMemory.trim()) return;
    try {
      const added = await api.addMemory(newMemory.trim());
      setMemories((prev) => [added, ...prev]);
      setNewMemory('');
    } catch (err) {
      console.error('Failed to save memory:', err);
    }
  };

  const handleDeleteMemory = async (id) => {
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm ${
      isLight ? 'bg-slate-900/30' : 'bg-black/70'
    }`}>
      <div className={`relative w-full max-w-xl rounded-2xl border shadow-2xl p-4 sm:p-6 flex flex-col max-h-[90dvh] transition-colors ${
        isLight
          ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
          : 'bg-slate-900 border-slate-800 text-slate-100 shadow-2xl'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between pb-4 border-b ${
          isLight ? 'border-purple-100' : 'border-slate-800'
        }`}>
          <div className="flex items-center gap-2">
            <Sliders size={18} className="text-purple-500" />
            <h2 className={`text-base font-bold ${
              isLight ? 'text-slate-900' : 'text-white'
            }`}>
              System Settings & Memory
            </h2>
          </div>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors ${
              isLight
                ? 'text-slate-400 hover:text-slate-900 hover:bg-purple-50'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab navigation */}
        <div className={`flex gap-4 border-b mt-3 text-xs font-semibold ${
          isLight ? 'border-purple-100' : 'border-slate-800'
        }`}>
          <button
            onClick={() => setActiveTab('general')}
            className={`pb-2.5 px-1 border-b-2 transition-colors ${
              activeTab === 'general'
                ? isLight
                  ? 'border-purple-600 text-purple-700'
                  : 'border-brand-500 text-brand-400'
                : isLight
                ? 'border-transparent text-slate-500 hover:text-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Model & Parameters
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`pb-2.5 px-1 border-b-2 transition-colors ${
              activeTab === 'memory'
                ? isLight
                  ? 'border-purple-600 text-purple-700'
                  : 'border-brand-500 text-brand-400'
                : isLight
                ? 'border-transparent text-slate-500 hover:text-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            AI Memory ({memories.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto py-4">
          {activeTab === 'general' ? (
            <div className="space-y-4 text-xs">
              {/* Default Model */}
              <div>
                <label className={`block font-medium mb-1.5 ${
                  isLight ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Default AI Model
                </label>
                <select
                  value={defaultModel}
                  onChange={(e) => setDefaultModel(e.target.value)}
                  className={`w-full rounded-xl p-2.5 text-xs focus:outline-none border ${
                    isLight
                      ? 'bg-purple-50/60 border-purple-200 text-slate-900 focus:bg-white focus:border-purple-400'
                      : 'bg-slate-950 border-slate-800 text-slate-200 focus:border-brand-500'
                  }`}
                >
                  {availableModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.provider})
                    </option>
                  ))}
                </select>
                <p className={`mt-1 text-[11px] ${
                  isLight ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  Select which model handles new conversations by default.
                </p>
              </div>

              {/* Temperature */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className={`font-medium ${
                    isLight ? 'text-slate-700' : 'text-slate-300'
                  }`}>
                    Creativity / Temperature:{' '}
                    <span className="text-purple-600 font-mono font-bold">{temperature}</span>
                  </label>
                  <span className={`text-[10px] ${
                    isLight ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {temperature < 0.4 ? 'Precise & Deterministic' : temperature > 0.8 ? 'Creative & Exploratory' : 'Balanced'}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-purple-600 cursor-pointer"
                />
              </div>

              {/* Custom Instructions */}
              <div>
                <label className={`block font-medium mb-1.5 ${
                  isLight ? 'text-slate-700' : 'text-slate-300'
                }`}>
                  Personal System Instructions
                </label>
                <textarea
                  rows={4}
                  value={systemInstructions}
                  onChange={(e) => setSystemInstructions(e.target.value)}
                  placeholder="e.g. Always respond with concise code snippets. Avoid unnecessary pleasantries. Prefer modern TypeScript or Python."
                  className={`w-full rounded-xl p-3 text-xs focus:outline-none border ${
                    isLight
                      ? 'bg-purple-50/60 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-400'
                      : 'bg-slate-950 border-slate-800 text-slate-200 placeholder-slate-400 focus:border-brand-500'
                  }`}
                />
                <p className={`mt-1 text-[11px] ${
                  isLight ? 'text-slate-500' : 'text-slate-400'
                }`}>
                  These directives will be injected into every conversation session.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className={`flex items-center gap-2 p-3 rounded-xl border text-xs ${
                isLight
                  ? 'bg-purple-50 border-purple-200/80 text-purple-950'
                  : 'bg-slate-850/80 border-slate-800 text-slate-300'
              }`}>
                <Brain size={18} className="text-purple-500 flex-shrink-0" />
                <span>
                  Pluto AI remembers facts, style rules, and preferences you specify here to personalize future replies.
                </span>
              </div>

              {/* Add Memory Input */}
              <form onSubmit={handleAddMemory} className="flex gap-2">
                <input
                  type="text"
                  value={newMemory}
                  onChange={(e) => setNewMemory(e.target.value)}
                  placeholder="Remember that: I work on macOS and write full-stack apps..."
                  className={`flex-1 rounded-xl px-3 py-2 text-xs focus:outline-none border ${
                    isLight
                      ? 'bg-purple-50/60 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-400'
                      : 'bg-slate-950 border-slate-800 text-slate-200 placeholder-slate-400 focus:border-brand-500'
                  }`}
                />
                <button
                  type="submit"
                  className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1 shadow-sm"
                >
                  <Plus size={14} />
                  <span>Add</span>
                </button>
              </form>

              {/* Memories List */}
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {memories.length === 0 ? (
                  <p className={`text-xs text-center py-6 ${
                    isLight ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    No memories saved yet. Add preferences above.
                  </p>
                ) : (
                  memories.map((m) => (
                    <div
                      key={m.id}
                      className={`flex items-start justify-between p-3 rounded-xl border text-xs ${
                        isLight
                          ? 'bg-purple-50/50 border-purple-200 text-slate-800'
                          : 'bg-slate-950 border-slate-800 text-slate-200'
                      }`}
                    >
                      <span className="flex-1 mr-2 leading-relaxed">{m.content}</span>
                      <button
                        onClick={() => handleDeleteMemory(m.id)}
                        className={`p-1 rounded transition-colors ${
                          isLight
                            ? 'text-slate-400 hover:text-rose-600'
                            : 'text-slate-400 hover:text-rose-400'
                        }`}
                        title="Delete memory"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {activeTab === 'general' && (
          <div className={`pt-3 border-t flex justify-end gap-2 ${
            isLight ? 'border-purple-100' : 'border-slate-800'
          }`}>
            <button
              onClick={onClose}
              className={`px-4 py-2 rounded-xl text-xs ${
                isLight ? 'text-slate-600 hover:text-slate-900' : 'text-slate-400 hover:text-white'
              }`}
            >
              Cancel
            </button>
            <button
              onClick={handleSaveSettings}
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-purple-600/30 transition-all"
            >
              {savedSuccess ? (
                <>
                  <Check size={14} className="text-emerald-300" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>Save Settings</span>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
