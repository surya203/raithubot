export function Button({ variant = "primary", className = "", type = "button", ...props }) {
  const styles = {
    primary: "bg-sage text-earth hover:bg-[#868c4c]",
    secondary: "border border-sand bg-white text-earth hover:bg-cream",
    dark: "bg-earth text-cream hover:bg-bark",
    danger: "border border-sand bg-white text-rust hover:bg-[#f8efe8]",
  }
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`}
      {...props}
    />
  )
}

export const inputClass =
  "w-full rounded-xl border border-sand bg-white px-3 py-2 text-earth outline-none placeholder:text-taupe focus:border-sage focus:ring-2 focus:ring-sage/30"

export function Field({ label, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold text-bark">{label}</span>
      {children}
    </label>
  )
}

export function Card({ className = "", children }) {
  return (
    <section className={`rounded-2xl border border-sand/80 bg-paper p-5 shadow-card ${className}`}>
      {children}
    </section>
  )
}

export function PageHeader({ title, text, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-3xl font-semibold text-earth">{title}</h1>
        {text ? <p className="mt-1 max-w-2xl text-cocoa">{text}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function Loading({ label = "Loading" }) {
  return <p className="text-sm font-medium text-cocoa">{label}…</p>
}

export function Empty({ title, text }) {
  return (
    <div className="rounded-2xl border border-dashed border-sand bg-cream/70 px-4 py-8 text-center">
      <p className="font-semibold text-earth">{title}</p>
      {text ? <p className="mt-1 text-sm text-cocoa">{text}</p> : null}
    </div>
  )
}

export function Notice({ tone = "error", children }) {
  const styles = {
    error: "border-rust/30 bg-[#f8efe8] text-rust",
    warn: "border-amber/40 bg-[#fbf3e4] text-bark",
    ok: "border-sage/40 bg-[#f3f5ea] text-bark",
  }
  return <div className={`rounded-xl border px-4 py-3 text-sm ${styles[tone]}`}>{children}</div>
}

export function Badge({ children, tone = "sage" }) {
  const styles = {
    sage: "bg-[#eef1df] text-bark",
    gold: "bg-[#f8ead0] text-bark",
    rust: "bg-[#f3e4d8] text-rust",
    sand: "bg-sand/70 text-bark",
  }
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${styles[tone]}`}>
      {children}
    </span>
  )
}

export function riskTone(level) {
  if (level === "high") return "rust"
  if (level === "moderate") return "gold"
  if (level === "low") return "sage"
  return "sand"
}

export function severityTone(level) {
  if (level === "high") return "rust"
  if (level === "moderate") return "gold"
  if (level === "low") return "sage"
  return "sand"
}
