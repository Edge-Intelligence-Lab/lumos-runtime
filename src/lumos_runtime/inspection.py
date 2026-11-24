"""Discover host-visible robot endpoints without opening devices."""

from dataclasses import dataclass
from pathlib import Path
import platform


ARPHRD_CAN = "280"


@dataclass(frozen=True)
class HostInventory:
    architecture: str
    python_version: str
    camera_nodes: tuple[str, ...]
    serial_by_id: tuple[str, ...]
    serial_nodes: tuple[str, ...]
    can_interfaces: tuple[str, ...]


def inspect_host(
    dev_root: Path = Path("/dev"),
    network_root: Path = Path("/sys/class/net"),
) -> HostInventory:
    """Return device candidates from Linux device nodes and sysfs."""
    return HostInventory(
        architecture=platform.machine(),
        python_version=platform.python_version(),
        camera_nodes=tuple(str(path) for path in sorted(dev_root.glob("video[0-9]*"))),
        serial_by_id=tuple(str(path) for path in sorted((dev_root / "serial/by-id").glob("*"))),
        serial_nodes=tuple(
            sorted(
                str(path)
                for pattern in ("ttyUSB[0-9]*", "ttyACM[0-9]*", "ttyS[0-9]*")
                for path in dev_root.glob(pattern)
            )
        ),
        can_interfaces=tuple(
            entry.name for entry in sorted(network_root.glob("*")) if _is_can(entry)
        ),
    )


def _is_can(interface: Path) -> bool:
    try:
        return (interface / "type").read_text(encoding="ascii").strip() == ARPHRD_CAN
    except FileNotFoundError:
        # An adapter may be unplugged after sysfs enumeration.
        return False
