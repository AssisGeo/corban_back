from pydantic import BaseModel, field_validator
from datetime import datetime
from utils.format_string_datetime import format_string_datetime


class In100Request(BaseModel):
    cpf: str
    benefit: str
    city: str
    state: str
    birthdate: datetime
    name: str
    phone: str

    @field_validator("*", mode="before")
    @classmethod
    def uppercase_strings(cls, value):
        if isinstance(value, str):
            return value.upper()
        return value


def generate_request_in100_payload(data: In100Request, login, password):
    return f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:web="http://webservice.econsig.bmg.com">
        <soapenv:Header/>
        <soapenv:Body>
            <web:inserirSolicitacao>
                <solicitacaoIN100>
                    <login>{login}</login>
                    <senha>{password}</senha>
                    <cidade>{data.city}</cidade>
                    <cpf>{data.cpf}</cpf>
                    <dataNascimento>{format_string_datetime(data.birthdate)}</dataNascimento>
                    <ddd>{data.phone[:2]}</ddd>
                    <estado>{data.state}</estado>
                    <matricula>{data.benefit}</matricula>
                    <nome>{data.name}</nome>
                    <telefone>{data.phone[2:]}</telefone>
                </solicitacaoIN100>
            </web:inserirSolicitacao>
        </soapenv:Body>
    </soapenv:Envelope>
    """
