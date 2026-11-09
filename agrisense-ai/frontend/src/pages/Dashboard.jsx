import { useEffect, useState } from "react"
import { CloudRain, Droplets, Thermometer, Wind } from "lucide-react"
import { Link } from "react-router-dom"
import { useFarm } from "../context/FarmContext"
import { api, errorMessage, formatWhen, labelFor, reading } from "../services/api"
import { AdvisoryView } from "../components/AdvisoryView"
import { Badge, Button, Card, Empty, Field, Loading, Notice, PageHeader, inputClass, severityTone } from "../components/ui"

export default function Dashboard() {
  const farm = useFarm()
  const [weather, setWeather] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [history, setHistory] = useState([])
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [soil, setSoil] = useState({ soil_moisture: "", soil_ph: "" })
  const [saving, setSaving] = useState(false)
  const [note, setNote] = useState("")

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!farm.locationId) {
        setWeather(null)
        setForecast(null)
        setAlerts([])
        setRecords([])
        return
      }
      setLoading(true)
      setError("")
      try {
        const params = { location_id: farm.locationId }
        const [current, coming, alertRows, environmentRows, advisoryRows] = await Promise.all([
          api.get("/api/weather/current", { params: { ...params, crop_id: farm.cropId || undefined } }),
          api.get("/api/weather/forecast", { params }),
          api.get("/api/alerts", { params: { ...params, limit: 4 } }),
          api.get("/api/environment", { params: { ...params, limit: 4 } }),
          api.get("/api/advisory/history", { params: { crop_id: farm.cropId || undefined, limit: 3 } }),
        ])
        if (cancelled) return
        setWeather(current.data)
        setForecast(coming.data)
        setAlerts(alertRows.data)
        setRecords(environmentRows.data)
        setHistory(advisoryRows.data)
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
  }, [farm.locationId, farm.cropId])

  async function saveSoil(event) {
    event.preventDefault()
    setSaving(true)
    setNote("")
    try {
      await api.post("/api/environment", {
        location_id: farm.locationId,
        crop_id: farm.cropId || null,
        soil_moisture: soil.soil_moisture === "" ? null : Number(soil.soil_moisture),
        soil_ph: soil.soil_ph === "" ? null : Number(soil.soil_ph),
        source: "operator",
      })
      setNote("Soil reading saved.")
      setSoil({ soil_moisture: "", soil_ph: "" })
      const response = await api.get("/api/environment", {
        params: { location_id: farm.locationId, limit: 4 },
      })
      setRecords(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const maxTemp = Math.max(
    ...((forecast?.days || []).map((day) => day.temperature_max).filter((value) => value != null)),
    1,
  )

  return (
    <div>
      <PageHeader
        title="Dashboard"
        text="Current conditions, the selected crop, and the latest advisories. Missing readings stay blank."
      />
      {!farm.locationId ? (
        <Empty
          title="Choose a location"
          text="Add a location in Crop Management, then select it in the header to load weather."
        />
      ) : null}
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      {loading ? <Loading label="Loading field conditions" /> : null}

      {weather ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-cocoa">Weather</p>
                <h2 className="font-display text-2xl text-earth">{farm.location?.name}</h2>
                <p className="text-sm text-cocoa">
                  {farm.location?.district}, {farm.location?.state}
                </p>
              </div>
              <div className="text-right text-sm text-cocoa">
                <p>{weather.conditions || "Condition unavailable"}</p>
                <p>{formatWhen(weather.observation_time_ist || weather.fetched_at_ist)}</p>
                {weather.stale ? <p className="font-semibold text-rust">Stale cached reading</p> : null}
                {weather.from_cache && !weather.stale ? <p>Cached reading</p> : null}
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric icon={Thermometer} label="Temperature" value={reading(weather.temperature, "°C")} />
              <Metric icon={Droplets} label="Humidity" value={reading(weather.humidity, "%")} />
              <Metric icon={CloudRain} label="Rainfall" value={reading(weather.rainfall, "mm")} />
              <Metric icon={Wind} label="Wind" value={reading(weather.wind_speed, "km/h")} />
            </div>
            <p className="mt-3 text-sm text-cocoa">
              Rain probability: {reading(weather.precipitation_probability, "%") || "Unavailable"}
            </p>
            {weather.unavailable_fields?.length ? (
              <p className="mt-2 text-sm text-rust">
                Unavailable: {weather.unavailable_fields.join(", ")}
              </p>
            ) : null}
            {weather.snapshot_note ? <p className="mt-2 text-sm text-cocoa">{weather.snapshot_note}</p> : null}
          </Card>
          <Card>
            <h2 className="font-display text-xl text-earth">Active crop</h2>
            {farm.crop ? (
              <div className="mt-3 space-y-2 text-sm">
                <p className="text-lg font-semibold">{farm.crop.crop_name}</p>
                <p>Stage: {labelFor(farm.crop.growth_stage)}</p>
                <p>Soil: {farm.crop.soil_type}{farm.crop.soil_ph != null ? ` · pH ${farm.crop.soil_ph}` : ""}</p>
                <p>Irrigation: {farm.crop.irrigation_method}</p>
                <p>Sown: {farm.crop.sowing_date}</p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-cocoa">Select a crop in the header, or add one in Crop Management.</p>
            )}
            <Link to="/crops" className="mt-4 inline-block text-sm font-semibold text-bark underline">
              Manage crops
            </Link>
          </Card>
        </div>
      ) : null}

      {forecast?.days?.length ? (
        <Card className="mt-4">
          <h2 className="font-display text-xl text-earth">Three-day forecast</h2>
          <div className="mt-4 flex items-end gap-3">
            {forecast.days.map((day) => {
              const height = day.temperature_max == null ? 8 : Math.max(16, (day.temperature_max / maxTemp) * 96)
              return (
                <div key={day.date} className="flex flex-1 flex-col items-center">
                  <div className="flex h-28 w-full items-end">
                    <div className="w-full rounded-t-lg bg-sage" style={{ height }} title="Daily maximum temperature" />
                  </div>
                  <p className="mt-2 text-sm font-semibold">{day.temperature_max == null ? "—" : `${day.temperature_max}°`}</p>
                  <p className="text-xs text-cocoa">{day.date}</p>
                  <p className="text-xs text-cocoa">{day.precipitation_sum == null ? "Rain n/a" : `${day.precipitation_sum} mm`}</p>
                </div>
              )
            })}
          </div>
          {forecast.unavailable_fields?.length ? (
            <p className="mt-3 text-sm text-cocoa">Some forecast fields were not returned: {forecast.unavailable_fields.join(", ")}</p>
          ) : null}
          {forecast.stale ? <p className="mt-2 text-sm font-semibold text-rust">Forecast is stale.</p> : null}
        </Card>
      ) : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-xl text-earth">Alerts</h2>
            <Link to="/alerts" className="text-sm font-semibold text-bark underline">View all</Link>
          </div>
          {alerts.length ? (
            <ul className="space-y-2">
              {alerts.map((alert) => (
                <li key={alert.id} className="rounded-xl bg-cream px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold">{alert.title}</p>
                    <Badge tone={severityTone(alert.severity)}>{labelFor(alert.severity)}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-bark">{alert.description}</p>
                </li>
              ))}
            </ul>
          ) : (
            <Empty title="No alerts for this location" text="Run a check from the Alerts page after weather is loaded." />
          )}
        </Card>
        <Card>
          <h2 className="font-display text-xl text-earth">Record soil moisture</h2>
          <p className="mt-1 text-sm text-cocoa">Only enter a value you measured. Leave a field blank if you do not have it.</p>
          <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={saveSoil}>
            <Field label="Soil moisture">
              <input className={inputClass} value={soil.soil_moisture} onChange={(event) => setSoil({ ...soil, soil_moisture: event.target.value })} inputMode="decimal" />
            </Field>
            <Field label="Soil pH">
              <input className={inputClass} value={soil.soil_ph} onChange={(event) => setSoil({ ...soil, soil_ph: event.target.value })} inputMode="decimal" />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={!farm.locationId || saving}>{saving ? "Saving…" : "Save reading"}</Button>
            </div>
          </form>
          {note ? <p className="mt-3 text-sm text-bark">{note}</p> : null}
          <ul className="mt-4 space-y-2 text-sm">
            {records.map((record) => (
              <li key={record.id} className="flex justify-between gap-3 text-cocoa">
                <span>{record.source}</span>
                <span>
                  Moisture {record.soil_moisture ?? "—"} · pH {record.soil_ph ?? "—"} · {formatWhen(record.recorded_at_ist || record.recorded_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-4">
        <h2 className="font-display text-xl text-earth">Recent advisories</h2>
        <div className="mt-4 space-y-6">
          {history.length ? history.map((record) => <AdvisoryView key={record.id} record={record} />) : (
            <Empty title="No advisories yet" text="Generate one from Crop Management or Disease Advisory." />
          )}
        </div>
      </Card>
    </div>
  )
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-2xl bg-cream px-3 py-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-cocoa">
        <Icon size={16} />
        {label}
      </div>
      <p className="mt-2 font-display text-2xl text-earth">{value || "Unavailable"}</p>
    </div>
  )
}
