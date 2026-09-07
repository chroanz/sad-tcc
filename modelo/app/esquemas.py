"""Modelos Pydantic v2 do contrato ``POST /otimizar``.

Os nomes dos campos JSON são exatamente os de ``docs/contrato-otimizacao.md`` — o contrato
é imutável e a API Go é implementada de forma independente contra ele. Toda violação das
regras de validação do contrato vira ``HTTP 422`` automaticamente, pois os validadores
levantam ``ValueError`` durante a desserialização do corpo da requisição.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.configuracao import CONFIGURACAO


class StatusOtimizacao(str, Enum):
    """Status agregado devolvido ao cliente.

    ``OTIMO`` indica otimalidade provada pelo CP-SAT, ``VIAVEL`` indica solução encontrada
    com o limite de tempo atingido e ``INVIAVEL`` cobre os demais casos (nenhuma solução).
    """

    OTIMO = "OTIMO"
    VIAVEL = "VIAVEL"
    INVIAVEL = "INVIAVEL"


class MotivoNaoAtendido(str, Enum):
    """Motivo pelo qual um item da lista não recebeu alocação."""

    SEM_CANDIDATO = "SEM_CANDIDATO"
    SEM_CANDIDATO_COM_ESTOQUE = "SEM_CANDIDATO_COM_ESTOQUE"


class Coordenada(BaseModel):
    """Ponto geográfico em graus decimais (WGS84)."""

    model_config = ConfigDict(extra="ignore")

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class MercadoEntrada(BaseModel):
    """Mercado considerado na instância, com sua localização."""

    model_config = ConfigDict(extra="ignore")

    mercado_id: int
    nome: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class CandidatoEntrada(BaseModel):
    """Oferta conhecida de um item em um mercado (preço vigente e estoque do snapshot)."""

    model_config = ConfigDict(extra="ignore")

    mercado_id: int
    marca_id: Optional[int] = None
    marca_nome: Optional[str] = None
    preco_unitario_centavos: int = Field(gt=0)
    quantidade_disponivel: float = Field(ge=0.0)


class ItemEntrada(BaseModel):
    """Item da lista de compras e suas ofertas candidatas."""

    model_config = ConfigDict(extra="ignore")

    item_id: int
    descricao: str
    quantidade: float = Field(gt=0.0)
    unidade: str
    candidatos: List[CandidatoEntrada] = Field(default_factory=list)

    @field_validator("candidatos")
    @classmethod
    def _validar_par_item_mercado_unico(
        cls, candidatos: List[CandidatoEntrada]
    ) -> List[CandidatoEntrada]:
        """Garante a regra 3 do contrato: o par (item, mercado) não se repete."""
        mercados = [candidato.mercado_id for candidato in candidatos]
        if len(set(mercados)) != len(mercados):
            raise ValueError(
                "o par (item_id, mercado_id) nao pode aparecer duas vezes em candidatos"
            )
        return candidatos


class RequisicaoOtimizacao(BaseModel):
    """Payload completo de ``POST /otimizar``.

    Os campos logísticos e o limite de tempo têm padrões vindos da configuração
    (``MODELO_*``), de modo que a API Go possa omiti-los.
    """

    model_config = ConfigDict(extra="ignore")

    origem: Coordenada
    peso_conveniencia: float = Field(ge=0.0)
    custo_por_visita_centavos: int = Field(
        default_factory=lambda: CONFIGURACAO.custo_por_visita_centavos, ge=0
    )
    custo_por_km_centavos: int = Field(
        default_factory=lambda: CONFIGURACAO.custo_por_km_centavos, ge=0
    )
    limite_tempo_segundos: float = Field(
        default_factory=lambda: CONFIGURACAO.limite_tempo_segundos, gt=0.0
    )
    mercados: List[MercadoEntrada]
    itens: List[ItemEntrada]

    @model_validator(mode="after")
    def _validar_identificadores(self) -> "RequisicaoOtimizacao":
        """Aplica as regras 1 e 2 do contrato: unicidade de IDs e referência válida."""
        identificadores_mercados = [mercado.mercado_id for mercado in self.mercados]
        if len(set(identificadores_mercados)) != len(identificadores_mercados):
            raise ValueError("mercado_id nao pode se repetir em mercados")

        identificadores_itens = [item.item_id for item in self.itens]
        if len(set(identificadores_itens)) != len(identificadores_itens):
            raise ValueError("item_id nao pode se repetir em itens")

        conhecidos = set(identificadores_mercados)
        for item in self.itens:
            for candidato in item.candidatos:
                if candidato.mercado_id not in conhecidos:
                    raise ValueError(
                        f"candidato do item {item.item_id} referencia o mercado "
                        f"{candidato.mercado_id}, ausente em mercados"
                    )
        return self


class ParadaRota(BaseModel):
    """Uma parada da rota sugerida, na ordem de visita."""

    ordem: int
    mercado_id: int
    nome: str
    distancia_do_anterior_km: float


class ItemComprado(BaseModel):
    """Item alocado a um mercado, com o preço e o custo efetivamente aplicados."""

    item_id: int
    descricao: str
    marca_id: Optional[int] = None
    marca_nome: Optional[str] = None
    quantidade: float
    unidade: str
    preco_unitario_centavos: int
    custo_centavos: int


class CompraPorMercado(BaseModel):
    """Agrupamento da recomendação: o que comprar em um mercado."""

    mercado_id: int
    nome: str
    subtotal_centavos: int
    itens: List[ItemComprado]


class ItemNaoAtendido(BaseModel):
    """Item da lista que ficou sem alocação, com o motivo."""

    item_id: int
    descricao: str
    motivo: MotivoNaoAtendido


class Economia(BaseModel):
    """Comparação da recomendação com o baseline de mercado único.

    Quando nenhum mercado cobre sequer um item atendido, os campos numéricos vêm nulos e
    ``observacao`` explica o motivo — a economia nunca é inventada.
    """

    mercado_unico_id: Optional[int] = None
    mercado_unico_nome: Optional[str] = None
    custo_mercado_unico_centavos: Optional[int] = None
    economia_centavos: Optional[int] = None
    economia_percentual: Optional[float] = None
    itens_comparados: int = 0
    comparacao_parcial: bool = False
    observacao: Optional[str] = None


class Diagnostico(BaseModel):
    """Telemetria do solver, usada nos experimentos da Fase 4."""

    status_solver: str
    tempo_solver_segundos: float
    quantidade_variaveis: int
    quantidade_restricoes: int


class RespostaOtimizacao(BaseModel):
    """Resposta de ``POST /otimizar``, campo a campo conforme o contrato."""

    status: StatusOtimizacao
    custo_itens_centavos: int
    custo_logistico_centavos: int
    custo_total_centavos: int
    valor_objetivo_centavos: int
    peso_conveniencia: float
    quantidade_mercados_visitados: int
    distancia_total_km: float
    rota: List[ParadaRota] = Field(default_factory=list)
    compras_por_mercado: List[CompraPorMercado] = Field(default_factory=list)
    itens_nao_atendidos: List[ItemNaoAtendido] = Field(default_factory=list)
    economia: Economia
    diagnostico: Diagnostico


class RespostaSaude(BaseModel):
    """Resposta de ``GET /saude``, consumida pelo healthcheck do Docker Compose."""

    status: str
    servico: str
    versao: str
