import { useState, useEffect } from 'react'
import {
  Brain, Search, Target, Palette, Send, Shield,
  TrendingUp, CheckCircle2, Clock, AlertTriangle,
  Activity, Zap, ArrowUpRight, BarChart3, Timer,
  RefreshCw, ChevronRight, Cpu, HardDrive,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, RadialBarChart, RadialBar,
  PieChart, Pie, Cell,
} from 'recharts'
import clsx from 'clsx'

const AGENT_ICONS: Record<string, typeof Brain> = {
  ATLAS: Brain, SCOUT: Search, FORGE: Target,
  APOLLO: Palette, HERMES: Send, SENTINEL: Shield,
}

const AGENT_COLORS: Record<string, string> = {
  ATLAS: '#C9A84C', SCOUT: '#3B82F6', FORGE: '#8B5CF6',
  APOLLO: '#F59E0B', HERMES: '#10B981', SENTINEL: '#EF4444',
}

const STATUS_CONFIG = {
  online: { color: 'text-status-active', bg: 'bg-status-active', label: 'Online' },
  active: { color: 'text-status-active', bg: 'bg-status-active', label: 'Active' },
  warning: { color: 'text-status-warning', bg: 'bg-status-warning', label: 'Warning' },
  error: { color: 'text-status-error', bg: 'bg-status-error', label: 'Error' },
}

// Demo data for when API isn't connected yet
const DEMO_DATA = {
  kpis: {
    total_agents: 6, active_agents: 6, total_tasks: 247,
    completed_tasks: 231, today_completed: 18, completion_rate: 93.5,
    uptime_days: 12, pending_tasks: 8, running_tasks: 3,
    failed_tasks: 5, awaiting_approval: 2,
  },
  performance: [
    { day: 'Mon', completed: 32, failed: 2, accuracy: 94 },
    { day: 'Tue', completed: 28, failed: 1, accuracy: 97 },
    { day: 'Wed', completed: 45, failed: 3, accuracy: 94 },
    { day: 'Thu', completed: 38, failed: 1, accuracy: 97 },
    { day: 'Fri', completed: 52, failed: 2, accuracy: 96 },
    { day: 'Sat', completed: 18, failed: 0, accuracy: 100 },
    { day: 'Sun', completed: 24, failed: 1, accuracy: 96 },
  ],
  agent_tasks: { ATLAS: 45, SCOUT: 62, FORGE: 48, APOLLO: 55, HERMES: 22, SENTINEL: 15 },
  system: { disk_free_gb: 234.5, disk_total_gb: 500, disk_usage_pct: 53.1 },
}

const DEMO_AGENTS = [
  { name: 'ATLAS', role: 'Chief of Staff', status: 'active', stats: { total: 45, completed: 44, running: 1, success_rate: 97.8 }, last_action: 'Routed research request to SCOUT' },
  { name: 'SCOUT', role: 'Research & Intelligence', status: 'active', stats: { total: 62, completed: 59, running: 2, success_rate: 95.2 }, last_action: 'Deep research: AI marketing trends Q1' },
  { name: 'FORGE', role: 'Strategy & Clients', status: 'online', stats: { total: 48, completed: 47, running: 0, success_rate: 97.9 }, last_action: 'Pipeline completed for The Imagine Team' },
  { name: 'APOLLO', role: 'Creative & Content', status: 'active', stats: { total: 55, completed: 52, running: 1, success_rate: 94.5 }, last_action: 'Generated 20 social posts for exhibition campaign' },
  { name: 'HERMES', role: 'Outreach & Comms', status: 'online', stats: { total: 22, completed: 21, running: 0, success_rate: 95.5 }, last_action: 'Newsletter sent: AI Marketing Daily' },
  { name: 'SENTINEL', role: 'Operations & Performance', status: 'online', stats: { total: 15, completed: 15, running: 0, success_rate: 100 }, last_action: 'System health check: all clear' },
]

interface DashboardData {
  kpis: typeof DEMO_DATA.kpis
  performance: typeof DEMO_DATA.performance
  agent_tasks: typeof DEMO_DATA.agent_tasks
  system: typeof DEMO_DATA.system
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>(DEMO_DATA)
  const [agents, setAgents] = useState(DEMO_AGENTS)
  const [isLive, setIsLive] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  async function fetchData() {
    try {
      const [dashRes, agentsRes] = await Promise.all([
        fetch('/api/dashboard'),
        fetch('/api/agents'),
      ])
      if (dashRes.ok && agentsRes.ok) {
        setData(await dashRes.json())
        setAgents(await agentsRes.json())
        setIsLive(true)
      }
    } catch {
      // Use demo data when API isn't available
    }
    setLastRefresh(new Date())
  }

  const { kpis, performance, agent_tasks, system } = data

  // Agent task distribution for pie chart
  const agentDistribution = Object.entries(agent_tasks).map(([name, value]) => ({
    name, value, color: AGENT_COLORS[name] || '#666',
  }))

  // Radial bar data for completion rate
  const completionData = [{ name: 'Rate', value: kpis.completion_rate, fill: '#C9A84C' }]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Mission Control</h2>
          <p className="text-auros-text-muted mt-1">
            {isLive ? 'Live data' : 'Preview mode'} — Last updated {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-auros-card border border-auros-border hover:border-auros-gold/50 text-sm font-medium transition-all duration-200 hover:gold-glow"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <KpiCard
          title="Active Agents"
          value={`${kpis.active_agents}`}
          subtitle={`of ${kpis.total_agents} total`}
          icon={Cpu}
          trend={null}
          accentColor="text-auros-gold"
          chart={
            <div className="w-16 h-16">
              <RadialBarChart width={64} height={64} innerRadius="60%" outerRadius="100%" data={[{ value: (kpis.active_agents / kpis.total_agents) * 100 }]} startAngle={90} endAngle={-270}>
                <RadialBar dataKey="value" fill="#C9A84C" background={{ fill: '#2A2A3A' }} cornerRadius={10} />
              </RadialBarChart>
            </div>
          }
        />
        <KpiCard
          title="Tasks Completed"
          value={kpis.completed_tasks.toLocaleString()}
          subtitle={`${kpis.today_completed} today`}
          icon={CheckCircle2}
          trend={{ value: kpis.today_completed, positive: true }}
          accentColor="text-status-active"
        />
        <KpiCard
          title="Success Rate"
          value={`${kpis.completion_rate}%`}
          subtitle={`${kpis.failed_tasks} failed`}
          icon={TrendingUp}
          trend={{ value: kpis.completion_rate > 90 ? kpis.completion_rate - 90 : 0, positive: kpis.completion_rate > 90 }}
          accentColor="text-status-info"
        />
        <KpiCard
          title="Uptime"
          value={`${kpis.uptime_days}d`}
          subtitle="Continuous operation"
          icon={Timer}
          trend={null}
          accentColor="text-auros-gold"
          chart={
            <div className="flex items-center gap-1">
              {Array.from({ length: 7 }).map((_, i) => (
                <div key={i} className="w-1.5 h-8 rounded-full bg-auros-gold/30" style={{ height: `${20 + Math.random() * 20}px`, opacity: 0.3 + i * 0.1 }} />
              ))}
            </div>
          }
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Performance Chart — spans 2 cols */}
        <div className="lg:col-span-2 glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold">Agent Performance</h3>
              <p className="text-sm text-auros-text-muted mt-0.5">Tasks completed & accuracy over 7 days</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 rounded bg-auros-gold" />Tasks
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 rounded bg-status-info" />Accuracy
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={performance}>
              <defs>
                <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#C9A84C" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#C9A84C" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1C1C28" />
              <XAxis dataKey="day" stroke="#5A5A70" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#5A5A70" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#16161F', border: '1px solid #2A2A3A', borderRadius: '12px', fontSize: '13px' }}
                labelStyle={{ color: '#E8E8F0' }}
              />
              <Area type="monotone" dataKey="completed" stroke="#C9A84C" strokeWidth={2.5} fill="url(#goldGradient)" dot={{ fill: '#C9A84C', r: 4, strokeWidth: 0 }} activeDot={{ r: 6, fill: '#C9A84C', stroke: '#08080C', strokeWidth: 2 }} />
              <Area type="monotone" dataKey="accuracy" stroke="#3B82F6" strokeWidth={2} fill="url(#blueGradient)" dot={false} strokeDasharray="5 5" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Status Panel */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-semibold">Agent Status</h3>
            <span className="text-xs text-auros-text-muted">{agents.filter(a => a.status === 'active' || a.status === 'online').length} online</span>
          </div>
          <div className="space-y-3">
            {agents.map((agent) => {
              const Icon = AGENT_ICONS[agent.name] || Brain
              const color = AGENT_COLORS[agent.name] || '#666'
              const statusCfg = STATUS_CONFIG[agent.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.online
              return (
                <div key={agent.name} className="flex items-center gap-3 p-3 rounded-xl bg-auros-surface/50 hover:bg-auros-card-hover transition-all duration-200 group cursor-pointer">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
                    <Icon className="w-5 h-5" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{agent.name}</span>
                      <div className={clsx('w-1.5 h-1.5 rounded-full', statusCfg.bg)} />
                    </div>
                    <p className="text-xs text-auros-text-muted truncate">{agent.last_action}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-auros-text-muted">{agent.stats.success_rate}%</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Task Distribution */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">Task Distribution</h3>
          <div className="flex items-center justify-center">
            <PieChart width={200} height={200}>
              <Pie
                data={agentDistribution}
                cx={100} cy={100}
                innerRadius={55} outerRadius={85}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
              >
                {agentDistribution.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <text x={100} y={95} textAnchor="middle" fill="#E8E8F0" fontSize={24} fontWeight={700}>
                {kpis.total_tasks}
              </text>
              <text x={100} y={115} textAnchor="middle" fill="#8888A0" fontSize={11}>
                total tasks
              </text>
            </PieChart>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {agentDistribution.map(({ name, value, color }) => (
              <div key={name} className="flex items-center gap-2 text-xs">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-auros-text-muted">{name}</span>
                <span className="ml-auto font-mono">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            {[
              { label: 'New Client Onboarding', icon: Target, desc: 'Start full pipeline', color: '#8B5CF6' },
              { label: 'Run Market Scan', icon: Search, desc: 'SCOUT deep research', color: '#3B82F6' },
              { label: 'Create Content Batch', icon: Palette, desc: 'APOLLO content generation', color: '#F59E0B' },
              { label: 'Send Newsletter', icon: Send, desc: 'HERMES daily dispatch', color: '#10B981' },
              { label: 'System Health Check', icon: Shield, desc: 'SENTINEL diagnostics', color: '#EF4444' },
            ].map(({ label, icon: Icon, desc, color }) => (
              <button key={label} className="w-full flex items-center gap-3 p-3 rounded-xl bg-auros-surface/50 hover:bg-auros-card-hover border border-transparent hover:border-auros-border transition-all duration-200 text-left group">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
                  <Icon className="w-4 h-4" style={{ color }} />
                </div>
                <div className="flex-1">
                  <span className="text-sm font-medium">{label}</span>
                  <p className="text-xs text-auros-text-muted">{desc}</p>
                </div>
                <ChevronRight className="w-4 h-4 text-auros-text-dim group-hover:text-auros-text-muted transition-colors" />
              </button>
            ))}
          </div>
        </div>

        {/* System Resources */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">System Resources</h3>

          {/* Disk Usage */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-auros-text-muted flex items-center gap-2">
                <HardDrive className="w-4 h-4" /> Storage
              </span>
              <span className="text-sm font-mono">{system.disk_usage_pct}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-auros-surface overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: `${system.disk_usage_pct}%`,
                  background: system.disk_usage_pct > 80
                    ? 'linear-gradient(90deg, #EF4444, #F59E0B)'
                    : 'linear-gradient(90deg, #C9A84C, #E5D5A0)',
                }}
              />
            </div>
            <p className="text-xs text-auros-text-dim mt-1.5">{system.disk_free_gb}GB free of {system.disk_total_gb}GB</p>
          </div>

          {/* Task Queue Status */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-auros-text-muted">Task Queue</h4>
            {[
              { label: 'Pending', value: kpis.pending_tasks, icon: Clock, color: '#F59E0B' },
              { label: 'Running', value: kpis.running_tasks, icon: Activity, color: '#3B82F6' },
              { label: 'Awaiting Approval', value: kpis.awaiting_approval, icon: AlertTriangle, color: '#EF4444' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-auros-text-muted">
                  <Icon className="w-4 h-4" style={{ color }} />
                  {label}
                </span>
                <span className="text-lg font-bold font-mono" style={{ color }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Approval Button */}
          {kpis.awaiting_approval > 0 && (
            <button className="w-full mt-5 py-2.5 rounded-xl bg-auros-gold/10 border border-auros-gold/30 text-auros-gold text-sm font-semibold hover:bg-auros-gold/20 transition-all duration-200">
              Review {kpis.awaiting_approval} Pending Approval{kpis.awaiting_approval > 1 ? 's' : ''}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// KPI Card Component
// ---------------------------------------------------------------------------

function KpiCard({
  title, value, subtitle, icon: Icon, trend, accentColor, chart,
}: {
  title: string
  value: string
  subtitle: string
  icon: typeof Brain
  trend: { value: number; positive: boolean } | null
  accentColor: string
  chart?: React.ReactNode
}) {
  return (
    <div className="glass-card-hover p-5 animate-slide-up">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-auros-text-muted font-medium">{title}</p>
          <p className="kpi-value mt-2">{value}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-auros-text-dim">{subtitle}</span>
            {trend && (
              <span className={clsx(
                'flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded-md',
                trend.positive ? 'text-status-active bg-status-active/10' : 'text-status-error bg-status-error/10'
              )}>
                <ArrowUpRight className={clsx('w-3 h-3', !trend.positive && 'rotate-90')} />
                {trend.value.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        {chart || (
          <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center bg-auros-surface', accentColor)}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  )
}
