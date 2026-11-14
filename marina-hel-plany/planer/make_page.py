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
header{align-items:center}.views{margin-left:auto}
.kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}
.kpi{border:1px solid var(--line);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:2px;min-width:0}
.kpi b{font:600 28px/1.05 var(--head);font-variant-numeric:tabular-nums;color:var(--accent)}
.kpi span{font-size:12px;color:var(--mut)}
.plan .total{font-family:var(--sans);font-size:12px;margin:0 0 10px}.plan .total b{font-size:13px}
.line{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.line label,.line>span{color:var(--mut);font-size:13px}
.line input[type=number]{width:5.2em;font:600 15px var(--sans);text-align:right;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:5px 7px}
.line select{flex:1;min-width:0}
.fold{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:0 12px}
.fold>summary{cursor:pointer;padding:10px 0;font-weight:600;color:var(--fg);list-style-position:inside}
.fold[open]{padding-bottom:12px}
.side{gap:8px}.side section{margin:0}
#edit{margin:0}#edit .bar{margin-bottom:8px}#edit .saved{margin:0 0 8px}
#map.viewing .hnd,#map.viewing .lab{display:none}#map.viewing [data-k]{pointer-events:none}
.v3{position:absolute;left:8px;top:8px;width:230px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.v3 .line input[type=range]{flex:1;min-width:0;accent-color:var(--accent)}.v3 .v{font-size:12px;color:var(--mut);width:36px;text-align:right}
#v3-fl{display:grid;grid-template-columns:1fr 1fr;gap:2px 8px}#v3-fl .chk{color:var(--fg)}.v3 .note{margin-top:6px}
.types td,.types th{padding:3px 4px;font-size:12px}.types .chk{color:var(--fg)}.types .sw{display:inline-block;vertical-align:-2px}
#pl-vars{display:flex;flex-direction:column;gap:3px}
.var{display:flex;justify-content:space-between;gap:8px;text-align:left;font-size:12px;padding:5px 8px}
#pl-res td{white-space:normal;overflow-wrap:anywhere}#pl-res .n{max-width:11em}
.var span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.var b{font-family:var(--mono)}
</style>''')
# ---- nagłówek i panel generatora ----
rep('<h1>Edytor obrysu terenu</h1>', '<h1>Planer zabudowy terenu</h1>')
rep('''    <div class="side">
      <section>
        <h2>Warstwy</h2>''', '''    <div class="side">
      <section class="plan">
        <div class="kpis">
          <div class="kpi"><b id="kpi-n">–</b><span>budynków</span></div>
          <div class="kpi"><b id="kpi-lok">–</b><span>lokali</span></div>
          <div class="kpi"><b id="kpi-pu">–</b><span>m² powierzchni użytkowej</span></div>
          <div class="kpi"><b id="kpi-cov">–</b><span>terenu zabudowane</span></div>
        </div>
        <p class="note" id="kpi-var"></p>
        <div class="seg" id="pl-var" role="group" aria-label="Zestaw typów budynków">
          <button data-v="base" aria-pressed="false">Wersja podstawowa</button>
          <button data-v="v2" aria-pressed="false">Po modyfikacji</button>
          <button data-v="v3" aria-pressed="true">Po modyfikacji + lustrzane A w miejscu C</button>
        </div>
        <div class="line"><label for="pl-cov">Zabudowa terenu do</label><input type="number" id="pl-cov" min="1" max="100" step="1" value="100" inputmode="numeric"><span>% powierzchni</span></div>
        <div class="line"><label for="pl-goal">Cel</label><select id="pl-goal"><option value="lokale">Najwięcej lokali</option><option value="pu">Największa powierzchnia użytkowa</option><option value="budynki">Najwięcej budynków</option><option value="zabudowa">Największa powierzchnia zabudowy</option></select></div>
        <div id="pl-state" role="status"></div>
      </section>
      <details class="fold"><summary>Warianty do porównania</summary><div id="pl-vars"></div></details>
      <details class="fold"><summary>Typy budynków</summary>
        <table class="types"><thead><tr><th>Typ</th><th class="n">Kond.</th><th class="n">Lokale</th><th class="n">PU</th><th class="n">Zab.</th></tr></thead><tbody id="pl-types"></tbody></table>
      </details>
      <details class="fold"><summary>Odstępy i odsunięcia</summary>
        <div class="prm">
          <label for="pl-sb">Odsunięcie od granicy</label><input type="range" id="pl-sb" min="0" max="30" step="1" value="4"><span class="v" id="pl-sbv"></span>
          <label for="pl-se">Od stref wyłączonych</label><input type="range" id="pl-se" min="0" max="30" step="1" value="0"><span class="v" id="pl-sev"></span>
          <label for="pl-dist">Odległość między budynkami</label><input type="range" id="pl-dist" min="0" max="40" step="1" value="8"><span class="v" id="pl-distv"></span>
        </div>
      </details>
      <details class="fold"><summary>Szczegóły wyniku i porównanie</summary>
        <table><tbody id="pl-res"></tbody></table>
        <table style="margin-top:10px"><thead><tr><th>Układ</th><th class="n">Bud.</th><th class="n">Lokali</th><th class="n">PU [m²]</th><th class="n">Zab.</th></tr></thead><tbody id="pl-cmp"></tbody></table>
        <div class="grp" style="margin-top:8px"><button id="pl-csv">Kopiuj statystyki CSV</button></div>
        <p class="note">To analiza chłonności terenu, nie projekt: nie ma jeszcze dróg, parkingów ani warunku dojazdu, a wartości domyślne są przykładowe. * Lokale bez budynku C – nie mam dla niego danych o lokalach.</p>
      </details>
      <details class="fold"><summary>Teren: warstwy i bilans</summary>
      <section>
        <h2>Warstwy</h2>''')
rep('''      <section>
        <h2 id="seg-h">Odcinki</h2>''', '''      </details>
      <details class="fold"><summary>Długości boków</summary>
      <section>
        <h2 id="seg-h">Odcinki</h2>''')
rep('''      <section>
        <details id="det">''', '''      </details>
      <section>
        <details id="det" class="fold">''')
# ---- nagłówek: tytuł i przełącznik widoku; narzędzia edycji i zapisane tereny schowane w zwijanej sekcji ----
_i0 = h.index('<header>'); _i1 = h.index('<div class="main">'); _top = h[_i0:_i1]
_lines = _top.split('\n')
_saved = next(l for l in _lines if '<div class="saved"' in l); _view = next(l for l in _lines if 'id="v-2d"' in l); _total = next(l for l in _lines if 'class="total"' in l)
_b0 = _top.index('<div class="bar">'); _b1 = _top.index('<div id="msg"')
_bar = _top[_b0:_b1].replace(_view + '\n', '')
h = h[:_i0] + '<header>\n    <h1>Planer zabudowy terenu</h1>\n' + _view.replace('class="grp"', 'class="grp views"') + '\n  </header>\n' \
    + '  <details class="fold" id="edit"><summary>Edycja terenu: granica, strefy, zapisane tereny</summary>\n  ' + _bar + _saved.replace('class="saved"', 'class="saved grp"') + '\n  <div id="msg" role="status"></div>\n  </details>\n\n  ' + h[_i1:]
rep('''        <p class="note" id="kpi-var"></p>''', '''        <p class="note" id="kpi-var"></p>
        ''' + _total.strip().replace('Dostępne pod zabudowę', 'Teren dostępny pod zabudowę'))
# ---- nakładka 3D: prześwit brył i piętra ----
rep('<div class="modes" id="modes" hidden>', '''<div class="v3" id="v3" hidden>
        <div class="line"><label for="v3-op">Prześwit brył</label><input type="range" id="v3-op" min="0" max="1" step="0.01" value="0"><span class="v" id="v3-opv">0%</span></div>
        <div class="line"><span>Plany pięter</span><button id="v3-all">Wszystkie</button><button id="v3-none">Żadne</button></div>
        <div id="v3-fl"></div>
        <p class="note">Plany mieszkań widać po zwiększeniu prześwitu.</p>
      </div>
      <div class="modes" id="modes" hidden>''')
rep("$('modes').hidden=!is3;", "$('modes').hidden=!is3;$('v3').hidden=!is3;")
rep("gL=el('g',{},svg),gP=el('g',{},svg)", "gL=el('g',{class:'lab'},svg),gP=el('g',{class:'hnd'},svg)")
# ---- skrypt: warstwa budynków, przykład startowy, haki ----
rep("gF=el('g',{},svg),gS=el('g',{},svg)", "gF=el('g',{},svg),gB=el('g',{},svg),gS=el('g',{},svg)")
rep("const INIT={mpp:MPP,seq:1,active:0,polys:[{kind:'site',name:'Granica terenu',v:[]}]};",
    "const INIT={mpp:MPP,seq:1,active:0,polys:[{kind:'site',name:'Granica terenu',v:[]}]};\n"
    "const SAMPLE={mpp:MPP,seq:2,active:0,polys:[{kind:'site',name:'Granica (przykład – zastąp swoją)',v:[[380,520],[1560,470],[1640,1420],[470,1500]]}]};")
rep("let S=clone(INIT), hist=[]", "let S=clone(SAMPLE), hist=[]")
# jednorazowe sprzątanie: przykładowa strefa wyłączona z pierwszej wersji planera znika także z zapisanego stanu przeglądarki
rep("try{const s=localStorage.getItem(KEY); if(s){const o=JSON.parse(s); if(valid(o)) S=o;}}catch(e){}",
    "try{const s=localStorage.getItem(KEY); if(s){const o=JSON.parse(s); if(valid(o)) S=o;}}catch(e){}\n"
    "{const n0=S.polys.length;S.polys=S.polys.filter((p,i)=>!i||!(p.kind==='excl'&&p.name==='Wyłączona 1 (przykład)'));if(S.polys.length!==n0){S.active=0;try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}}")
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
