from __future__ import annotations

import ctypes
import getpass
import logging
import os
from dataclasses import dataclass

from northssl.core.models import PrivilegeSnapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SystemPrivilegeDetector:
    def detect(self) -> PrivilegeSnapshot:
        username = getpass.getuser()

        if os.name == "nt":
            try:
                elevated = bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception as exc:  # pragma: no cover - Windows-only fallback
                logger.debug("Unable to check Windows admin privileges: %s", exc)
                elevated = False

            return PrivilegeSnapshot(
                elevated=elevated,
                mechanism="windows-administrator",
                username=username,
            )

        geteuid = getattr(os, "geteuid", None)
        getegid = getattr(os, "getegid", None)
        uid = geteuid() if callable(geteuid) else None
        gid = getegid() if callable(getegid) else None
        elevated = uid == 0 if uid is not None else False
        mechanism = "root" if elevated else "user"

        if os.environ.get("SUDO_USER"):
            mechanism = "sudo"

        return PrivilegeSnapshot(
            elevated=elevated,
            mechanism=mechanism,
            username=username,
            uid=uid,
            gid=gid,
        )