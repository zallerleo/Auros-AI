import { useState, useEffect } from 'react'
import {
  CheckCircle2, XCircle, Clock, PlayCircle, AlertTriangle,
  Filter, RefreshCw, ChevronRight, ArrowRight,
} from 'lucide-react'
import clsx from 'clsx'

const STATUS_CONFIG = {
  completed: { icon: CheckCircle2, color: 'text-status-active', bg: 'bg-status-active/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-status-error', bg: 'bg-status-error/10', label: 'Failed' },
  pending: { icon: Clock, color: 'text-status-warning', bg: 'bg-status-warning/10', label: 'Pending' },
  running: { icon: PlayCircle, color: 'text-status-info', bg: 'bg-status-info/10', label: 'Running' },
  awaiting_approval: { icon: AlertTriangle, color: 'text-auros-gold', bg: 'bg-auros-gold/10', label: 'Awaiting Approval' },
  approved: { icon: CheckCircle2, color: 'text-status-active', bg: 'bg-status-active/10', label: 'Approved' },
  rejected: { icon: XCircle, color: 'text-status-error', bg: 'bg-status-error/10', label: 'Rejected' },
}

const AGENT_COLORS: Record<string, string> = {
  ATLAS: '#C9A84C', SCOUT: '#3B82F6', FORGE: '#8B5CF6',
  APOLLO: '#F59E0B', HERMES: '#10B981', SENTINEL: '#EF4444',
  SCHEDULER: '#8888A0', LEO: '#C9A84C',
}

const DEMO_TASKS = [
  { id: 'a1b2c3', from_agent: 'SCHEDULER', to_agent: 'SCOUT', task_type: 'daily_scan', status: 'completed', created_at: '2026-03-23T07:00:00', completed_at: '2026-03-23T07:02:15', priority: 3 },
  { id: 'd4e5f6', from_agent: 'SCHEDULER', to_agent: 'HERMES', task_type: 'send_newsletter', status: 'completed', created_at: '2026-03-23T07:30:00', completed_at: '2026-03-23T07:31:45', priority: 3 },
  { id: 'g7h8i9', from_agent: 'ATLAS', to_agent: 'SCOUT', task_type: 'deep_research', status: 'running', created_at: '2026-03-23T09:15:00', priority: 5 },
  { id: 'j1k2l3', from_agent: 'FORGE', to_agent: 'LEO', task_type: 'approval_request', status: 'awaiting_approval', created_at: '2026-03-23T09:20:00', priority: 1, payload: { description: 'Start onboarding pipeline for TechCo Barcelona' } },
  { id: 'm4n5o6', from_agent: 'FORGE', to_agent: 'APOLLO', task_type: 'content_brief', status: 'pending', created_at: '2026-03-23T09:25:00', priority: 5 },
  { id: 'p7q8r9', from_agent: 'SCHEDULER', to_agent: 'SENTINEL', task_type: 'system_health', status: 'completed', created_at: '2026-03-23T09:00:00', completed_at: '2026-03-23T09:00:30', priority: 3 },
  { id: 's1t2u3', from_agent: 'SCOUT', to_agent: 'FORGE', task_type: 'intelligence_update', status: 'completed', created_at: '2026-03-23T08:05:00', completed_at: '2026-03-23T08:05:02', priority: 5 },
  { id: 'v4w5x6', from_agent: 'ATLAS', to_agent: 'APOLLO', task_type: 'create_social_posts', status: 'completed', created_at: '2026-03-22T14:30:00', completed_at: '2026-03-22T14:32:10', priority: 5 },
  { id: 'y7z8a1', from_agent: 'SCHEDULER', to_agent: 'SENTINEL', task_type: 'daily_check', status: 'completed', created_at: '2026-03-22T18:00:00', completed_at: '2026-03-22T18:01:00', priority: 3 },
  { id: 'b2c3d4', from_agent: 'ATLAS', to_agent: 'HERMES', task_type: 'draft_outreach', status: 'completed', created_at: '2026-03-22T11:00:00', completed_at: '2026-03-22T11:01:30', priority: 5 },
]

type FilterStatus = 'all' | keyof typeof STATUS_CONFIG

export default function Tasks() {
  const [tasks, setTasks] = useState(DEMO_TASKS)
  const [filter, setFilter] = useState<FilterStatus>('all')

  useEffect(() => {
    fetch('/api/tasks?limit=50').then(r => r.json()).then(setTasks).catch(() => {})
  }, [])

  const filtered = filter === 'all' ? tasks : tasks.filter(t => t.status === filter)

  const counts = tasks.reduce((acc, t) => {
    acc[t.status] = (acc[t.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  async function handleApprove(taskId: string) {
    try {
      await fetch(`/api/tasks/${taskId}/approve`, { method: 'POST' })
      setTasks(tasks.map(t => t.id === taskId ? { ...t, status: 'pending' } : t))
    } catch { /* demo mode */ }
  }

  async function handleReject(taskId: string) {
    try {
      await fetch(`/api/tasks/${taskId}/reject`, { method: 'POST' })
      setTasks(tasks.map(t => t.id === taskId ? { ...t, status: 'rejected' } : t))
    } catch { /* demo mode */ }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Task Queue</h2>
          <p className="text-auros-text-muted mt-1">{tasks.length} tasks total</p>
        </div>
        <button
          onClick={() => fetch('/api/tasks?limit=50').then(r => r.json()).then(setTasks).catch(() => {})}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-auros-card border border-auros-border hover:border-auros-gold/50 text-sm font-medium transition-all"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        {(['all', 'awaiting_approval', 'running', 'pending', 'completed', 'failed'] as FilterStatus[]).map((status) => {
          const count = status === 'all' ? tasks.length : (counts[status] || 0)
          const cfg = status !== 'all' ? STATUS_CONFIG[status] : null
          const isActive = filter === status
          return (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-auros-gold/10 text-auros-gold border border-auros-gold/30'
                  : 'bg-auros-card text-auros-text-muted border border-auros-border hover:border-auros-border-light'
              )}
            >
              {cfg && <cfg.icon className="w-3.5 h-3.5" />}
              {status === 'all' ? 'All' : cfg?.label}
              <span className="ml-1 text-xs font-mono opacity-60">{count}</span>
            </button>
          )
        })}
      </div>

      {/* Task List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <p className="text-auros-text-muted">No tasks match this filter.</p>
          </div>
        ) : (
          filtered.map((task) => {
            const cfg = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending
            const StatusIcon = cfg.icon
            const fromColor = AGENT_COLORS[task.from_agent] || '#666'
            const toColor = AGENT_COLORS[task.to_agent] || '#666'
            const isApproval = task.status === 'awaiting_approval'
            const payload = (task as any).payload

            return (
              <div key={task.id} className={clsx('glass-card-hover p-4', isApproval && 'border-auros-gold/30')}>
                <div className="flex items-center gap-4">
                  {/* Status Icon */}
                  <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center', cfg.bg)}>
                    <StatusIcon className={clsx('w-4.5 h-4.5', cfg.color)} />
                  </div>

                  {/* Task Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold font-mono" style={{ color: fromColor }}>{task.from_agent}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-auros-text-dim" />
                      <span className="text-sm font-semibold font-mono" style={{ color: toColor }}>{task.to_agent}</span>
                      <span className="text-xs px-2 py-0.5 rounded-md bg-auros-surface text-auros-text-muted">{task.task_type}</span>
                    </div>
                    {isApproval && payload?.description && (
                      <p className="text-sm text-auros-gold mt-1">{payload.description}</p>
                    )}
                    <p className="text-xs text-auros-text-dim mt-1">
                      {new Date(task.created_at).toLocaleString()}
                      {(task as any).completed_at && ` — completed ${new Date((task as any).completed_at).toLocaleTimeString()}`}
                    </p>
                  </div>

                  {/* ID & Actions */}
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-auros-text-dim">{task.id}</span>
                    {isApproval && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(task.id)}
                          className="px-3 py-1.5 rounded-lg bg-status-active/10 text-status-active text-xs font-semibold hover:bg-status-active/20 transition-all"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleReject(task.id)}
                          className="px-3 py-1.5 rounded-lg bg-status-error/10 text-status-error text-xs font-semibold hover:bg-status-error/20 transition-all"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
