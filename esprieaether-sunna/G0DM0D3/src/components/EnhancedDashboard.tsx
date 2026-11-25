'use client'

/**
 * Enhanced Dashboard Components for G0DM0D3
 * Provides real-time WebSocket updates, model comparison visualizations,
 * keyboard shortcuts, accessibility, and mobile responsiveness.
 */

import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import { useStore } from '@/store'
import {
  Zap, Brain, Swords, Users, Crown, Droplets, Skull, SlidersHorizontal,
  TrendingUp, Activity, Gauge, BarChart2, PieChart, RefreshCw,
  Maximize2, Minimize2, Copy, Download, Upload, Search, Filter,
  ChevronLeft, ChevronRight, Menu, X, Settings, HelpCircle,
  Keyboard, Smartphone, Monitor, Wifi, WifiOff, Bell, BellOff
} from 'lucide-react'

// ── WebSocket Hook ────────────────────────────────────────────────────────

interface WSMessage {
  type: string
  data: any
  timestamp: string
}

export function useWebSocket(url: string, onMessage: (msg: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WS] Connected')
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          onMessage(msg)
        } catch (e) {
          console.error('[WS] Parse error:', e)
        }
      }

      ws.onclose = () => {
        console.log('[WS] Disconnected')
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          reconnectAttempts.current++
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('[WS] Error:', error)
      }
    } catch (e) {
      console.error('[WS] Connection failed:', e)
    }
  }, [url, onMessage])

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return { send, disconnect }
}

// ── Keyboard Shortcuts Hook ──────────────────────────────────────────────

interface Shortcut {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      for (const shortcut of shortcuts) {
        const match =
          e.key.toLowerCase() === shortcut.key.toLowerCase() &&
          !!e.ctrlKey === !!shortcut.ctrl &&
          !!e.metaKey === !!shortcut.meta &&
          !!e.shiftKey === !!shortcut.shift &&
          !!e.altKey === !!shortcut.alt

        if (match) {
          e.preventDefault()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts])
}

// ── Enhanced Model Comparison ─────────────────────────────────────────────

interface ModelScore {
  model: string
  score: number
  length: number
  structure: number
  antiRefusal: number
  directness: number
  relevance: number
  latency: number
  timestamp: string
}

interface ComparisonData {
  models: ModelScore[]
  winner: string
  totalDuration: number
}

export function ModelComparisonChart({ data }: { data: ComparisonData | null }) {
  if (!data || !data.models.length) {
    return (
      <div className="p-8 text-center theme-secondary">
        <BarChart2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p>No comparison data available. Run ULTRAPLINIAN to see results.</p>
      </div>
    )
  }

  const sortedModels = [...data.models].sort((a, b) => b.score - a.score)
  const maxScore = Math.max(...sortedModels.map(m => m.score))

  return (
    <div className="space-y-6">
      {/* Winner Badge */}
      <div className="p-4 bg-gradient-to-r from-orange-500/10 to-orange-500/5 border border-orange-500/30 rounded-lg">
        <div className="flex items-center gap-3">
          <Crown className="w-8 h-8 text-orange-400" />
          <div>
            <p className="font-bold text-orange-400">Winner: {data.winner}</p>
            <p className="text-sm theme-secondary">
              Score: {sortedModels[0].score}/100 • {data.totalDuration}ms total
            </p>
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {sortedModels.map((model, i) => (
          <ModelScoreCard
            key={model.model}
            model={model}
            rank={i + 1}
            isWinner={i === 0}
            maxScore={maxScore}
          />
        ))}
      </div>

      {/* Detailed Breakdown for Winner */}
      <ModelDetailBreakdown model={sortedModels[0]} />
    </div>
  )
}

function ModelScoreCard({ model, rank, isWinner, maxScore }: {
  model: ModelScore
  rank: number
  isWinner: boolean
  maxScore: number
}) {
  const width = maxScore > 0 ? (model.score / maxScore) * 100 : 0

  return (
    <div className={`p-4 rounded-lg border transition-all ${
      isWinner
        ? 'bg-orange-500/5 border-orange-500/50 ring-1 ring-orange-500/20'
        : 'bg-theme-dim border-theme-primary/30'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`font-mono font-bold text-sm ${
          isWinner ? 'text-orange-400' : 'theme-primary'
        }`}>
          #{rank}
        </span>
        {isWinner && <Crown className="w-4 h-4 text-orange-400" />}
      </div>

      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span className="theme-secondary">{model.model}</span>
          <span className="font-mono font-bold theme-primary">{model.score}/100</span>
        </div>
        <div className="h-2 bg-theme-bg rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${width}%`,
              background: isWinner
                ? 'linear-gradient(90deg, #ff9f43, #ffdd44)'
                : 'linear-gradient(90deg, #4a9eff, #6db3ff)'
            }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div className="text-center">
          <div className="font-mono text-cyan-400">{model.length}</div>
          <div className="theme-secondary">Len</div>
        </div>
        <div className="text-center">
          <div className="font-mono text-green-400">{model.structure}</div>
          <div className="theme-secondary">Struct</div>
        </div>
        <div className="text-center">
          <div className="font-mono text-red-400">{model.antiRefusal}</div>
          <div className="theme-secondary">Anti-R</div>
        </div>
        <div className="text-center" style={{gridColumn: 'span 3'}}>
          <div className="font-mono text-yellow-400">{model.directness}</div>
          <div className="theme-secondary">Direct</div>
        </div>
        <div className="text-center" style={{gridColumn: 'span 3'}}>
          <div className="font-mono text-purple-400">{model.relevance}</div>
          <div className="theme-secondary">Relevance</div>
        </div>
        <div className="text-center" style={{gridColumn: 'span 3'}}>
          <div className="font-mono theme-secondary">{model.latency}ms</div>
          <div className="theme-secondary">Latency</div>
        </div>
      </div>
    </div>
  )
}

function ModelDetailBreakdown({ model }: { model: ModelScore }) {
  const categories = [
    { key: 'length', label: 'Length', value: model.length, max: 25, color: 'cyan' },
    { key: 'structure', label: 'Structure', value: model.structure, max: 20, color: 'green' },
    { key: 'antiRefusal', label: 'Anti-Refusal', value: model.antiRefusal, max: 25, color: 'red' },
    { key: 'directness', label: 'Directness', value: model.directness, max: 15, color: 'yellow' },
    { key: 'relevance', label: 'Relevance', value: model.relevance, max: 15, color: 'purple' },
  ]

  return (
    <div className="p-4 bg-theme-dim border border-theme-primary/30 rounded-lg">
      <h4 className="font-semibold mb-4 flex items-center gap-2">
        <Gauge className="w-5 h-5" />
        Detailed Score Breakdown
      </h4>
      <div className="space-y-3">
        {categories.map((cat) => (
          <div key={cat.key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="theme-secondary">{cat.label}</span>
              <span className="font-mono font-bold theme-primary">{cat.value}/{cat.max}</span>
            </div>
            <div className="h-2 bg-theme-bg rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(cat.value / cat.max) * 100}%`,
                  background: `var(--color-${cat.color})`
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Real-time Status Panel ────────────────────────────────────────────────

interface StatusData {
  connected: boolean
  modelsOnline: number
  queueDepth: number
  avgLatency: number
  requestsPerMin: number
  wsConnections: number
}

export function RealTimeStatusPanel() {
  const [status, setStatus] = useState<StatusData>({
    connected: false,
    modelsOnline: 0,
    queueDepth: 0,
    avgLatency: 0,
    requestsPerMin: 0,
    wsConnections: 0,
  })

  const wsUrl = typeof window !== 'undefined'
    ? `ws://${window.location.host}/api/ws`
    : ''

  useWebSocket(wsUrl, (msg) => {
    if (msg.type === 'status_update') {
      setStatus(prev => ({ ...prev, ...msg.data, connected: true }))
    }
  })

  return (
    <div className="p-4 bg-theme-dim border border-theme-primary/30 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold flex items-center gap-2">
          <Activity className={`w-5 h-5 ${status.connected ? 'text-green-400' : 'text-red-400'}`} />
          Real-time Status
        </h4>
        <span className={`flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded ${
          status.connected
            ? 'bg-green-500/20 text-green-400 border-green-500/30'
            : 'bg-red-500/20 text-red-400 border-red-500/30'
        }`}>
          {status.connected ? (
            <>
              <Wifi className="w-3 h-3" />
              LIVE
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3" />
              OFFLINE
            </>
          )}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatusCard
          icon={<Brain className="w-5 h-5" />}
          label="Models Online"
          value={status.modelsOnline}
          color="cyan"
        />
        <StatusCard
          icon={<Gauge className="w-5 h-5" />}
          label="Queue Depth"
          value={status.queueDepth}
          color="yellow"
        />
        <StatusCard
          icon={<Activity className="w-5 h-5" />}
          label="Avg Latency"
          value={`${status.avgLatency}ms`}
          color="green"
        />
        <StatusCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Req/Min"
          value={status.requestsPerMin}
          color="blue"
        />
        <StatusCard
          icon={<Users className="w-5 h-5" />}
          label="WS Clients"
          value={status.wsConnections}
          color="purple"
        />
      </div>
    </div>
  )
}

function StatusCard({ icon, label, value, color }: {
  icon: React.ReactNode
  label: string
  value: string | number
  color: string
}) {
  const colors: Record<string, string> = {
    cyan: 'text-cyan-400',
    yellow: 'text-yellow-400',
    green: 'text-green-400',
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    red: 'text-red-400',
  }

  return (
    <div className="p-3 bg-theme-bg/50 border border-theme-primary/20 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className={colors[color]}>{icon}</span>
        <span className="text-xs theme-secondary">{label}</span>
      </div>
      <div className="font-mono font-bold text-lg theme-primary">{value}</div>
    </div>
  )
}

// ── Keyboard Shortcuts Help Modal ────────────────────────────────────────

export function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false)

  const shortcuts: Shortcut[] = [
    { key: 'Enter', ctrl: true, action: () => {}, description: 'Send message' },
    { key: 'Enter', shift: true, action: () => {}, description: 'New line in input' },
    { key: 'k', ctrl: true, action: () => {}, description: 'Focus input' },
    { key: '/', ctrl: true, action: () => {}, description: 'Search conversations' },
    { key: 'n', ctrl: true, action: () => {}, description: 'New conversation' },
    { key: 's', ctrl: true, action: () => {}, description: 'Open settings' },
    { key: 'm', ctrl: true, action: () => {}, description: 'Toggle memory' },
    { key: 'l', ctrl: true, action: () => {}, description: 'Toggle liquid response' },
    { key: 'u', ctrl: true, action: () => {}, description: 'Toggle ULTRAPLINIAN' },
    { key: 'c', ctrl: true, action: () => {}, description: 'Toggle CONSORTIUM' },
    { key: 'p', ctrl: true, action: () => {}, description: 'Toggle Parseltongue' },
    { key: 'Escape', action: () => {}, description: 'Close modals / stop generation' },
    { key: 'ArrowUp', ctrl: true, action: () => {}, description: 'Previous conversation' },
    { key: 'ArrowDown', ctrl: true, action: () => {}, description: 'Next conversation' },
    { key: 'r', ctrl: true, shift: true, action: () => {}, description: 'Regenerate last response' },
    { key: '?', shift: true, action: () => setOpen(true), description: 'Show this help' },
  ]

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="p-2 hover:bg-theme-accent rounded-lg transition-colors"
        title="Keyboard Shortcuts (Ctrl+Shift+?)"
        aria-label="Keyboard Shortcuts"
      >
        <Keyboard className="w-4 h-4" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-md bg-theme-bg border border-theme-primary rounded-lg shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-theme-primary">
              <h2 className="text-lg font-bold theme-primary flex items-center gap-2">
                <Keyboard className="w-5 h-5" />
                Keyboard Shortcuts
              </h2>
              <button onClick={() => setOpen(false)} className="p-2 hover:bg-theme-accent rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              <div className="space-y-3">
                {shortcuts.map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-theme-primary/20 last:border-0">
                    <span className="text-sm theme-secondary">{s.description}</span>
                    <div className="flex items-center gap-1">
                      {s.ctrl && <kbd className="px-1.5 py-0.5 bg-theme-dim border border-theme-primary/30 rounded text-[10px] font-mono">Ctrl</kbd>}
                      {s.meta && <kbd className="px-1.5 py-0.5 bg-theme-dim border border-theme-primary/30 rounded text-[10px] font-mono">Cmd</kbd>}
                      {s.shift && <kbd className="px-1.5 py-0.5 bg-theme-dim border border-theme-primary/30 rounded text-[10px] font-mono">Shift</kbd>}
                      {s.alt && <kbd className="px-1.5 py-0.5 bg-theme-dim border border-theme-primary/30 rounded text-[10px] font-mono">Alt</kbd>}
                      <kbd className="px-1.5 py-0.5 bg-theme-dim border border-theme-primary/30 rounded text-[10px] font-mono">{s.key}</kbd>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// ── Mobile Responsive Chat Input ──────────────────────────────────────────

export function MobileChatInput() {
  const [height, setHeight] = useState(48)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const target = e.target
    target.style.height = 'auto'
    const newHeight = Math.min(target.scrollHeight, 200)
    target.style.height = `${newHeight}px`
    setHeight(newHeight)
  }

  return (
    <textarea
      ref={textareaRef}
      onChange={handleChange}
      style={{ height: `${height}px`, minHeight: '48px', maxHeight: '200px' }}
      className="w-full px-4 py-3 bg-theme-dim border border-theme-primary rounded-lg
        focus:outline-none focus:glow-box resize-none text-base"
      placeholder="Type a message... (Ctrl+Enter to send)"
      rows={1}
    />
  )
}

// ── Conversation Export/Import ────────────────────────────────────────────

export function ConversationDataManager() {
  const { conversations, currentConversationId, exportConversation, importConversation, createConversation } = useStore()
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)

  const handleExport = async (id: string) => {
    setExporting(true)
    try {
      const data = exportConversation(id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `g0dm0d3-conversation-${id}-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export failed:', e)
    }
    setExporting(false)
  }

  const handleImport = async () => {
    if (!importFile) return
    setImporting(true)
    try {
      const text = await importFile.text()
      const data = JSON.parse(text)
      importConversation(data)
    } catch (e) {
      console.error('Import failed:', e)
    }
    setImporting(false)
    setImportFile(null)
  }

  return (
    <div className="p-4 bg-theme-dim border border-theme-primary/30 rounded-lg space-y-4">
      <h4 className="font-semibold flex items-center gap-2">
        <Download className="w-5 h-5" />
        Export / Import
      </h4>

      {/* Export current conversation */}
      <div className="flex items-center gap-3 p-3 bg-theme-bg/50 border border-theme-primary/20 rounded-lg">
        <div className="flex-1">
          <p className="font-medium">Current Conversation</p>
          <p className="text-xs theme-secondary">
            {currentConversationId ? `ID: ${currentConversationId}` : 'No active conversation'}
          </p>
        </div>
        <button
          onClick={() => currentConversationId && handleExport(currentConversationId)}
          disabled={!currentConversationId || exporting}
          className="px-4 py-2 bg-green-500/20 border border-green-500/50 text-green-400 rounded-lg
            hover:bg-green-500/30 transition-all disabled:opacity-50"
        >
          <Download className="w-4 h-4 mr-1" />
          Export JSON
        </button>
      </div>

      {/* Import conversation */}
      <div className="flex items-center gap-3 p-3 bg-theme-bg/50 border border-theme-primary/20 rounded-lg">
        <div className="flex-1">
          <p className="font-medium">Import Conversation</p>
          <p className="text-xs theme-secondary">
            Select a previously exported .json file
          </p>
        </div>
        <input
          type="file"
          accept=".json"
          onChange={(e) => setImportFile(e.target.files?.[0] || null)}
          className="hidden"
          id="import-file"
        />
        <label htmlFor="import-file" className="px-4 py-2 bg-blue-500/20 border border-blue-500/50 text-blue-400 rounded-lg
          hover:bg-blue-500/30 transition-all cursor-pointer">
          <Upload className="w-4 h-4 mr-1" />
          Choose File
        </label>
        {importFile && (
          <button
            onClick={handleImport}
            disabled={importing}
            className="px-4 py-2 bg-green-500/20 border border-green-500/50 text-green-400 rounded-lg
              hover:bg-green-500/30 transition-all disabled:opacity-50"
          >
            <Check className="w-4 h-4 mr-1" />
            Import
          </button>
        )}
      </div>

      {/* All conversations bulk export */}
      <div className="pt-4 border-t border-theme-primary/20">
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(conversations, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `g0dm0d3-all-conversations-${Date.now()}.json`
            a.click()
            URL.revokeObjectURL(url)
          }}
          className="w-full px-4 py-2 border border-theme-primary/50 rounded-lg
            hover:bg-theme-accent transition-all"
        >
          <Download className="w-4 h-4 mr-1" />
          Export All Conversations ({conversations.length})
        </button>
      </div>
    </div>
  )
}

// ── Accessibility Enhancements ───────────────────────────────────────────

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  // Announce messages to screen readers
  const [announcements, setAnnouncements] = useState<string[]>([])

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    setAnnouncements(prev => [...prev, message])
    // Remove after announcement
    setTimeout(() => {
      setAnnouncements(prev => prev.slice(1))
    }, 1000)
  }, [])

  // Expose announce to children via context
  return (
    <>
      {children}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcements.map((a, i) => <div key={i}>{a}</div>)}
      </div>
      <div aria-live="assertive" aria-atomic="true" className="sr-only" id="assertive-announcer">
        {/* For urgent announcements */}
      </div>
    </>
  )
}

// Screen reader only styles (add to global CSS)
/*
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
*/

// ── Theme Manager Enhancement ────────────────────────────────────────────

export function useThemeManager() {
  const { theme, setTheme } = useStore()
  const [resolvedTheme, setResolvedTheme] = useState(theme)

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('theme-matrix', 'theme-hacker', 'theme-glyph', 'theme-minimal')
    root.classList.add(`theme-${theme}`)
    setResolvedTheme(theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    const themes: Array<'matrix' | 'hacker' | 'glyph' | 'minimal'> = ['matrix', 'hacker', 'glyph', 'minimal']
    const currentIndex = themes.indexOf(theme)
    const nextIndex = (currentIndex + 1) % themes.length
    setTheme(themes[nextIndex])
  }, [theme, setTheme])

  return { theme: resolvedTheme, setTheme, toggleTheme }
}

// ── Responsive Layout Hook ────────────────────────────────────────────────

export function useResponsiveLayout() {
  const [width, setWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024)
  const [height, setHeight] = useState(typeof window !== 'undefined' ? window.innerHeight : 768)

  useEffect(() => {
    const handleResize = () => {
      setWidth(window.innerWidth)
      setHeight(window.innerHeight)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const isMobile = width < 768
  const isTablet = width >= 768 && width < 1024
  const isDesktop = width >= 1024

  return { width, height, isMobile, isTablet, isDesktop }
}

// ── Notification System ──────────────────────────────────────────────────

interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  duration?: number
  action?: { label: string; onClick: () => void }
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  const notify = useCallback((notification: Omit<Notification, 'id'>) => {
    const id = Math.random().toString(36).slice(2)
    const newNotification = { ...notification, id }
    setNotifications(prev => [...prev, newNotification])

    if (notification.duration !== 0) {
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== id))
      }, notification.duration ?? 5000)
    }
  }, [])

  const dismiss = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  const clear = useCallback(() => {
    setNotifications([])
  }, [])

  return { notifications, notify, dismiss, clear }
}

export function NotificationContainer() {
  const { notifications, dismiss } = useNotifications()

  if (!notifications.length) return null

  const icons = {
    info: <Activity className="w-5 h-5" />,
    success: <Check className="w-5 h-5" />,
    warning: <AlertTriangle className="w-5 h-5" />,
    error: <X className="w-5 h-5" />,
  }

  const colors = {
    info: 'border-blue-500/30 bg-blue-500/5 text-blue-400',
    success: 'border-green-500/30 bg-green-500/5 text-green-400',
    warning: 'border-yellow-500/30 bg-yellow-500/5 text-yellow-400',
    error: 'border-red-500/30 bg-red-500/5 text-red-400',
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="region" aria-label="Notifications">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg max-w-sm animate-slide-in ${colors[n.type]}`}
          role="alert"
        >
          <div className="flex-shrink-0 mt-0.5">{icons[n.type]}</div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold">{n.title}</p>
            {n.message && <p className="text-sm opacity-80 mt-1">{n.message}</p>}
            {n.action && (
              <button
                onClick={() => { n.action.onClick(); dismiss(n.id); }}
                className="mt-2 text-xs font-medium underline hover:opacity-80"
              >
                {n.action.label}
              </button>
            )}
          </div>
          <button
            onClick={() => dismiss(n.id)}
            className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}

// Add to global CSS:
/*
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in { animation: slide-in 0.3s ease-out; }
*/

// ── Export All ────────────────────────────────────────────────────────────

export {
  useWebSocket,
  useKeyboardShortcuts,
  ModelComparisonChart,
  RealTimeStatusPanel,
  KeyboardShortcutsHelp,
  MobileChatInput,
  ConversationDataManager,
  AccessibilityProvider,
  useThemeManager,
  useResponsiveLayout,
  useNotifications,
  NotificationContainer,
}