import { labelFor, formatWhen } from "../services/api"
import { Badge, Card, riskTone } from "./ui"

export function AdvisoryView({ record }) {
  const body = record?.advisory_response || {}
  const evidence = body.evidence || body.references || []
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={riskTone(body.risk_level)}>{labelFor(body.risk_level || "unspecified")}</Badge>
        <Badge>{labelFor(record.advisory_type)}</Badge>
        {body.disease_status ? <Badge tone="sand">{labelFor(body.disease_status)}</Badge> : null}
        <span className="text-sm text-cocoa">{formatWhen(record.created_at_ist || record.created_at)}</span>
      </div>
      <p className="font-display text-xl text-earth">
        {body.crop || "Advisory"}
        {body.growth_stage ? ` · ${labelFor(body.growth_stage)}` : ""}
      </p>
      <AdviceList title="Observations" items={body.observations} />
      <AdviceList title="Possible concerns" items={body.possible_concerns} />
      <AdviceList title="Recommendations" items={body.recommendations} />
      {body.answer ? (
        <Card>
          <h3 className="font-semibold text-earth">Answer</h3>
          <p className="mt-2 whitespace-pre-wrap text-bark">{body.answer}</p>
        </Card>
      ) : null}
      {evidence.length ? (
        <div>
          <h3 className="mb-2 font-semibold text-earth">Sources</h3>
          <div className="space-y-2">
            {evidence.map((item, index) => (
              <Card key={`${item.title}-${index}`} className="p-4">
                <p className="font-semibold text-earth">{item.title}</p>
                <p className="text-sm text-cocoa">{item.source_organization || "Source not named"}</p>
                {item.excerpt ? <p className="mt-2 text-sm text-bark">{item.excerpt}</p> : null}
              </Card>
            ))}
          </div>
        </div>
      ) : null}
      <AdviceList title="Missing information" items={body.missing_information} />
      <AdviceList title="Limitations" items={body.limitations} />
    </div>
  )
}

function AdviceList({ title, items }) {
  if (!items?.length) return null
  return (
    <div>
      <h3 className="mb-2 font-semibold text-earth">{title}</h3>
      <ul className="space-y-1.5 text-sm text-bark">
        {items.map((item) => (
          <li key={item} className="rounded-xl bg-cream px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
