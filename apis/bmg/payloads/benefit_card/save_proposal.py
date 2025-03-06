from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from decimal import Decimal

from utils.format_string_datetime import format_string_datetime


class Agency(BaseModel):
    number: str
    secure_digit: str = ""


class Account(BaseModel):
    number: str
    secure_digit: str


class IdentityDocument(BaseModel):
    type: str
    number: str
    emission_date: datetime
    issuer: str
    state: str


class Address(BaseModel):
    zipCode: str
    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    complement: Optional[str] = ""


class Customer(BaseModel):
    cellphone: str
    city_of_birth: str
    cpf: str
    date_of_birth: str
    email: Optional[EmailStr] = ""
    address: Address
    marital_status: Optional[str] = "S"
    educational_level: Optional[str] = "7"
    identity_document: IdentityDocument
    nationality: str
    name: str
    spouse_name: Optional[str] = ""
    mother_name: str
    ppe: Optional[bool] = False
    gender: str
    state_of_birth: str


class SaveProposalRequest(BaseModel):
    abertura_contaPagamento: int = 0
    bank_num: int
    agency: Agency
    account: Account
    banco_ordem_pagamento: int
    customer: Customer
    finalidade_credito: Optional[int] = 1
    income_date: datetime
    margin: Decimal
    benefit: str
    benefit_type: int
    uf_benefit: str
    income_value: Decimal


def build_save_benefit_card_proposal_payload(
    data: SaveProposalRequest, login, password, loginConsig, senhaConsig
):
    customer = data.customer
    address = customer.address
    identity_document = customer.identity_document

    return f"""
<soapenv:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:web="http://webservice.econsig.bmg.com" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">
    <soapenv:Header/>
    <soapenv:Body>
    <web:gravarPropostaCartao soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <proposta xsi:type="web:CartaoParameter">
        <login xsi:type="soapenc:string">{login}</login>
        <senha xsi:type="soapenc:string">{password}</senha>
        <aberturaContaPagamento xsi:type="xsd:int">{data.abertura_contaPagamento}</aberturaContaPagamento>
        <banco xsi:type="web:BancoParameter">
            <numero xsi:type="xsd:int">{data.bank_num}</numero>
        </banco>
        <agencia xsi:type="web:AgenciaParameter">
            <digitoVerificador xsi:type="soapenc:string">{data.agency.secure_digit}</digitoVerificador>
            <numero xsi:type="soapenc:string">{data.agency.number}</numero>
        </agencia>
        <conta xsi:type="web:ContaParameter">
            <digitoVerificador xsi:type="soapenc:string">{data.account.secure_digit}</digitoVerificador>
            <numero xsi:type="soapenc:string">{data.account.number}</numero>
        </conta>
        <bancoOrdemPagamento xsi:type="xsd:int">{data.banco_ordem_pagamento}</bancoOrdemPagamento>
        <cliente xsi:type="web:ClienteParameter">
            <celular1 xsi:type="web:TelefoneParameter">
                <ddd xsi:type="soapenc:string">{customer.cellphone[:2]}</ddd>
                <numero xsi:type="soapenc:string">{customer.cellphone[2:]}</numero>
        </celular1>
        <cidadeNascimento xsi:type="soapenc:string">{customer.city_of_birth}</cidadeNascimento>
        <cpf xsi:type="soapenc:string">{customer.cpf}</cpf>
        <dataNascimento xsi:type="xsd:dateTime">{format_string_datetime(customer.date_of_birth)}</dataNascimento>
        <email xsi:type="soapenc:string">{customer.email}</email>
        <endereco xsi:type="web:EnderecoParamter">
            <bairro xsi:type="soapenc:string">{address.neighborhood}</bairro>
            <cep xsi:type="soapenc:string">{address.zipCode}</cep>
            <cidade xsi:type="soapenc:string">{address.city}</cidade>
            <complemento xsi:type="soapenc:string">{address.complement}</complemento>
            <logradouro xsi:type="soapenc:string">{address.street}</logradouro>
            <numero xsi:type="soapenc:string">{address.number}</numero>
            <uf xsi:type="soapenc:string">{address.state}</uf>
        </endereco>
        <estadoCivil xsi:type="soapenc:string">{customer.marital_status}</estadoCivil>
        <grauInstrucao xsi:type="soapenc:string">{customer.educational_level}</grauInstrucao>
        <identidade xsi:type="web:IdentidadeParameter">
            <dataEmissao xsi:type="xsd:dateTime">{format_string_datetime(identity_document.emission_date)}</dataEmissao>
            <emissor xsi:type="soapenc:string">{identity_document.issuer}</emissor>
            <numero xsi:type="soapenc:string">{identity_document.number}</numero>
            <tipo xsi:type="soapenc:string">{identity_document.type}</tipo>
            <uf xsi:type="soapenc:string">{identity_document.state}</uf>
        </identidade>
        <nacionalidade xsi:type="soapenc:string">{customer.nationality}</nacionalidade>
        <nome xsi:type="soapenc:string">{customer.name}</nome>
        <nomeConjuge xsi:type="soapenc:string">{customer.spouse_name}</nomeConjuge>
        <nomeMae xsi:type="soapenc:string">{customer.mother_name}</nomeMae>
        <nomePai xsi:type="soapenc:string">Não declarado</nomePai>
        <pessoaPoliticamenteExposta xsi:type="xsd:boolean">{customer.ppe}</pessoaPoliticamenteExposta>
        <sexo xsi:type="soapenc:string">{customer.gender}</sexo>
        <ufNascimento xsi:type="soapenc:string">{customer.state_of_birth}</ufNascimento>
        </cliente>
        <finalidadeCredito xsi:type="xsd:int">{data.finalidade_credito}</finalidadeCredito>
        <codigoEntidade xsi:type="soapenc:string">4277-</codigoEntidade>
        <codigoFormaEnvioTermo xsi:type="soapenc:string">15</codigoFormaEnvioTermo>
        <codigoLoja xsi:type="soapenc:int">54442</codigoLoja>
        <codigoServico xsi:type="soapenc:string">141</codigoServico>
        <cpf xsi:type="soapenc:string">{customer.cpf}</cpf>
        <dataRenda xsi:type="xsd:dateTime">{format_string_datetime(data.income_date)}</dataRenda>
        <formaCredito xsi:type="xsd:int">2</formaCredito>
        <loginConsig xsi:type="soapenc:string">{loginConsig}</loginConsig>
        <senhaConsig xsi:type="soapenc:string">{senhaConsig}</senhaConsig>
        <margem xsi:type="xsd:double">{data.margin}</margem>
        <matricula xsi:type="soapenc:string">{data.benefit}</matricula>
        <tipoBeneficio xsi:type="soapenc:int">{data.benefit_type}</tipoBeneficio>
        <tipoDomicilioBancario xsi:type="soapenc:short">1</tipoDomicilioBancario>
        <token xsi:type="soapenc:string"></token>
        <ufContaBeneficio xsi:type="soapenc:string">{data.uf_benefit}</ufContaBeneficio>
        <valorRenda xsi:type="xsd:double">{data.income_value}</valorRenda>
        <tipoFormaEnvioFatura xsi:type="soapenc:string">W</tipoFormaEnvioFatura>
    </proposta>
    </web:gravarPropostaCartao>
    </soapenv:Body>
</soapenv:Envelope>"""
