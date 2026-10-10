"""WSGI and local-development entry point."""

import os

from teiko.config import Settings
from teiko.dashboard import DashboardFactory

app = DashboardFactory(Settings.from_environment()).create()
server = app.server


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8050")), debug=False)
