from pydantic import BaseModel


class AddressResponse(BaseModel):
    zipCode: str | None = None
    street: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
