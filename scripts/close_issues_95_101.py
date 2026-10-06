import subprocess
import urllib.request
import json
import sys
import time

REPO = "vitorbuss04/splendid-hypatia"
API_BASE = f"https://api.github.com/repos/{REPO}"

def get_token():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True
    )
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line[9:]
    return None

RESOLUTIONS = {
    95: {
        "comment": """### ✅ Resolução - Issue #95

**Causa Raiz**:
Ao importar arquivos 3MF ou G-Code individualmente no card de uma placa existente (`handleSinglePlateFile`), os analisadores extraíam com sucesso os parâmetros de manufatura (`nozzle_diameter`, `layer_height` e `bed_type`), mas esses campos não eram atribuídos ao objeto `state.currentPlates[plateIdx]`, sendo descartados e mantendo os valores antigos/padrão.

**Correção Implementada**:
- Em `frontend/js/app.js` (`handleSinglePlateFile`), adicionada a atribuição explícita de `nozzle_diameter`, `layer_height` e `bed_type` para `state.currentPlates[plateIdx]` tanto no bloco de importação 3MF quanto no bloco de G-Code.

**Verificação**:
- Testes automatizados em `tests/test_frontend_inputs.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    96: {
        "comment": """### ✅ Resolução - Issue #96

**Causa Raiz**:
No leitor de arquivos 3MF (`frontend/js/parsers/threemf.js`), o tempo de impressão convertido em horas aplicava diretamente `toFixed(2)`, arredondando para zero (`0.0h`) peças de calibração, torres de teste ou purgas rápidas com duração inferior a 18 segundos.

**Correção Implementada**:
- Em `frontend/js/parsers/threemf.js`, implementado fallback de precisão com `toFixed(4)` quando `roundedHours === 0 && printTimeHours > 0`, tanto no nó principal de placa quanto no fallback de configurações de fatiamento.
- Atualizado espelho `python_parse_3mf` em `tests/test_parsers.py`.

**Verificação**:
- Testes automatizados `test_3mf_sub_minute_calibration_print_hours` em `tests/test_parsers.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    97: {
        "comment": """### ✅ Resolução - Issue #97

**Causa Raiz**:
No leitor de arquivos 3MF (`frontend/js/parsers/threemf.js`), o laço sobre os nós de filamento utilizava a condição `if (flushG > 0 && purgeGrams === 0) purgeGrams += flushG;`. Ao processar o primeiro filamento, `purgeGrams` se tornava maior que zero, fazendo com que todos os filamentos subsequentes de impressões multi-materiais (Bambu AMS) tivessem suas purgas ignoradas.

**Correção Implementada**:
- Em `frontend/js/parsers/threemf.js`, implementada a soma cumulativa `filamentFlushSum += flushG` sobre todos os filamentos da placa quando o peso de purga global não é fixado pelo cabeçalho do fatiador (`!hasMetadataPurge`), atribuindo o somatório total correto.
- Atualizado espelho `python_parse_3mf` em `tests/test_parsers.py`.

**Verificação**:
- Teste automatizado `test_3mf_multi_filament_flush_accumulation` em `tests/test_parsers.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    98: {
        "comment": """### ✅ Resolução - Issue #98

**Causa Raiz**:
O gerador de relatórios ReportLab (`backend/pdf_service.py`) não incluía o campo de anotações/especificações técnicas (`notes`) dos itens de insumos/componentes (BOM) nem na Proposta Comercial do Cliente nem no Checklist de Montagem da Ficha Técnica de Produção.

**Correção Implementada**:
- Em `backend/pdf_service.py`, adicionada a renderização descritiva do campo `notes` sob o nome do componente em estilo tipográfico refinado com formatação segura (`html.escape`), contemplando tanto a tabela de BOM da proposta comercial quanto o checklist da ficha técnica de produção.

**Verificação**:
- Teste automatizado `test_pdf_bom_notes_rendered_issue_98` em `tests/test_api.py`.
- Script de integração `scripts/test_pdf_bom_notes.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    99: {
        "comment": """### ✅ Resolução - Issue #99

**Causa Raiz**:
No modal de cadastro e edição de impressoras (`handleSavePrinter` em `frontend/js/app.js`), não havia validação no cliente para vida útil estimada estritamente positiva (`lifespan_hours > 0`) nem para valores negativos nos custos operacionais, potência e taxas, disparando erro HTTP 422 Unprocessable Entity da API sem feedback claro.

**Correção Implementada**:
- Em `frontend/js/app.js` (`handleSavePrinter`), adicionadas validações de integridade no frontend com toasts específicos e foco automático nos campos correspondentes para `lifespan_hours > 0` e valores não-negativos de aquisição, potência, manutenção e energia.

**Verificação**:
- Testes automatizados em `tests/test_frontend_inputs.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    100: {
        "comment": """### ✅ Resolução - Issue #100

**Causa Raiz**:
No formulário de Preferências da Oficina (`handleSavePreferences` em `frontend/js/app.js`), valores fora do intervalo permitido pela API (como alíquota de impostos >= 100% ou taxas negativas) eram submetidos diretamente, causando rejeição com erro HTTP 422 sem identificar o campo inválido.

**Correção Implementada**:
- Em `frontend/js/app.js` (`handleSavePreferences`), adicionadas validações de intervalo para alíquota de impostos (0% a 99%) e garantia de valores não-negativos para margem de lucro, taxa de perda, tarifas de energia e taxas horárias de modelagem CAD e pós-processamento.

**Verificação**:
- Testes automatizados em `tests/test_frontend_inputs.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
    101: {
        "comment": """### ✅ Resolução - Issue #101

**Causa Raiz**:
Na geração da Ficha Técnica de Produção em PDF (`backend/pdf_service.py`), quando um projeto continha apenas insumos (BOM) e horas de serviço (sem nenhuma placa 3D cadastrada), a tabela de parâmetros operacionais de produção era gerada apenas com o cabeçalho de colunas sem nenhuma linha de conteúdo.

**Correção Implementada**:
- Em `backend/pdf_service.py`, adicionada a verificação `if not plates_details:` na visualização técnica, incluindo linha explicativa padronizada "Nenhuma peça impressa configurada" com traços informativos.

**Verificação**:
- Teste automatizado `test_pdf_technical_empty_plates_note_issue_101` em `tests/test_api.py`.
- 186/186 testes passando na suíte de regressão.""",
    },
}

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado via git credential!")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "IssueCloserV11"
    }

    for issue_num, data in RESOLUTIONS.items():
        print(f"\n--- Fechando Issue #{issue_num} ---")
        
        # 1. Enviar comentário de resolução
        comment_url = f"{API_BASE}/issues/{issue_num}/comments"
        comment_payload = json.dumps({"body": data["comment"]}).encode("utf-8")
        req_comment = urllib.request.Request(comment_url, data=comment_payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req_comment) as resp:
                print(f" -> Comentário de resolução publicado na Issue #{issue_num} (status {resp.status})")
        except urllib.error.HTTPError as e:
            print(f" -> Erro ao postar comentário na Issue #{issue_num}: HTTP {e.code}")
            continue

        time.sleep(1.0)

        # 2. Fechar a issue
        close_url = f"{API_BASE}/issues/{issue_num}"
        close_payload = json.dumps({"state": "closed", "state_reason": "completed"}).encode("utf-8")
        req_close = urllib.request.Request(close_url, data=close_payload, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req_close) as resp:
                print(f" -> Issue #{issue_num} fechada com sucesso como 'completed' (status {resp.status})")
        except urllib.error.HTTPError as e:
            print(f" -> Erro ao fechar Issue #{issue_num}: HTTP {e.code}")

        time.sleep(1.0)

    print("\nProcessamento de fechamento de issues concluído!")

if __name__ == "__main__":
    main()
