import { create } from 'zustand';
import { fetchOpenRouterModels } from './services/openrouter';
import { sampleLogs } from './data/mockData';

const AGENTS = [
  { id: 'classifier', label: 'Classifier', time: 0 },
  { id: 'severity', label: 'Severity', time: 0 },
  { id: 'rootCause', label: 'Root Cause', time: 0 },
  { id: 'remediation', label: 'Remediation', time: 0 },
  { id: 'runbook', label: 'Runbook', time: 0 },
  { id: 'jira', label: 'JIRA', time: 0 },
  { id: 'alerts', label: 'Alerts', time: 0 },
];

const simulateAgentTime = () => 800 + Math.random() * 1800;

export const useStore = create((set, get) => ({
  // Connections Status
  connections: [
    { name: 'OpenRouter', status: 'red' },
    { name: 'LangSmith', status: 'red' },
    { name: 'JIRA', status: 'red' },
  ],
  fetchConnections: async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/health`);
      const data = await response.json();
      if (data.connections) {
        set({ connections: data.connections });
      }
    } catch (e) {
      console.error("Failed to fetch connection status", e);
    }
  },

  // Auth / API Keys
  byokProvider: 'openrouter',
  liveLogs: [],
  addLiveLog: (log) => set((state) => ({ 
    liveLogs: [log, ...state.liveLogs].slice(0, 100) 
  })),
  clearLiveLogs: () => set({ liveLogs: [] }),

  byokKeys: {
    openrouter: localStorage.getItem('openrouter_api_key') || '',
    openai: localStorage.getItem('openai_api_key') || '',
    anthropic: localStorage.getItem('anthropic_api_key') || '',
    google: localStorage.getItem('google_api_key') || '',
    ollama: localStorage.getItem('ollama_url') || 'http://localhost:11434',
    nvidia: 'https://integrate.api.nvidia.com/v1',
  },
  
  byokStatus: 'idle',
  
  setByokProvider: (provider) => {
    set({ 
      byokProvider: provider, 
      models: [], 
      byokStatus: 'checking',
      selectedProvider: provider === 'ollama' ? 'ollama' : (provider === 'nvidia' ? 'nvidia' : (provider === 'openrouter' ? 'openai' : provider))
    });
    get().fetchModels();
    get().checkByokConnection();
  },

  
  setByokKey: (provider, key) => {
    localStorage.setItem(`${provider}_api_key`, key);
    set((state) => ({
      byokKeys: { ...state.byokKeys, [provider]: key },
      byokStatus: 'checking'
    }));
    // Throttle checks
    if (get().byokProvider === provider) {
      get().fetchModels();
      get().checkByokConnection();
    }
  },

  checkByokConnection: async () => {
    const state = get();
    const provider = state.byokProvider;
    const key = state.byokKeys[provider];
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
      if (provider === 'ollama') {
        const host = state.byokKeys.ollama || 'http://localhost:11434';
        const resp = await fetch(`${apiUrl}/models/ollama?base_url=${encodeURIComponent(host)}`);
        const data = await resp.json();
        set({ byokStatus: data.models?.length >= 0 ? 'online' : 'offline' });
      } else if (provider === 'openrouter') {
        set({ byokStatus: localStorage.getItem('openrouter_api_key') ? 'online' : 'idle' });
      } else if (provider === 'nvidia') {
        set({ byokStatus: state.byokKeys.nvidia && localStorage.getItem('nvidia_api_key') ? 'online' : 'idle' });
      } else {
        set({ byokStatus: key ? 'online' : 'idle' });
      }

    } catch (e) {
      set({ byokStatus: 'offline' });
    }
  },


  // Legacy compatibility (keep userApiKey as an alias for openrouter key)
  userApiKey: localStorage.getItem('openrouter_api_key') || '',
  setUserApiKey: (key) => get().setByokKey('openrouter', key),


  // Models
  models: [],
  isLoadingModels: false,
  selectedProvider: 'openai',
  setSelectedProvider: (provider) => set({ selectedProvider: provider }),
  fetchModels: async () => {
    const state = get();
    set({ isLoadingModels: true });
    
    let models = [];
    try {
      if (state.byokProvider === 'openrouter') {
        const key = state.byokKeys.openrouter;
        models = await fetchOpenRouterModels(key);
      } else if (state.byokProvider === 'ollama') {
        const host = state.byokKeys.ollama || 'http://localhost:11434';
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        try {
          // Use our backend proxy to avoid CORS issues
          const response = await fetch(`${apiUrl}/models/ollama?base_url=${encodeURIComponent(host)}`);
          const data = await response.json();
          if (data.models) {
            models = data.models.map(m => {
              const modelName = m.name || m;
              return {
                id: modelName,
                name: modelName,
                provider: 'ollama',
                category: (
                  modelName.includes('70b') || 
                  modelName.includes('34b') || 
                  modelName.includes('r1') || 
                  modelName.includes('vision') ||
                  modelName.includes('q')
                ) ? 'reasoning' : 'fast'
              };
            });
          }

        } catch (e) {
          console.warn("Ollama proxy failed", e);
        }
      } else if (provider === 'nvidia') {
        const url = state.byokKeys.nvidia;
        const key = localStorage.getItem('nvidia_api_key');
        if (key) {
          try {
            const response = await fetch(`${url}/models`, {
              headers: { 'Authorization': `Bearer ${key}` }
            });
            const data = await response.json();
            if (data.data) {
              models = data.data.map(m => ({
                id: m.id,
                name: m.id,
                provider: 'nvidia',
                category: (m.id.includes('70b') || m.id.includes('large')) ? 'reasoning' : 'fast'
              }));
            }
          } catch (e) {
            console.warn("Nvidia fetch failed", e);
          }
        }
      } else {

        // Direct providers fallback to basic lists or future direct API implementation
        models = [];
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    }
    
    set({ models, isLoadingModels: false });
  },

  // Navigation
  activePage: 'home',
  setActivePage: (page) => set({ activePage: page }),

  // Pipeline
  pipelineStatus: 'idle', // idle | running | completed
  agents: AGENTS.map((a) => ({ ...a, status: 'pending' })),
  currentAgentIndex: -1,
  pipelineStartTime: 0,
  analysisResult: null,

  // Input
  activeTab: 'sample',
  setActiveTab: (tab) => set({ activeTab: tab }),
  selectedSample: null,
  setSelectedSample: (id) => set({ selectedSample: id }),
  logContent: '',
  setLogContent: (content) => set({ logContent: content }),

  // Tuning Parameters
  tuning: {
    fast_model: "openai/gpt-4o-mini",
    reasoning_model: "openai/gpt-4o",
    generation_model: "openai/gpt-4o-mini",
    fast_temp: 0.05,
    reasoning_temp: 0.15,
    generation_temp: 0.25,
    fast_max_tokens: 600,
    reasoning_max_tokens: 1500,
    generation_max_tokens: 1500,
    rag_top_k: 4,
    rag_similarity_threshold: 0.28,
    rag_chunk_size: 768,
    kb_fallback: true,
    max_log_chars: 5000,
    truncation_strategy: "Tail (last N chars)",
    strip_timestamps: false,
    deduplicate_lines: true,
    p1p2_full_pipeline: true,
    p1_threshold: 3,
    notify_on_p3: false,
  },
  
  updateTuning: (updates) => set((state) => ({
    tuning: { ...state.tuning, ...updates }
  })),

  applyPreset: (preset) => set({ tuning: preset }),

  // Legacy RAG (for compatibility with current UI if needed, but we'll transition)
  temperature: 0.3,
  setTemperature: (v) => set({ temperature: v }),
  topP: 0.85,
  setTopP: (v) => set({ topP: v }),
  retrievalK: 5,
  setRetrievalK: (v) => set({ retrievalK: v }),

  startPipeline: async () => {
    const state = get();
    if (state.pipelineStatus === 'running') return;

    let raw_logs = '';
    if (state.activeTab === 'log') {
      raw_logs = state.logContent;
    } else if (state.activeTab === 'sample' && state.selectedSample) {
      const sample = sampleLogs.find(s => s.id === state.selectedSample);
      if (sample) {
        raw_logs = `${sample.title}\n${sample.description}`;
      }
    }

    if (!raw_logs || !raw_logs.trim()) {
      alert("Please provide log content to analyze.");
      return;
    }

    const agents = AGENTS.map((a) => ({ ...a, status: 'pending', time: 0 }));
    set({
      pipelineStatus: 'running',
      agents,
      currentAgentIndex: -1,
      pipelineStartTime: Date.now(),
      analysisResult: null,
      selectedSample: null,
    });

    set((s) => ({
      agents: s.agents.map(a => ({ ...a, status: 'processing', time: 0 }))
    }));

    try {
      const response = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_logs,
          fast_model: state.tuning.fast_model,
          smart_model: state.tuning.reasoning_model,
          jira_mock: false,
          notif_mock: false,
          source: state.activeTab === 'log' ? 'custom' : 'sample',
          provider: state.byokProvider,
          api_key: state.byokKeys[state.byokProvider],
          base_url: state.byokProvider === 'ollama' ? state.byokKeys.ollama : undefined
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const nodeMap = {
        'classifier': 'classifier',
        'severity': 'severity',
        'root_cause': 'rootCause',
        'remediation': 'remediation',
        'cookbook': 'runbook',
        'jira': 'jira',
        'notification': 'alerts'
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              set({ pipelineStatus: 'completed' });
              continue;
            }

            try {
              const eventData = JSON.parse(dataStr);
              // LangGraph update is { [node_name]: state_values }
              const nodeName = Object.keys(eventData)[0];
              const agentId = nodeMap[nodeName];

              if (agentId) {
                set((s) => ({
                  agents: s.agents.map(a => 
                    a.id === agentId 
                      ? { ...a, status: 'done', time: simulateAgentTime() } 
                      : a
                  ),
                  // Update analysis results incrementally
                  analysisResult: {
                    ...s.analysisResult,
                    ...eventData[nodeName]
                  }
                }));
              }
            } catch (e) {
              console.error("Error parsing stream chunk:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Streaming Error:", error);
      set({ pipelineStatus: 'idle' });
      alert("Failed to connect to backend API: " + error.message);
    }
  },

  resetPipeline: () => {
    set({
      pipelineStatus: 'idle',
      agents: AGENTS.map((a) => ({ ...a, status: 'pending', time: 0 })),
      currentAgentIndex: -1,
      pipelineStartTime: 0,
      analysisResult: null,
    });
  },
}));
