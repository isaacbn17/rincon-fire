import { NavLink } from "react-router-dom"

const linkBaseClass = "rounded-md px-3 py-1.5 text-sm transition-colors"
const activeClass = "bg-primary text-primary-foreground"
const inactiveClass = "text-muted-foreground hover:bg-muted hover:text-foreground"

export function NavHeader() {
  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 p-4 md:p-6">
        <h1 className="text-lg font-semibold tracking-tight">Rincon Fire</h1>
        <nav aria-label="Primary navigation" className="flex items-center gap-2">
          <NavLink
            className={({ isActive }) => `${linkBaseClass} ${isActive ? activeClass : inactiveClass}`}
            end
            to="/"
          >
            Dashboard
          </NavLink>
          <NavLink
            className={({ isActive }) => `${linkBaseClass} ${isActive ? activeClass : inactiveClass}`}
            to="/compare"
          >
            Compare
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
