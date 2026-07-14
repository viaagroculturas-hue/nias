from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Date, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class RecomendacaoVigia(Base):
    __tablename__ = "recomendacao_vigia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String(100))
    titulo = Column(String(255))
    descricao = Column(String)
    justificativa = Column(String)
    dados_utilizados = Column(JSONB)
    fontes = Column(JSONB)
    impacto_financeiro_estimado = Column(Numeric(14, 2))
    confianca_pct = Column(Numeric(5, 2))
    prazo_acao = Column(TIMESTAMP(timezone=True))
    nivel_urgencia = Column(String(20))
    talhao_id = Column(UUID(as_uuid=True), ForeignKey("talhao.id"))
    safra_id = Column(UUID(as_uuid=True), ForeignKey("safra.id"))
    tarefa_gerada_id = Column(UUID(as_uuid=True), ForeignKey("tarefa_operacional.id"))
    status = Column(String(50), default="pendente")
    resultado_real = Column(String)
    acuracia_pct = Column(Numeric(5, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    talhao = relationship("Talhao", back_populates="recomendacoes")
    safra = relationship("Safra", back_populates="recomendacoes")
    tarefa_gerada = relationship("TarefaOperacional", back_populates="recomendacao",
                                 foreign_keys=[tarefa_gerada_id])
    aprendizados = relationship("AprendizadoVigia", back_populates="recomendacao")


class RelatórioManha(Base):
    __tablename__ = "relatorio_manha"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_referencia = Column(Date, nullable=False)
    gerado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    resumo_executivo = Column(String)
    alertas_criticos = Column(JSONB)
    alertas_atencao = Column(JSONB)
    oportunidades = Column(JSONB)
    mercado_snapshot = Column(JSONB)
    clima_snapshot = Column(JSONB)
    enso_snapshot = Column(JSONB)
    acoes_do_dia = Column(JSONB)          # sempre exatamente 3
    municipios_monitorados = Column(Integer)
    alertas_gerados = Column(Integer)
    fontes_consultadas = Column(JSONB)
    tempo_geracao_ms = Column(Integer)
    enviado_whatsapp = Column(Boolean, default=False)
    enviado_email = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class GritoTerra(Base):
    __tablename__ = "grito_terra"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alerta_id = Column(UUID(as_uuid=True), ForeignKey("alerta_climatico.id"))
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    cultura = Column(String(100))
    situacao = Column(String, nullable=False)
    risco = Column(String, nullable=False)
    janela_horas = Column(Integer, nullable=False)
    acao_exata = Column(String, nullable=False)
    impacto_financeiro = Column(Numeric(14, 2))
    confianca_pct = Column(Numeric(5, 2))
    fontes = Column(JSONB)
    disparado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    notificados = Column(JSONB)
    vidas_em_risco = Column(Boolean, default=False)
    patrimonio_em_risco = Column(Numeric(14, 2))
    resolvido = Column(Boolean, default=False)
    resolvido_em = Column(TIMESTAMP(timezone=True))
    resultado = Column(String)

    alerta = relationship("AlertaClimatico", back_populates="grito_terra")


class DadoVerificado(Base):
    __tablename__ = "dado_verificado"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String(100))
    entidade_ref = Column(String(100))
    entidade_id = Column(UUID(as_uuid=True))
    campo = Column(String(100))
    valor_final = Column(Numeric(20, 6))
    unidade = Column(String(20))
    fontes = Column(JSONB)
    n_fontes_independentes = Column(Integer)
    desvio_entre_fontes_pct = Column(Numeric(6, 2))
    score_confianca = Column(Integer)
    status_verificacao = Column(String(50))
    anomalia_detectada = Column(Boolean, default=False)
    z_score = Column(Numeric(6, 3))
    revisao_humana = Column(Boolean, default=False)
    hash_dado_raw = Column(String(64))
    agente_coletor = Column(String(100))
    data_referencia = Column(Date)
    proximo_refresh = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AuditoriaVigia(Base):
    __tablename__ = "auditoria_vigia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entidade = Column(String(100))
    entidade_id = Column(UUID(as_uuid=True))
    acao = Column(String(100))
    dados_anteriores = Column(JSONB)
    dados_novos = Column(JSONB)
    agente = Column(String(100))
    ip = Column(String(45))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ExecucaoAutomacao(Base):
    __tablename__ = "execucao_automacao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255))
    tipo = Column(String(100))
    status = Column(String(50))
    iniciado_em = Column(TIMESTAMP(timezone=True))
    concluido_em = Column(TIMESTAMP(timezone=True))
    registros_processados = Column(Integer)
    erros = Column(Integer, default=0)
    resultado = Column(JSONB)
    erro_descricao = Column(String)
    proxima_execucao = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AprendizadoVigia(Base):
    __tablename__ = "aprendizado_vigia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recomendacao_id = Column(UUID(as_uuid=True), ForeignKey("recomendacao_vigia.id"))
    tipo_previsao = Column(String(100))
    valor_previsto = Column(JSONB)
    valor_real = Column(JSONB)
    erro_percentual = Column(Numeric(8, 4))
    ajuste_aplicado = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    recomendacao = relationship("RecomendacaoVigia", back_populates="aprendizados")


class SeedStatus(Base):
    __tablename__ = "seed_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    etapa = Column(Integer, nullable=False)
    nome = Column(String(255))
    status = Column(String(50))   # pendente | rodando | concluido | erro
    registros_total = Column(Integer)
    registros_processados = Column(Integer)
    pct_concluido = Column(Numeric(5, 2))
    iniciado_em = Column(TIMESTAMP(timezone=True))
    concluido_em = Column(TIMESTAMP(timezone=True))
    erro = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
