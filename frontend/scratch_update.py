file_path = r'c:\Users\Vitor\Documents\antigravity\splendid-hypatia\frontend\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<span class="font-mono font-bold text-sm text-emerald-400" id="live-net-profit">R$ 0,00 (0.0%)</span>', '<span class="font-mono font-bold text-sm text-emerald-400" id="live-net-profit">R$ 0,00</span>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated successfully")
