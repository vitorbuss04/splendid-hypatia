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
        "title": "[BUG/SLICER] findBestMatchingFilament força arbitrariamente o primeiro filamento do estoque quando não há correspondência de material, causando precificação incorreta de materiais técnicos (ex: TPU, Nylon, ABS)",
        "labels": ["bug", "slicer-import", "frontend"],
        "body": """### Descrição do Problema
Na função `findBestMatchingFilament` (`frontend/js/app.js`, linhas 82-150), o algoritmo analisa os metadados do fatiador (`slicerProfile`, `filamentType`, `hexColor`, `plateName`) e busca um filamento compatível no inventário (`state.filaments`) em cinco níveis de especificidade decrescente (Marca + Material + Cor, Material + Cor, Marca + Material, Perfil Completo, e Tipo de Material).

No entanto, caso nenhum desses critérios seja satisfeito, a função executa na linha 149 um fallback incondicional forçado:
```javascript
// Fallback: first filament
return filaments[0];
```

Quando um operador possui filamentos cadastrados (por exemplo, bobinas de PLA) e importa um arquivo fatiado com material técnico distinto (como TPU flexível, Nylon, PC, ASA, Resina ou PEEK), nenhum dos critérios de casamento de material é atendido. Em vez de retornar `null` para que a placa seja configurada como "Personalizado (Manual)" com taxa apropriada ou solicite configuração, a função retorna arbitrariamente `filaments[0]` (o primeiro carretel de PLA da lista).

Além disso, em `handleSinglePlateFile` (`frontend/js/app.js`, linhas 2630-2634 e 2708-2712), a ausência de um bloco `else` faz com que uma placa previamente selecionada mantenha o `filament_id` antigo caso nenhum filamento compatível seja localizado.

### Impacto
- **Subdimensionamento Grave de Preços**: Peças fatiadas em polímeros de engenharia (como TPU flexível a R$ 160/kg ou PEEK a R$ 800/kg) são silenciosamente precificadas com o custo de grama do PLA comum (R$ 90/kg), gerando margem de lucro negativa e grande prejuízo comercial para a oficina.
- **Divergência Visual e Operacional**: A placa exibe no card a cor e especificações do PLA padrão, ocultando do operador que o fatiador original utilizava outro tipo de filamento.

### Passos para Reproduzir
1. Cadastrar no estoque apenas carretéis de PLA (ex: "PLA Preto - 3D Prime").
2. No editor de orçamentos, importar um arquivo 3MF ou G-Code fatiado explicitamente com material `TPU` ou `Nylon`.
3. Observar que `findBestMatchingFilament` retorna o carretel de PLA e a placa associa automaticamente o `filament_id` do PLA, em vez de manter o seletor em "Personalizado (Manual)" e preservar o tipo de material original.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 148-150 (`findBestMatchingFilament`), linhas 2630-2634 e 2708-2712 (`handleSinglePlateFile`).

### Solução Proposta
Retornar `null` em `findBestMatchingFilament` quando nenhum critério de casamento for atendido, e em `handleSinglePlateFile`, adicionar o bloco `else` para desvincular o filamento anterior (`filament_id = null; custom_filament_cost_per_g = 0.10;`), alinhando o comportamento com `additionalPlates` e `handleSlicerFiles`:
```javascript
// Em findBestMatchingFilament:
return null;

// Em handleSinglePlateFile (bloco 3MF e bloco G-Code):
if (matchedFilament) {
    state.currentPlates[plateIdx].filament_id = matchedFilament.id;
    state.currentPlates[plateIdx].custom_filament_cost_per_g = null;
} else {
    state.currentPlates[plateIdx].filament_id = null;
    state.currentPlates[plateIdx].custom_filament_cost_per_g = 0.10;
}
```
"""
    },
    {
        "title": "[UX/FEAT] Card de placa no editor de orçamentos e Ficha Técnica (PDF) omitem observações e instruções operacionais da placa (plate.notes)",
        "labels": ["enhancement", "ux", "pdf", "frontend"],
        "body": """### Descrição do Problema
No modelo de dados `Plate` (`backend/models.py`) e nos schemas da API (`backend/schemas.py`), a entidade de placa possui o campo `notes` (`Text, nullable=True`), o qual é devidamente serializado e persistido ao salvar (`saveCurrentProject` em `frontend/js/app.js`: `notes: p.notes`) e clonado ao duplicar projetos (`duplicate_project`: `notes=pl.notes`). Além disso, o analisador de arquivos 3MF (`frontend/js/parsers/threemf.js`, linha 522) preenche automaticamente a nota `"Arquivo 3MF sem metadados de fatiamento. Preencha o tempo e peso manualmente."` ao importar arquivos brutos sem fatiamento.

No entanto:
1. No editor de orçamentos (`renderPlates()` em `frontend/js/app.js`, linhas 1688-1868), não existe nenhum campo de formulário (input ou textarea) para exibir ou editar as anotações e instruções da placa (ao contrário da seção de insumos BOM, onde o campo "Especificações / Obs" foi implementado com sucesso na Issue #84).
2. Na Ficha Técnica de Produção em PDF (`doc_type == "technical"` em `backend/pdf_service.py`, linhas 434-489), a tabela de parâmetros operacionais de placas omite totalmente a exibição do campo `plate.notes`.

### Impacto
- **Perda de Instruções Críticas de Fabricação**: O operador não tem como registrar no card instruções técnicas essenciais de manufatura aditiva para aquela placa específica (ex: "Pausar na camada 52 para inserção de porcas M3", "Ativar borda de 5mm para evitar warping", "Suportes orgânicos ativados").
- **Invisibilidade de Avisos do Fatiador**: A nota gerada pelo parser para arquivos 3MF não-fatiados nunca é exibida na interface, deixando o operador sem feedback visual sobre a ausência de metadados.
- **Risco de Falhas na Oficina**: A ordem de serviço impressa (Ficha Técnica em PDF) não traz as notas operacionais das placas, aumentando a probabilidade de erros durante o processo de impressão 3D.

### Passos para Reproduzir
1. Abrir um orçamento no editor (`#/project-editor`).
2. Observar o card de qualquer placa: existem campos para hardware, bico, camada, mesa, tempo e pesos, mas nenhum campo de "Observações / Instruções da Placa".
3. Importar um arquivo 3MF bruto: a nota interna `"Arquivo 3MF sem metadados..."` é atribuída no objeto em memória, mas nunca é renderizada no DOM.
4. Emitir a Ficha Técnica de Produção em PDF: a tabela de placas não traz nenhuma coluna ou linha descritiva para observações operacionais.

### Arquivos e Linhas Afetadas
- `frontend/js/app.js`: linhas 1688-1868 (`renderPlates`).
- `backend/pdf_service.py`: linhas 434-489 (tabela de placas da Ficha Técnica).

### Solução Proposta
1. Em `frontend/js/app.js` (`renderPlates`), incluir um campo discreto de entrada para observações/instruções da placa no rodapé do card da placa:
```html
<div class="plate-field-col pt-1">
    <label class="text-[10px] font-medium text-slate-400 mb-1 block">Observações / Instruções de Impressão</label>
    <input type="text" value="${esc(plate.notes || '')}" oninput="state.currentPlates[${idx}].notes = this.value" class="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500" placeholder="Ex: Pausa na camada 45 para ímã, usar cola bastão...">
</div>
```
2. Em `backend/pdf_service.py` (tabela de placas da ficha técnica), renderizar as notas da placa abaixo do setup de manufatura ou na descrição da placa com escape seguro de HTML:
```python
notes_txt = str(p.get("notes") or "").strip()
if notes_txt:
    safe_notes = html.escape(notes_txt)
    setup_desc += f"<br/><font color='#64748b' size='7'>{safe_notes}</font>"
```
"""
    },
    {
        "title": "[API/PADRÃO] Endpoint POST /api/projects/{id}/duplicate retorna status HTTP 200 OK em vez de HTTP 201 Created divergindo dos endpoints de duplicação de impressoras e filamentos",
        "labels": ["bug", "backend"],
        "body": """### Descrição do Problema
Na API FastAPI (`backend/routes/project_routes.py`, linha 410), o endpoint de clonagem de projetos foi declarado da seguinte forma:
```python
@router.post("/{project_id}/duplicate", response_model=schemas.ProjectResponse)
def duplicate_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```
Por omitir o argumento `status_code=status.HTTP_201_CREATED`, o endpoint responde com status padrão `HTTP 200 OK`.

No entanto, nos endpoints análogos de duplicação de recursos:
- `POST /api/printers/{id}/duplicate` (`backend/routes/printer_routes.py`, linha 83):
  `@router.post("/{printer_id}/duplicate", response_model=schemas.PrinterResponse, status_code=status.HTTP_201_CREATED)`
- `POST /api/filaments/{id}/duplicate` (`backend/routes/filament_routes.py`, linha 75):
  `@router.post("/{filament_id}/duplicate", response_model=schemas.FilamentResponse, status_code=status.HTTP_201_CREATED)`
a API retorna o código semântico RESTful `HTTP 201 Created` para sinalizar a criação de uma nova entidade persistida no banco de dados.

### Impacto
- **Inconsistência de Contrato REST**: Viola a padronização interna da API, onde operações de clonagem/criação via requisições POST retornam 201 Created.
- **Previsibilidade para Clientes HTTP**: Clientes e testes automatizados que validam códigos de resposta padrão para criação de recursos recebem códigos distintos dependendo do tipo de recurso duplicado.

### Passos para Reproduzir
1. Executar uma requisição `POST /api/projects/{id}/duplicate` com token válido.
2. Inspecionar o código HTTP de status da resposta: retorna `200` em vez de `201`.

### Arquivos e Linhas Afetadas
- `backend/routes/project_routes.py`: linha 410.

### Solução Proposta
Adicionar `status_code=status.HTTP_201_CREATED` ao decorator do endpoint:
```python
@router.post("/{project_id}/duplicate", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def duplicate_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```
"""
    }
]

def main():
    token = get_token()
    if not token:
        print("ERRO: Token do GitHub não encontrado nas credenciais git locais.")
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
                "User-Agent": "Antigravity-IssuePublisher-V13"
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

    out_file = Path("data/created_issues_v13.json")
    out_file.parent.mkdir(exist_ok=True, parents=True)
    out_file.write_text(json.dumps(created_issues, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFinalizado! {len(created_issues)} issues criadas e salvas em {out_file}.")

if __name__ == "__main__":
    main()
