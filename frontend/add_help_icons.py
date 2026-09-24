file_path = r'c:\Users\Vitor\Documents\antigravity\splendid-hypatia\frontend\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

replacements = [
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Horas Modelagem CAD</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Horas Modelagem CAD <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Tempo total dedicado à criação, adaptação ou modelagem CAD 3D do modelo antes de fatiar."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Taxa CAD (R$/h)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Taxa CAD (R$/h) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Valor cobrado por hora de trabalho técnico de modelagem 3D ou engenharia."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Horas Pós-Processo</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Horas Pós-Processo <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Tempo gasto em atividades manuais como remoção de suportes, lixamento, pintura ou montagem."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Taxa Pós (R$/h)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Taxa Pós (R$/h) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Valor cobrado por hora de mão de obra para acabamento e pós-processamento das peças."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Overhead / Indiretos (R$)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Overhead / Indiretos (R$) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Custos fixos de operação (aluguel, internet, software, embalagens gerais) atribuídos a este lote."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Margem Lucro Alvo (%)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Margem Lucro Alvo (%) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Percentual de margem de lucro desejado sobre o custo total de produção do projeto."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Impostos / Taxas (%)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Impostos / Taxas (%) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Alíquota de impostos (ex: Simples Nacional/MEI) e taxas de cartão ou emissão de nota fiscal."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    ),
    (
        '<label class="block text-xs font-medium text-slate-300 mb-1.5">Desconto Comercial (%)</label>',
        '<label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">Desconto Comercial (%) <span class="info-icon text-slate-400 hover:text-blue-400 transition-colors" data-tooltip="Percentual de desconto comercial a ser concedido sobre o valor final de venda do projeto."><i data-lucide="help-circle" class="w-3.5 h-3.5"></i></span></label>'
    )
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        print("Replaced:", old[:30])
    else:
        print("Not found:", old[:30])

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
