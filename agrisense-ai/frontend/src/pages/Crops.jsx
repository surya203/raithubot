import { useEffect, useState } from "react"
import { useFarm } from "../context/FarmContext"
import { api, errorMessage, GROWTH_STAGES, labelFor } from "../services/api"
import { AdvisoryView } from "../components/AdvisoryView"
import { Button, Card, Empty, Field, Notice, PageHeader, inputClass } from "../components/ui"

const emptyLocation = { name: "", state: "", district: "", latitude: "", longitude: "" }
const emptyCrop = {
  location_id: "",
  crop_name: "",
  variety: "",
  sowing_date: "",
  expected_harvest_date: "",
  growth_stage: "vegetative",
  soil_type: "",
  soil_ph: "",
  nitrogen: "",
  phosphorus: "",
  potassium: "",
  irrigation_method: "",
  observations: "",
}

export default function Crops() {
  const farm = useFarm()
  const [locationForm, setLocationForm] = useState(emptyLocation)
  const [cropForm, setCropForm] = useState({ ...emptyCrop, location_id: farm.locationId })
  const [editingId, setEditingId] = useState("")
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const [advisory, setAdvisory] = useState(null)
  const [workingId, setWorkingId] = useState("")

  useEffect(() => {
    if (!editingId && farm.locationId) {
      setCropForm((current) => ({ ...current, location_id: current.location_id || farm.locationId }))
    }
  }, [farm.locationId, editingId])

  function editCrop(crop) {
    setEditingId(crop.id)
    setCropForm({
      location_id: crop.location_id,
      crop_name: crop.crop_name,
      variety: crop.variety || "",
      sowing_date: crop.sowing_date,
      expected_harvest_date: crop.expected_harvest_date || "",
      growth_stage: crop.growth_stage,
      soil_type: crop.soil_type,
      soil_ph: crop.soil_ph ?? "",
      nitrogen: crop.nitrogen ?? "",
      phosphorus: crop.phosphorus ?? "",
      potassium: crop.potassium ?? "",
      irrigation_method: crop.irrigation_method,
      observations: crop.observations || "",
    })
  }

  async function saveLocation(event) {
    event.preventDefault()
    setSaving(true)
    setError("")
    try {
      const response = await api.post("/api/locations", {
        ...locationForm,
        latitude: Number(locationForm.latitude),
        longitude: Number(locationForm.longitude),
      })
      setLocationForm(emptyLocation)
      await farm.refresh()
      farm.setLocationId(response.data.id)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function saveCrop(event) {
    event.preventDefault()
    setSaving(true)
    setError("")
    const payload = {
      ...cropForm,
      variety: cropForm.variety || null,
      expected_harvest_date: cropForm.expected_harvest_date || null,
      soil_ph: blankNumber(cropForm.soil_ph),
      nitrogen: blankNumber(cropForm.nitrogen),
      phosphorus: blankNumber(cropForm.phosphorus),
      potassium: blankNumber(cropForm.potassium),
      observations: cropForm.observations || null,
    }
    try {
      if (editingId) await api.put(`/api/crops/${editingId}`, payload)
      else {
        const response = await api.post("/api/crops", payload)
        farm.setCropId(response.data.id)
      }
      setEditingId("")
      setCropForm({ ...emptyCrop, location_id: farm.locationId })
      await farm.refresh()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function removeCrop(crop) {
    if (!window.confirm(`Delete ${crop.crop_name}? Past advisories stay in history.`)) return
    setError("")
    try {
      await api.delete(`/api/crops/${crop.id}`)
      if (farm.cropId === crop.id) farm.setCropId("")
      await farm.refresh()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function generate(crop) {
    setWorkingId(crop.id)
    setError("")
    setAdvisory(null)
    try {
      const response = await api.post("/api/advisory/crop", { crop_id: crop.id })
      setAdvisory(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setWorkingId("")
    }
  }

  return (
    <div>
      <PageHeader title="Crop Management" text="Keep location, crop stage, and soil notes current before asking for advice." />
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-3">
          {farm.crops.length ? farm.crops.map((crop) => (
            <Card key={crop.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-display text-xl">{crop.crop_name}{crop.variety ? ` · ${crop.variety}` : ""}</h2>
                  <p className="text-sm text-cocoa">{crop.location_name || "Location"} · {labelFor(crop.growth_stage)}</p>
                  <p className="mt-2 text-sm">Sown {crop.sowing_date} · {crop.soil_type} · {crop.irrigation_method}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => editCrop(crop)}>Edit</Button>
                  <Button onClick={() => generate(crop)} disabled={workingId === crop.id}>
                    {workingId === crop.id ? "Preparing…" : "Advisory"}
                  </Button>
                  <Button variant="danger" onClick={() => removeCrop(crop)}>Delete</Button>
                </div>
              </div>
            </Card>
          )) : <Empty title="No crops yet" text="Add a location and a crop with the forms." />}
          {advisory ? <Card><AdvisoryView record={advisory} /></Card> : null}
        </div>
        <div className="space-y-4">
          <Card>
            <h2 className="font-display text-xl">Add location</h2>
            <form className="mt-4 space-y-3" onSubmit={saveLocation}>
              <Field label="Name"><input className={inputClass} required value={locationForm.name} onChange={(event) => setLocationForm({ ...locationForm, name: event.target.value })} /></Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="State"><input className={inputClass} required value={locationForm.state} onChange={(event) => setLocationForm({ ...locationForm, state: event.target.value })} /></Field>
                <Field label="District"><input className={inputClass} required value={locationForm.district} onChange={(event) => setLocationForm({ ...locationForm, district: event.target.value })} /></Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Latitude"><input className={inputClass} required inputMode="decimal" value={locationForm.latitude} onChange={(event) => setLocationForm({ ...locationForm, latitude: event.target.value })} /></Field>
                <Field label="Longitude"><input className={inputClass} required inputMode="decimal" value={locationForm.longitude} onChange={(event) => setLocationForm({ ...locationForm, longitude: event.target.value })} /></Field>
              </div>
              <Button type="submit" disabled={saving}>Save location</Button>
            </form>
          </Card>
          <Card>
            <h2 className="font-display text-xl">{editingId ? "Edit crop" : "Add crop"}</h2>
            <form className="mt-4 space-y-3" onSubmit={saveCrop}>
              <Field label="Location">
                <select className={inputClass} required value={cropForm.location_id} onChange={(event) => setCropForm({ ...cropForm, location_id: event.target.value })}>
                  <option value="">Select</option>
                  {farm.locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}
                </select>
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Crop name"><input className={inputClass} required value={cropForm.crop_name} onChange={(event) => setCropForm({ ...cropForm, crop_name: event.target.value })} /></Field>
                <Field label="Variety"><input className={inputClass} value={cropForm.variety} onChange={(event) => setCropForm({ ...cropForm, variety: event.target.value })} /></Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Sowing date"><input type="date" className={inputClass} required value={cropForm.sowing_date} onChange={(event) => setCropForm({ ...cropForm, sowing_date: event.target.value })} /></Field>
                <Field label="Expected harvest"><input type="date" className={inputClass} value={cropForm.expected_harvest_date} onChange={(event) => setCropForm({ ...cropForm, expected_harvest_date: event.target.value })} /></Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Growth stage">
                  <select className={inputClass} value={cropForm.growth_stage} onChange={(event) => setCropForm({ ...cropForm, growth_stage: event.target.value })}>
                    {GROWTH_STAGES.map((stage) => <option key={stage} value={stage}>{labelFor(stage)}</option>)}
                  </select>
                </Field>
                <Field label="Soil type"><input className={inputClass} required value={cropForm.soil_type} onChange={(event) => setCropForm({ ...cropForm, soil_type: event.target.value })} /></Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Irrigation"><input className={inputClass} required value={cropForm.irrigation_method} onChange={(event) => setCropForm({ ...cropForm, irrigation_method: event.target.value })} /></Field>
                <Field label="Soil pH"><input className={inputClass} inputMode="decimal" value={cropForm.soil_ph} onChange={(event) => setCropForm({ ...cropForm, soil_ph: event.target.value })} /></Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="N"><input className={inputClass} inputMode="decimal" value={cropForm.nitrogen} onChange={(event) => setCropForm({ ...cropForm, nitrogen: event.target.value })} /></Field>
                <Field label="P"><input className={inputClass} inputMode="decimal" value={cropForm.phosphorus} onChange={(event) => setCropForm({ ...cropForm, phosphorus: event.target.value })} /></Field>
                <Field label="K"><input className={inputClass} inputMode="decimal" value={cropForm.potassium} onChange={(event) => setCropForm({ ...cropForm, potassium: event.target.value })} /></Field>
              </div>
              <Field label="Observations"><textarea className={inputClass} rows="3" value={cropForm.observations} onChange={(event) => setCropForm({ ...cropForm, observations: event.target.value })} /></Field>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>{editingId ? "Update crop" : "Save crop"}</Button>
                {editingId ? <Button variant="secondary" onClick={() => { setEditingId(""); setCropForm({ ...emptyCrop, location_id: farm.locationId }) }}>Cancel</Button> : null}
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  )
}

function blankNumber(value) {
  return value === "" ? null : Number(value)
}
