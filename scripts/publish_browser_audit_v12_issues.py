import subprocess
import urllib.request
import urllib.error
import json
import sys
import time
from pathlib import Path

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

ISSUES_TO_CREATE = [
    {
        "title": "[BUG/CÁLCULO] updatePlateTime zera o tempo de impressão (print_time_hours = 0) de peças de calibração e testes rápidos ao salvar orçamento",
        "labels": ["bug", "calculation", "frontend"],
        "body": """### Descrição do Problema
Nas correções recentes (Issue #87 e Issue #96), os analisadores de G-Code e 3MF foram ajustados para preservar com precisão (`toFixed(4)`) o tempo de impressão de peças de calibração rápida, torres de teste ou purgas com duração inferior a 18 segundos (tempo < 0.005 horas).

No entanto, no editor de orçamentos, o card da placa divide a entrada de tempo em dois campos inteiros: Horas (`plate-time-h-${idx}`) e Minutos (`plate-time-m-${idx}`). Na função `renderPlates()`, o valor em minutos é derivado via `Math.round((plate.print_time_hours || 0) * 60)`. Para impressões de calibração com duração inferior a 30 segundos (ex: 15 segundos = 0.0042h), o arredondamento resulta em `0` horas e `0` minutos exibidos nos inputs.

Quando o operador clica no botão "Salvar Orçamento" (`saveCurrentProject` em `frontend/js/app.js`), a linha 2219 executa:
```javascript
if (state.currentPlates) {
    state.currentPlates.forEach((_, idx) => updatePlateTime(idx));
}
```
A função `updatePlateTime(idx)` lê os inputs de hora e minuto:
```javascript
const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
```
Como `h === 0` e `m === 0`, `state.currentPlates[idx].print_time_hours` é sobrescrito para `0.0`, descartando completamente o tempo real de impressão extraído do fatiador.

### Impacto
- **Perda de Custos de Máquina**: Ao salvar o projeto, o tempo da placa é permanentemente gravado como `0.0` no banco de dados. Os custos de depreciação, energia elétrica e manutenção preventiva da placa passam a ser calculados como R$ 0,00.
- **Divergência entre Leitura e Persistência**: O operador importa com sucesso o arquivo fatiado com tempo de calibração não-nulo, mas ao salvar a proposta comercial ou navegar para outra tela, o valor é zerado silenciosamente.

### Passos para Reproduzir
1. Abrir um orçamento no editor (`#/project-editor`).
2. Importar um arquivo G-code ou 3MF de calibração rápida (duração de 15 segundos).
3. Verificar que o card exibe tempo reduzido e custo associado.
4. Clicar em "Salvar Orçamento".
5. Abrir o orçamento novamente ou inspecionar a carga útil enviada à API (`/api/projects`): o campo `print_time_hours` foi persistido como `0.0`.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1646-1656 (`updatePlateTime`) e 2218-2220 (`saveCurrentProject`).

### Solução Proposta
Em `updatePlateTime(idx)`, se `h === 0` e `m === 0`, preservar o `print_time_hours` existente se ele for positivo e inferior a 1 minuto (`> 0 && < 1/60`):
```javascript
function updatePlateTime(idx) {
    const hElem = document.getElementById(`plate-time-h-${idx}`);
    const mElem = document.getElementById(`plate-time-m-${idx}`);
    if (!hElem && !mElem) {
        return;
    }
    const h = Math.max(0, parseInt(hElem?.value, 10) || 0);
    const m = Math.max(0, parseInt(mElem?.value, 10) || 0);
    const currentHours = state.currentPlates[idx]?.print_time_hours || 0;
    
    // Se inputs estão zerados mas a placa possui tempo submétrico positivo pré-existente (ex: fatiado < 30s), preservar
    if (h === 0 && m === 0 && currentHours > 0 && currentHours < (1 / 60)) {
        recalcLiveSummary();
        return;
    }

    state.currentPlates[idx].print_time_hours = Number((h + (m / 60)).toFixed(4));
    recalcLiveSummary();
}
```
"""
    },
    {
        "title": "[BUG/SLICER] Fallbacks de importação de 3MF (arquivos sem slice_info.xml e 3MF não-fatiados) omitem diâmetro do bico (nozzle_diameter), altura de camada (layer_height) e tipo de mesa (bed_type)",
        "labels": ["bug", "slicer-import", "frontend"],
        "body": """### Descrição do Problema
No analisador de arquivos 3MF (`frontend/js/parsers/threemf.js`), foram introduzidos os parâmetros operacionais de manufatura: `nozzle_diameter`, `layer_height` e `bed_type`. Eles são extraídos no bloco principal de `slice_info.xml` (linhas 113-177) e no fallback de arquivos G-code embarcados dentro do arquivo compactado (linhas 439-441).

No entanto, nos dois blocos de fallback subsequentes de `parse3mfMetadata`:
1. **Fallback 3** (linhas 454-486, arquivos com `model_settings.config`, `project_settings.config` ou `print_config.ini`): O objeto gerado contém apenas `name`, `print_time_hours`, `part_weight_g`, `purge_weight_g`, `filament_type`, `slicer_filament_profile`, `failure_margin_percent` e `quantity`. As propriedades `nozzle_diameter`, `layer_height` e `bed_type` são omitidas. Além disso, configurações como `nozzle_diameter = 0.4` ou `layer_height = 0.2` presentes no arquivo de configuração do Slic3r/Prusa/Orca são ignoradas.
2. **Fallback 4** (linhas 490-502, arquivos 3MF brutos sem metadados de fatiamento): O objeto de placa gerado igualmente omite `nozzle_diameter`, `layer_height` e `bed_type`.

### Impacto
- **Inconsistência de Estrutura de Placas**: Placas importadas através dos mecanismos de fallback não possuem os atributos de manufatura padronizados, gerando valores `undefined` em `state.currentPlates`.
- **Divergência na Ficha Técnica de Produção**: A Ficha Técnica em PDF e a exibição do card no editor ficam sujeitas a falhas ou ausência de dados de setup operacional.

### Passos para Reproduzir
1. Carregar um arquivo 3MF exportado pelo PrusaSlicer ou SuperSlicer contendo apenas `print_config.ini` (sem `slice_info.xml`).
2. Inspecionar o objeto retornado por `parse3mfMetadata`: as chaves `nozzle_diameter`, `layer_height` e `bed_type` estão ausentes.

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/threemf.js`: linhas 454-503.

### Solução Proposta
1. No Fallback 3, extrair `nozzle_diameter`, `layer_height` e `bed_type` do texto de configuração caso existam (usando expressões regulares semelhantes a `gcode.js`), com fallback para os padrões (`'0.4'`, `'0.20'`, `'Textured PEI'`).
2. No Fallback 4, inicializar explicitamente `nozzle_diameter: '0.4'`, `layer_height: '0.20'` e `bed_type: 'Textured PEI'`.
"""
    },
    {
        "title": "[UX/PDF] Ficha Técnica de Produção (PDF) omite desconto comercial e frete no Demonstrativo de Custos Internos, gerando divergência entre custo/margem e preço final sugerido",
        "labels": ["ux", "pdf", "backend"],
        "body": """### Descrição do Problema
No serviço gerador de documentos PDF (`backend/pdf_service.py`), ao gerar a Ficha Técnica de Produção (`doc_type="technical"`), a Seção 3 ("DEMONSTRATIVO DE CUSTOS INTERNOS E MARGENS", linhas 529-548) lista todos os componentes de custos:
- Consumo Total de Filamento
- Tempo Total de Máquina
- Energia Elétrica Estimada
- Depreciação de Máquina
- Reserva de Manutenção
- Custo Total BOM / Insumos
- Mão de Obra (CAD + Pós)
- Custos Indiretos / Overhead
- Custo Base Total (R$ base_cost)
- Margem de Lucro Alvo (% profit_margin_percent)
- Alíquota Impostos / Taxas (% tax_rate_percent e R$ tax_amount)
- Preço Final de Venda Sugerido (R$ final_price_to_client)
- Lucro Líquido Real Estimado (R$ net_profit)

Diferente do Orçamento Comercial (`doc_type="client"`), que possui linhas dedicadas para "Desconto Comercial" e "Frete / Envio" no resumo financeiro, o demonstrativo técnico pula diretamente do Custo Base / Impostos para o "Preço Final de Venda Sugerido".

Quando o projeto possui desconto comercial aplicado (ex: 10%) ou frete configurado (ex: R$ 30,00), esses valores não aparecem em nenhuma linha da tabela técnica.

### Impacto
- **Divergência Aritmética Aparente**: O gestor ou operador da oficina que examina a Ficha Técnica não consegue conciliar o cálculo `(Base * (1 + Margem)) / (1 - Impostos)` com o "Preço Final de Venda Sugerido", pois o desconto comercial reduziu o valor ou o frete aumentou o montante cobrado sem qualquer indicação visual no documento.
- **Risco de Cobrança ou Envio Incorreto**: A produção técnica não tem visibilidade se o valor final cotado inclui ou não despesas de frete/envio já pactuadas com o cliente.

### Passos para Reproduzir
1. Criar um projeto com placas, aplicar 15% de desconto comercial e adicionar R$ 25,00 de frete.
2. Exportar o PDF com `type=technical` (`/api/projects/{id}/pdf?type=technical`).
3. Analisar a Seção 3 da Ficha Técnica: as linhas de desconto e frete estão completamente ausentes da tabela de custos internos.

### Arquivos e Linhas Afetadas
- `backend/pdf_service.py`: linhas 529-558.

### Solução Proposta
No bloco `doc_type != "client"` de `backend/pdf_service.py`, incluir linhas condicionais para Desconto Comercial e Frete / Envio logo antes do Preço Final de Venda Sugerido:
```python
        if summary.get("discount_amount", 0.0) > 0:
            cost_breakdown_data.append([
                Paragraph(f"Desconto Comercial ({summary.get('discount_percent', 0.0):.1f}%):", style_cell),
                Paragraph(f"- R$ {summary.get('discount_amount', 0.0):.2f}", style_cell_right)
            ])
        if summary.get("shipping_cost", 0.0) > 0:
            cost_breakdown_data.append([
                Paragraph("Frete / Envio:", style_cell),
                Paragraph(f"+ R$ {summary.get('shipping_cost', 0.0):.2f}", style_cell_right)
            ])
```
"""
    }
]

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado via git credential fill.")
        sys.exit(1)

    print(f"Token obtido com sucesso. Publicando {len(ISSUES_TO_CREATE)} issues no repositório {REPO}...\n")

    created_issues = []
    for idx, issue in enumerate(ISSUES_TO_CREATE, 1):
        print(f"[{idx}/{len(ISSUES_TO_CREATE)}] Criando issue: {issue['title']}...")
        payload = json.dumps({
            "title": issue["title"],
            "body": issue["body"].strip(),
            "labels": issue["labels"]
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{API_BASE}/issues",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "Antigravity-IssuePublisher-V12"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                issue_num = data.get("number")
                html_url = data.get("html_url")
                print(f"    -> Criada com sucesso: #{issue_num} ({html_url})")
                created_issues.append({
                    "number": issue_num,
                    "title": issue["title"],
                    "url": html_url
                })
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            print(f"    -> Erro HTTP {e.code}: {e.reason}")
            print(f"    -> Detalhes: {error_body}")
        except Exception as e:
            print(f"    -> Erro inesperado: {str(e)}")

        time.sleep(1.0)

    out_file = Path("data/created_issues_v12.json")
    out_file.parent.mkdir(exist_ok=True, parents=True)
    out_file.write_text(json.dumps(created_issues, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFinalizado! {len(created_issues)} issues criadas e salvas em {out_file}.")

if __name__ == "__main__":
    main()
