from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class LimitRequest(BaseModel):
    entity: int
    cpf: str
    birthdate: datetime
    degree: str
    store: int
    benefit: str
    card_limit: Decimal


def get_limit(data: LimitRequest, login, password):
    return f"""
<soapenv:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:web="http://webservice.econsig.bmg.com">
   <soapenv:Header/>
   <soapenv:Body>
      <web:buscarLimiteSaque soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
         <param xsi:type="web:LimiteSaqueParameter">
            <login xsi:type="soapenc:string" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{login}</login>
            <senha xsi:type="soapenc:string" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{password}</senha>
            <codigoEntidade xsi:type="xsd:int">{data.entity}</codigoEntidade>
            <cpf xsi:type="soapenc:string" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{data.cpf}</cpf>
            <dataNascimento xsi:type="xsd:dateTime">{data.birthdate}</dataNascimento>
            <grauInstrucao xsi:type="soapenc:string" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{data.degree}</grauInstrucao>
            <loja xsi:type="soapenc:int" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{data.store}</loja>
            <matricula xsi:type="soapenc:string" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">{data.benefit}</matricula>
            <valorMargem xsi:type="xsd:double">{data.card_limit}</valorMargem>
         </param>
      </web:buscarLimiteSaque>
   </soapenv:Body>
</soapenv:Envelope>"""
