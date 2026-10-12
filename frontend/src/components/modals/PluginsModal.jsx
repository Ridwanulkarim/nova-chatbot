import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Search,
  Plus,
  Check,
  ChevronRight,
  Sparkles,
  ExternalLink,
  Shield,
  Layers,
  Zap,
  Globe,
  Sliders,
  Code,
  Compass,
} from 'lucide-react';
import { api } from '../../services/api';

// Complete dataset based on the ChatGPT Plugins & Skills directory screenshots
const PLUGINS_DATA = [
  // Popular
  { id: 'gmail', name: 'Gmail', desc: 'Read and manage Gmail', category: 'Popular', iconBg: 'bg-red-500/20 text-red-400', iconText: 'M', type: 'Personal' },
  { id: 'health', name: 'Health', desc: 'Explore your health data in Pluto AI', category: 'Popular', iconBg: 'bg-rose-500/20 text-rose-400', iconText: '♥', type: 'Personal' },
  { id: 'google_drive', name: 'Google Drive', desc: 'Drive, Docs, Sheets or Slides', category: 'Popular', iconBg: 'bg-amber-500/20 text-amber-400', iconText: '▲', type: 'Personal' },
  { id: 'github', name: 'GitHub', desc: 'Triage PRs, issues, CI, and publish flows', category: 'Popular', iconBg: 'bg-slate-700 text-white', iconText: 'GH', type: 'Public' },
  { id: 'supabase', name: 'Supabase', desc: 'Manage and query databases', category: 'Popular', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: '⚡', type: 'Public' },
  { id: 'outlook_email', name: 'Outlook Email', desc: 'Triage Outlook inboxes', category: 'Popular', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'O', type: 'Personal' },

  // New & Noteworthy
  { id: 'adobe', name: 'Adobe', desc: 'Design, combine, and edit', category: 'New & Noteworthy', iconBg: 'bg-red-600/20 text-red-500', iconText: 'A', type: 'Public' },
  { id: 'tldraw', name: 'tldraw', desc: 'Draw and diagram with agents', category: 'New & Noteworthy', iconBg: 'bg-slate-800 text-slate-200', iconText: '✎', type: 'Public' },
  { id: 'canva', name: 'Canva', desc: 'Create, review, edit designs', category: 'New & Noteworthy', iconBg: 'bg-cyan-500/20 text-cyan-400', iconText: 'C', type: 'Public' },
  { id: 'figma', name: 'Figma', desc: 'Create designs, ship to code', category: 'New & Noteworthy', iconBg: 'bg-purple-500/20 text-purple-400', iconText: 'F', type: 'Public' },
  { id: 'shopify', name: 'Shopify', desc: 'Create and manage your store', category: 'New & Noteworthy', iconBg: 'bg-lime-500/20 text-lime-400', iconText: 'S', type: 'Public' },
  { id: 'magicpath', name: 'MagicPath', desc: 'Design directly in Pluto AI', category: 'New & Noteworthy', iconBg: 'bg-emerald-500/20 text-emerald-300', iconText: '✦', type: 'Public' },

  // Small Business
  { id: 'dropbox', name: 'Dropbox', desc: 'Find, create, and take action', category: 'Small Business', iconBg: 'bg-blue-600/20 text-blue-400', iconText: '❖', type: 'Personal' },
  { id: 'hubspot', name: 'HubSpot', desc: 'Insights to action in HubSpot', category: 'Small Business', iconBg: 'bg-orange-500/20 text-orange-400', iconText: 'H', type: 'Public' },
  { id: 'stripe', name: 'Stripe', desc: 'Accept payments. Grow revenue.', category: 'Small Business', iconBg: 'bg-indigo-500/20 text-indigo-400', iconText: 'S', type: 'Public' },
  { id: 'gusto', name: 'Gusto', desc: 'People and payroll, made easy', category: 'Small Business', iconBg: 'bg-rose-500/20 text-rose-400', iconText: 'G', type: 'Public' },

  // Productivity
  { id: 'notion', name: 'Notion', desc: 'Create docs, tasks, databases', category: 'Productivity', iconBg: 'bg-slate-800 text-slate-100', iconText: 'N', type: 'Personal' },
  { id: 'google_calendar', name: 'Google Calendar', desc: 'Manage Google Calendar events', category: 'Productivity', iconBg: 'bg-blue-500/20 text-blue-400', iconText: '31', type: 'Personal' },
  { id: 'outlook_calendar', name: 'Outlook Calendar', desc: 'Manage Outlook schedules', category: 'Productivity', iconBg: 'bg-sky-500/20 text-sky-400', iconText: '📅', type: 'Personal' },
  { id: 'todoist', name: 'Todoist: To Do List & Calendar', desc: 'Planner & Reminders', category: 'Productivity', iconBg: 'bg-red-500/20 text-red-400', iconText: '✓', type: 'Personal' },
  { id: 'sharepoint', name: 'SharePoint', desc: 'Summarize SharePoint content', category: 'Productivity', iconBg: 'bg-teal-500/20 text-teal-400', iconText: 'S', type: 'Public' },

  // Communication
  { id: 'slack', name: 'Slack', desc: 'Read and manage Slack', category: 'Communication', iconBg: 'bg-emerald-600/20 text-emerald-400', iconText: '#', type: 'Personal' },
  { id: 'teams', name: 'Teams', desc: 'Summarize Teams and follow up', category: 'Communication', iconBg: 'bg-indigo-600/20 text-indigo-300', iconText: 'T', type: 'Personal' },
  { id: 'hostinger_mail', name: 'Hostinger Mail', desc: 'Use Hostinger Mail', category: 'Communication', iconBg: 'bg-purple-600/20 text-purple-400', iconText: 'H', type: 'Personal' },
  { id: 'zoom', name: 'Zoom', desc: 'Insights from Zoom', category: 'Communication', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'Z', type: 'Personal' },
  { id: 'mailopoly', name: 'Mailopoly Inbox', desc: 'Search, send emails & messages', category: 'Communication', iconBg: 'bg-violet-500/20 text-violet-400', iconText: '✉', type: 'Personal' },
  { id: 'superhuman', name: 'Superhuman Mail', desc: 'Best email+calendar assistant', category: 'Communication', iconBg: 'bg-pink-500/20 text-pink-400', iconText: '⚡', type: 'Personal' },

  // Creativity
  { id: 'product_design', name: 'Product Design', desc: 'Explore and prototype ideas', category: 'Creativity', iconBg: 'bg-fuchsia-500/20 text-fuchsia-400', iconText: '❖', type: 'Public' },
  { id: 'higgsfield', name: 'Higgsfield', desc: 'Every image and video model', category: 'Creativity', iconBg: 'bg-yellow-500/20 text-yellow-400', iconText: 'H', type: 'Public' },
  { id: 'runway', name: 'Runway', desc: 'Generate with every AI model', category: 'Creativity', iconBg: 'bg-slate-800 text-slate-200', iconText: 'R', type: 'Public' },

  // Developer Tools
  { id: 'vercel', name: 'Vercel', desc: 'Build and deploy apps', category: 'Developer Tools', iconBg: 'bg-slate-800 text-white', iconText: '▲', type: 'Public' },
  { id: 'lovable', name: 'Lovable', desc: 'Build full-stack apps by chat', category: 'Developer Tools', iconBg: 'bg-rose-500/20 text-rose-400', iconText: 'L', type: 'Public' },
  { id: 'remote_desktop', name: 'Remote Desktop Commander', desc: 'Build and automate, anywhere', category: 'Developer Tools', iconBg: 'bg-slate-800 text-sky-400', iconText: '⌨', type: 'Public' },
  { id: 'base44', name: 'Base44', desc: 'Build Apps & Websites with AI', category: 'Developer Tools', iconBg: 'bg-amber-600/20 text-amber-400', iconText: 'B', type: 'Public' },
  { id: 'exa', name: 'Exa', desc: 'Web search for AI agents', category: 'Developer Tools', iconBg: 'bg-blue-600/20 text-blue-400', iconText: 'E', type: 'Public' },
  { id: 'replit', name: 'Replit', desc: 'Turn your ideas into real apps', category: 'Developer Tools', iconBg: 'bg-orange-500/20 text-orange-400', iconText: 'R', type: 'Public' },

  // Healthcare
  { id: 'fitness_ai', name: 'Fitness AI Connector', desc: 'AI coach for your Garmin data', category: 'Healthcare', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: '🏃', type: 'Personal' },
  { id: 'coros', name: 'COROS', desc: 'Training and health insights', category: 'Healthcare', iconBg: 'bg-slate-800 text-slate-200', iconText: 'C', type: 'Personal' },
  { id: 'tredict', name: 'Tredict', desc: 'Analyze workouts, create plans', category: 'Healthcare', iconBg: 'bg-teal-500/20 text-teal-400', iconText: 'T', type: 'Personal' },
  { id: 'calorie_tracker', name: 'Calorie Tracker', desc: 'Track your food and calories', category: 'Healthcare', iconBg: 'bg-amber-500/20 text-amber-400', iconText: '🥗', type: 'Personal' },
  { id: 'freddy', name: 'freddy', desc: 'Ask about your health data', category: 'Healthcare', iconBg: 'bg-orange-500/20 text-orange-400', iconText: 'F', type: 'Personal' },
  { id: 'caliber', name: 'Caliber', desc: 'Analyze your fitness data', category: 'Healthcare', iconBg: 'bg-red-500/20 text-red-400', iconText: 'C', type: 'Personal' },

  // Finance
  { id: 'ibkr', name: 'Interactive Brokers (IBKR)', desc: 'Analyze global markets', category: 'Finance', iconBg: 'bg-red-600/20 text-red-500', iconText: 'IB', type: 'Personal' },
  { id: 'public_equity', name: 'Public Equity Investing', desc: 'Public equity research', category: 'Finance', iconBg: 'bg-emerald-600/20 text-emerald-400', iconText: '📈', type: 'Public' },
  { id: 'binance', name: 'Binance', desc: 'Explore Binance market data', category: 'Finance', iconBg: 'bg-yellow-500/20 text-yellow-400', iconText: 'B', type: 'Public' },
  { id: 'longbridge', name: 'Longbridge', desc: 'Stock quotes, financial data', category: 'Finance', iconBg: 'bg-cyan-500/20 text-cyan-400', iconText: 'L', type: 'Public' },
  { id: 'iol', name: 'IOL invertironline', desc: 'Trade Argentine investments', category: 'Finance', iconBg: 'bg-slate-800 text-indigo-400', iconText: 'IO', type: 'Public' },

  // Travel
  { id: 'booking', name: 'Booking.com', desc: 'Find all best stays and more.', category: 'Travel', iconBg: 'bg-blue-600/20 text-blue-400', iconText: 'B.', type: 'Public' },
  { id: 'skyscanner', name: 'Skyscanner', desc: 'Find cheap flights', category: 'Travel', iconBg: 'bg-sky-500/20 text-sky-400', iconText: '✈', type: 'Public' },
  { id: 'trip', name: 'Trip.com', desc: 'All-in-one Travel Companion', category: 'Travel', iconBg: 'bg-blue-500/20 text-blue-300', iconText: 'T', type: 'Public' },
  { id: 'wikiloc', name: 'Wikiloc', desc: 'Your perfect trail. Just ask.', category: 'Travel', iconBg: 'bg-lime-500/20 text-lime-400', iconText: 'W', type: 'Public' },
  { id: 'flight_network', name: 'Flight Network', desc: 'Search and book flights', category: 'Travel', iconBg: 'bg-indigo-500/20 text-indigo-400', iconText: '✈', type: 'Public' },
  { id: 'tripadvisor', name: 'Tripadvisor', desc: 'Book top-rated hotels', category: 'Travel', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: '🦉', type: 'Public' },

  // Entertainment
  { id: 'spotify', name: 'Spotify', desc: 'Music and podcasts for you', category: 'Entertainment', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: '♫', type: 'Personal' },
  { id: 'chessy', name: 'Chessy', desc: 'Play Chess Against Pluto AI', category: 'Entertainment', iconBg: 'bg-purple-500/20 text-purple-400', iconText: '♞', type: 'Public' },
  { id: 'destiny_astrology', name: 'Destiny AI Astrology', desc: 'Birth Charts & Horoscopes', category: 'Entertainment', iconBg: 'bg-indigo-500/20 text-indigo-400', iconText: '★', type: 'Public' },
  { id: 'smart_chess', name: 'Smart Chess:Train+Learn to win', desc: 'Play+improve: coach+strategy', category: 'Entertainment', iconBg: 'bg-amber-500/20 text-amber-400', iconText: '♚', type: 'Public' },
  { id: 'soundbreak', name: 'SoundBreak', desc: 'Create AI Music with Artists', category: 'Entertainment', iconBg: 'bg-slate-800 text-rose-400', iconText: '♬', type: 'Public' },
  { id: 'shazam', name: 'Shazam', desc: 'Identify songs instantly', category: 'Entertainment', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'S', type: 'Public' },

  // Education
  { id: 'consensus', name: 'Consensus', desc: 'Explore scientific research', category: 'Education', iconBg: 'bg-slate-800 text-slate-200', iconText: 'C', type: 'Public' },
  { id: 'zotero', name: 'Zotero', desc: 'Find papers and add citations from Zotero', category: 'Education', iconBg: 'bg-red-500/20 text-red-400', iconText: 'Z', type: 'Personal' },
  { id: 'scispace', name: 'SciSpace', desc: 'For science and research', category: 'Education', iconBg: 'bg-amber-500/20 text-amber-400', iconText: 'S', type: 'Public' },
  { id: 'sider_scholar', name: 'Sider Scholar', desc: 'Search 350M+ Paper. Save. Chat', category: 'Education', iconBg: 'bg-purple-500/20 text-purple-400', iconText: '🎓', type: 'Public' },
  { id: 'acumen', name: 'Acumen by Talarion', desc: 'Keep your AI up to date.', category: 'Education', iconBg: 'bg-slate-800 text-slate-100', iconText: 'T', type: 'Public' },
  { id: 'scite', name: 'Scite', desc: 'Search scientific literature', category: 'Education', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'S_', type: 'Public' },

  // Business & Operations
  { id: 'sales', name: 'Sales', desc: 'Practical workflows for sales', category: 'Business & Operations', iconBg: 'bg-orange-500/20 text-orange-400', iconText: 'S', type: 'Public' },
  { id: 'vidiq', name: 'vidIQ', desc: 'Grow on YouTube, IG & TikTok', category: 'Business & Operations', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'IQ', type: 'Public' },
  { id: 'wix', name: 'Wix', desc: 'Create your own website', category: 'Business & Operations', iconBg: 'bg-slate-800 text-slate-100', iconText: 'W', type: 'Public' },
  { id: 'apollo', name: 'Apollo.io', desc: 'Find buyers and close deals', category: 'Business & Operations', iconBg: 'bg-yellow-500/20 text-yellow-400', iconText: 'A', type: 'Public' },

  // Data & Analytics
  { id: 'data_analyzer', name: 'Data', desc: 'Answer questions with data', category: 'Data & Analytics', iconBg: 'bg-blue-500/20 text-blue-400', iconText: '📊', type: 'Public' },
  { id: 'posthog', name: 'PostHog', desc: 'Analyze your product data', category: 'Data & Analytics', iconBg: 'bg-slate-800 text-amber-400', iconText: '🦔', type: 'Public' },
  { id: 'blockscout', name: 'Blockscout Blockchain Data', desc: 'Find & analyze blockchain data', category: 'Data & Analytics', iconBg: 'bg-purple-500/20 text-purple-400', iconText: 'B', type: 'Public' },
  { id: 'helium10', name: 'Helium 10', desc: 'Access your Helium 10 data', category: 'Data & Analytics', iconBg: 'bg-blue-600/20 text-blue-400', iconText: 'H', type: 'Public' },
  { id: 'amplitude', name: 'Amplitude', desc: 'Analyze your product data', category: 'Data & Analytics', iconBg: 'bg-blue-500/20 text-blue-400', iconText: 'A', type: 'Public' },
  { id: 'mixpanel', name: 'Mixpanel', desc: 'Query and analyze Mixpanel', category: 'Data & Analytics', iconBg: 'bg-purple-600/20 text-purple-300', iconText: 'M', type: 'Public' },

  // Scientific Research
  { id: 'undermind', name: 'Undermind', desc: 'Find and read research papers', category: 'Scientific Research', iconBg: 'bg-blue-600/20 text-blue-400', iconText: 'µ', type: 'Public' },
  { id: 'life_sciences', name: 'Life Sciences Literature', desc: 'Find biomedical papers, preprints, and open-access...', category: 'Scientific Research', iconBg: 'bg-sky-500/20 text-sky-400', iconText: '🔬', type: 'Public' },
  { id: 'ngs_workbench', name: 'NGS Analysis Workbench', desc: 'Analyze sequencing data', category: 'Scientific Research', iconBg: 'bg-cyan-500/20 text-cyan-400', iconText: '🧬', type: 'Public' },
  { id: 'boltz', name: 'Boltz', desc: 'Predict structures, screen molecules and proteins,...', category: 'Scientific Research', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: 'B', type: 'Public' },
  { id: 'tamarind_bio', name: 'Tamarind Bio', desc: 'Protein and molecular design', category: 'Scientific Research', iconBg: 'bg-teal-500/20 text-teal-400', iconText: 'T', type: 'Public' },
  { id: 'bio_aligner', name: 'Biological Sequence & Alignment Viewer', desc: 'Inspect, analyze, and compare biological...', category: 'Scientific Research', iconBg: 'bg-slate-800 text-purple-400', iconText: '▦', type: 'Public' },

  // Security
  { id: 'codex_security', name: 'Codex Security', desc: 'Security scanning for your codebase', category: 'Security', iconBg: 'bg-blue-500/20 text-blue-400', iconText: '🛡', type: 'Public' },
  { id: 'malwarebytes', name: 'Malwarebytes', desc: 'Verify links, domains, phones.', category: 'Security', iconBg: 'bg-blue-600/20 text-blue-300', iconText: 'M', type: 'Public' },
  { id: 'ajaxx', name: 'AJAXX Data Scrubber', desc: 'Remove exposed personal data', category: 'Security', iconBg: 'bg-teal-500/20 text-teal-400', iconText: 'AX', type: 'Public' },
  { id: 'privacyhawk', name: 'PrivacyHawk', desc: 'Protect your personal data', category: 'Security', iconBg: 'bg-red-500/20 text-red-400', iconText: '🦅', type: 'Public' },
  { id: 'soluvery', name: 'Soluvery', desc: 'Audit Google Drive Permissions', category: 'Security', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: 'S', type: 'Public' },
  { id: 'toolcheck', name: 'ToolCheck by M8ven', desc: 'Is this MCP safe to connect?', category: 'Security', iconBg: 'bg-amber-500/20 text-amber-400', iconText: '❖', type: 'Public' },

  // Other
  { id: 'tarot', name: 'Tarot', desc: 'Tarot Reading & Divination', category: 'Other', iconBg: 'bg-indigo-500/20 text-indigo-400', iconText: '✡', type: 'Public' },
  { id: 'linkedin', name: 'LinkedIn', desc: 'Find the right professional', category: 'Other', iconBg: 'bg-blue-600/20 text-blue-400', iconText: 'in', type: 'Personal' },
  { id: 'steer_astro', name: 'Steer Astro', desc: 'Your Personal AI Astrologer', category: 'Other', iconBg: 'bg-slate-800 text-amber-400', iconText: '☼', type: 'Public' },
  { id: 'etsy', name: 'Etsy', desc: 'Shop Home, Style & More', category: 'Other', iconBg: 'bg-orange-600/20 text-orange-400', iconText: 'E', type: 'Public' },
  { id: 'ask_tarot', name: 'Ask Tarot Cards', desc: 'Tarot card readings', category: 'Other', iconBg: 'bg-yellow-500/20 text-yellow-400', iconText: '🃏', type: 'Public' },
  { id: 'kleinanzeigen', name: 'Kleinanzeigen', desc: 'Echte Deals. Echte Menschen.', category: 'Other', iconBg: 'bg-lime-500/20 text-lime-400', iconText: 'K', type: 'Public' },
];

const SKILLS_DATA = [
  { id: 'code_interpreter', name: 'Code Interpreter & Sandbox', desc: 'Execute real Python code, compute stats, and generate files.', category: 'Core Skills', iconBg: 'bg-emerald-500/20 text-emerald-400', iconText: '</>' },
  { id: 'web_search_agent', name: 'Live Web Research', desc: 'Real-time multi-engine web search with citation grounding.', category: 'Core Skills', iconBg: 'bg-blue-500/20 text-blue-400', iconText: '🌐' },
  { id: 'image_gen_studio', name: 'AI Image & Art Studio', desc: 'Generate photorealistic and artistic images on demand.', category: 'Core Skills', iconBg: 'bg-purple-500/20 text-purple-400', iconText: '🎨' },
  { id: 'apple_vision_ocr', name: 'Apple Vision & OCR Engine', desc: 'Analyze screenshots, diagrams, and extract legible text.', category: 'Core Skills', iconBg: 'bg-sky-500/20 text-sky-400', iconText: '👁' },
  { id: 'voice_assistant_engine', name: 'Live Hands-Free Voice Mode', desc: 'Bidirectional speech synthesis and real-time voice conversations.', category: 'Core Skills', iconBg: 'bg-indigo-500/20 text-indigo-400', iconText: '🎙' },
  { id: 'rag_document_indexer', name: 'RAG Document Intelligence', desc: 'Chunk, embed, and query your uploaded PDFs, docs, and notes.', category: 'Core Skills', iconBg: 'bg-amber-500/20 text-amber-400', iconText: '📚' },
  { id: 'latex_math_solver', name: 'LaTeX & Math Reasoning', desc: 'Step-by-step calculus, linear algebra, and physics derivations.', category: 'Specialized Skills', iconBg: 'bg-rose-500/20 text-rose-400', iconText: '∑' },
  { id: 'database_architect', name: 'SQL & Database Architect', desc: 'Design schemas, optimize queries, and inspect relational models.', category: 'Specialized Skills', iconBg: 'bg-teal-500/20 text-teal-400', iconText: '🗄' },
  { id: 'browser_page_reader', name: 'Deep Web Page Reader', desc: 'Fetch, clean, and analyze arbitrary URLs and web documentation.', category: 'Specialized Skills', iconBg: 'bg-cyan-500/20 text-cyan-400', iconText: '📄' },
];

export function PluginsModal({ isOpen, onClose, theme }) {
  const isLight = theme === 'lavender-glow';
  const [activeTab, setActiveTab] = useState('plugins'); // 'plugins' | 'skills'
  const [search, setSearch] = useState('');
  const [installedFilter, setInstalledFilter] = useState('All'); // 'All' | 'Public' | 'Personal'
  const [installedIds, setInstalledIds] = useState(new Set(['github', 'supabase', 'notion']));

  // Load installed plugins on open
  useEffect(() => {
    if (isOpen) {
      api.getInstalledPlugins().then((res) => {
        if (res?.installed_plugin_ids) {
          setInstalledIds(new Set(res.installed_plugin_ids));
        }
      });
    }
  }, [isOpen]);

  const toggleInstall = async (id, e) => {
    e.stopPropagation();
    const isCurrentlyInstalled = installedIds.has(id);
    const action = isCurrentlyInstalled ? 'uninstall' : 'install';

    setInstalledIds((prev) => {
      const next = new Set(prev);
      if (isCurrentlyInstalled) next.delete(id);
      else next.add(id);
      return next;
    });

    try {
      await api.togglePlugin(id, action);
    } catch (err) {
      console.warn('Could not persist plugin toggle:', err);
    }
  };

  // Filtered dataset
  const activeDataset = activeTab === 'plugins' ? PLUGINS_DATA : SKILLS_DATA;

  const filteredItems = useMemo(() => {
    return activeDataset.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(search.toLowerCase()) ||
        item.desc.toLowerCase().includes(search.toLowerCase()) ||
        item.category.toLowerCase().includes(search.toLowerCase());
      return matchesSearch;
    });
  }, [activeDataset, search]);

  // Group by category
  const categories = useMemo(() => {
    const map = {};
    filteredItems.forEach((item) => {
      if (!map[item.category]) map[item.category] = [];
      map[item.category].push(item);
    });
    return map;
  }, [filteredItems]);

  // Installed items list
  const installedItems = useMemo(() => {
    return activeDataset.filter((item) => {
      if (!installedIds.has(item.id)) return false;
      if (installedFilter === 'All') return true;
      return item.type === installedFilter;
    });
  }, [activeDataset, installedIds, installedFilter]);

  if (!isOpen) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 backdrop-blur-md animate-in fade-in duration-200 ${
      isLight ? 'bg-slate-900/30' : 'bg-black/75'
    }`}>
      <div className={`w-full max-w-4xl h-[92vh] flex flex-col rounded-3xl border shadow-2xl overflow-hidden relative transition-colors ${
        isLight
          ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
          : theme === 'lavender-dark'
          ? 'bg-slate-900/95 backdrop-blur-2xl text-slate-100 border-purple-900/40 shadow-2xl shadow-purple-950/30'
          : 'bg-slate-900/95 backdrop-blur-2xl text-slate-100 border-slate-700/80 shadow-2xl'
      }`}>
        {/* Top Header with Segmented Pill & Close Button */}
        <div className={`pt-4 px-6 flex items-center justify-between border-b pb-3 flex-shrink-0 ${
          isLight ? 'border-purple-100 bg-white/70' : 'border-slate-800/80 bg-slate-900/80'
        }`}>
          <div className="w-8" /> {/* Spacer */}

          {/* Segmented Switch: Plugins | Skills */}
          <div className={`flex items-center p-1 rounded-full border ${
            isLight ? 'bg-purple-50 border-purple-200/70' : 'bg-slate-950/80 border-slate-800'
          }`}>
            <button
              onClick={() => setActiveTab('plugins')}
              className={`px-5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'plugins'
                  ? isLight
                    ? 'bg-white text-purple-950 shadow-sm'
                    : 'bg-slate-800 text-white shadow-xs border border-slate-700/60'
                  : isLight
                  ? 'text-slate-600 hover:text-slate-900'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Plugins
            </button>
            <button
              onClick={() => setActiveTab('skills')}
              className={`px-5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeTab === 'skills'
                  ? isLight
                    ? 'bg-white text-purple-950 shadow-sm'
                    : 'bg-slate-800 text-white shadow-xs border border-slate-700/60'
                  : isLight
                  ? 'text-slate-600 hover:text-slate-900'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Skills
            </button>
          </div>

          {/* Close X */}
          <button
            onClick={onClose}
            className={`p-2 rounded-full transition-colors ${
              isLight
                ? 'hover:bg-purple-100 text-slate-500 hover:text-slate-900'
                : 'hover:bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Main Area */}
        <div className="flex-1 overflow-y-auto px-6 sm:px-12 py-6 custom-scrollbar">
          {/* Main Title & Subtitle */}
          <div className="mb-6">
            <h1 className={`text-2xl sm:text-3xl font-bold tracking-tight mb-1.5 ${
              isLight ? 'text-slate-900' : 'text-slate-100'
            }`}>
              {activeTab === 'plugins' ? 'Plugins' : 'Skills'}
            </h1>
            <p className={`text-sm ${
              isLight ? 'text-slate-600' : 'text-slate-400'
            }`}>
              {activeTab === 'plugins'
                ? 'Connect plugins to let Pluto AI work across your tools'
                : 'Supercharge Pluto AI with specialized autonomous capabilities'}
            </p>
          </div>

          {/* Search Bar */}
          <div className="relative mb-8">
            <Search
              size={17}
              className={`absolute left-4 top-1/2 -translate-y-1/2 ${
                isLight ? 'text-purple-400' : 'text-slate-500'
              }`}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={
                activeTab === 'plugins' ? 'Search plugins' : 'Search skills'
              }
              className={`w-full rounded-full pl-11 pr-4 py-3 text-sm focus:outline-none transition-all shadow-inner border ${
                isLight
                  ? 'bg-purple-50/70 border-purple-200 text-slate-900 placeholder-slate-400 hover:border-purple-300 focus:border-purple-500 focus:bg-white'
                  : 'bg-slate-950/80 border-slate-800 hover:border-slate-700 focus:border-brand-500/80 text-slate-100 placeholder-slate-500'
              }`}
            />
          </div>

          {/* Installed Section */}
          {!search && installedItems.length > 0 && (
            <div className={`mb-10 pb-8 border-b ${
              isLight ? 'border-purple-100' : 'border-slate-800/80'
            }`}>
              <div className="flex items-center justify-between mb-3">
                <button className={`flex items-center gap-1.5 text-base font-semibold transition-colors ${
                  isLight ? 'text-slate-900 hover:text-purple-900' : 'text-slate-100 hover:text-white'
                }`}>
                  <span>Installed</span>
                  <ChevronRight size={16} className={isLight ? 'text-purple-400' : 'text-slate-500'} />
                </button>
              </div>

              {/* Public | Personal Filter Pills */}
              {activeTab === 'plugins' && (
                <div className="flex items-center gap-2 mb-4">
                  {['All', 'Public', 'Personal'].map((f) => (
                    <button
                      key={f}
                      onClick={() => setInstalledFilter(f)}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                        installedFilter === f
                          ? isLight
                            ? 'bg-purple-100 text-purple-900 border border-purple-300 font-semibold'
                            : 'bg-slate-800 text-slate-100 border border-slate-700 shadow-xs'
                          : isLight
                          ? 'bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200'
                          : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              )}

              {/* Installed Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {installedItems.map((item) => (
                  <div
                    key={`installed-${item.id}`}
                    className={`flex items-center justify-between p-3.5 rounded-2xl transition-all group border ${
                      isLight
                        ? 'bg-purple-50/60 border-purple-200/80 hover:border-purple-300 shadow-xs'
                        : 'bg-slate-850/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800 transition-colors shadow-sm'
                    }`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div
                        className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-base flex-shrink-0 ${item.iconBg}`}
                      >
                        {item.iconText}
                      </div>
                      <div className="truncate">
                        <div className={`font-semibold text-sm truncate flex items-center gap-1.5 ${
                          isLight ? 'text-slate-900' : 'text-slate-100'
                        }`}>
                          <span>{item.name}</span>
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        </div>
                        <div className={`text-xs truncate ${
                          isLight ? 'text-slate-600' : 'text-slate-400'
                        }`}>
                          {item.desc}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={(e) => toggleInstall(item.id, e)}
                      className={`p-2 rounded-full border transition-all flex-shrink-0 ml-3 ${
                        isLight
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300 hover:bg-rose-100 hover:text-rose-700 hover:border-rose-300'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20'
                      }`}
                      title="Click to disconnect"
                    >
                      <Check size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Categorized Sections */}
          <div className="space-y-10">
            {Object.entries(categories).map(([catTitle, items]) => (
              <div key={catTitle}>
                {/* Category Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className={`flex items-center gap-1.5 text-base font-semibold ${
                    isLight ? 'text-slate-900' : 'text-slate-100'
                  }`}>
                    <span>{catTitle}</span>
                    <ChevronRight size={16} className={isLight ? 'text-purple-400' : 'text-slate-500'} />
                  </div>
                </div>

                {/* Grid of Plugins in this Category */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {items.map((item) => {
                    const isInstalled = installedIds.has(item.id);

                    return (
                      <div
                        key={item.id}
                        className={`flex items-center justify-between p-3.5 rounded-2xl transition-all group cursor-pointer border ${
                          isLight
                            ? 'bg-white hover:bg-purple-50/60 border-purple-200/80 hover:border-purple-300 shadow-xs'
                            : 'bg-slate-900/80 hover:bg-slate-850 border-slate-800/80 hover:border-slate-700 transition-all shadow-sm'
                        }`}
                      >
                        {/* App Icon + Title + Description */}
                        <div className="flex items-center gap-3.5 min-w-0">
                          <div
                            className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-base flex-shrink-0 shadow-sm ${item.iconBg}`}
                          >
                            {item.iconText}
                          </div>
                          <div className="truncate pr-2">
                            <div className={`font-semibold text-sm truncate ${
                              isLight ? 'text-slate-900 group-hover:text-purple-950' : 'text-slate-100 group-hover:text-white'
                            }`}>
                              {item.name}
                            </div>
                            <div className={`text-xs truncate ${
                              isLight ? 'text-slate-600' : 'text-slate-400'
                            }`}>
                              {item.desc}
                            </div>
                          </div>
                        </div>

                        {/* Plus / Check Install Button */}
                        <button
                          onClick={(e) => toggleInstall(item.id, e)}
                          className={`p-2 rounded-full transition-all flex-shrink-0 ml-2 ${
                            isInstalled
                              ? isLight
                                ? 'bg-emerald-100 text-emerald-800 hover:bg-rose-100 hover:text-rose-700'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20'
                              : isLight
                              ? 'text-purple-700 hover:text-purple-950 bg-purple-50 hover:bg-purple-100 border border-purple-200/60'
                              : 'text-slate-400 hover:text-white hover:bg-slate-800 bg-slate-850/60 border border-slate-700/60'
                          }`}
                          title={isInstalled ? 'Installed (Click to remove)' : 'Install Plugin'}
                        >
                          {isInstalled ? <Check size={17} /> : <Plus size={18} />}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {filteredItems.length === 0 && (
              <div className={`text-center py-16 text-sm ${
                isLight ? 'text-slate-500' : 'text-slate-400'
              }`}>
                No matching plugins or skills found for &ldquo;{search}&rdquo;
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
