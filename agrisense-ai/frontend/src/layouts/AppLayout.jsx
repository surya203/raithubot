import { NavLink, Outlet } from "react-router-dom"
import {
  Bell,
  BookOpen,
  History,
  LayoutDashboard,
  Menu,
  MessageSquare,
  ShieldAlert,
  Sprout,
  X,
} from "lucide-react"
import { useState } from "react"
import { useFarm } from "../context/FarmContext"
import { Notice } from "../components/ui"

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/crops", label: "Crop Management", icon: Sprout },
  { to: "/disease", label: "Disease Advisory", icon: ShieldAlert },
  { to: "/assistant", label: "AI Assistant", icon: MessageSquare },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/history", label: "Advisory History", icon: History },
  { to: "/knowledge", label: "Knowledge Base", icon: BookOpen },
]

export default function AppLayout() {
  const [open, setOpen] = useState(false)
  const farm = useFarm()

  return (
    <div className="min-h-screen bg-cream text-earth">
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col bg-earth text-cream transition-transform md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-white/10 px-5 py-5">
          <p className="font-display text-2xl font-semibold">AgriSense AI</p>
          <p className="mt-1 text-sm text-sand">Intelligent Agricultural Advisory for Better Farming Decisions</p>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {links.map((link) => {
            const Icon = link.icon
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold ${
                    isActive ? "bg-sage text-earth" : "text-cream hover:bg-white/10"
                  }`
                }
              >
                <Icon size={18} />
                {link.label}
              </NavLink>
            )
          })}
        </nav>
      </aside>
      {open ? (
        <button
          className="fixed inset-0 z-20 bg-earth/40 md:hidden"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <div className="md:pl-72">
        <header className="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-sand bg-cream/95 px-4 py-3 backdrop-blur">
          <button
            className="rounded-xl border border-sand bg-paper p-2 md:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
          <label className="min-w-44 flex-1 text-sm">
            <span className="mb-1 block font-semibold text-bark">Location</span>
            <select
              className="w-full rounded-xl border border-sand bg-paper px-3 py-2"
              value={farm.locationId}
              onChange={(event) => farm.setLocationId(event.target.value)}
            >
              <option value="">All locations</option>
              {farm.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}, {location.district}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-44 flex-1 text-sm">
            <span className="mb-1 block font-semibold text-bark">Crop</span>
            <select
              className="w-full rounded-xl border border-sand bg-paper px-3 py-2"
              value={farm.cropId}
              onChange={(event) => farm.setCropId(event.target.value)}
            >
              <option value="">No crop selected</option>
              {farm.cropsForLocation.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.crop_name}
                  {crop.variety ? ` (${crop.variety})` : ""}
                </option>
              ))}
            </select>
          </label>
        </header>
        <main className="px-4 py-6 md:px-8">
          {farm.error ? <div className="mb-4"><Notice>{farm.error}</Notice></div> : null}
          <Outlet />
        </main>
      </div>
    </div>
  )
}
