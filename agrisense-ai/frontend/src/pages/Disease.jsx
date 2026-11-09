import { useEffect, useState } from "react"
import { useFarm } from "../context/FarmContext"
import { api, errorMessage, reading } from "../services/api"
import { AdvisoryView } from "../components/AdvisoryView"
import { Button, Card, Empty, Field, Notice, PageHeader, inputClass } from "../components/ui"

export default function Disease() {
  const farm = useFarm()
  const [symptoms, setSymptoms] = useState("")
  const [weather, setWeather] = useState(null)
  const [advisory, setAdvisory] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function loadWeather() {
      if (!farm.crop?.location_id) {
        setWeather(null)
        return
      }
      try {
        const response = await api.get("/api/weather/current", {
          params: { location_id: farm.crop.location_id, crop_id: farm.crop.id },
        })
        if (!cancelled) setWeather(response.data)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err))
      }
    }
    loadWeather()
    return () => {
      cancelled = true
    }
  }, [farm.crop])

  async function generate(event) {
    event.preventDefault()
    if (!farm.cropId) return
    setLoading(true)
    setError("")
    setAdvisory(null)
    try {
      const response = await api.post("/api/advisory/disease", {
        crop_id: farm.cropId,
        symptoms,
      })
      setAdvisory(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Disease Advisory"
        text="Weather can suggest environmental risk. Symptoms can suggest a concern. Neither confirms a diagnosis."
      />
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      {!farm.crop ? <Empty title="Select a crop" text="Use the crop menu in the header." /> : null}
      {farm.crop ? (
        <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <Card>
            <h2 className="font-display text-xl">{farm.crop.crop_name}</h2>
            <p className="text-sm text-cocoa">{farm.crop.location_name} · {farm.crop.growth_stage}</p>
            <div className="mt-4 space-y-1 text-sm">
              <p>Temperature: {reading(weather?.temperature, "°C") || "Unavailable"}</p>
              <p>Humidity: {reading(weather?.humidity, "%") || "Unavailable"}</p>
              <p>Rainfall: {reading(weather?.rainfall, "mm") || "Unavailable"}</p>
              <p>Condition: {weather?.conditions || "Unavailable"}</p>
              {weather?.stale ? <p className="font-semibold text-rust">Weather reading is stale.</p> : null}
            </div>
            <form className="mt-5 space-y-3" onSubmit={generate}>
              <Field label="Reported symptoms">
                <textarea
                  className={inputClass}
                  rows="5"
                  placeholder="Leave blank to review environmental risk only."
                  value={symptoms}
                  onChange={(event) => setSymptoms(event.target.value)}
                />
              </Field>
              <Button type="submit" disabled={loading}>{loading ? "Reviewing conditions…" : "Generate advisory"}</Button>
            </form>
          </Card>
          <Card>
            {advisory ? <AdvisoryView record={advisory} /> : <Empty title="No advisory yet" text="The result will separate environmental risk from symptom-based suspicion." />}
          </Card>
        </div>
      ) : null}
    </div>
  )
}
