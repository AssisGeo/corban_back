# Flake8: noqa
from .vctex_api_client import VCTEXAPIClient
from .cep_api_client import CepAPIClient
from .prata_apli_client import PrataApi
from .inapi_client import InApiClient
from .bmg.bmg_api_client import (
    BmgApiClient,
    In100Request,
    In100ConsultFilter,
    SingleConsultRequest,
    OfferRequest,
)
from .bmg.payloads.benefit_card.get_offer import CustomerFirstStep
from .bmg.payloads.benefit_card.save_proposal import (
    IdentityDocument,
    Customer,
    Address,
    SaveProposalRequest,
)
