"""Składa planer/index.html: edytor obrysu terenu (planer/src/edytor_obrysu.html) + generator zabudowy (generator.js)
+ niebieski interfejs jak w przeglądarce 3D budynków. Uruchamiać z katalogu projektu."""
import re
h = open('planer/src/edytor_obrysu.html', encoding='utf-8').read(); gen = open('planer/generator.js', encoding='utf-8').read()
def rep(old, new, count=1):
    global h
    assert h.count(old) >= 1, 'brak: ' + old[:70]
    h = h.replace(old, new, count)
# ---- tytuł, czcionki, paleta ----
rep('<title>Edytor obrysu terenu</title>', '<title>Planer zabudowy terenu</title>')
rep('<style>', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">\n<style>')
a = h.index(':root{'); b = h.index('*{box-sizing:border-box}')
h = h[:a] + ''':root{
  --bg:#e9edf0; --fg:#17222b; --mut:#5a6b78; --card:#f7f9fa; --line:#cfd7dc;
  --accent:#0b6e8e; --accent-fg:#ffffff; --warn:#b3261e; --map:#14181a; --sel:#dcebf1;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; --head:"Space Grotesk","Inter",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#10171c; --fg:#e6edf1; --mut:#93a4b0; --card:#172128; --line:#2c3a44;
  --accent:#4fb6d6; --accent-fg:#06222c; --warn:#ff8a80; --map:#0b0e0f; --sel:#1d3440; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#10171c; --fg:#e6edf1; --mut:#93a4b0; --card:#172128; --line:#2c3a44;
  --accent:#4fb6d6; --accent-fg:#06222c; --warn:#ff8a80; --map:#0b0e0f; --sel:#1d3440; color-scheme:dark}
''' + h[b:]
rep('h1{font-size:20px;font-weight:650;margin:0;letter-spacing:-.01em}', 'h1{font:600 22px/1.15 var(--head);margin:0}')
rep('</style>', '''.seg{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--line);border-radius:6px;overflow:hidden;margin-bottom:8px}
.seg button{border:0;border-radius:0;padding:8px 6px;font-size:13px;background:var(--card)}
.seg button[data-v="v3"]{grid-column:1/-1;border-top:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-fg)}
.prm{display:grid;grid-template-columns:auto minmax(0,1fr) 48px;gap:4px 8px;align-items:center;margin-bottom:6px}
.prm input[type=range]{width:100%;accent-color:var(--accent)}
.prm .v{text-align:right;font-family:var(--mono);font-size:12px;color:var(--mut)}
.leg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--mut);margin-top:6px}
.leg i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:4px;vertical-align:-1px}
#pl-state{color:var(--mut);font-size:12px;min-height:1.4em}
.plan{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.types td,.types th{padding:3px 4px;font-size:12px}.types .chk{color:var(--fg)}.types .sw{display:inline-block;vertical-align:-2px}
#pl-vars{display:flex;flex-direction:column;gap:3px}
.var{display:flex;justify-content:space-between;gap:8px;text-align:left;font-size:12px;padding:5px 8px}
#pl-res td{white-space:normal;overflow-wrap:anywhere}#pl-res .n{max-width:11em}
.var span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.var b{font-family:var(--mono)}
</style>''')
# ---- nagłówek i panel generatora ----
rep('<h1>Edytor obrysu terenu</h1>', '<h1>Planer zabudowy terenu</h1>')
rep('<div class="total">Dostępne pod zabudowę <b id="tot">–</b> · <span id="totha">–</span></div>',
    '<div class="total">Dostępne pod zabudowę <b id="tot">–</b> · <span id="totha">–</span> · generator: <b id="totz">–</b></div>')
rep('''    <div class="side">
      <section>
        <h2>Warstwy</h2>''', '''    <div class="side">
      <section class="plan">
        <h2>Zabudowa: automatyczne wypełnienie</h2>
        <div class="seg" id="pl-var" role="group" aria-label="Zestaw typów budynków">
          <button data-v="base" aria-pressed="false">Wersja podstawowa</button>
          <button data-v="v2" aria-pressed="false">Po modyfikacji</button>
          <button data-v="v3" aria-pressed="true">Po modyfikacji + lustrzane A w miejscu C</button>
        </div>
        <table class="types"><thead><tr><th>Typ budynku</th><th class="n">Kond.</th><th class="n">Lokale</th><th class="n">PU</th><th class="n">Zab.</th></tr></thead><tbody id="pl-types"></tbody></table>
        <div class="prm" style="margin-top:10px">
          <label for="pl-sb">Odsunięcie od granicy</label><input type="range" id="pl-sb" min="0" max="30" step="1" value="4"><span class="v" id="pl-sbv"></span>
          <label for="pl-se">Od stref wyłączonych</label><input type="range" id="pl-se" min="0" max="30" step="1" value="0"><span class="v" id="pl-sev"></span>
          <label for="pl-dist">Odległość między budynkami</label><input type="range" id="pl-dist" min="0" max="40" step="1" value="8"><span class="v" id="pl-distv"></span>
          <label for="pl-cov">Maks. udział zabudowy</label><input type="range" id="pl-cov" min="5" max="100" step="5" value="100"><span class="v" id="pl-covv"></span>
        </div>
        <div class="grp" style="margin-bottom:6px"><span>Cel</span><select id="pl-goal" aria-label="Cel optymalizacji"><option value="lokale">Największa liczba lokali</option><option value="pu">Największa powierzchnia użytkowa</option><option value="budynki">Największa liczba budynków</option><option value="zabudowa">Największa powierzchnia zabudowy</option></select></div>
        <div id="pl-state" role="status"></div>
        <h2 style="margin-top:8px">Warianty (wartość celu)</h2>
        <div id="pl-vars"></div>
        <h2 style="margin-top:12px">Wynik wybranego wariantu</h2>
        <table><tbody id="pl-res"></tbody></table>
        <h2 style="margin-top:12px">Porównanie</h2>
        <table><thead><tr><th>Układ</th><th class="n">Bud.</th><th class="n">Lokali</th><th class="n">PU [m²]</th><th class="n">Zab.</th></tr></thead><tbody id="pl-cmp"></tbody></table>
        <div class="grp" style="margin-top:8px"><button id="pl-csv">Kopiuj statystyki CSV</button></div>
        <p class="note">Generator ustawia pojedyncze budynki wybranych typów, w czterech obrotach co 90° względem kierunku siatki, i sprawdza kolizje na prawdziwych obrysach. To analiza chłonności, nie projekt: nie ma jeszcze dróg, parkingów ani warunku dojazdu, a wartości domyślne są przykładowe. * Lokale bez budynku C – nie mam dla niego danych o lokalach.</p>
      </section>
      <section>
        <h2>Warstwy</h2>''')
# ---- skrypt: warstwa budynków, przykład startowy, haki ----
rep("gF=el('g',{},svg),gS=el('g',{},svg)", "gF=el('g',{},svg),gB=el('g',{},svg),gS=el('g',{},svg)")
rep("const INIT={mpp:MPP,seq:1,active:0,polys:[{kind:'site',name:'Granica terenu',v:[]}]};",
    "const INIT={mpp:MPP,seq:1,active:0,polys:[{kind:'site',name:'Granica terenu',v:[]}]};\n"
    "const SAMPLE={mpp:MPP,seq:2,active:0,polys:[{kind:'site',name:'Granica (przykład – zastąp swoją)',v:[[380,520],[1560,470],[1640,1420],[470,1500]]},{kind:'excl',name:'Wyłączona 1 (przykład)',v:[[900,900],[1120,890],[1130,1080],[910,1090]]}]};")
rep("let S=clone(INIT), hist=[]", "let S=clone(SAMPLE), hist=[]")
rep("  if(is3)zones3();\n}", "  if(is3)zones3();\n  drawPlan();planUI();planSchedule();\n}")
rep("function exportData(b){", gen + "\nfunction exportData(b){")
rep("balance_m2:b.hasSite", "plan:KIT?planExport():null,balance_m2:b.hasSite")
core = open('planer/gen_core.js', encoding='utf-8').read()
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>', '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script id="gen-core">' + core + '</script>')
rep("zones3();setMode3(mode3);requestAnimationFrame(frame)}", "zones3();plan3();setMode3(mode3);requestAnimationFrame(frame)}")
rep("if(!SV['MS zabudowa']&&S.polys[0].v.length>=3){", "if(!SV['MS zabudowa']&&S.polys[0].v.length>=3&&JSON.stringify(S.polys)!==JSON.stringify(SAMPLE.polys)){")
# start generatora na końcu skryptu edytora
i = h.rindex('})();'); h = h[:i] + 'planInit();\n' + h[i:]
open('planer/index.html', 'w', encoding='utf-8').write(h)
js = re.findall(r'<script>(.*?)</script>', h, re.S)[-1]; open('/tmp/claude-0/-home-user-claude-workspace-msz/099adb85-f613-587d-b925-e0767528f8de/scratchpad/b3d/chk2.js', 'w').write(js)
print(len(h))
