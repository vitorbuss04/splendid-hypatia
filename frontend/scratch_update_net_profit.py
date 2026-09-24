file_path = r'c:\Users\Vitor\Documents\antigravity\splendid-hypatia\frontend\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_block = '''                                <!-- 2. Net Profit & Margin Pod -->
                                <div class="net-profit-box p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-800/30 flex items-center justify-between shadow-inner transition-colors">
                                    <div class="flex items-center gap-2">
                                        <div class="w-7 h-7 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 flex items-center justify-center shrink-0">
                                            <i data-lucide="trending-up" class="w-3.5 h-3.5"></i>
                                        </div>
                                        <div class="flex flex-col">
                                            <span class="text-[11px] font-semibold text-slate-200">Lucro Líquido Real</span>
                                            <span class="text-[10px] text-slate-400">Margem pós-custos e taxas</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2 text-right">
                                        <span class="font-mono font-bold text-sm text-emerald-400" id="live-net-profit">R$ 0,00</span>
                                        <span class="profit-margin-pill px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">+0.0%</span>
                                    </div>
                                </div>'''

new_block = '''                                <!-- 2. Net Profit & Margin Pod -->
                                <div class="net-profit-box p-3 rounded-xl bg-slate-900/90 border border-emerald-500/30 flex items-center justify-between shadow-md transition-all">
                                    <div class="flex items-center gap-2.5">
                                        <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0 text-emerald-400">
                                            <i data-lucide="trending-up" class="w-4 h-4"></i>
                                        </div>
                                        <div class="flex flex-col">
                                            <span class="text-[11px] font-semibold text-slate-300 leading-tight">Lucro Líquido Real</span>
                                            <span class="text-[10px] text-slate-400">Margem pós-custos e taxas</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <span class="font-mono font-bold text-base text-emerald-400" id="live-net-profit">R$ 0,00</span>
                                        <span class="profit-margin-pill px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">+0.0%</span>
                                    </div>
                                </div>'''

if old_block in text:
    text = text.replace(old_block, new_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Replaced successfully")
else:
    print("old_block not found")
