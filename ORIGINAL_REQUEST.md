# Original User Request

## Initial Request — 2026-09-24T02:22:29Z

Redesenhar completamente a interface e a experiência de usuário (UI/UX) do 3D Print Calc Pro, elevando o sistema para um padrão visual SaaS Premium moderno e elegante em Dark Mode, preservando 100% dos fluxos de dados, fórmulas de cálculo e a integridade de todos os testes automatizados da aplicação.

Working directory: C:/Users/augus/.gemini/antigravity/worktrees/splendid-hypatia/redesign_system_ui
Integrity mode: development

## Verification Resources
- Suíte completa de testes automatizados: `python -m pytest` (61 testes cobrindo inputs HTML, atributos numéricos, endpoints da API, cálculos de engenharia de custo e parsers de fatiadores .3mf/.gcode).
- Arquivos de especificação de contrato: `tests/test_frontend_inputs.py`.

## Requirements

### R1. Design System & Identidade Visual SaaS Dark Mode
Desenvolver uma nova identidade visual premium para a plataforma em Dark Mode, com paleta sofisticada (tons ardósia/grafite profundos, acentos em azul royal, esmeralda e violeta), tipografia de alta legibilidade, sombras sutis com efeito de profundidade, cards com bordas suaves e micro-interações de feedback.

### R2. Reestruturação e Acabamento das Telas Principais
Renovar o layout e a estética de todas as seções da aplicação:
- **Painel Geral (Dashboard):** Métricas operacionais em destaque, gráficos/indicadores visuais de volume e orçamentos, estado inicial amigável e lista de orçamentos recentes.
- **Lista de Projetos:** Tabela/grid moderna com busca em tempo real, badges de status de projeto com cores distintas e ações rápidas.
- **Calculadora & Editor de Orçamento:** Interface de trabalho fluida com dropzone interativa para arquivos .3MF/.GCODE, gerenciador de placas impressas, tabela de insumos (BOM), campos de mão de obra e card sticky de resumo financeiro em tempo real com destaque para formação de preço e margem líquida.
- **Gestão de Impressoras e Filamentos:** Catálogos visuais com visualização de cores de filamentos, especificações técnicas e modais de cadastro ergonômicos.
- **Configurações da Oficina & Autenticação:** Telas e modais de login/registro e dados da oficina com acabamento profissional e responsivo.

### R3. Preservação Estrita de Contratos Funcionais e Testes
Garantir que todos os IDs de elementos, inputs, tipos de atributos numéricos (`step`, `min`, `max`), classes essenciais, estruturas de formulário e integrações em `frontend/js/app.js` e `frontend/js/api.js` permaneçam em total conformidade, sem quebrar nenhuma funcionalidade ou teste existente.

## Acceptance Criteria

### Testes Automatizados e Confiabilidade
- [ ] O comando `python -m pytest` executa e passa com 100% de sucesso (mínimo de 61 testes aprovados sem falhas ou avisos impeditivos).
- [ ] Todos os testes em `tests/test_frontend_inputs.py` passam sem necessidade de relaxar asserções.
- [ ] Não há erros no console do navegador ao navegar entre abas, abrir modais, salvar projetos ou calcular preços.

### Excelência de Design e Usabilidade
- [ ] A aplicação apresenta padrão visual coeso de SaaS contemporâneo em Dark Mode.
- [ ] O resumo financeiro do projeto recalcula instantaneamente durante a digitação de valores ou adição de placas/insumos.
- [ ] Os modais de impressoras, filamentos e exportação de PDF funcionam com feedback visual claro.

## Follow-up — 2026-09-24T11:53:08Z

Continue execution of the redesign project from Milestone 3 (Calculator Workspace & Financial Terminal) through Milestone 4 (Catalogs, Settings, Modals, preview.html) and Milestone 5 (Final Verification & Hardening). Ensure all tests and contract invariants in PROJECT.md continue to pass.
