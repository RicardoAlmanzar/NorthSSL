from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import CertificateMetadata
from northssl.database.models import CertificateRecord
from northssl.database.session import create_session_factory, initialize_database


class CertificateRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: NorthSSLSettings | None = None) -> CertificateRepository:
        resolved_settings = settings or NorthSSLSettings()
        initialize_database(resolved_settings)
        return cls(create_session_factory(resolved_settings))

    def save(self, metadata: CertificateMetadata) -> CertificateMetadata:
        with self._session_factory() as session:
            record = session.scalar(select(CertificateRecord).where(CertificateRecord.domain == metadata.domain))
            if record is None:
                record = CertificateRecord(domain=metadata.domain)
                session.add(record)

            self._populate_record(record, metadata)
            session.commit()
            session.refresh(record)
            return self._to_metadata(record)

    def list_all(self) -> list[CertificateMetadata]:
        with self._session_factory() as session:
            records = session.scalars(select(CertificateRecord).order_by(CertificateRecord.domain.asc())).all()
            return [self._to_metadata(record) for record in records]

    def get_by_domain(self, domain: str) -> CertificateMetadata | None:
        with self._session_factory() as session:
            record = session.scalar(select(CertificateRecord).where(CertificateRecord.domain == domain))
            return self._to_metadata(record) if record else None

    def delete_by_domain(self, domain: str) -> None:
        with self._session_factory() as session:
            record = session.scalar(select(CertificateRecord).where(CertificateRecord.domain == domain))
            if record is None:
                return
            session.delete(record)
            session.commit()

    def _populate_record(self, record: CertificateRecord, metadata: CertificateMetadata) -> None:
        record.domain = metadata.domain
        record.provider = metadata.provider
        record.certificate_path = metadata.certificate_path
        record.private_key_path = metadata.private_key_path
        record.chain_path = metadata.chain_path
        record.issued_at = metadata.issued_at
        record.expires_at = metadata.expires_at
        record.status = metadata.status
        record.validation_method = metadata.validation_method
        record.issuer = metadata.issuer
        record.sans_json = json.dumps(metadata.sans)
        record.serial_number = metadata.serial_number
        now = datetime.now(timezone.utc)
        if record.created_at is None:
            record.created_at = now
        record.updated_at = now

    def _to_metadata(self, record: CertificateRecord) -> CertificateMetadata:
        return CertificateMetadata(
            domain=record.domain,
            provider=record.provider,
            certificate_path=record.certificate_path,
            private_key_path=record.private_key_path,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            status=record.status,
            validation_method=record.validation_method,
            chain_path=record.chain_path,
            issuer=record.issuer,
            sans=json.loads(record.sans_json) if record.sans_json else [],
            serial_number=record.serial_number,
        )