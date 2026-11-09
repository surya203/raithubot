import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { api, errorMessage } from "../services/api"

const FarmContext = createContext(null)

export function FarmProvider({ children }) {
  const [locations, setLocations] = useState([])
  const [crops, setCrops] = useState([])
  const [locationId, setLocationId] = useState(() => localStorage.getItem("agrisense.locationId") || "")
  const [cropId, setCropId] = useState(() => localStorage.getItem("agrisense.cropId") || "")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [locationResponse, cropResponse] = await Promise.all([
        api.get("/api/locations"),
        api.get("/api/crops"),
      ])
      setLocations(locationResponse.data)
      setCrops(cropResponse.data)
      setError("")
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    localStorage.setItem("agrisense.locationId", locationId)
  }, [locationId])

  useEffect(() => {
    localStorage.setItem("agrisense.cropId", cropId)
  }, [cropId])

  useEffect(() => {
    if (!locations.length) return
    if (locationId && !locations.some((item) => item.id === locationId)) {
      setLocationId("")
    }
  }, [locations, locationId])

  useEffect(() => {
    if (cropId && !crops.some((item) => item.id === cropId)) {
      setCropId("")
    }
  }, [crops, cropId])

  const value = useMemo(() => {
    const location = locations.find((item) => item.id === locationId) || null
    const crop = crops.find((item) => item.id === cropId) || null
    const cropsForLocation = locationId
      ? crops.filter((item) => item.location_id === locationId)
      : crops
    return {
      locations,
      crops,
      cropsForLocation,
      location,
      crop,
      locationId,
      cropId,
      setLocationId,
      setCropId,
      loading,
      error,
      refresh,
    }
  }, [locations, crops, locationId, cropId, loading, error, refresh])

  return <FarmContext.Provider value={value}>{children}</FarmContext.Provider>
}

export function useFarm() {
  const value = useContext(FarmContext)
  if (!value) throw new Error("useFarm must be used inside FarmProvider")
  return value
}
