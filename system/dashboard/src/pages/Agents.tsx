import { useState, useEffect } from 'react'
import {
  Brain, Search, Target, Palette, Send, Shield,
  Activity, CheckCircle2, XCircle, Clock, Wrench,
  MessageSquare, Database, ChevronDown, ChevronUp,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts'
import clsx from 'clsx'

const ICONS: Record<string, typeof Brain> = {
  ATLAS: Brain, SCOUT: Search, FORGE: Target,
  APOLLO: Palette, HERMES: Send, SENTINEL: Shield,
}

const COLORS: Record<string, string> = {
  ATLAS: '#C9A84C', SCOUT: '#3B82F6', FORGE: '#8B5CF6',
  APOLLO: '#F59E0B', HERMES: '#10B981', SENTINEL: '#EF4444',
}

const DEMO_AGENTS = [
  {
    name: 'ATLAS', role: 'Chief of Staff', color: '#C9A84C', status: 'active',
    description: 'Routes requests, coordinates agents, compiles briefings, manages approval queue',
    stats: { total: 45, completed: 44, failed: 0, running: 1, success_rate: 97.8 },
    tools: ['route_message', 'daily_briefing', 'approval_queue', 'system_status'],
    last_action: 'Routed research request to SCOUT', memory_count: 8,
  },
  {
    name: 'SCOUT', role: 'Research & Intelligence', color: '#3B82F6', status: 'active',
    description: 'Deep market research, competitive analysis, trends, sector scanning, GEO monitoring',
    stats: { total: 62, completed: 59, failed: 1, running: 2, success_rate: 95.2 },
    tools: ['deep_research', 'quick_search', 'competitive_analysis', 'market_scan', 'trend_analysis', 'geo_check'],
    last_action: 'Deep research: AI marketing trends Q1 2026', memory_count: 15,
  },
  {
    name: 'FORGE', role: 'Strategy & Clients', color: '#8B5CF6', status: 'online',
    description: 'Client onboarding, marketing strategy, positioning, proposals, pipeline management',
    stats: { total: 48, completed: 47, failed: 1, running: 0, success_rate: 97.9 },
    tools: ['run_pipeline', 'run_stage', 'pipeline_status', 'create_proposal', 'marketing_audit', 'brand_analysis'],
    last_action: 'Pipeline completed for The Imagine Team', memory_count: 22,
  },
  {
    name: 'APOLLO', role: 'Creative & Content', color: '#F59E0B', status: 'active',
    description: 'Content creation, video scripts, social posts, copywriting, creative direction',
    stats: { total: 55, completed: 52, failed: 2, running: 1, success_rate: 94.5 },
    tools: ['create_social_posts', 'create_video_script', 'generate_hooks', 'content_calendar', 'creative_brief', 'adapt_content'],
    last_action: 'Generated 20 social posts for exhibition campaign', memory_count: 18,
  },
  {
    name: 'HERMES', role: 'Outreach & Comms', color: '#10B981', status: 'online',
    description: 'Cold outreach, email campaigns, newsletters, follow-up sequences, client communication',
    stats: { total: 22, completed: 21, failed: 0, running: 0, success_rate: 95.5 },
    tools: ['draft_outreach', 'draft_sequence', 'send_newsletter', 'draft_followup', 'outreach_strategy'],
    last_action: 'Newsletter sent: AI Marketing Daily', memory_count: 6,
  },
  {
    name: 'SENTINEL', role: 'Operations & Performance', color: '#EF4444', status: 'online',
    description: 'KPI tracking, analytics, anomaly detection, system health, API cost monitoring',
    stats: { total: 15, completed: 15, failed: 0, running: 0, success_rate: 100 },
    tools: ['performance_report', 'system_health', 'cost_tracking', 'task_analytics', 'anomaly_check'],
    last_action: 'System health check: all clear', memory_count: 4,
  },
]

export default function Agents() {
  const [agents, setAgents] = useState(DEMO_AGENTS)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/agents').then(r => r.json()).then(setAgents).catch(() => {})
  }, [])

  const chartData = agents.map(a => ({
    name: a.name,
    tasks: a.stats.total,
    success: a.stats.success_rate,
    color: COLORS[a.name] || '#666',
  }))

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Agent Team</h2>
        <p className="text-auros-text-muted mt-1">6 department heads managing your marketing empire</p>
      </div>

      {/* Overview Bar Chart */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold mb-4">Tasks by Agent</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} barSize={40}>
            <XAxis dataKey="name" stroke="#5A5A70" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#5A5A70" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#16161F', border: '1px solid #2A2A3A', borderRadius: '12px' }}
              cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            />
            <Bar dataKey="tasks" radius={[8, 8, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} fillOpacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {agents.map((agent) => {
          const Icon = ICONS[agent.name] || Brain
          const color = COLORS[agent.name] || '#666'
          const isExpanded = expandedAgent === agent.name
          const isActive = agent.status === 'active'

          return (
            <div key={agent.name} className="glass-card-hover overflow-hidden">
              {/* Header */}
              <div
                className="p-5 cursor-pointer"
                onClick={() => setExpandedAgent(isExpanded ? null : agent.name)}
              >
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center relative" style={{ backgroundColor: `${color}15` }}>
                    <Icon className="w-7 h-7" style={{ color }} />
                    <div className={clsx(
                      'absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-auros-card',
                      isActive ? 'bg-status-active' : 'bg-status-active/50'
                    )} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold">{agent.name}</h3>
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: `${color}15`, color }}>
                        {agent.role}
                      </span>
                    </div>
                    <p className="text-sm text-auros-text-muted mt-1">{agent.description}</p>
                    <p className="text-xs text-auros-text-dim mt-2 flex items-center gap-1.5">
                      <Activity className="w-3 h-3" />
                      {agent.last_action}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className="text-2xl font-bold font-mono" style={{ color }}>{agent.stats.success_rate}%</span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-auros-text-dim" /> : <ChevronDown className="w-4 h-4 text-auros-text-dim" />}
                  </div>
                </div>

                {/* Stats Bar */}
                <div className="flex items-center gap-5 mt-4 pt-4 border-t border-auros-border/30">
                  {[
                    { label: 'Total', value: agent.stats.total, icon: Activity },
                    { label: 'Completed', value: agent.stats.completed, icon: CheckCircle2 },
                    { label: 'Failed', value: agent.stats.failed, icon: XCircle },
                    { label: 'Running', value: agent.stats.running, icon: Clock },
                  ].map(({ label, value, icon: StatIcon }) => (
                    <div key={label} className="flex items-center gap-1.5 text-xs">
                      <StatIcon className="w-3.5 h-3.5 text-auros-text-dim" />
                      <span className="text-auros-text-muted">{label}:</span>
                      <span className="font-mono font-semibold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-5 pb-5 pt-2 border-t border-auros-border/30 animate-slide-up">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                        <Wrench className="w-3.5 h-3.5 text-auros-text-muted" /> Tools
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {(agent.tools || []).map(tool => (
                          <span key={tool} className="text-xs px-2 py-1 rounded-md bg-auros-surface text-auros-text-muted font-mono">
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-auros-text-muted" /> Memory
                      </h4>
                      <p className="text-sm text-auros-text-muted">{agent.memory_count} stored insights</p>
                      <p className="text-xs text-auros-text-dim mt-1">Agent learns from every interaction</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
