import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Zap, LayoutDashboard, Users, ListTodo, Activity, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tasks from './pages/Tasks'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/agents', icon: Users, label: 'Agents' },
  { to: '/tasks', icon: ListTodo, label: 'Tasks' },
]

export default function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-auros-border/50 bg-auros-midnight/80 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-auros-gold to-auros-gold-dark flex items-center justify-center gold-glow">
              <Zap className="w-5 h-5 text-auros-midnight" strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-auros-gold">AUROS</span>
                <span className="text-auros-text-muted font-normal ml-1.5">AI</span>
              </h1>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, icon: Icon, label }) => {
              const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
              return (
                <NavLink
                  key={to}
                  to={to}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'text-auros-gold bg-auros-gold/10'
                      : 'text-auros-text-muted hover:text-auros-text hover:bg-auros-card'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </NavLink>
              )
            })}
          </nav>

          {/* Status indicator */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-active/10 border border-status-active/20">
              <div className="w-2 h-2 rounded-full bg-status-active animate-pulse-slow" />
              <span className="text-xs font-medium text-status-active">System Online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[1600px] mx-auto w-full px-6 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/tasks" element={<Tasks />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-auros-border/30 py-4">
        <div className="max-w-[1600px] mx-auto px-6 flex items-center justify-between text-xs text-auros-text-dim">
          <span>AUROS AI Mission Control v1.0</span>
          <span className="flex items-center gap-1.5">
            <Activity className="w-3 h-3" />
            Real-time agent monitoring
          </span>
        </div>
      </footer>
    </div>
  )
}
