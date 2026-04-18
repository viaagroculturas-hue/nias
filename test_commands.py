#!/usr/bin/env python3
"""
Script de Teste NIA$ - Valida todos os comandos do sistema
"""

import requests
import re
import sys

BASE_URL = "http://localhost:8080"

def test_file_exists():
    """Testa se o arquivo index.html existe e é acessível"""
    try:
        response = requests.get(f"{BASE_URL}/index.html", timeout=10)
        if response.status_code == 200:
            print("✅ Arquivo index.html acessível")
            return response.text
        else:
            print(f"❌ Erro ao acessar index.html: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def test_javascript_functions(html_content):
    """Testa se todas as funções JavaScript estão definidas"""
    functions = [
        'function showPanel(',
        'function toggleLayer(',
        'function setZoomLevel(',
        'function setTheme(',
        'function showPolosMap(',
        'function closePolosMap(',
        'function initMap(',
        'function initBioCommand(',
        'function initMunicipal(',
        'function initSankey(',
        'function bcTrocarCultura(',
        'function bcSetRiskMode(',
        'function bcToggleLayer(',
        'function pushAnomalyEvent(',
    ]
    
    print("\n📋 Testando funções JavaScript:")
    all_ok = True
    for func in functions:
        if func in html_content:
            print(f"  ✅ {func}")
        else:
            print(f"  ❌ {func} - NÃO ENCONTRADA")
            all_ok = False
    return all_ok

def test_onclick_handlers(html_content):
    """Testa se todos os handlers onclick estão configurados"""
    handlers = [
        ("showPanel('overview')", "Visão Geral"),
        ("showPanel('municipal')", "Municipal"),
        ("showPanel('biocommand')", "Bio-Command"),
        ("showPanel('oferta')", "Mercado"),
        ("showPanel('flv_insights')", "FLV"),
        ("showPanel('warroom')", "War Room"),
        ("showPanel('predictix')", "PREDICTIX"),
        ("showPanel('chat')", "Assistente IA"),
        ("showPanel('map')", "Mapa"),
        ("showPanel('logistica')", "Logística"),
        ("setTheme('dark')", "Tema Dark"),
        ("setTheme('light')", "Tema Light"),
        ("setTheme('cyber')", "Tema Cyber"),
        ("setZoomLevel(0)", "Zoom Z0"),
        ("setZoomLevel(1)", "Zoom Z1"),
        ("setZoomLevel(2)", "Zoom Z2"),
        ("showPolosMap()", "Mapa de Polos"),
        ("bcTrocarCultura('soja')", "Cultura Soja"),
        ("bcTrocarCultura('milho')", "Cultura Milho"),
        ("bcTrocarCultura('trigo')", "Cultura Trigo"),
        ("bcTrocarCultura('arroz')", "Cultura Arroz"),
        ("bcTrocarCultura('cafe')", "Cultura Café"),
        ("bcTrocarCultura('cana')", "Cultura Cana"),
        ("bcTrocarCultura('pecuaria_corte')", "Cultura Pecuária"),
        ("bcTrocarCultura('all')", "Cultura Todas"),
        ("bcSetRiskMode('radar')", "Sonar Radar"),
        ("bcSetRiskMode('impact')", "Sonar Impacto"),
        ("bcSetRiskMode('off')", "Sonar Off"),
    ]
    
    print("\n📋 Testando handlers onclick:")
    all_ok = True
    for handler, desc in handlers:
        if handler in html_content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - {handler}")
            all_ok = False
    return all_ok

def test_layer_checkboxes(html_content):
    """Testa se todos os checkboxes de camada estão configurados"""
    layers = [
        ("toggleLayer('soja'", "Camada Soja"),
        ("toggleLayer('milho'", "Camada Milho"),
        ("toggleLayer('cana'", "Camada Cana"),
        ("toggleLayer('pastagem'", "Camada Pastagem"),
        ("toggleLayer('horti'", "Camada Horti"),
        ("toggleLayer('alertas'", "Camada Alertas"),
        ("toggleLayer('portos'", "Camada Portos"),
        ("toggleLayer('tomate-mesa'", "Camada Tomate Mesa"),
        ("toggleLayer('tomate-ind'", "Camada Tomate Ind"),
        ("toggleLayer('planet'", "Camada Planet"),
        ("toggleLayer('country-borders'", "Camada Contornos"),
        ("bcToggleLayer('sonar-poi'", "BC Camada Sonar"),
        ("bcToggleLayer('portos'", "BC Camada Portos"),
        ("bcToggleLayer('planet'", "BC Camada Planet"),
        ("bcToggleLayer('sar'", "BC Camada SAR"),
    ]
    
    print("\n📋 Testando checkboxes de camadas:")
    all_ok = True
    for layer, desc in layers:
        if layer in html_content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - {layer}")
            all_ok = False
    return all_ok

def test_south_america_data(html_content):
    """Testa se os dados da América do Sul estão presentes"""
    countries = [
        ("country:'CO'", "Colômbia"),
        ("country:'VE'", "Venezuela"),
        ("country:'AR'", "Argentina"),
        ("country:'PY'", "Paraguai"),
        ("country:'UY'", "Uruguai"),
        ("country:'CL'", "Chile"),
        ("country:'PE'", "Peru"),
        ("country:'EC'", "Equador"),
        ("country:'BO'", "Bolívia"),
    ]
    
    print("\n📋 Testando dados dos países sul-americanos:")
    all_ok = True
    for code, name in countries:
        if code in html_content:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} - {code}")
            all_ok = False
    return all_ok

def test_map_config(html_content):
    """Testa se as configurações do mapa estão corretas"""
    print("\n📋 Testando configurações do mapa:")
    all_ok = True
    
    # Verificar centro do mapa
    if "center: [-10, -60]" in html_content or "center:[-10,-60]" in html_content:
        print("  ✅ Centro do mapa ajustado para América do Sul")
    else:
        print("  ⚠️  Centro do mapa pode não cobrir toda a América do Sul")
    
    # Verificar zoom
    if "zoom: 3" in html_content:
        print("  ✅ Zoom 3 configurado")
    else:
        print("  ⚠️  Zoom pode não estar configurado para visão continental")
    
    # Verificar contornos dos países
    if "southAmericaCountries" in html_content:
        print("  ✅ Contornos dos países definidos")
    else:
        print("  ❌ Contornos dos países não encontrados")
        all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("🧪 TESTE DE COMANDOS NIA$")
    print("=" * 60)
    
    html_content = test_file_exists()
    if not html_content:
        sys.exit(1)
    
    results = []
    results.append(("Funções JavaScript", test_javascript_functions(html_content)))
    results.append(("Handlers onclick", test_onclick_handlers(html_content)))
    results.append(("Checkboxes de camadas", test_layer_checkboxes(html_content)))
    results.append(("Dados América do Sul", test_south_america_data(html_content)))
    results.append(("Configurações do mapa", test_map_config(html_content)))
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("=" * 60)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM - Verifique os detalhes acima")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
