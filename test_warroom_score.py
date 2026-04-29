from flv.warroom.engine import (
    CRITICAL_RISK_ALERT_TYPE,
    CRITICAL_RISK_THRESHOLD,
    SovereignEntity,
    build_critical_risk_alert,
    classify_score_color,
    compute_score_soberano_v2,
    is_critical_risk_score,
)


def test_score_soberano_formula_uses_requested_weights():
    score = compute_score_soberano_v2({
        "Volume_Operacional": 10,
        "Geografia": 8,
        "Risco_Insumo": 6,
        "Growth": 4,
    })

    assert score == 7.9


def test_score_above_threshold_generates_critical_risk_state():
    assert is_critical_risk_score(CRITICAL_RISK_THRESHOLD) is False
    assert is_critical_risk_score(CRITICAL_RISK_THRESHOLD + 0.01) is True
    assert classify_score_color(CRITICAL_RISK_THRESHOLD + 0.01) == "vermelho"


def test_critical_risk_alert_payload_is_report_ready():
    entity = SovereignEntity(
        entity_type="distributor",
        entity_id="123",
        name="Fornecedor Teste",
        lat=None,
        lon=None,
        country="BR",
        state_uf="SP",
        score=8.75,
        components={
            "Volume_Operacional": 9,
            "Importancia_Geografica": 9,
            "Risco_Insumo": 8.5,
            "Growth_Potential": 7,
        },
        status_color="vermelho",
    )

    alert = build_critical_risk_alert(entity, "update", 8.2)

    assert alert["type"] == CRITICAL_RISK_ALERT_TYPE
    assert alert["severity"] == "vermelho"
    assert alert["score_after"] == 8.75
    assert alert["threshold"] == CRITICAL_RISK_THRESHOLD
    assert "Risco Crítico" in alert["message"]
