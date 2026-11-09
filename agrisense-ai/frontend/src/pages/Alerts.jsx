import { useEffect, useState } from "react"
import { useFarm } from "../context/FarmContext"
import { api, errorMessage, formatWhen, labelFor } from "../services/api"
import { Badge, Button, Card, Empty, Loading, Notice, PageHeader, severityTone } from "../components/ui"

export default function Alerts() {
  const farm = useFarm()
  const [alerts, setAlerts] = useState([])
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [checking, setChecking] = useState(false)

  async function load() {
    setLoading(true)
    setError("")
    try {
      const response = await api.get("/api/alerts", {
        params: {
          location_id: farm.locationId || undefined,
          crop_id: farm.cropId || undefined,
          unread_only: unreadOnly,
          limit: 100,
        },
      })
      setAlerts(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [farm.locationId, farm.cropId, unreadOnly])

  async function markRead(alert) {
    try {
      const response = await api.patch(`/api/alerts/${alert.id}/read`)
      setAlerts((current) => current.map((item) => (item.id === alert.id ? response.data : item)))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function evaluate() {
    if (!farm.locationId) return
    setChecking(true)
    setError("")
    try {
      await api.post("/api/alerts/evaluate", {
        location_id: farm.locationId,
        crop_id: farm.cropId || null,
      })
      await load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Alerts"
        text="Rules use internal thresholds. They are awareness checks, not official warnings or disease predictions."
        action={<Button onClick={evaluate} disabled={!farm.locationId || checking}>{checking ? "Checking…" : "Check conditions"}</Button>}
      />
      <label className="mb-4 flex items-center gap-2 text-sm font-semibold">
        <input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} />
        Unread only
      </label>
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      {loading ? <Loading label="Loading alerts" /> : null}
      {!loading && !alerts.length ? <Empty title="No alerts" text="Select a location and check conditions, or wait until a rule matches." /> : null}
      <div className="space-y-3">
        {alerts.map((alert) => (
          <Card key={alert.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-xl">{alert.title}</h2>
                  <Badge tone={severityTone(alert.severity)}>{labelFor(alert.severity)}</Badge>
                  <Badge>{labelFor(alert.category)}</Badge>
                  {!alert.is_read ? <Badge tone="gold">Unread</Badge> : null}
                </div>
                <p className="mt-2 text-sm text-bark">{alert.description}</p>
                <p className="mt-2 text-xs text-cocoa">{formatWhen(alert.created_at_ist || alert.created_at)}</p>
              </div>
              {!alert.is_read ? <Button variant="secondary" onClick={() => markRead(alert)}>Mark read</Button> : null}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
