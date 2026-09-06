-- ao/reconfx_ledger.lua
Steps = Steps or {}
Residual = Residual or 0
Decisions = Decisions or {}

Handlers.add("RecordStep",
  Handlers.utils.hasMatchingTag("Action", "RecordStep"),
  function(msg)
    local d = json.decode(msg.Data)
    table.insert(Steps, {
      act            = d.act,                -- "EXCAVATION" | "INVESTIGATION"
      factor_id      = d.factor_id,
      classification = d.classification,
      transaction_ids= d.transaction_ids,
      evidence_refs  = d.evidence_refs,
      factor_usd     = d.factor_usd,
      residual_before= Residual,
      residual_after = d.new_residual,
      accepted       = d.accepted,
      rejection_reason = d.rejection_reason,
      ts             = msg.Timestamp
    })
    Residual = d.new_residual
    ao.send({ Target = msg.From, Data = json.encode({ ok = true, step = #Steps }) })
  end)

Handlers.add("RecordDecision",
  Handlers.utils.hasMatchingTag("Action", "RecordDecision"),
  function(msg)
    local d = json.decode(msg.Data)
    table.insert(Decisions, {
      decision_type = d.decision_type,       -- APPROVE_TRUEUP | APPROVE_COLLECTION | REJECT
      actor         = d.actor,
      payload_hash  = d.payload_hash,
      ts            = msg.Timestamp
    })
    ao.send({ Target = msg.From, Data = json.encode({ ok = true }) })
  end)

Handlers.add("GetLedger",
  Handlers.utils.hasMatchingTag("Action", "GetLedger"),
  function(msg)
    ao.send({ Target = msg.From,
              Data = json.encode({ steps = Steps, decisions = Decisions,
                                   residual = Residual }) })
  end)
