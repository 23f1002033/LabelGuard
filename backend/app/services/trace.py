from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import AnalysisTrace, TraceEvent


class TraceRecorder:
    def __init__(self, system: str, case_id: str | None = None):
        self.trace = AnalysisTrace(system=system, case_id=case_id)

    def log(
        self,
        agent: str,
        step: str,
        result: str = "",
        decision: str = "",
        tool_used: str = "",
        input_reference: str = "",
        duration_ms: int | None = None,
    ) -> None:
        self.trace.events.append(
            TraceEvent(
                timestamp=datetime.now(timezone.utc),
                agent=agent,
                step=step,
                input_reference=input_reference,
                tool_used=tool_used,
                result=result,
                decision=decision,
                duration_ms=duration_ms,
            )
        )

    def save(self) -> None:
        if not self.trace.case_id:
            return
        settings.trace_dir.mkdir(parents=True, exist_ok=True)
        path = settings.trace_dir / f"{self.trace.system}_{self.trace.case_id}.json"
        path.write_text(self.trace.model_dump_json(indent=2, exclude_none=True))
