import logging
import time

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client import start_http_server

from ssacli import get_all_drives

logger = logging.getLogger(__name__)


class SSACLICollector:
    def __init__(self, binary: str = "ssacli", cache_ttl: int = 1800):
        self.binary = binary
        self.scrape_errors = 0
        self.cache_ttl = cache_ttl
        self._cached_logical: list = []
        self._cached_physical: list = []
        self._cache_time: float = 0

    def _get_drives(self):
        now = time.time()
        if now - self._cache_time < self.cache_ttl and self._cache_time > 0:
            logger.debug("Using cached drive data (age: %.0fs)", now - self._cache_time)
            return self._cached_logical, self._cached_physical

        logical, physical = get_all_drives(self.binary)
        self._cached_logical = logical
        self._cached_physical = physical
        self._cache_time = now
        logger.info("Refreshed drive data: %d logical, %d physical", len(logical), len(physical))
        return logical, physical

    def collect(self):
        ld_status = GaugeMetricFamily(
            "hp_ssacli_logical_drive_status",
            "Status of each logical drive (1=healthy, 0=unhealthy)",
            labels=["controller", "logicaldrive", "size", "raid_level", "status_text"],
        )
        ld_healthy = GaugeMetricFamily(
            "hp_ssacli_logical_drives_healthy_total",
            "Total number of healthy logical drives",
        )
        ld_failed = GaugeMetricFamily(
            "hp_ssacli_logical_drives_failed_total",
            "Total number of failed/degraded logical drives",
        )
        pd_status = GaugeMetricFamily(
            "hp_ssacli_physical_drive_status",
            "Status of each physical drive (1=healthy, 0=unhealthy)",
            labels=["controller", "location", "media", "size", "status_text"],
        )
        pd_healthy = GaugeMetricFamily(
            "hp_ssacli_physical_drives_healthy_total",
            "Total number of healthy physical drives",
        )
        pd_failed = GaugeMetricFamily(
            "hp_ssacli_physical_drives_failed_total",
            "Total number of failed physical drives",
        )
        scrape_errors = CounterMetricFamily(
            "hp_ssacli_scrape_errors_total",
            "Total number of scrape errors",
        )

        try:
            logical_drives, physical_drives = self._get_drives()
        except Exception:
            logger.exception("Failed to collect drives")
            self.scrape_errors += 1
            scrape_errors.add_metric([], self.scrape_errors)
            yield scrape_errors
            return

        healthy_ld = 0
        failed_ld = 0
        for d in logical_drives:
            val = 1.0 if d.is_healthy else 0.0
            if d.is_healthy:
                healthy_ld += 1
            else:
                failed_ld += 1
            ld_status.add_metric(
                [str(d.controller), str(d.id), d.size, d.raid_level, d.status], val
            )

        healthy_pd = 0
        failed_pd = 0
        for d in physical_drives:
            val = 1.0 if d.is_healthy else 0.0
            if d.is_healthy:
                healthy_pd += 1
            else:
                failed_pd += 1
            pd_status.add_metric(
                [str(d.controller), d.location, d.media, d.size, d.status], val
            )

        ld_healthy.add_metric([], healthy_ld)
        ld_failed.add_metric([], failed_ld)
        pd_healthy.add_metric([], healthy_pd)
        pd_failed.add_metric([], failed_pd)
        scrape_errors.add_metric([], self.scrape_errors)

        yield ld_status
        yield ld_healthy
        yield ld_failed
        yield pd_status
        yield pd_healthy
        yield pd_failed
        yield scrape_errors


def start_exporter(port: int = 9100, binary: str = "ssacli", cache_ttl: int = 1800):
    REGISTRY.register(SSACLICollector(binary, cache_ttl=cache_ttl))
    start_http_server(port)
    logger.info("HP SSACLI exporter started on :%d/metrics", port)
    while True:
        time.sleep(1)
