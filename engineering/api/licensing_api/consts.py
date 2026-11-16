"""Field shapes several routes share."""

from typing import Annotated

from pydantic import Field

StateCode = Annotated[str, Field(pattern=r'^[A-Z]{2}$', description='Two-letter state code')]
