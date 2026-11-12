"""Fetch one FSMB report and say whether it fits the models, without showing what it holds.

Run with ``just fsmb-check <fid>`` against the FSMB that ``FSMB_API_URL`` names. A report that
doesn't fit prints each field and why, as the Worker logs it; docs/fsmb.md says what to do next.
"""

import asyncio
import sys

from licensing_api.config import Settings
from licensing_api.fsmb import REPORT_NOT_READY, FsmbError, create_fsmb_client


async def check(fid: str) -> int:
    """Print the outcome for one FID; 1 when FSMB failed or the report doesn't fit."""
    settings = Settings()
    fsmb = create_fsmb_client(settings)
    try:
        report = await fsmb.get_current_report(fid)
    except FsmbError as error:
        print(f'{settings.fsmb_api_url}: {error}')
        return 1
    finally:
        await fsmb.aclose()
    if report is REPORT_NOT_READY:
        print(f'{settings.fsmb_api_url}: 204, FSMB has no report for this member yet.')
    elif report is None:
        print(f'{settings.fsmb_api_url}: 404, not on the roster or no report.')
    else:
        print(f'{settings.fsmb_api_url}: the report fits the models.')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(check(sys.argv[1])))
