"""Look up one PA's NCCPA certification and say whether it fits the model, without showing it.

Run with ``just nccpa-check <pa-id>`` against the NCCPA that ``NCCPA_API_URL`` names. A response
that doesn't fit prints each field and why, as the Worker logs it; docs/nccpa.md says what next.
"""

import asyncio
import sys

from licensing_api.config import Settings
from licensing_api.nccpa import NccpaError, create_nccpa_client


async def check(pa_id: int) -> int:
    """Print the outcome for one PA ID; 1 when NCCPA failed or the response doesn't fit."""
    settings = Settings()
    nccpa = create_nccpa_client(settings)
    try:
        status = await nccpa.get_certification_status(pa_id)
    except NccpaError as error:
        print(f'{settings.nccpa_api_url}: {error}')
        return 1
    finally:
        await nccpa.aclose()
    if status is None:
        print(f'{settings.nccpa_api_url}: 404, NCCPA has no such PA.')
    else:
        print(f'{settings.nccpa_api_url}: the response fits the model.')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(check(int(sys.argv[1]))))
