from typing import Dict, List, Any, Optional, Union
from .banks.base import BankProposal, ProposalResult
from pymongo import MongoClient, DESCENDING
from .adapters.base import BankAdapter
import logging
import os
from math import ceil
from datetime import datetime
from memory import MongoDBMemoryManager
from models.normalized.proposal import NormalizedProposalRequest

logger = logging.getLogger(__name__)


class ProposalService:
    def __init__(self):
        self._proposal_providers: Dict[str, BankProposal] = {}
        self._adapters: Dict[str, BankAdapter] = {}
        self.mongo_client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.mongo_client["fgts_agent"]
        self.proposals = self.db["fgts_proposals"]
        self.simulations = self.db["fgts_simulations"]
        self.memory_manager = MongoDBMemoryManager()
        self.bank_config_collection = self.db["bank_configs"]

    def get_active_banks(self, feature: str = "proposal") -> List[str]:
        """Retorna a lista de bancos ativos para uma determinada feature"""
        try:
            config = self.bank_config_collection.find_one({})
            if not config or "banks" not in config:
                return list(self._proposal_providers.keys())

            active_banks = []
            for bank_name, bank_info in config["banks"].items():
                if bank_info.get("active", True) and feature in bank_info.get(
                    "features", []
                ):
                    active_banks.append(bank_name)

            return active_banks
        except Exception as e:
            logger.error(f"Erro ao obter bancos ativos: {str(e)}")
            return list(self._proposal_providers.keys())

    def is_bank_active(self, bank_name: str, feature: str = "proposal") -> bool:
        """Verifica se um banco está ativo para uma determinada feature"""
        try:
            config = self.bank_config_collection.find_one({})
            if not config or "banks" not in config:
                return True

            if bank_name not in config["banks"]:
                return False

            bank_info = config["banks"][bank_name]
            return bank_info.get("active", True) and feature in bank_info.get(
                "features", []
            )
        except Exception as e:
            logger.error(f"Erro ao verificar se banco está ativo: {str(e)}")
            return True

    def register_provider(self, provider: BankProposal):
        """Registra um novo provedor de proposta no serviço"""
        self._proposal_providers[provider.bank_name] = provider
        logger.info(f"Provedor de proposta registrado: {provider.bank_name}")

    def register_adapter(self, adapter: BankAdapter):
        """Registra um adaptador de banco"""
        self._adapters[adapter.bank_name] = adapter
        logger.info(f"Adaptador registrado: {adapter.bank_name}")

    async def submit_proposal(
        self,
        proposal_data: Union[NormalizedProposalRequest, Dict[str, Any]],
        bank_name: Optional[str] = None,
    ) -> ProposalResult:
        try:
            # 1. Determinar o banco para envio da proposta
            target_bank = bank_name

            # Extrair o financial_id independentemente do tipo de entrada
            if isinstance(proposal_data, dict):
                financial_id = proposal_data.get("financial_id", "")
                if not financial_id:
                    financial_id = proposal_data.get("financialId", "")
            else:
                financial_id = proposal_data.financial_id

            # 2. Buscar dados da simulação armazenada
            simulation_data = self._get_simulation_data(financial_id)

            # 3. Buscar dados do cliente relacionados a esta simulação
            customer_data = self._get_customer_data(financial_id)

            # Se não encontrou dados do cliente, extrair da própria proposta
            if not customer_data and isinstance(proposal_data, dict):
                logger.info(
                    f"Extraindo dados do cliente da própria proposta para {financial_id}"
                )
                extracted_customer = {}

                # Extrair dados do cliente da proposta atual
                if "borrower" in proposal_data:
                    borrower = proposal_data["borrower"]
                    extracted_customer = {
                        "name": borrower.get("name", ""),
                        "cpf": borrower.get("cpf", ""),
                        "email": borrower.get("email", ""),
                        "phone": borrower.get("phoneNumber", ""),
                        "mother_name": borrower.get("motherName", ""),
                        "birth_date": borrower.get("birthdate", ""),
                    }

                # Ou para outro formato
                elif "nome" in proposal_data:
                    extracted_customer = {
                        "name": proposal_data.get("nome", ""),
                        "cpf": proposal_data.get("cpf", ""),
                        "email": proposal_data.get("email", ""),
                        "phone": proposal_data.get("celular", ""),
                        "mother_name": proposal_data.get("nome_mae", ""),
                        "birth_date": proposal_data.get("data_nascimento", ""),
                    }

                if extracted_customer:
                    customer_data = {"customer_data": extracted_customer}

                    # Salva os dados extraídos na sessão para uso futuro
                    self.memory_manager.set_session_data(
                        financial_id, "customer_data", extracted_customer
                    )

            if not target_bank:
                # Se não foi especificado, consulta pelo financialId
                target_bank = self._get_bank_for_financial_id(financial_id)

                if not target_bank:
                    # Padrão para VCTEX se não encontrar
                    target_bank = "VCTEX"
                    logger.warning(
                        f"Banco não identificado para o ID {financial_id}, usando padrão: {target_bank}"
                    )

            # Verificar se o banco está ativo para propostas
            active_banks = self.get_active_banks(feature="proposal")
            if target_bank not in active_banks:
                error_msg = f"Banco {target_bank} não está ativo para propostas"
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # Verificar se o provedor está registrado
            if target_bank not in self._proposal_providers:
                error_msg = f"Provedor não registrado: {target_bank}"
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # Verificar se existe adaptador para o banco
            if target_bank not in self._adapters:
                error_msg = f"Adaptador não encontrado para banco: {target_bank}"
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # Obter a tabela ativa para o banco alvo
            table_id = self._get_active_table_for_bank(target_bank)
            if table_id:
                logger.info(
                    f"Usando tabela {table_id} para proposta com banco {target_bank}"
                )
            else:
                logger.warning(
                    f"Nenhuma tabela ativa encontrada para banco {target_bank}, usando padrão"
                )

            if isinstance(proposal_data, dict):
                try:
                    from models.normalized.proposal import NormalizedProposalRequest

                    # Enriquece a proposta com dados da simulação e do cliente
                    enriched_data = proposal_data.copy()

                    if simulation_data:
                        for key, value in simulation_data.items():
                            if key not in enriched_data:
                                enriched_data[key] = value

                    if customer_data:
                        for key, value in customer_data.items():
                            if key not in enriched_data:
                                enriched_data[key] = value

                    normalized_data = NormalizedProposalRequest(**enriched_data)
                except Exception as e:
                    error_msg = (
                        f"Erro ao converter dados para formato normalizado: {str(e)}"
                    )
                    logger.error(error_msg)
                    return ProposalResult(
                        bank_name=target_bank,
                        error_message=error_msg,
                        success=False,
                        raw_response={
                            "error": error_msg,
                            "original_data": proposal_data,
                        },
                    )
            else:
                normalized_data = proposal_data

            # Usar o adaptador para converter para o formato específico do banco
            adapter = self._adapters[target_bank]
            try:
                bank_specific_data = adapter.prepare_proposal_request(normalized_data)
                logger.info(
                    f"Dados convertidos para formato específico do banco {target_bank}"
                )

                # Adicionar o ID da tabela aos dados específicos do banco
                if table_id:
                    if target_bank == "FACTA":
                        if isinstance(bank_specific_data, dict):
                            bank_specific_data["tabela"] = table_id
                    elif target_bank in ["VCTEX", "QI"]:
                        if isinstance(bank_specific_data, dict):
                            try:
                                bank_specific_data["feeScheduleId"] = int(table_id)
                            except ValueError:
                                logger.warning(
                                    f"Tabela {table_id} não é um número válido para feeScheduleId"
                                )
                                bank_specific_data["feeScheduleId"] = 0

            except Exception as e:
                error_msg = (
                    f"Erro ao adaptar dados para o banco {target_bank}: {str(e)}"
                )
                logger.error(error_msg)
                return ProposalResult(
                    bank_name=target_bank,
                    error_message=error_msg,
                    success=False,
                    raw_response={"error": error_msg},
                )

            # Enviar a proposta usando o provedor específico
            provider = self._proposal_providers[target_bank]
            result = await provider.submit_proposal(bank_specific_data)

            # Salvar o resultado enriquecido com os dados da simulação e do cliente
            self._save_proposal_result(
                financial_id, result, simulation_data, customer_data, normalized_data
            )

            # Se for bem-sucedido, atualizar a sessão com o número do contrato
            if result.success and result.contract_number:
                # Atualiza por financial_id
                self.memory_manager.set_session_data(
                    financial_id, "contract_number", result.contract_number
                )

                # Converter objetos Pydantic para dicionários antes de salvar
                original_data_dict = {}
                if hasattr(normalized_data, "model_dump"):
                    original_data_dict = normalized_data.model_dump()
                elif isinstance(normalized_data, dict):
                    original_data_dict = normalized_data

                # Salva também os metadados
                metadata = {
                    "proposal_created_at": datetime.utcnow(),
                    "proposal_bank": target_bank,
                    "proposal_sent": True,
                    "formalization_link": result.formalization_link,
                }

                for key, value in metadata.items():
                    self.memory_manager.set_session_data(financial_id, key, value)

                # Salva separadamente os dados da proposta para evitar problemas de serialização
                proposal_data_dict = {
                    "simulation_summary": {
                        "available_amount": (
                            simulation_data.get("available_amount")
                            if simulation_data
                            else None
                        ),
                        "total_amount": (
                            simulation_data.get("total_amount")
                            if simulation_data
                            else None
                        ),
                        "interest_rate": (
                            simulation_data.get("interest_rate")
                            if simulation_data
                            else None
                        ),
                    },
                    "contract_number": result.contract_number,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                self.memory_manager.set_session_data(
                    financial_id, "proposal_data", proposal_data_dict
                )

                # Define os dados na collection customer_data
                self.memory_manager.set_session_data(
                    financial_id, "customer_data.proposal_sent", True
                )

                self.memory_manager.set_session_data(
                    financial_id,
                    "customer_data.proposal_created_at",
                    datetime.utcnow(),
                )

                # Armazena dados da simulação que foram usados (garantindo que não são objetos Pydantic)
                if simulation_data:
                    simulation_data_serializable = {}
                    for key, value in simulation_data.items():
                        if hasattr(value, "model_dump"):
                            simulation_data_serializable[key] = value.model_dump()
                        else:
                            simulation_data_serializable[key] = value

                    self.memory_manager.set_session_data(
                        financial_id,
                        "customer_data.simulation_data",
                        simulation_data_serializable,
                    )

                # Armazena o request original como dicionário serializado
                self.memory_manager.set_session_data(
                    financial_id,
                    "customer_data.proposal_request",
                    original_data_dict,
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao enviar proposta: {str(e)}")
            return ProposalResult(
                bank_name=bank_name or "DESCONHECIDO",
                error_message=str(e),
                success=False,
                raw_response={"error": str(e)},
            )

    async def check_proposal_status(
        self, contract_number: str, bank_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica o status de uma proposta existente.

        Args:
            contract_number: Número do contrato
            bank_name: Nome do banco (opcional, se não fornecido tenta descobrir)

        Returns:
            Dict com informações de status
        """
        if not bank_name:
            bank_name = self._get_bank_for_contract(contract_number)

            if not bank_name:
                return {
                    "success": False,
                    "error": f"Banco não encontrado para o contrato {contract_number}",
                    "status": "unknown",
                }

        if bank_name not in self._proposal_providers:
            return {
                "success": False,
                "error": f"Provedor não registrado: {bank_name}",
                "status": "provider_not_found",
            }

        provider = self._proposal_providers[bank_name]
        return await provider.check_status(contract_number)

    def _get_bank_for_financial_id(self, financial_id: str) -> Optional[str]:
        """
        Determina qual banco usar baseado no financial_id.

        Regras:
        - Se começar com "facta_", usa Facta
        - Se começar com "bmg_", usa BMG
        - Caso contrário, consulta no histórico de simulações
        """
        if financial_id.startswith("facta_"):
            return "FACTA"

        if financial_id.startswith("bmg_"):
            return "BMG"

        # Consulta na collection de simulações
        simulation = self.db["fgts_simulations"].find_one(
            {"financial_id": financial_id}
        )

        if simulation:
            return simulation.get("bank_provider") or simulation.get("bank_name")

        # Consulta na memória da sessão
        from memory import MongoDBMemoryManager

        memory_manager = MongoDBMemoryManager()
        bank_provider = memory_manager.get_session_data(financial_id, "bank_provider")

        return bank_provider

    def _get_bank_for_contract(self, contract_number: str) -> Optional[str]:
        """Determina o banco para um número de contrato"""
        proposal = self.proposals.find_one({"contract_number": contract_number})

        if proposal:
            return proposal.get("bank_name")

        return None

    def _save_proposal_result(
        self,
        financial_id: str,
        result: ProposalResult,
        simulation_data: Dict[str, Any] = None,
        customer_data: Dict[str, Any] = None,
        original_request: Any = None,
    ):
        """Salva o resultado da proposta no MongoDB com dados enriquecidos"""
        try:
            original_request_dict = {}
            if hasattr(original_request, "model_dump"):
                original_request_dict = original_request.model_dump()
            elif isinstance(original_request, dict):
                original_request_dict = original_request
            else:
                original_request_dict = {"data": str(original_request)}
            extracted_customer = {}
            phone_number = ""
            if original_request_dict:
                if "customer" in original_request_dict:
                    customer = original_request_dict["customer"]
                    extracted_customer = {
                        "name": customer.get("name", ""),
                        "cpf": customer.get("cpf", ""),
                        "email": customer.get("email", ""),
                        "phone": customer.get("phone", ""),
                        "mother_name": customer.get("mother_name", ""),
                    }
                    phone_number = customer.get("phone", "")
                elif "borrower" in original_request_dict:
                    borrower = original_request_dict["borrower"]
                    extracted_customer = {
                        "name": borrower.get("name", ""),
                        "cpf": borrower.get("cpf", ""),
                        "email": borrower.get("email", ""),
                        "phone": borrower.get("phoneNumber", ""),
                        "mother_name": borrower.get("motherName", ""),
                    }
                    phone_number = borrower.get("phoneNumber", "")

            # Se não encontrou telefone, tenta extrair de outras fontes
            if not phone_number and "celular" in original_request_dict:
                phone_number = original_request_dict.get("celular", "")

            # Atualize o telefone no extracted_customer
            if phone_number:
                extracted_customer["phone"] = phone_number

            # Extrair dados de endereço e outros detalhes
            address = {}
            if original_request_dict:
                if "address" in original_request_dict:
                    address_data = original_request_dict["address"]
                    address = {
                        "zipCode": address_data.get("zip_code", ""),
                        "street": address_data.get("street", ""),
                        "number": address_data.get("number", ""),
                        "neighborhood": address_data.get("neighborhood", ""),
                        "city": address_data.get("city", ""),
                        "state": address_data.get("state", ""),
                        "complement": address_data.get("complement", ""),
                    }

            # Extrair dados bancários
            bank_data = {}
            if original_request_dict:
                if "bank_data" in original_request_dict:
                    bank = original_request_dict["bank_data"]
                    bank_data = {
                        "bankCode": bank.get("bank_code", ""),
                        "branchNumber": bank.get("branch_number", ""),
                        "accountNumber": bank.get("account_number", ""),
                        "accountDigit": bank.get("account_digit", ""),
                        "accountType": bank.get("account_type", ""),
                    }
                elif "disbursementBankAccount" in original_request_dict:
                    bank = original_request_dict["disbursementBankAccount"]
                    bank_data = {
                        "bankCode": bank.get("bankCode", ""),
                        "branchNumber": bank.get("branchNumber", ""),
                        "accountNumber": bank.get("accountNumber", ""),
                        "accountDigit": bank.get("accountDigit", ""),
                        "accountType": bank.get("accountType", ""),
                    }

            # Extrair dados da simulação de forma correta
            sim_values = {}
            if simulation_data:
                # Primeiro, obtenha o valor correto da simulação
                available_amount = ""
                if "available_amount" in simulation_data:
                    available_amount = simulation_data["available_amount"]
                elif (
                    "simulation_data" in simulation_data
                    and "available_amount" in simulation_data["simulation_data"]
                ):
                    available_amount = simulation_data["simulation_data"][
                        "available_amount"
                    ]
                interest_rate = ""
                if "interest_rate" in simulation_data:
                    interest_rate = simulation_data["interest_rate"]
                elif (
                    "simulation_data" in simulation_data
                    and "interest_rate" in simulation_data["simulation_data"]
                ):
                    interest_rate = simulation_data["simulation_data"]["interest_rate"]

                # Para IOF
                iof_fee = ""
                if "iof_amount" in simulation_data:
                    iof_fee = simulation_data["iof_amount"]
                elif (
                    "simulation_data" in simulation_data
                    and "iof_amount" in simulation_data["simulation_data"]
                ):
                    iof_fee = simulation_data["simulation_data"]["iof_amount"]

                sim_values = {
                    "total_released": str(available_amount),
                    "total_to_pay": str(available_amount),
                    "interest_rate": str(interest_rate),
                    "iof_fee": str(iof_fee),
                }

            if phone_number:
                clean_phone = "".join(c for c in phone_number if c.isdigit())
                if len(clean_phone) >= 10:
                    formatted_phone = clean_phone
                else:
                    formatted_phone = phone_number
            else:
                formatted_phone = ""

            from memory import MongoDBMemoryManager

            memory_manager = MongoDBMemoryManager()
            sessions_collection = memory_manager.db["sessions"]

            clean_customer_data = {
                "customer_info": {
                    **extracted_customer,
                    "phone": formatted_phone,
                },
                "address": address,
                "bank_data": bank_data,
                "proposal_sent": True,
                "formalization_initiated": False,
                "proposal_created_at": datetime.utcnow(),
            }

            session_id = formatted_phone if formatted_phone else financial_id
            sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "contract_number": result.contract_number,
                        "formalization_link": result.formalization_link,
                        "financial_id": financial_id,
                        "customer_data": clean_customer_data,
                        "simulation_data": sim_values,
                        "proposal_data": {
                            "contract_number": result.contract_number,
                            "formalization_link": result.formalization_link,
                            "created_at": datetime.utcnow(),
                            "total_released": sim_values.get("total_released", ""),
                        },
                        "timestamp": datetime.utcnow(),
                        "phone_number": extracted_customer.get("phone"),
                    }
                },
                upsert=True,
            )
            proposal_doc = {
                "financial_id": financial_id,
                "bank_name": result.bank_name,
                "contract_number": result.contract_number,
                "formalization_link": result.formalization_link,
                "customer_name": extracted_customer.get("name", ""),
                "customer_cpf": extracted_customer.get("cpf", ""),
                "customer_email": extracted_customer.get("email", ""),
                "customer_phone": extracted_customer.get("phone"),
                "phone_number": extracted_customer.get("phone"),
                "total_released": sim_values.get("total_released", ""),
                "total_to_pay": sim_values.get("total_released", ""),
                "interest_rate": sim_values.get("interest_rate", ""),
                "iof_fee": sim_values.get("iof_fee", ""),
                "stage": "formalize",
                "status": "PENDING_FORMALIZATION",
                "created_at": datetime.utcnow(),
                "customer_data": clean_customer_data,
                "simulation_data": sim_values,
                "success": result.success,
                "timestamp": result.timestamp,
            }

            self.proposals.update_one(
                {"financial_id": financial_id}, {"$set": proposal_doc}, upsert=True
            )

            if result.contract_number:
                self.proposals.update_one(
                    {"contract_number": result.contract_number},
                    {"$set": proposal_doc},
                    upsert=True,
                )

            logger.info(
                f"Proposta salva para {financial_id} com banco {result.bank_name} e dados completos"
            )

        except Exception as e:
            logger.error(f"Erro ao salvar proposta: {str(e)}")

    def get_proposal_history(
        self, financial_id: Optional[str] = None, contract_number: Optional[str] = None
    ) -> List[Dict]:
        """
        Recupera histórico de propostas por financial_id ou contract_number.
        Pelo menos um dos parâmetros deve ser fornecido.
        """
        if not financial_id and not contract_number:
            return []

        query = {}
        if financial_id:
            query["financial_id"] = financial_id
        if contract_number:
            query["contract_number"] = contract_number

        return list(
            self.proposals.find(
                query,
                {
                    "_id": 0,
                    "financial_id": 1,
                    "bank_name": 1,
                    "contract_number": 1,
                    "formalization_link": 1,
                    "success": 1,
                    "error_message": 1,
                    "timestamp": 1,
                },
            ).sort("timestamp", DESCENDING)
        )

    def get_all_proposals(
        self,
        page: int = 1,
        per_page: int = 10,
        bank_name: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> Dict:
        """Recupera todas as propostas com paginação e filtros"""
        query = {}
        if bank_name:
            query["bank_name"] = bank_name
        if success is not None:
            query["success"] = success

        # Calcula o total de documentos e páginas
        total_docs = self.proposals.count_documents(query)
        total_pages = ceil(total_docs / per_page)

        # Aplica paginação
        skip = (page - 1) * per_page
        cursor = (
            self.proposals.find(
                query,
                {
                    "_id": 0,
                    "financial_id": 1,
                    "bank_name": 1,
                    "contract_number": 1,
                    "formalization_link": 1,
                    "success": 1,
                    "error_message": 1,
                    "timestamp": 1,
                },
            )
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(per_page)
        )

        return {
            "items": list(cursor),
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_docs,
        }

    def list_providers(self) -> List[str]:
        """Lista todos os provedores de proposta disponíveis e ativos"""
        active_providers = self.get_active_banks("proposal")
        return [bank for bank in active_providers if bank in self._proposal_providers]

    def _get_simulation_data(self, financial_id: str) -> Dict[str, Any]:
        """Busca os dados de simulação associados ao financial_id"""
        try:
            # Busca na coleção de simulações
            simulation = self.simulations.find_one({"financial_id": financial_id})
            if simulation:
                # Remove o ID do MongoDB para evitar problemas de serialização
                if "_id" in simulation:
                    del simulation["_id"]

                logger.info(f"Dados de simulação encontrados para {financial_id}")
                return {
                    "simulation_data": simulation,
                    "available_amount": simulation.get("available_amount"),
                    "total_amount": simulation.get("total_amount"),
                    "interest_rate": simulation.get("interest_rate"),
                }

            # Busca na memória da sessão
            session_simulation = self.memory_manager.get_session_data(
                financial_id, "simulation_data"
            )
            if session_simulation:
                logger.info(
                    f"Dados de simulação encontrados na sessão para {financial_id}"
                )
                return {"simulation_data": session_simulation}

            logger.warning(f"Nenhum dado de simulação encontrado para {financial_id}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao buscar dados da simulação: {str(e)}")
            return {}

    def _get_customer_data(self, financial_id: str) -> Dict[str, Any]:
        """Busca os dados do cliente associados ao financial_id"""
        try:
            # Busca na memória da sessão
            customer_data = self.memory_manager.get_session_data(
                financial_id, "customer_data"
            )
            if customer_data:
                logger.info(f"Dados do cliente encontrados para {financial_id}")
                return {"customer_data": customer_data}

            # Tenta encontrar por sessão que tenha este financial_id
            sessions = self.db["sessions"].find_one({"financial_id": financial_id})
            if sessions:
                customer_data = sessions.get("customer_data", {})
                logger.info(
                    f"Dados do cliente encontrados na sessão para {financial_id}"
                )
                return {"customer_data": customer_data}

            # Também busca nas propostas anteriores (se for um reenvio)
            previous_proposal = self.proposals.find_one({"financial_id": financial_id})
            if previous_proposal:
                customer_data = previous_proposal.get("customer_details", {})
                if customer_data:
                    logger.info(
                        f"Dados do cliente encontrados em proposta anterior para {financial_id}"
                    )
                    return {"customer_data": customer_data}

            # Busca também diretamente na sessão pelo financial_id como session_id
            # (alguns sistemas usam o financial_id como session_id)
            session = self.db["sessions"].find_one({"session_id": financial_id})
            if session:
                customer_data = session.get("customer_data", {})
                logger.info(
                    f"Dados do cliente encontrados na sessão com ID {financial_id}"
                )
                return {"customer_data": customer_data}

            logger.warning(f"Nenhum dado de cliente encontrado para {financial_id}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao buscar dados do cliente: {str(e)}")
            return {}

    def _get_active_table_for_bank(self, bank_name: str) -> Optional[str]:
        """
        Retorna o ID da tabela ativa para um banco específico

        Args:
            bank_name: Nome do banco

        Returns:
            ID da tabela ativa ou None se não encontrar
        """
        try:
            config = self.db["table_configs"].find_one({})
            if not config or "tables" not in config:
                return None

            for table_id, table_info in config["tables"].items():
                if table_info.get("bank_name") == bank_name and table_info.get(
                    "active", True
                ):
                    return table_id

            return None
        except Exception as e:
            logger.error(f"Erro ao obter tabela ativa para banco {bank_name}: {str(e)}")
            return None
