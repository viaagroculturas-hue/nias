"""
Serviço de notificação — WhatsApp (Twilio ou Z-API) + SMS.
Destinatários configurados via env vars, nunca hardcoded.
"""
import logging
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _destinos_whatsapp() -> list[str]:
    raw = settings.notificacao_destinos_whatsapp.strip()
    if not raw:
        return []
    return [n.strip() for n in raw.split(",") if n.strip()]


def _destinos_sms() -> list[str]:
    raw = settings.notificacao_destinos_sms.strip()
    if not raw:
        return []
    return [n.strip() for n in raw.split(",") if n.strip()]


class NotificacaoService:

    async def enviar_whatsapp_resumo(self, relatorio) -> bool:
        msg = self._formatar_resumo_whatsapp(relatorio)
        return await self._enviar_whatsapp(msg)

    async def enviar_terra(self, terra) -> bool:
        msg = self._formatar_terra(terra)
        ok_wa  = await self._enviar_whatsapp(msg, urgente=True)
        ok_sms = await self._enviar_sms(msg[:1600])
        return ok_wa or ok_sms

    async def enviar_alerta(self, alerta) -> bool:
        """Alertas críticos não-TERRA — só WhatsApp."""
        if alerta.nivel != "critico":
            return False
        msg = (
            f"*VIGÍA — ALERTA CRÍTICO*\n\n"
            f"{alerta.titulo}\n\n"
            f"{alerta.descricao}\n\n"
            f"→ {alerta.acao_recomendada}\n"
            f"Confiança: {alerta.confianca_pct}%"
        )
        return await self._enviar_whatsapp(msg)

    # ── Internos ──────────────────────────────────────────────────

    async def _enviar_whatsapp(self, msg: str, urgente: bool = False) -> bool:
        destinos = _destinos_whatsapp()
        if not destinos:
            logger.warning("NOTIF: nenhum destino WhatsApp configurado (NOTIFICACAO_DESTINOS_WHATSAPP)")
            return False

        resultados = []
        for numero in destinos:
            if settings.twilio_account_sid and settings.twilio_auth_token:
                ok = await self._twilio_whatsapp(msg, numero)
            elif settings.zapi_instance_id and settings.zapi_token:
                ok = await self._zapi_whatsapp(msg, numero)
            else:
                logger.warning("NOTIF: nenhum provedor WhatsApp configurado (Twilio ou Z-API)")
                return False
            resultados.append(ok)

        return any(resultados)

    async def _enviar_sms(self, msg: str) -> bool:
        destinos = _destinos_sms()
        if not destinos:
            return False
        if not settings.twilio_account_sid:
            return False

        resultados = []
        for numero in destinos:
            ok = await self._twilio_sms(msg, numero)
            resultados.append(ok)
        return any(resultados)

    async def _twilio_whatsapp(self, msg: str, numero: str) -> bool:
        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            destino = f"whatsapp:{numero}" if not numero.startswith("whatsapp:") else numero
            client.messages.create(
                body=msg,
                from_=settings.twilio_whatsapp_from,
                to=destino,
            )
            logger.info(f"NOTIF WhatsApp Twilio → {numero[:8]}***")
            return True
        except Exception as e:
            logger.error(f"Twilio WhatsApp {numero[:8]}*** erro: {e}")
            return False

    async def _twilio_sms(self, msg: str, numero: str) -> bool:
        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            from_num = settings.twilio_sms_from or settings.twilio_whatsapp_from.replace("whatsapp:", "")
            client.messages.create(body=msg, from_=from_num, to=numero)
            logger.info(f"NOTIF SMS → {numero[:8]}***")
            return True
        except Exception as e:
            logger.error(f"SMS {numero[:8]}*** erro: {e}")
            return False

    async def _zapi_whatsapp(self, msg: str, numero: str) -> bool:
        try:
            import httpx
            # Normalizar — Z-API espera apenas dígitos
            phone = numero.lstrip("+").replace(" ", "")
            url = (
                f"https://api.z-api.io/instances/{settings.zapi_instance_id}"
                f"/token/{settings.zapi_token}/send-text"
            )
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(url, json={"phone": phone, "message": msg})
                r.raise_for_status()
            logger.info(f"NOTIF WhatsApp Z-API → {phone[:8]}***")
            return True
        except Exception as e:
            logger.error(f"Z-API {numero[:8]}*** erro: {e}")
            return False

    # ── Formatadores ─────────────────────────────────────────────

    def _formatar_terra(self, terra) -> str:
        pat = float(terra.patrimonio_em_risco or 0)
        return (
            f"*TERRA.*\n\n"
            f"*{terra.cultura.replace('_', ' ').upper()}*\n\n"
            f"{terra.situacao}\n\n"
            f"⏱ Janela: *{terra.janela_horas}h*\n"
            f"💰 Patrimônio em risco: *R$ {pat:,.0f}*\n"
            f"✅ Confiança: {terra.confianca_pct}%\n\n"
            f"*AÇÃO IMEDIATA:*\n{terra.acao_exata}\n\n"
            f"Fontes: {', '.join(str(f) for f in (terra.fontes or []))}"
        )

    def _formatar_resumo_whatsapp(self, r) -> str:
        criticos = len(r.alertas_criticos or [])
        acoes    = r.acoes_do_dia or []
        acao1    = acoes[0]["titulo"] if acoes else "—"
        data_str = r.data_referencia.strftime("%d/%m") if r.data_referencia else ""
        return (
            f"*VIGÍA · {data_str}*\n"
            f"🔴 {criticos} alertas críticos\n"
            f"📌 {acao1}\n\n"
            f"Abra o VIGÍA para o relatório completo."
        )
