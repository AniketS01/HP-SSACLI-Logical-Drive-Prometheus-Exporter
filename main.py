import argparse
import logging

from exporter import start_exporter


def main():
    parser = argparse.ArgumentParser(description="HP SSACLI Logical Drive Prometheus Exporter")
    parser.add_argument("--port", type=int, default=9100, help="Port to expose metrics on (default: 9100)")
    parser.add_argument("--ssacli-bin", default="ssacli", help="Path to ssacli binary (default: ssacli)")
    parser.add_argument("--cache-ttl", type=int, default=1800, help="Seconds to cache ssacli results (default: 1800 = 30 min)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    start_exporter(port=args.port, binary=args.ssacli_bin, cache_ttl=args.cache_ttl)


if __name__ == "__main__":
    main()
