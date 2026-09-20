import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Ask from './routes/Ask'
import Card from './routes/Card'
import HowItWorks from './routes/HowItWorks'
import Maya from './routes/Maya'
import Onboard from './routes/Onboard'

const NAV = [
  { to: '/maya', label: 'Queue' },
  { to: '/ask', label: 'Ask' },
  { to: '/c/c-jessica', label: 'Card' },
  { to: '/onboard', label: 'Standard' },
  { to: '/how-it-works', label: 'How it works' },
]

export default function App() {
  const { pathname } = useLocation()

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner page">
          <span className="brand">Maya Rao</span>
          <span className="brand-sub">her judgement, running without her</span>
          <nav className="topnav" aria-label="Primary">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? 'on' : '')}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* The entrance animations are plain CSS on the route's own markup, so
          they only run when the element is created. React Router keeps the
          same element alive across a param change (/c/c-jessica → /c/c-priya),
          and re-uses the DOM wherever it can, so without a key the second
          visit to a page would arrive with no motion at all.

          Keying on the pathname forces a remount on every navigation — and
          because the pathname contains the card id, /c/:id gets one per card
          too. Route state is meant to be thrown away on navigation anyway. */}
      <main key={pathname}>
        <Routes>
          <Route path="/" element={<Navigate to="/maya" replace />} />
          <Route path="/maya" element={<Maya />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/c/:id" element={<Card />} />
          <Route path="/onboard" element={<Onboard />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="*" element={<Navigate to="/maya" replace />} />
        </Routes>
      </main>
    </div>
  )
}
