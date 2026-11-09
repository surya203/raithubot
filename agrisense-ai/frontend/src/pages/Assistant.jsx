import { useState } from "react"
import { Send } from "lucide-react"
import { useFarm } from "../context/FarmContext"
import { api, errorMessage } from "../services/api"
import { Button, Card, Empty, Notice, PageHeader, inputClass } from "../components/ui"

const prompts = [
  "What should I watch at this growth stage?",
  "How should I think about irrigation after rain?",
  "What field checks help when the weather is humid?",
]

export default function Assistant() {
  const farm = useFarm()
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState("")
  const [error, setError] = useState("")
  const [sending, setSending] = useState(false)

  async function send(text) {
    const message = (text || draft).trim()
    if (!message) return
    setDraft("")
    setError("")
    setSending(true)
    setMessages((current) => [...current, { role: "user", message }])
    try {
      const response = await api.post("/api/chat", {
        message,
        conversation_id: conversationId,
        crop_id: farm.cropId || null,
      })
      setConversationId(response.data.conversation_id)
      const answer = response.data.answer
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          message: answer.answer,
          references: answer.references || [],
          limitations: answer.limitations || [],
          missing: answer.missing_information || [],
        },
      ])
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="AI Assistant"
        text={farm.crop ? `Using ${farm.crop.crop_name} and its location when weather is available.` : "Select a crop to include field context, or ask a general question."}
        action={<Button variant="secondary" onClick={() => { setConversationId(null); setMessages([]) }}>New conversation</Button>}
      />
      {error ? <div className="mb-4"><Notice>{error}</Notice></div> : null}
      <Card className="flex min-h-[32rem] flex-col">
        <div className="flex-1 space-y-4">
          {messages.length ? messages.map((item, index) => (
            <div key={`${item.role}-${index}`} className={item.role === "user" ? "ml-auto max-w-2xl" : "max-w-2xl"}>
              <div className={`rounded-2xl px-4 py-3 ${item.role === "user" ? "bg-earth text-cream" : "bg-cream text-bark"}`}>
                <p className="whitespace-pre-wrap">{item.message}</p>
              </div>
              {item.references?.length ? (
                <ul className="mt-2 space-y-1 text-sm text-cocoa">
                  {item.references.map((reference) => (
                    <li key={reference.title}>
                      {reference.title}{reference.source_organization ? ` · ${reference.source_organization}` : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
              {item.limitations?.length ? <p className="mt-2 text-sm text-cocoa">{item.limitations.join(" ")}</p> : null}
            </div>
          )) : (
            <Empty title="Ask about the crop, weather, soil, or prevention." text="Answers cite knowledge documents only when one was retrieved." />
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {prompts.map((prompt) => (
            <button key={prompt} className="rounded-full border border-sand bg-white px-3 py-1 text-sm text-bark" onClick={() => send(prompt)} disabled={sending}>
              {prompt}
            </button>
          ))}
        </div>
        <form className="mt-3 flex gap-2" onSubmit={(event) => { event.preventDefault(); send() }}>
          <input className={inputClass} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask an agricultural question" />
          <Button type="submit" disabled={sending || !draft.trim()} aria-label="Send">
            <Send size={16} />
            {sending ? "Thinking…" : "Send"}
          </Button>
        </form>
      </Card>
    </div>
  )
}
