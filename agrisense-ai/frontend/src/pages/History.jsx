import { useEffect, useState } from "react"
import { useFarm } from "../context/FarmContext"
import { ADVISORY_TYPES, api, errorMessage, formatWhen, istDayEnd, istDayStart, labelFor } from "../services/api"
import { AdvisoryView } from "../components/AdvisoryView"
import { Button, Card, Empty, Field, Loading, Notice, PageHeader, inputClass } from "../components/ui"

export default function History() {
  const farm = useFarm()
  const [rows, setRows] = useState([])
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ advisory_type: "", date_from: "", date_to: "" })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError("")
      try {
        const response = await api.get("/api/advisory/history", {
          params: {
            crop_id: farm.cropId || undefined,
            advisory_type: filters.advisory_type || undefined,
            date_from: istDayStart(filters.date_from),
            date_to: istDayEnd(filters.date_to),
            limit: 100,
          },
        })
        if (cancelled) return
        setRows(response.data)
        setSelected(response.data[0] || null)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [farm.cropId, filters])

  return (
    <div>
      <PageHeader title="Advisory History" text="Earlier crop advice, disease reviews, and assistant replies for the selected crop." />
      <Card className="mb-4">
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Type">
            <select className={inputClass} value={filters.advisory_type} onChange={(event) => setFilters({ ...filters, advisory_type: event.target.value })}>
              <option value="">All types</option>
              {ADVISORY_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
          </Field>
          <Field label="From"><input type="date" className={inputClass} value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} /></Field>
          <Field label="To"><input type="date" className={inputClass} value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} /></Field>
        </div>
        <Button className="mt-3" variant="secondary" onClick={() => setFilters({ advisory_type: "", date_from: "", date_to: "" })}>Clear filters</Button>
      </Card>
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      {loading ? <Loading label="Loading history" /> : null}
      {!loading && !rows.length ? <Empty title="No matching advisories" text="Generate an advisory, or clear the crop and date filters." /> : null}
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-2">
          {rows.map((row) => (
            <button key={row.id} className={`w-full rounded-2xl border px-4 py-3 text-left ${selected?.id === row.id ? "border-earth bg-sand/50" : "border-sand bg-paper"}`} onClick={() => setSelected(row)}>
              <p className="font-semibold">{labelFor(row.advisory_type)}</p>
              <p className="text-sm text-cocoa">{row.advisory_response?.crop || "General"} · {formatWhen(row.created_at_ist || row.created_at)}</p>
            </button>
          ))}
        </div>
        <Card>{selected ? <AdvisoryView record={selected} /> : null}</Card>
      </div>
    </div>
  )
}
