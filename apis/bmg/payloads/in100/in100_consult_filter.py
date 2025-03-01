from pydantic import BaseModel

class In100ConsultFilter(BaseModel):
    cpf: str

def build_in100_consult_filter(data: In100ConsultFilter, login, password):
    return f"""
    soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:web="http://webservice.econsig.bmg.com"> 
    <soapenv:Header/> 
    <soapenv:Body> 
        <web:pesquisar> 
            <FiltroConsultaIN100> 
            <login>{login}</login> 
            <senha>{password}</senha> 
            <cpf>{data.cpf}</cpf> 
            <numeroSolicitacao></numeroSolicitacao> 
            </FiltroConsultaIN100> 
        </web:pesquisar> 
    </soapenv:Body> 
    </soapenv:Envelope>"""