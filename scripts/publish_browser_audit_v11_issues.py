import subprocess
import urllib.request
import urllib.error
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

ISSUES_TO_CREATE = [
    {
        "title": "[BUG/SLICER] Importação individual de arquivo 3MF e G-Code via handleSinglePlateFile descarta diâmetro do bico (nozzle_diameter), altura de camada (layer_height) e tipo de mesa (bed_type)",
        "labels": ["bug", "slicer-import", "frontend"],
        "body": """### Descrição do Problema
No editor de orçamentos, ao carregar um arquivo 3MF ou G-Code individualmente em um card de placa existente (`handleSinglePlateFile` em `frontend/js/app.js`), os metadados de impressão extraídos pelos analisadores (`parse3mfMetadata` e `parseGcodeMetadata`) contêm com sucesso as propriedades de manufatura: `nozzle_diameter`, `layer_height` e `bed_type`.

No entanto, a função `handleSinglePlateFile` atribui apenas os campos `name`, `print_time_hours`, `part_weight_g`, `purge_weight_g` e `slicer_filament_profile` à placa alvo (`state.currentPlates[plateIdx]`). Ela deixa de atribuir `nozzle_diameter`, `layer_height` e `bed_type` tanto no bloco de importação de arquivos 3MF (linhas 2598-2619) quanto no bloco de arquivos G-Code (linhas 2673-2693).

Diferente da importação em lote (`handleSlicerFiles`) e da criação de placas subsequentes (`additionalPlates`), onde esses parâmetros são preservados, a placa alvo importada individualmente ignora completamente a configuração do arquivo fatiado.

### Impacto
- **Perda de Parâmetros de Manufatura**: Quando o operador refatia uma peça ou atualiza o arquivo de uma placa existente usando um bico diferente (ex: 0.6mm ou 0.2mm) ou perfil de camada específico (ex: 0.12mm high detail), a placa mantém silenciosamente os valores antigos ou defaults genéricos (0.4mm, 0.20mm, Textured PEI).
- **Inconsistência na Ficha Técnica de Produção**: A ordem de serviço e a Ficha Técnica de Produção em PDF são geradas com parâmetros incorretos, induzindo a oficina a imprimir a peça com diâmetro de bico e altura de camada divergentes do fatiamento real.

### Passos para Reproduzir
1. Abrir um orçamento no editor (`#/project-editor`).
2. No card da Placa 1, clicar no botão "Importar 3MF/Gcode" e selecionar um arquivo fatiado com bico de 0.6mm e altura de camada de 0.12mm.
3. Observar que o tempo de impressão e o peso são atualizados, mas os campos "Bico (Diâmetro)", "Camada (Altura)" e "Tipo de Mesa" permanecem inalterados com os valores anteriores (ex: 0.4 e 0.20).

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2596-2619 (bloco 3MF de `handleSinglePlateFile`) e linhas 2670-2695 (bloco GCode de `handleSinglePlateFile`).

### Solução Proposta
Atribuir explicitamente os parâmetros de setup extraídos à placa alvo:
```javascript
// No bloco 3MF de handleSinglePlateFile:
if (plates[0].nozzle_diameter) state.currentPlates[plateIdx].nozzle_diameter = plates[0].nozzle_diameter;
if (plates[0].layer_height) state.currentPlates[plateIdx].layer_height = plates[0].layer_height;
if (plates[0].bed_type) state.currentPlates[plateIdx].bed_type = plates[0].bed_type;

// No bloco G-Code de handleSinglePlateFile:
if (meta.nozzle_diameter) state.currentPlates[plateIdx].nozzle_diameter = meta.nozzle_diameter;
if (meta.layer_height) state.currentPlates[plateIdx].layer_height = meta.layer_height;
if (meta.bed_type) state.currentPlates[plateIdx].bed_type = meta.bed_type;
```
"""
    },
    {
        "title": "[BUG/PARSER] Leitor de arquivos 3MF (threemf.js) zera o tempo de impressão (print_time_hours = 0) para peças de calibração ou testes rápidos devido a arredondamento prematuro toFixed(2)",
        "labels": ["bug", "parsers", "slicer-import"],
        "body": """### Descrição do Problema
No analisador de arquivos 3MF (`frontend/js/parsers/threemf.js`, linhas 278 e 461), o tempo de impressão convertido em horas é formatado usando `parseFloat(printTimeHours.toFixed(2))` e `parseFloat((secs / 3600).toFixed(2))`.

Para peças pequenas, testes rápidos de fluxo, torres de calibração ou scripts de purge que levam menos de 18 segundos, o tempo em horas é inferior a 0.005h (ex: 15 segundos equivalem a 0.00416h). A chamada `.toFixed(2)` trunca e arredonda esse valor para `"0.00"`, resultando em `print_time_hours = 0.0`.

Esse mesmo bug foi corrigido no analisador de G-Code na Issue #87, mas o leitor de arquivos 3MF permaneceu com a mesma vulnerabilidade de arredondamento prematuro.

### Impacto
- **Custos Operacionais Zerados**: Placas importadas a partir de arquivos 3MF com impressões curtas têm o tempo de máquina zerado. Com isso, os custos de depreciação, manutenção preventiva e energia elétrica são calculados como R$ 0,00 pelo motor contábil.
- **Distorção no Orçamento**: A proposta comercial é subprecificada e a estimativa de prazo/tempo total de impressão do lote é afetada.

### Passos para Reproduzir
1. Criar ou importar um arquivo 3MF fatiado com tempo de 15 segundos e peso de 1.2g.
2. Analisar o objeto retornado por `parse3mfMetadata`: `print_time_hours` retorna `0`, enquanto `part_weight_g` é computado corretamente.

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/threemf.js`: linha 278 e linha 461.

### Solução Proposta
Adotar o mesmo fallback de 4 casas decimais para tempos curtos implementado no parser de G-Code:
```javascript
let roundedHours = parseFloat(printTimeHours.toFixed(2));
if (roundedHours === 0 && printTimeHours > 0) {
    roundedHours = parseFloat(printTimeHours.toFixed(4));
}
```
"""
    },
    {
        "title": "[BUG/SLICER] Leitor de 3MF (threemf.js) descarta o peso de purga/flush dos filamentos subsequentes em impressões multi-materiais (Bambu AMS)",
        "labels": ["bug", "parsers", "slicer-import", "calculation-engine"],
        "body": """### Descrição do Problema
Em projetos multi-materiais ou multi-cores fatiados no Bambu Studio ou OrcaSlicer (para uso com sistema AMS), o arquivo `slice_info.xml` ou `slice_info.config` lista múltiplos elementos `<filament>` dentro do nó `<plate>`, detalhando o consumo de cada carretel (`used_g`) e a respectiva purga na torre de transição / poço de descarte (`flush_g`).

Em `frontend/js/parsers/threemf.js` (linhas 243-245), o acumulador de purga foi escrito com a seguinte condição:
```javascript
totalFilamentGrams += usedG;
if (flushG > 0 && purgeGrams === 0) {
    purgeGrams += flushG;
}
```
Na primeira iteração do laço (filamento 1), se `flushG > 0`, a variável `purgeGrams` recebe esse valor. A partir do segundo filamento (filamentos 2, 3, 4, etc.), `purgeGrams` já é estritamente maior que zero, fazendo com que a cláusula `purgeGrams === 0` avalie como `false` e descarte silenciosamente o peso de purga de todos os filamentos adicionais.

### Impacto
- **Subdimensionamento Crítico de Custos**: Em impressões multi-cores complexas, o descarte por purga frequentemente ultrapassa o peso da peça em si (ex: 4 cores gerando 15g, 25g, 30g e 20g de flush). O parser contabiliza apenas os 15g do primeiro filamento e descarta os outros 75g de purga real, gerando grande prejuízo financeiro para a oficina de impressão 3D.

### Passos para Reproduzir
1. Fatiar um modelo multi-cor com 3 filamentos (ex: Filament 1: 5.0g flush, Filament 2: 12.0g flush, Filament 3: 8.0g flush).
2. Carregar o arquivo 3MF no leitor.
3. Constatar que `purge_weight_g` na placa resultante é computado apenas como 5.0g em vez dos 25.0g totais.

### Arquivos e Linhas Afetadas
- `frontend/js/parsers/threemf.js`: linhas 243-245.

### Solução Proposta
Identificar se o valor de purga já veio definido no nível global da placa (`<metadata key="flush_weight">`) e, caso contrário, somar todos os atributos `flushG` de cada filamento:
```javascript
const hasMetadataPurge = purgeGrams > 0;
// No loop de filamentNodes:
if (flushG > 0 && !hasMetadataPurge) {
    purgeGrams += flushG;
}
```
"""
    },
    {
        "title": "[UX/PDF] Ficha Técnica de Produção e Proposta Comercial em PDF omitem observações e especificações técnicas (notes) dos itens do BOM",
        "labels": ["enhancement", "pdf", "pdf-generation", "ux"],
        "body": """### Descrição do Problema
Na Issue #84 foi adicionado com sucesso o campo de anotações/especificações técnicas (`notes`) na linha de insumos (BOM) da calculadora de orçamentos, permitindo ao operador registrar o tipo de rosca, comprimento, código do fornecedor ou especificação de acabamento dos fixadores e componentes adicionais.

No entanto, no gerador de relatórios ReportLab (`backend/pdf_service.py`), esse campo `notes` não é impresso em nenhuma das tabelas de insumos:
1. **Na Proposta Comercial do Cliente (`doc_type == 'client'`, linhas 278-286)**: A tabela exibe apenas Componente, Categoria, Qtd e Subtotal.
2. **Na Ficha Técnica de Produção (`doc_type == 'technical'`, linhas 483-491)**: O Checklist de Montagem exibe apenas Item Insumo, Categoria, Qtd Requerida e Caixa de Conferência `[ ] Conferido`.

### Impacto
- **Risco de Erros na Linha de Montagem**: O operador na oficina imprime a Ficha Técnica de Produção para separar e montar o projeto, mas não consegue visualizar se o "Parafuso M3" deve ser cabeça abaulada, cabeça escareada, em inox 304 ou comprimento 16mm, aumentando o risco de montagem com insumos incorretos.
- **Falta de Discriminação para o Cliente**: Especificações técnicas acordadas de itens adicionais (ex: "Embalagem plástica antiestática com lacre de segurança") não constam no documento comercial.

### Passos para Reproduzir
1. Criar um projeto e adicionar um item no BOM: Nome "Parafuso M3", Categoria "Fixadores", Especificações/Obs "Aço Inox 304 Cabeça Abaulada M3x12".
2. Emitir a Proposta Comercial em PDF ou a Ficha Técnica de Produção.
3. Observar a tabela de BOM gerada: as especificações técnicas cadastradas não aparecem em nenhuma coluna ou linha.

### Arquivos e Linhas Afetadas
- `backend/pdf_service.py`: linhas 278-297 (tabela BOM da proposta cliente) e linhas 483-502 (checklist BOM da ficha técnica).

### Solução Proposta
Renderizar o texto de `notes` como subtítulo descritivo estilizado sob o nome do item:
```python
notes_txt = str(b.get("notes") or "").strip()
cell_content = f"<b>{b_name}</b>"
if notes_txt:
    safe_notes = html.escape(notes_txt)
    cell_content += f"<br/><font color='#64748b' size='7'>{safe_notes}</font>"
```
"""
    },
    {
        "title": "[UX/BUG] Modal de impressora não valida vida útil estritamente positiva (lifespan_hours > 0) nem impede valores negativos no frontend antes de submeter requisição à API",
        "labels": ["bug", "printers", "ux", "frontend"],
        "body": """### Descrição do Problema
No modal de cadastro e edição de impressoras (`handleSavePrinter` em `frontend/js/app.js`), o formulário valida unicamente se o campo de nome foi informado (`if (!name)`). 

Diferente do modal de filamento (cujas validações foram implementadas na Issue #86), os parâmetros numéricos de impressora não contam com validação de cliente para vida útil (`lifespan_hours > 0`) nem para valores não-negativos de custos, potência ou reserva de manutenção.

Como o schema Pydantic `PrinterBase` (`backend/schemas.py`) possui a restrição `lifespan_hours: float = Field(5000.0, gt=0)` e `ge=0` nos demais campos, submeter o formulário com vida útil 0 ou negativa dispara uma resposta HTTP 422 Unprocessable Entity da API (`Input should be greater than 0`).

### Impacto
- **Experiência de Usuário Ruim**: O operador recebe um toast de erro genérico da API (`422 Unprocessable Entity`) em vez de receber uma mensagem amigável no formulário orientando o preenchimento e colocando foco no campo incorreto.

### Passos para Reproduzir
1. Acessar a tela de Impressoras (`#/printers`).
2. Clicar em "+ Cadastrar Impressora".
3. Preencher o nome e definir "Vida Útil Estimada (horas)" como `0`.
4. Clicar em "Salvar Impressora": a requisição falha com status HTTP 422.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 2781-2804 (`handleSavePrinter`).

### Solução Proposta
Adicionar validações no cliente em `handleSavePrinter` antes de invocar a API:
```javascript
const lifespan = parseLocaleFloat(document.getElementById('printer-lifespan').value, 5000);
if (isNaN(lifespan) || lifespan <= 0) {
    showToast('A vida útil estimada deve ser maior que zero horas.', 'error');
    document.getElementById('printer-lifespan')?.focus();
    return;
}
const cost = Math.max(0, parseLocaleFloat(document.getElementById('printer-cost').value, 0));
const power = Math.max(0, parseLocaleFloat(document.getElementById('printer-power').value, 150));
const maint = Math.max(0, parseLocaleFloat(document.getElementById('printer-maintenance').value, 1.0));
const energy = Math.max(0, parseLocaleFloat(document.getElementById('printer-energy').value, 0.85));
```
"""
    },
    {
        "title": "[UX/BUG] Formulário de Preferências da Oficina não valida limites nos campos percentuais (alíquota de impostos até 99% e valores não-negativos) antes de submeter requisição à API",
        "labels": ["bug", "ux", "frontend"],
        "body": """### Descrição do Problema
Na tela de Configurações da Oficina (`handleSavePreferences` em `frontend/js/app.js`), os campos de preferências padrão são extraídos com `parseLocaleFloat` e enviados à API sem validação de intervalos ou limites no cliente.

No backend, o schema `UserPreferencesUpdate` (`backend/schemas.py`) define:
- `default_tax_rate: Optional[float] = Field(None, ge=0, le=99.0)`
- `default_failure_rate: Optional[float] = Field(None, ge=0)`
- `default_profit_margin: Optional[float] = Field(None, ge=0)`
- `default_energy_rate: Optional[float] = Field(None, ge=0)`

Se o usuário digitar uma alíquota de impostos de 100% ou um número negativo em qualquer taxa, a requisição é rejeitada pela API com erro HTTP 422 Unprocessable Entity, exibindo uma notificação genérica de erro.

### Impacto
- **Ausência de Feedback Claro**: O formulário não indica qual dos múltiplos inputs percentuais violou a regra de negócio da API, forçando o usuário a adivinhar o motivo do erro 422.

### Passos para Reproduzir
1. Acessar a tela de Configurações (`#/settings`).
2. No campo "Alíquota de Impostos (%)", digitar `100` ou um valor negativo.
3. Clicar em "Salvar Preferências": a chamada falha com erro HTTP 422.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 3340-3356 (`handleSavePreferences`).

### Solução Proposta
Validar os limites no cliente em `handleSavePreferences`:
```javascript
const taxRate = parseLocaleFloat(document.getElementById('pref-tax').value, 6);
if (isNaN(taxRate) || taxRate < 0 || taxRate > 99) {
    showToast('A alíquota de impostos padrão deve estar entre 0% e 99%.', 'error');
    document.getElementById('pref-tax')?.focus();
    return;
}
```
"""
    },
    {
        "title": "[PDF/UX] Ficha Técnica de Produção (PDF) gera tabela de placas vazia sem mensagem explicativa quando projeto contém apenas insumos (BOM) e serviços",
        "labels": ["enhancement", "pdf", "pdf-generation", "ux"],
        "body": """### Descrição do Problema
No serviço de geração de PDFs (`backend/pdf_service.py`), na seção de itens fabricados da Proposta Comercial (`doc_type == 'client'`, linhas 238-245), existe um tratamento explícito para projetos sem placas impressas (`if not plates_details:`), adicionando a linha informativa "Nenhuma peça impressa configurada".

Porém, na Ficha Técnica de Produção (`doc_type == 'technical'`, linhas 429-471), quando o projeto é composto exclusivamente por insumos/BOM e horas de modelagem CAD ou montagem (sem nenhuma placa 3D cadastrada), o laço `for p in plates_details:` não é executado e nenhuma linha é adicionada a `tech_table_data`. 

A tabela é renderizada contendo apenas o cabeçalho de colunas (Placa, Impressora, Material, Setup Fab., Tempo Un., Peso Peça, Purga, Qtd, Tempo Total) totalmente em branco, seguida imediatamente pela seção de BOM.

### Impacto
- **Aparência de Documento Corrompido**: O PDF técnico para ordens de serviço de montagem ou engenharia CAD apresenta uma tabela de manufatura sem nenhuma linha preenchida ou mensagem de justificativa, dando a impressão de falha no sistema de impressão de relatórios.

### Passos para Reproduzir
1. Criar um orçamento contendo apenas itens de BOM e horas de CAD (remover todas as placas).
2. Gerar a Ficha Técnica de Produção em PDF (`doc_type=technical`).
3. Observar a Seção 1 "PARÂMETROS OPERACIONAIS DE PRODUÇÃO (PLACAS)": apenas os títulos das colunas são renderizados, sem nenhuma linha de conteúdo.

### Arquivos e Linhas Afetadas
- `backend/pdf_service.py`: linhas 429-471.

### Solução Proposta
Adicionar o tratamento para ausência de placas na visualização técnica com mensagem explicativa:
```python
if not plates_details:
    tech_table_data.append([
        Paragraph("Nenhuma peça impressa configurada", style_cell),
        Paragraph("—", style_cell),
        Paragraph("—", style_cell),
        Paragraph("—", style_cell),
        Paragraph("—", style_cell_right),
        Paragraph("—", style_cell_right),
        Paragraph("—", style_cell_right),
        Paragraph("0", style_cell_right),
        Paragraph("—", style_cell_right),
    ])
```
"""
    }
]

def main():
    token = get_token()
    if not token:
        print("Erro: Token do GitHub não encontrado via git credential!")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "BrowserAuditV11Publisher"
    }

    created = []
    for idx, iss in enumerate(ISSUES_TO_CREATE, 1):
        print(f"[{idx}/{len(ISSUES_TO_CREATE)}] Criando issue: {iss['title']}...")
        payload = {
            "title": iss["title"],
            "body": iss["body"],
            "labels": iss.get("labels", ["bug"])
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{API_BASE}/issues",
            data=data,
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                created.append(res)
                print(f" -> Sucesso! Issue #{res['number']} criada: {res['html_url']}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f" -> Erro HTTP {e.code}: {err_body}")
        except Exception as e:
            print(f" -> Erro inesperado: {e}")

        time.sleep(1.0)

    print(f"\nTotal de issues criadas com sucesso: {len(created)}/{len(ISSUES_TO_CREATE)}")

if __name__ == "__main__":
    main()
