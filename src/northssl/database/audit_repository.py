from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import AuditEvent
from northssl.database.models import AuditEventRecord
from northssl.database.session import create_session_factory, initialize_database


class AuditEventRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: NorthSSLSettings | None = None) -> AuditEventRepository:
        resolved_settings = settings or NorthSSLSettings()
        initialize_database(resolved_settings)
        return cls(create_session_factory(resolved_settings))

    def save(self, event: AuditEvent) -> AuditEvent:
        with self._session_factory() as session:
            record = AuditEventRecord(
                event_type=event.event_type,
                domain=event.domain,
                severity=event.severity,
                message=event.message,
                details_json=json.dumps(event.details, sort_keys=True),
                created_at=event.created_at,
            )
            session.add(record)
            session.commit()
            return event

    def list_recent(self, limit: int = 200) -> list[AuditEvent]:
        with self._session_factory() as session:
            records = session.scalars(
                select(AuditEventRecord).order_by(AuditEventRecord.created_at.desc()).limit(limit)
            ).all()
            return [self._to_event(record) for record in records]

    def _to_event(self, record: AuditEventRecord) -> AuditEvent:
        return AuditEvent(
            event_type=record.event_type,
            domain=record.domain,
            severity=record.severity,
            message=record.message,
            created_at=record.created_at,
            details=json.loads(record.details_json) if record.details_json else {},
        )