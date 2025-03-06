from pydantic import BaseModel

class SingleConsultRequest(BaseModel):
    request_number: str
    token: str

def single_consult_request(data: SingleConsultRequest, login, password):
    return f"""
    soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:web="http://webservice.econsig.bmg.com"> 
    <soapenv:Header/> 
    <soapenv:Body> 
        <web:realizarConsultaAvulsa> 
            <FiltroConsultaAvulsaIN100> 
            <login>{login}</login> 
            <senha>{password}</senha> 
            <numeroSolicitacao>{data.request_number}</numeroSolicitacao> 
            <token>{data.token}</token> 
            </FiltroConsultaAvulsaIN100> 
        </web:realizarConsultaAvulsa> 
    </soapenv:Body> 
    </soapenv:Envelope>"""