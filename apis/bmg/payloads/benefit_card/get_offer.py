from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from utils.format_string_datetime import format_string_datetime


class CustomerFirstStep(BaseModel):
    city_of_birth: str
    cpf: str
    birthdate: datetime
    name: str
    state_of_birth: str


class OfferRequest(BaseModel):
    bank_code: int
    bank_agency: str
    bank_account: str
    bank_account_digit: str = "0"
    customer: CustomerFirstStep
    benefit: str
    benefit_type: int
    card_avaiable_margin: Decimal
    uf_benefit: str
    income_value: Decimal


def build_get_offer_payload(
    data: OfferRequest, login, password, loginConsig, senhaConsig
):
    customer = data.customer

    return f"""
    <soapenv:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:web="http://webservice.econsig.bmg.com" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">
    <soapenv:Header/>
    <soapenv:Body>
        <web:geraScript soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <proposta xsi:type="web:CartaoParameter">
                <login xsi:type="soapenc:string">{login}</login>
                <senha xsi:type="soapenc:string">{password}</senha>
                <aberturaContaPagamento xsi:type="xsd:int">0</aberturaContaPagamento>
                <banco xsi:type="web:BancoParameter">
                    <numero xsi:type="xsd:int">{data.bank_code}</numero>
                </banco>
                <agencia xsi:type="web:AgenciaParameter">
                    <digitoVerificador xsi:type="soapenc:string"></digitoVerificador>
                    <numero xsi:type="soapenc:string">{data.bank_agency}</numero>
                </agencia>
                <conta xsi:type="web:ContaParameter">
                <digitoVerificador xsi:type="soapenc:string">{data.bank_account_digit}</digitoVerificador>
                <numero xsi:type="soapenc:string">{data.bank_account}</numero>
                </conta>
                <bancoOrdemPagamento xsi:type="xsd:int">{data.bank_code}</bancoOrdemPagamento>
                <cliente xsi:type="web:ClienteParameter">
                    <celular1 xsi:type="web:TelefoneParameter">
                        <ddd xsi:type="soapenc:string">21</ddd>
                        <numero xsi:type="soapenc:string">999601309</numero>
                    </celular1>
                    <cidadeNascimento xsi:type="soapenc:string">{customer.city_of_birth}</cidadeNascimento>
                    <cpf xsi:type="soapenc:string">{customer.cpf}</cpf>
                    <dataNascimento xsi:type="xsd:dateTime">{format_string_datetime(customer.birthdate)}</dataNascimento>
                    <email xsi:type="soapenc:string"></email>
                    <endereco xsi:type="web:EnderecoParamter">
                        <bairro xsi:type="soapenc:string">CENTRO</bairro>
                        <cep xsi:type="soapenc:string">24030001</cep>
                        <cidade xsi:type="soapenc:string">NITEROI</cidade>
                        <complemento xsi:type="soapenc:string"></complemento>
                        <logradouro xsi:type="soapenc:string">Rua Academico Walter Goncalves</logradouro>
                        <numero xsi:type="soapenc:string">1</numero>
                        <uf xsi:type="soapenc:string">RJ</uf>
                    </endereco>
                    <estadoCivil xsi:type="soapenc:string">S</estadoCivil>
                    <grauInstrucao xsi:type="soapenc:string">7</grauInstrucao>
                    <identidade xsi:type="web:IdentidadeParameter">
                        <dataEmissao xsi:type="xsd:dateTime">2010-10-25T00:00:00</dataEmissao>
                        <emissor xsi:type="soapenc:string">SSP</emissor>
                        <numero xsi:type="soapenc:string">4580973</numero>
                        <tipo xsi:type="soapenc:string">RG</tipo>
                        <uf xsi:type="soapenc:string">RJ</uf>
                    </identidade>
                    <nacionalidade xsi:type="soapenc:string">Brasileiro</nacionalidade>
                    <nome xsi:type="soapenc:string">{customer.name}</nome>
                    <nomeConjuge xsi:type="soapenc:string"></nomeConjuge>
                    <nomeMae xsi:type="soapenc:string">Maria Madalena Santos</nomeMae>
                    <nomePai xsi:type="soapenc:string">Não declarado</nomePai>
                    <pessoaPoliticamenteExposta xsi:type="xsd:boolean">false</pessoaPoliticamenteExposta>
                    <sexo xsi:type="soapenc:string">M</sexo>
                    <ufNascimento xsi:type="soapenc:string">{customer.state_of_birth}</ufNascimento>
                </cliente>
                <codigoEntidade xsi:type="soapenc:string">4277-</codigoEntidade>
                <codigoLoja xsi:type="soapenc:int">54442</codigoLoja>
                <codigoServico xsi:type="soapenc:string">141</codigoServico>
                <cpf xsi:type="soapenc:string">{customer.cpf}</cpf>
                <dataRenda xsi:type="xsd:dateTime">2025-02-05T00:00:00</dataRenda>
                <loginConsig xsi:type="soapenc:string">{loginConsig}</loginConsig>
                <formaCredito xsi:type="xsd:int">2</formaCredito>
                <codigoFormaEnvioTermo xsi:type="soapenc:string">14</codigoFormaEnvioTermo>
                <finalidadeCredito xsi:type="xsd:int">1</finalidadeCredito>
                <margem xsi:type="xsd:double">{data.card_avaiable_margin}</margem>
                <matricula xsi:type="soapenc:string">{data.benefit}</matricula>
                <senhaConsig xsi:type="soapenc:string">{senhaConsig}</senhaConsig>
                <tipoBeneficio xsi:type="soapenc:int">{data.benefit_type}</tipoBeneficio>
                <tipoDomicilioBancario xsi:type="soapenc:short">1</tipoDomicilioBancario>
                <token xsi:type="soapenc:string"></token>
                <ufContaBeneficio xsi:type="soapenc:string">{data.uf_benefit}</ufContaBeneficio>
                <valorRenda xsi:type="xsd:double">{data.income_value}</valorRenda>
                <tipoFormaEnvioFatura xsi:type="soapenc:string">W</tipoFormaEnvioFatura>
            </proposta>
        </web:geraScript>
    </soapenv:Body>
</soapenv:Envelope>"""
