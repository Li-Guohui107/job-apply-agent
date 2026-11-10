"""Run the local studio: python -m app"""

from __future__ import annotations

import os

from app.config import load_local_env
from app.server import serve


def main() -> None:
    load_local_env()
    host = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("PORT", "3000"))
    serve(host, port)


if __name__ == "__main__":
    main()
