from __future__ import annotations


class NorthSSLError(Exception):
    code = "northssl_error"


class ValidationError(NorthSSLError):
    code = "validation_error"


class DomainValidationError(ValidationError):
    code = "domain_validation_error"


class ProviderUnavailableError(NorthSSLError):
    code = "provider_unavailable"


class PrivilegeError(NorthSSLError):
    code = "insufficient_privileges"


class PortConflictError(NorthSSLError):
    code = "port_conflict"


class CertificateNotFoundError(NorthSSLError):
    code = "certificate_not_found"


class CertificateOperationError(NorthSSLError):
    code = "certificate_operation_failed"


class RenewalLockError(NorthSSLError):
    code = "renewal_lock_error"


class RenewalOperationError(NorthSSLError):
    code = "renewal_operation_failed"


class MonitoringError(NorthSSLError):
    code = "monitoring_error"


class SchedulerError(NorthSSLError):
    code = "scheduler_error"