import axios from "axios"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 120000,
})

export function errorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message).filter(Boolean).join(" ")
  }
  if (!error?.response) return "The API could not be reached. Start the backend, then refresh."
  return "The request failed."
}

export function reading(value, unit) {
  if (value === null || value === undefined || value === "") return null
  return unit ? `${value} ${unit}` : String(value)
}

export function formatWhen(value) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(date)
}

export function istDayStart(date) {
  return date ? `${date}T00:00:00+05:30` : undefined
}

export function istDayEnd(date) {
  return date ? `${date}T23:59:59+05:30` : undefined
}

export const GROWTH_STAGES = [
  "seedling",
  "vegetative",
  "flowering",
  "fruiting",
  "maturity",
  "harvest",
]

export const ADVISORY_TYPES = [
  { value: "crop_management", label: "Crop management" },
  { value: "disease_prevention", label: "Disease prevention" },
  { value: "chatbot", label: "AI assistant" },
  { value: "alert_explanation", label: "Alert explanation" },
]

export function labelFor(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
