# 3D Print Calc Pro 🖨️💰
### Calculadora Profissional de Custos e Sistema de Orçamentos para Impressão 3D

Sistema completo, moderno e pronto para produção para cálculo exato de custos, formação de preços de venda e emissão de orçamentos técnicos e comerciais para manufatura aditiva (FDM/Resina).

---

## 🚀 Principais Funcionalidades

1. **Docker-First & EasyPanel Ready:**
   - Pronto para execução local e deployment direto em VPS com **EasyPanel** ou Docker Swarm via `docker-compose.yml`.
   - Persistência garantida através de volume `/app/data`.
2. **Conta Inicial 100% Limpa:**
   - Ao se cadastrar, a conta do usuário inicia vazia (sem dados fictícios ou mock), permitindo cadastrar sua oficina e catálogo reais.
3. **Isolamento Rigoroso de Ambientes:**
   - `development`: banco de dados local `data/dev.db`.
   - `test`: banco isolado `data/test.db` / suíte pytest.
   - `production`: banco persistente `/app/data/prod.db` no Docker.
4. **Hierarquia Projeto > Múltiplas Placas + Insumos (BOM):**
   - Suporte a projetos multi-peças, permitindo que cada placa utilize impressoras e filamentos diferentes, somado a componentes não impressos (parafusos, insertos, rolamentos, eletrônica).
5. **Entrada Híbrida (Manual + 3MF / G-Code):**
   - Leitor no navegador para extração automática de tempo e peso de arquivos `.3mf` (Bambu Studio / OrcaSlicer via JSZip) e `.gcode` (Cura / PrusaSlicer).
6. **Motor Matemático Completo de Custos & Formação de Preço:**
   - Depreciação de máquina por hora de vida útil.
   - Custo de energia elétrica (Potência em Watts $\times$ Tarifa R$/kWh).
   - Reserva de manutenção por hora de operação.
   - Consumo de filamento com peso de purga e margem de falha configurável.
   - Mão de obra técnica (Modelagem CAD/Ajustes 3D e Pós-processamento manual).
   - Custos indiretos / Overhead.
   - Cálculo financeiro sobre venda: $\text{Preço} = \frac{\text{Custo Base} \times (1 + \text{Margem \%})}{1 - \text{Alíquota Impostos \%}}$.
7. **Emissão de Orçamentos em PDF:**
   - **Orçamento Comercial (Cliente):** Apresentação visual limpa com dados da oficina, detalhamento dos itens e serviços, chave PIX e condições comerciais.
   - **Ficha Técnica de Produção (Interno):** Ordem operacional com parâmetros de fatiamento por placa, checklist de montagem BOM e demonstrativo interno de custos e margens reais.
8. **Testes Automatizados (pytest):**
   - Suíte abrangente cobrindo todas as fórmulas matemáticas, isolamento multi-tenant entre usuários e endpoints da API RESTful.

---

## 📐 Fórmulas Financeiras e Modelo de Custos

### 1. Tarifa Horária da Impressora ($T_{\text{máquina}}$)
$$D_{\text{hora}} = \frac{\text{Custo de Aquisição (R\$)}}{\text{Vida Útil Estimada (horas)}}$$
$$E_{\text{hora}} = \left(\frac{\text{Potência Média (W)}}{1000}\right) \times \text{Tarifa Energia (R\$/kWh)}$$
$$T_{\text{máquina}} = D_{\text{hora}} + \text{Reserva Manutenção/hora} + E_{\text{hora}}$$

### 2. Custo da Placa Impressa ($C_{\text{placa}}$)
$$C_{\text{material}} = \left(\frac{\text{Peso Peça (g)} + \text{Purga (g)}}{\text{Peso Carretel (g)}}\right) \times \text{Preço Carretel} \times (1 + \text{Margem Falha \%})$$
$$C_{\text{tempo\_máquina}} = \text{Tempo de Impressão (h)} \times T_{\text{máquina}}$$
$$C_{\text{placa\_total}} = (C_{\text{material}} + C_{\text{tempo\_máquina}}) \times \text{Quantidade}$$

### 3. Custo Base do Projeto ($C_{\text{base}}$)
$$C_{\text{base}} = \sum C_{\text{placas}} + \sum C_{\text{BOM}} + (\text{Horas CAD} \times \text{Taxa CAD}) + (\text{Horas Pós} \times \text{Taxa Pós}) + \text{Overhead}$$

### 4. Preço de Venda Sugerido e Margens
$$\text{Preço Sugerido} = \frac{C_{\text{base}} \times (1 + \text{Margem Lucro \%})}{1 - \text{Alíquota Impostos \%}}$$
$$\text{Preço Final ao Cliente} = (\text{Preço Sugerido} - \text{Desconto Comercial}) + \text{Frete}$$

---

## 💻 Como Executar Localmente (Windows)

### Opção 1: Via script de 1 clique
Basta dar duplo clique em:
```bat
run_dev.bat
```

### Opção 2: Via terminal
```powershell
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar a aplicação
python app.py
```
Acesse a aplicação no navegador em: **`http://localhost:8000`**

A documentação interativa Swagger da API estará disponível em: **`http://localhost:8000/docs`**

---

## 🧪 Como Executar a Suíte de Testes Automatizados

Para rodar todos os testes unitários e de integração com cobertura das fórmulas e da API:
```powershell
python -m pytest -v
```

---

## 🐳 Como Implantar na VPS via EasyPanel

1. Crie um novo aplicativo no EasyPanel do tipo **App**.
2. Conecte ao seu repositório GitHub (`splendid-hypatia`).
3. O EasyPanel detectará automaticamente o `docker-compose.yml` ou `Dockerfile`.
4. Configure as variáveis de ambiente no painel:
   - `APP_ENV=production`
   - `SECRET_KEY=sua_chave_secreta_aleatoria_longa_e_segura`
   - `DATABASE_URL=sqlite:////app/data/prod.db`
   - `PORT=8000`
5. Configure o volume persistente montando `app_data` em `/app/data`.
6. Clique em **Deploy**. O EasyPanel construirá a imagem e publicará com certificado SSL automático!
