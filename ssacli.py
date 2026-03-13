import re
import subprocess
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Matches: logicaldrive 1 (10.92 TB, RAID 5, Interim Recovery Mode)
LOGICAL_DRIVE_RE = re.compile(
    r"logicaldrive\s+(\d+)\s+\(([^,]+),\s*RAID\s+(\S+),\s*(.+?)\)"
)

# Matches: physicaldrive 1I:3:3 (port 1I:box 3:bay 3, SAS HDD, 2.4 TB, OK)
PHYSICAL_DRIVE_RE = re.compile(
    r"physicaldrive\s+(\S+)\s+\((.+)\)"
)

SLOT_RE = re.compile(r"Slot\s+(\d+)")


@dataclass
class LogicalDrive:
    controller: int
    id: int
    status: str
    size: str
    raid_level: str

    @property
    def is_healthy(self) -> bool:
        return self.status.upper() == "OK"


@dataclass
class PhysicalDrive:
    controller: int
    location: str
    interface: str
    media: str
    size: str
    status: str

    @property
    def is_healthy(self) -> bool:
        return self.status.upper() == "OK"


def run_ssacli(args: list[str], binary: str = "ssacli") -> str:
    cmd = [binary] + args
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed (rc={result.returncode}): {result.stderr}")
    return result.stdout


def parse_config(output: str) -> tuple[list[LogicalDrive], list[PhysicalDrive]]:
    """Parse output of `ssacli ctrl all show config`.

    Example:

        Internal Drive Cage at Port 3I, Box 6, OK

        Array A (SAS,
           logicaldrive 1 (10.92 TB, RAID 5, Interim Recovery Mode)

           physicaldrive 1I:3:3 (port 1I:box 3:bay 3, SAS HDD, 2.4 TB, OK)
           physicaldrive 1I:3:4 (port 1I:box 3:bay 4, SAS HDD, 0 GB, Failed)

        Array B (SAS, Unused Space: 0  MB)
           logicaldrive 2 (1.09 TB, RAID 1, OK)
    """
    logical_drives: list[LogicalDrive] = []
    physical_drives: list[PhysicalDrive] = []
    current_slot = 0

    for line in output.splitlines():
        slot_match = SLOT_RE.search(line)
        if slot_match:
            current_slot = int(slot_match.group(1))
            continue

        ld_match = LOGICAL_DRIVE_RE.search(line)
        if ld_match:
            logical_drives.append(LogicalDrive(
                controller=current_slot,
                id=int(ld_match.group(1)),
                size=ld_match.group(2).strip(),
                raid_level=ld_match.group(3).strip(),
                status=ld_match.group(4).strip(),
            ))
            continue

        pd_match = PHYSICAL_DRIVE_RE.search(line)
        if pd_match:
            location = pd_match.group(1)
            parts = [p.strip() for p in pd_match.group(2).split(",")]
            # Last field is status, second-to-last is size,
            # third-to-last is media type, everything before is interface/port info
            if len(parts) >= 4:
                status = parts[-1]
                size = parts[-2]
                media = parts[-3]
                interface = ", ".join(parts[:-3])
            else:
                status = parts[-1] if parts else "Unknown"
                size = parts[-2] if len(parts) >= 2 else ""
                media = parts[-3] if len(parts) >= 3 else ""
                interface = ""

            physical_drives.append(PhysicalDrive(
                controller=current_slot,
                location=location,
                interface=interface,
                media=media,
                size=size,
                status=status,
            ))

    return logical_drives, physical_drives


def get_all_drives(binary: str = "ssacli") -> tuple[list[LogicalDrive], list[PhysicalDrive]]:
    """Run `ssacli ctrl all show config` and return parsed drives."""
    output = run_ssacli(["ctrl", "all", "show", "config"], binary)
    return parse_config(output)
