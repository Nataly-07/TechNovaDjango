"""
Settings dispatcher by environment.

Use TECHNOVA_ENV in: dev | staging | prod
"""

import os

environment = os.getenv("TECHNOVA_ENV", "dev").strip().lower()

if environment == "dev":
    from .settings_dev import *  # noqa: F403,F401
elif environment == "staging":
    from .settings_staging import *  # noqa: F403,F401
elif environment == "prod":
    from .settings_prod import *  # noqa: F403,F401
else:
    raise RuntimeError(
        "TECHNOVA_ENV invalido. Usa 'dev', 'staging' o 'prod'."
    )
