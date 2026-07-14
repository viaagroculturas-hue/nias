const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status, `${path} → ${res.status}`)
  return res.json()
}

// ── Seed ────────────────────────────────────────────────────────
export const seedApi = {
  status:  () => request<SeedStatus>('/api/seed/status'),
  iniciar: () => request<{ message: string; status: string }>('/api/seed/iniciar', { method: 'POST' }),
}

// ── Radar ───────────────────────────────────────────────────────
export const radarApi = {
  resumo:  () => request<RadarResumo>('/api/radar/'),
  alertas: (nivel?: string, limit = 50) =>
    request<Alerta[]>(`/api/radar/alertas?${nivel ? `nivel=${nivel}&` : ''}limit=${limit}`),
}

// ── Relatório ───────────────────────────────────────────────────
export const relatorioApi = {
  hoje:      () => request<RelatorioHoje>('/api/relatorio/hoje'),
  historico: (limit = 30) => request<any[]>(`/api/relatorio/historico?limit=${limit}`),
}

// ── Demanda ─────────────────────────────────────────────────────
export const demandaApi = {
  fatores: () => request<FatorDemanda[]>('/api/demanda/fatores'),
  eventos: () => request<EventoCalendario[]>('/api/demanda/eventos'),
}

// ── Clima ───────────────────────────────────────────────────────
export const climaApi = {
  enso:    () => request<EnsoStatus>('/api/clima/enso'),
  eventos: (limit = 50) => request<EventoClimatico[]>(`/api/clima/eventos?limit=${limit}`),
}

// ── Mercado ─────────────────────────────────────────────────────
export const mercadoApi = {
  cotacoes: (limit = 50) => request<Cotacao[]>(`/api/mercado/cotacoes?limit=${limit}`),
  rotas:    () => request<any[]>('/api/mercado/rotas'),
}

// ── Mapa ─────────────────────────────────────────────────────────
export const mapaApi = {
  municipios:   (pais?: string, limit = 500) =>
    request<Municipio[]>(`/api/mapa/municipios?limit=${limit}${pais ? `&pais=${pais}` : ''}`),
  mapeamentos:  (limit = 200) => request<any[]>(`/api/mapa/mapeamentos?limit=${limit}`),
  alertasGeo:   (nivel?: string, horas = 48) =>
    request<AlertaGeo[]>(`/api/mapa/alertas-geo?horas=${horas}${nivel ? `&nivel=${nivel}` : ''}`),
  ndviGeo:      (anomalia = false, limit = 500) =>
    request<NdviGeo[]>(`/api/mapa/ndvi-geo?limit=${limit}${anomalia ? '&anomalia=true' : ''}`),
}

// ── Inteligência ──────────────────────────────────────────────────
export const inteligenciaApi = {
  executarAgentes:    () => request<any>('/api/inteligencia/agentes/executar', { method: 'POST' }),
  testeNotificacao:   () => request<any>('/api/inteligencia/notificacao/teste', { method: 'POST' }),
  terraHistorico:     (limit = 20) => request<any[]>(`/api/inteligencia/terra/historico?limit=${limit}`),
}

// ── Health ───────────────────────────────────────────────────────
export const healthApi = {
  status: () => request<HealthStatus>('/api/health/'),
  ping:   () => request<{ status: string }>('/api/ping'),
}

// ─── Tipos ───────────────────────────────────────────────────────

export interface SeedStatus {
  iniciado: boolean
  pct_total: number
  concluido: boolean
  com_erro?: number
  etapas: SeedEtapa[]
}

export interface SeedEtapa {
  etapa: number
  nome: string
  status: 'pendente' | 'rodando' | 'concluido' | 'erro'
  pct_concluido: number
  registros_processados: number
  registros_total: number
  iniciado_em?: string
  concluido_em?: string
  erro?: string
}

export interface Alerta {
  id: string
  tipo: string
  nivel: 'info' | 'atencao' | 'critico' | 'terra'
  titulo: string
  descricao: string
  acao_recomendada: string
  confianca_pct: number
  impacto_financeiro: number
  fontes: string[]
  created_at: string
}

export interface RadarResumo {
  alertas: { critico: number; atencao: number; info: number }
  terra_ativo: TerraAtivo | null
  relatorio_hoje: RelatorioResumo | null
  ultima_atualizacao: string
}

export interface TerraAtivo {
  id: string
  cultura: string
  situacao: string
  risco: string
  janela_horas: number
  acao_exata: string
  patrimonio_em_risco: number
  confianca_pct: number
  disparado_em: string
}

export interface RelatorioResumo {
  resumo_executivo: string
  alertas_criticos: number
  acoes_do_dia: AcaoDia[]
  gerado_em: string
}

export interface RelatorioHoje {
  disponivel: boolean
  data_referencia?: string
  gerado_em?: string
  resumo_executivo?: string
  alertas_criticos?: Alerta[]
  alertas_atencao?: Alerta[]
  acoes_do_dia?: AcaoDia[]
  municipios_monitorados?: number
  alertas_gerados?: number
  enviado_whatsapp?: boolean
  enso_snapshot?: Record<string, any>
  mercado_snapshot?: Cotacao[]
}

export interface AcaoDia {
  titulo: string
  acao: string
  prazo: string
  origem: string
}

export interface FatorDemanda {
  id: string
  nome: string
  tipo: string
  impacto_direcao: 'reducao' | 'aumento'
  impacto_pct: number
  culturas_afetadas: string[]
  paises_afetados: string[]
  classes_renda_afetadas: string[]
  periodo_inicio?: string
  periodo_fim?: string
  fonte_dado: string
  confianca_pct: number
}

export interface EventoCalendario {
  id: string
  nome: string
  tipo: string
  pais: string
  data_inicio?: string
  data_fim?: string
  direcao: 'aumento' | 'reducao' | 'neutro'
  magnitude: string
  culturas_afetadas: string[]
}

export interface EnsoStatus {
  disponivel: boolean
  tipo_enso?: string
  oni_index?: number
  probabilidade_pct?: number
  nivel_alerta?: string
  culturas_em_risco?: string[]
  culturas_beneficiadas?: string[]
  recomendacoes?: string[]
  valido_ate?: string
  fonte?: string
}

export interface EventoClimatico {
  id: string
  tipo: string
  intensidade: string
  precipitacao_mm?: number
  temperatura_max?: number
  data_inicio?: string
  fonte: string
}

export interface Cotacao {
  id: string
  praca: string
  pais: string
  preco: number
  unidade: string
  data_cotacao: string
  variacao_pct?: number
  tendencia?: string
  fonte: string
}

export interface Municipio {
  id: string
  nome: string
  estado?: string
  pais: string
  lat?: number
  lon?: number
  regiao_agricola?: string
}

export interface HealthStatus {
  status: string
  sistema: string
  versao: string
  tempo_ms: number
  checks: Record<string, any>
}

export interface AlertaGeo {
  id: string
  tipo: string
  nivel: 'critico' | 'atencao' | 'info'
  titulo: string
  descricao: string
  acao_recomendada: string
  confianca_pct: number
  impacto_financeiro: number
  fontes: string[]
  lat: number
  lon: number
  municipio: string
  estado: string
  pais: string
  created_at: string
}

export interface NdviGeo {
  municipio_id: string
  municipio: string
  lat: number
  lon: number
  ndvi_medio: number
  fase_estimada: string
  anomalia_detectada: boolean
  data_imagem: string
  satelite: string
}
