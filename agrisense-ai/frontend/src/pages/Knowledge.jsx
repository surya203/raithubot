import { useEffect, useState } from "react"
import { api, errorMessage, formatWhen } from "../services/api"
import { Badge, Button, Card, Empty, Field, Loading, Notice, PageHeader, inputClass } from "../components/ui"

const empty = {
  title: "",
  source_organization: "",
  document_url: "",
  crop: "",
  disease: "",
  region: "",
  publication_date: "",
}

export default function Knowledge() {
  const [documents, setDocuments] = useState([])
  const [form, setForm] = useState(empty)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  async function load() {
    setLoading(true)
    try {
      const response = await api.get("/api/knowledge")
      setDocuments(response.data)
      setError("")
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function upload(event) {
    event.preventDefault()
    if (!file) return
    setSaving(true)
    setError("")
    const body = new FormData()
    body.append("file", file)
    Object.entries(form).forEach(([key, value]) => {
      if (value) body.append(key, value)
    })
    try {
      await api.post("/api/knowledge/upload", body, { timeout: 180000 })
      setForm(empty)
      setFile(null)
      event.target.reset()
      await load()
    } catch (err) {
      setError(errorMessage(err))
      await load()
    } finally {
      setSaving(false)
    }
  }

  async function remove(document) {
    if (!window.confirm(`Delete ${document.title}? Chunks for this document are removed. Past advisories keep their saved citations.`)) return
    try {
      await api.delete(`/api/knowledge/${document.id}`)
      await load()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        text="Upload ICAR, IMD, KVK, university, or extension documents. The assistant cites only indexed text."
      />
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <h2 className="font-display text-xl">Upload a document</h2>
          <form className="mt-4 space-y-3" onSubmit={upload}>
            <Field label="File">
              <input className={inputClass} type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" required onChange={(event) => setFile(event.target.files?.[0] || null)} />
            </Field>
            <Field label="Title"><input className={inputClass} required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
            <Field label="Source organization"><input className={inputClass} required value={form.source_organization} onChange={(event) => setForm({ ...form, source_organization: event.target.value })} /></Field>
            <Field label="Document URL"><input className={inputClass} value={form.document_url} onChange={(event) => setForm({ ...form, document_url: event.target.value })} /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Crop"><input className={inputClass} value={form.crop} onChange={(event) => setForm({ ...form, crop: event.target.value })} /></Field>
              <Field label="Disease"><input className={inputClass} value={form.disease} onChange={(event) => setForm({ ...form, disease: event.target.value })} /></Field>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Region"><input className={inputClass} value={form.region} onChange={(event) => setForm({ ...form, region: event.target.value })} /></Field>
              <Field label="Publication date"><input type="date" className={inputClass} value={form.publication_date} onChange={(event) => setForm({ ...form, publication_date: event.target.value })} /></Field>
            </div>
            <Button type="submit" disabled={saving}>{saving ? "Indexing…" : "Upload and index"}</Button>
          </form>
        </Card>
        <div className="space-y-3">
          {loading ? <Loading label="Loading documents" /> : null}
          {!loading && !documents.length ? <Empty title="No documents indexed" text="PDF, plain text, and Markdown files can be uploaded." /> : null}
          {documents.map((document) => (
            <Card key={document.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-display text-xl">{document.title}</h2>
                  <p className="text-sm text-cocoa">{document.source_organization}</p>
                  <p className="mt-2 text-sm">
                    {[document.crop, document.disease, document.region].filter(Boolean).join(" · ") || "No crop or region tags"}
                  </p>
                  <p className="mt-1 text-xs text-cocoa">{formatWhen(document.created_at_ist || document.created_at)}</p>
                  {document.ingestion_error ? <p className="mt-2 text-sm text-rust">{document.ingestion_error}</p> : null}
                </div>
                <div className="flex flex-col items-end gap-2">
                  <Badge tone={document.ingestion_status === "ready" ? "sage" : document.ingestion_status === "failed" ? "rust" : "gold"}>
                    {document.ingestion_status}
                  </Badge>
                  <Button variant="danger" onClick={() => remove(document)}>Delete</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
