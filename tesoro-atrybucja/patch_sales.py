import json
p = 'index.html'
s = open(p).read()

def rep(a, b):
    global s
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)

# --- CSS
rep(".tx-head { display: grid; gap: var(--cds-gap-sm); }",
""".tx-head { display: grid; gap: var(--cds-gap-sm); }
.tx-tabs { display: flex; gap: var(--cds-gap-xs); border-bottom: 1px solid var(--color-border-line); }
.tx-tabs button { all: unset; cursor: pointer; padding: var(--cds-pad-sm) var(--cds-pad-md); font-size: var(--cds-font-size-body); color: var(--color-fg-muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tx-tabs button[aria-selected="true"] { color: var(--color-fg); border-bottom-color: var(--color-fg); font-weight: var(--cds-font-weight-medium); }
.tx-tabs button:focus-visible { outline: 2px solid var(--color-fg); border-radius: 4px; }
.tx-page { display: grid; gap: var(--cds-gap-lg); }
.tx-seg { display: inline-flex; border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); overflow: hidden; }
.tx-seg button { all: unset; cursor: pointer; padding: var(--cds-pad-xs) var(--cds-pad-sm); font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); }
.tx-seg button[aria-pressed="true"] { background: var(--color-fg); color: var(--color-bg); }
.tx-seg button:focus-visible { outline: 2px solid var(--color-fg); }""")

# --- tabs in header
rep("""    <h1>Atrybucja leadów Tesoro</h1>
    <p class="tx-take" id="takeaway">""",
"""    <h1>Atrybucja leadów Tesoro</h1>
    <nav class="tx-tabs" role="tablist" aria-label="Zakładki">
      <button role="tab" id="tab-marketing" aria-selected="true" data-page="marketing">Marketing i leady</button>
      <button role="tab" id="tab-sprzedaz" aria-selected="false" data-page="sprzedaz">Sprzedaż i inwestycje</button>
    </nav>
    <p class="tx-take" id="takeaway">""")

rep("""    <p class="tx-note">Sprzedaż = podpisana umowa deweloperska, przedwstępna lub akt notarialny (bez anulowanych). Lead łączony z klientem po telefonie lub e-mailu; sprzedaż przypisana do pierwszego leada tej osoby, utworzonego przed umową. Leady z ostatnich miesięcy jeszcze nie zdążyły dojść do umowy.</p>
  </header>
""",
"""    <p class="tx-note" id="note-marketing">Sprzedaż = podpisana umowa deweloperska, przedwstępna lub akt notarialny (bez anulowanych). Lead łączony z klientem po telefonie lub e-mailu; sprzedaż przypisana do pierwszego leada tej osoby, utworzonego przed umową. Leady z ostatnich miesięcy jeszcze nie zdążyły dojść do umowy.</p>
    <p class="tx-note" id="note-sprzedaz" hidden>Sprzedaż = pierwsza podpisana umowa deweloperska, przedwstępna lub akt notarialny na dany lokal (bez anulowanych); kolejne umowy na ten sam lokal nie są liczone drugi raz. Typ nieruchomości ustalony z etapu w rezerwacjach i nazwy lokalu; dla części lokali Tesoro Golf Park bez słownika typ jest „Nieustalony”.</p>
  </header>

  <div class="tx-page" id="page-sprzedaz" hidden>
    <section class="tx-tiles" id="kpi-sprzedaz">
      <div class="tx-tile"><span class="lab">Sprzedane lokale</span><span class="val dash-skeleton" data-k="sprzedaze" data-source="sprzedaz_inw" data-field="sprzedaze">—</span><span class="sub">w wybranym okresie</span></div>
      <div class="tx-tile"><span class="lab">Wartość brutto</span><span class="val dash-skeleton" data-k="wartosc" data-source="sprzedaz_inw" data-field="wartosc">—</span><span class="sub">PLN, umowy sprzedażowe</span></div>
      <div class="tx-tile"><span class="lab">Sprzedana powierzchnia</span><span class="val dash-skeleton" data-k="m2" data-source="sprzedaz_inw" data-field="m2">—</span><span class="sub">m²</span></div>
      <div class="tx-tile"><span class="lab">Średnia cena</span><span class="val dash-skeleton" data-k="cena_m2" data-source="sprzedaz_inw" data-field="cena_m2">—</span><span class="sub">PLN / m²</span></div>
      <div class="tx-tile"><span class="lab">Rezerwacje</span><span class="val dash-skeleton" data-k="rezerwacje" data-source="sprzedaz_inw" data-field="rezerwacje">—</span><span class="sub">umowy rezerwacyjne</span></div>
      <div class="tx-tile"><span class="lab">Anulowane umowy</span><span class="val dash-skeleton" data-k="anulowane" data-source="sprzedaz_inw" data-field="anulowane">—</span><span class="sub">wszystkich typów</span></div>
    </section>

    <section class="tx-card" id="sprzedaz-inwestycje">
      <h2>Sprzedaż miesiąc po miesiącu wg inwestycji</h2>
      <div class="tx-filters">
        <div class="tx-seg" id="seg-miara" role="group" aria-label="Miara">
          <button aria-pressed="true" data-m="sprzedaze">Liczba lokali</button>
          <button aria-pressed="false" data-m="wartosc">Wartość brutto</button>
          <button aria-pressed="false" data-m="m2">Powierzchnia m²</button>
        </div>
      </div>
      <div class="tx-legend" id="lg-inw"></div>
      <div class="tx-chart dash-skeleton" id="ch-inw" data-source="sprzedaz_mies_inw"></div>
    </section>

    <div class="tx-grid">
      <section class="tx-card" id="typy">
        <h2>Jakie typy nieruchomości sprzedajemy</h2>
        <p class="tx-note">Sprzedane lokale wg typu: rok po roku dla całego okresu, miesiąc po miesiącu dla wybranego roku.</p>
        <div class="tx-legend" id="lg-typ"></div>
        <div class="tx-chart dash-skeleton" id="ch-typ" data-source="sprzedaz_typ"></div>
      </section>
      <section class="tx-card" id="typy-tabela">
        <h2>Typy: liczba, wartość, cena za m²</h2>
        <div class="tx-tablebox">
          <table class="tx-table" id="t-typ" data-source="typy" data-row-key="okres,inw,typ">
            <thead><tr>
              <th data-field="typ">Typ</th>
              <th data-field="sprzedaze">Sprzedane</th>
              <th data-field="udzial">% sprzedaży</th>
              <th data-field="wartosc">Wartość brutto</th>
              <th data-field="sr_m2">Śr. metraż</th>
              <th data-field="cena_m2">Śr. cena / m²</th>
              <th data-field="rezerwacje">Rezerwacje</th>
            </tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="tx-card" id="inwestycje-tabela">
      <h2>Inwestycje i etapy</h2>
      <p class="tx-note">Etap znany tylko dla lokali, które miały rezerwację w CRM; pozostałe zgrupowane jako „bez etapu”.</p>
      <div class="tx-tablebox">
        <table class="tx-table" id="t-etap" data-source="etapy_sprzedaz" data-row-key="okres,inw,etap">
          <thead><tr>
            <th data-field="inw">Inwestycja</th>
            <th data-field="etap">Etap</th>
            <th data-field="typ">Typ</th>
            <th data-field="sprzedaze">Sprzedane</th>
            <th data-field="wartosc">Wartość brutto</th>
            <th data-field="cena_m2">Śr. cena / m²</th>
            <th data-field="rezerwacje">Rezerwacje</th>
            <th data-field="anulowane">Anulowane</th>
            <th data-field="ostatnia">Ostatnia sprzedaż</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <section class="tx-card" id="oferta">
      <h2>Sprzedane vs. w ofercie, w budowie i planowane</h2>
      <p class="tx-note">Tej części nie da się dziś zbudować: klucz API nie ma dostępu do słownika lokali ani statusów inwestycji (endpointy <code>realestate-list</code>, <code>available-for-sale</code>, <code>sold-and-not-sold</code>, <code>investment-status</code>, <code>investments-sales-targets</code> zwracają 403). Po włączeniu ich przez Vox pokażę tu dla każdej inwestycji i etapu: lokale ogółem, sprzedane, zarezerwowane i wolne, tempo sprzedaży (lokali/mies.), prognozowany czas wyprzedania i realizację celów sprzedażowych.</p>
    </section>
  </div>

  <div class="tx-page" id="page-marketing">
""")

rep("""    </ul>
  </section>
</div>
""",
"""    </ul>
  </section>
  </div>
</div>
""")

# --- calcs
rep("dash.calc('czas', {",
"""dash.calc('sprzedaz_inw', {
  title: 'Sprzedaż wg inwestycji',
  description: 'Sprzedane lokale, wartość brutto, m², średnia cena/m², rezerwacje i anulowane umowy wg roku umowy i inwestycji; wiersz „all” to suma.',
  inputs: ['umowy'],
  fn: (umowy) => {
    const g = new Map();
    for (const r of umowy) for (const okres of ['all', r.data.slice(0, 4)]) for (const inw of ['all', r.inwestycja]) {
      const k = okres + '|' + inw;
      let a = g.get(k);
      if (!a) g.set(k, a = { okres, inw, sprzedaze: 0, wartosc: 0, m2: 0, rezerwacje: 0, anulowane: 0 });
      if (r.sprzedaz === '1') { a.sprzedaze++; a.wartosc += +r.cena_brutto || 0; a.m2 += +r.powierzchnia || 0; }
      if (r.rezerwacja === '1' && r.anulowana !== '1') a.rezerwacje++;
      if (r.anulowana === '1') a.anulowane++;
    }
    return [...g.values()].map((a) => ({ ...a, m2: Math.round(a.m2), cena_m2: a.m2 ? Math.round(a.wartosc / a.m2) : null }));
  },
});

dash.calc('sprzedaz_mies_inw', {
  title: 'Sprzedaż miesięcznie wg inwestycji',
  description: 'Sprzedane lokale, wartość brutto i m² wg miesiąca umowy i inwestycji.',
  inputs: ['umowy'],
  fn: (umowy) => {
    const g = new Map();
    for (const r of umowy) {
      if (r.sprzedaz !== '1') continue;
      const k = r.data.slice(0, 7) + '|' + r.inwestycja;
      let a = g.get(k);
      if (!a) g.set(k, a = { miesiac: r.data.slice(0, 7), inw: r.inwestycja, sprzedaze: 0, wartosc: 0, m2: 0 });
      a.sprzedaze++; a.wartosc += +r.cena_brutto || 0; a.m2 += +r.powierzchnia || 0;
    }
    return [...g.values()].map((a) => ({ ...a, m2: Math.round(a.m2) }));
  },
});

dash.calc('sprzedaz_typ', {
  title: 'Sprzedaż wg typu w czasie',
  description: 'Sprzedane lokale wg roku i miesiąca umowy, typu nieruchomości i inwestycji.',
  inputs: ['umowy'],
  fn: (umowy) => {
    const g = new Map();
    for (const r of umowy) {
      if (r.sprzedaz !== '1') continue;
      for (const inw of ['all', r.inwestycja]) {
        const k = inw + '|' + r.data.slice(0, 7) + '|' + r.typ_nieruchomosci;
        let a = g.get(k);
        if (!a) g.set(k, a = { inw, miesiac: r.data.slice(0, 7), typ: r.typ_nieruchomosci, sprzedaze: 0 });
        a.sprzedaze++;
      }
    }
    return [...g.values()];
  },
});

dash.calc('typy', {
  title: 'Typy nieruchomości',
  description: 'Sprzedane lokale, udział, wartość, średni metraż, średnia cena/m² i rezerwacje wg typu, roku umowy i inwestycji.',
  inputs: ['umowy'],
  fn: (umowy) => {
    const g = new Map();
    for (const r of umowy) for (const okres of ['all', r.data.slice(0, 4)]) for (const inw of ['all', r.inwestycja]) {
      const k = okres + '|' + inw + '|' + r.typ_nieruchomosci;
      let a = g.get(k);
      if (!a) g.set(k, a = { okres, inw, typ: r.typ_nieruchomosci, sprzedaze: 0, wartosc: 0, m2: 0, rezerwacje: 0 });
      if (r.sprzedaz === '1') { a.sprzedaze++; a.wartosc += +r.cena_brutto || 0; a.m2 += +r.powierzchnia || 0; }
      if (r.rezerwacja === '1' && r.anulowana !== '1') a.rezerwacje++;
    }
    const rows = [...g.values()];
    const tot = new Map();
    rows.forEach((a) => tot.set(a.okres + '|' + a.inw, (tot.get(a.okres + '|' + a.inw) || 0) + a.sprzedaze));
    return rows.map((a) => ({ ...a, udzial: tot.get(a.okres + '|' + a.inw) ? a.sprzedaze / tot.get(a.okres + '|' + a.inw) : 0,
      sr_m2: a.sprzedaze ? Math.round(a.m2 / a.sprzedaze) : null, cena_m2: a.m2 ? Math.round(a.wartosc / a.m2) : null }));
  },
});

dash.calc('etapy_sprzedaz', {
  title: 'Inwestycje i etapy',
  description: 'Sprzedane lokale, wartość, cena/m², rezerwacje, anulowane umowy i data ostatniej sprzedaży wg inwestycji, etapu, roku umowy; filtr inwestycji „all” lub nazwa.',
  inputs: ['umowy'],
  fn: (umowy) => {
    const g = new Map();
    for (const r of umowy) for (const okres of ['all', r.data.slice(0, 4)]) for (const inwf of ['all', r.inwestycja]) {
      const etap = r.etap || 'bez etapu';
      const k = okres + '|' + inwf + '|' + r.inwestycja + '|' + etap;
      let a = g.get(k);
      if (!a) g.set(k, a = { okres, inwf, inw: r.inwestycja, etap, typ: r.typ_nieruchomosci, sprzedaze: 0, wartosc: 0, m2: 0, rezerwacje: 0, anulowane: 0, ostatnia: null });
      if (r.sprzedaz === '1') { a.sprzedaze++; a.wartosc += +r.cena_brutto || 0; a.m2 += +r.powierzchnia || 0; if (!a.ostatnia || r.data > a.ostatnia) a.ostatnia = r.data; }
      if (r.rezerwacja === '1' && r.anulowana !== '1') a.rezerwacje++;
      if (r.anulowana === '1') a.anulowane++;
      if (a.etap === 'bez etapu') a.typ = 'różne';
    }
    return [...g.values()].map((a) => ({ ...a, cena_m2: a.m2 ? Math.round(a.wartosc / a.m2) : null }));
  },
});

dash.calc('czas', {""")

# --- drawers: tabs + sales page
rep("""  window.txDrawers = [drawTop, drawKanaly, drawKampanie, drawCrm];
  dash.onData(() => {
    selO.value = dash.params().okres; selI.value = dash.params().inw;
    window.txDrawers.forEach((f) => f());
  });""",
"""  // zakładki
  const pages = { marketing: document.getElementById('page-marketing'), sprzedaz: document.getElementById('page-sprzedaz') };
  window.txPage = 'marketing';
  function showPage(name) {
    window.txPage = pages[name] ? name : 'marketing';
    Object.entries(pages).forEach(([k, el]) => { el.hidden = k !== window.txPage; });
    document.getElementById('note-marketing').hidden = window.txPage !== 'marketing';
    document.getElementById('note-sprzedaz').hidden = window.txPage !== 'sprzedaz';
    document.querySelectorAll('.tx-tabs [role=tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.page === window.txPage)));
    document.getElementById('takeaway').hidden = window.txPage !== 'marketing';
    dash.setLink(window.txPage);
    window.txDrawers.forEach((f) => f());
  }
  document.querySelectorAll('.tx-tabs [role=tab]').forEach((b) => b.addEventListener('click', () => showPage(b.dataset.page)));
  window.txShowPage = showPage;

  window.txDrawers = [drawTop, drawKanaly, drawKampanie, drawCrm];
  dash.onData(() => {
    selO.value = dash.params().okres; selI.value = dash.params().inw;
    window.txDrawers.forEach((f) => f());
  });""")

rep("""  window.txDrawers.push(
    etapy,""",
"""  // ---------- zakładka Sprzedaż ----------
  const { fmtMoney } = window.txFmt;
  const INW = ['Ogrody Tesoro', 'Tesoro Golf Park'];
  const TYPY = ['Apartament', 'Dom szeregowy / kamieniczka', 'Dom bliźniaczy', '4PLEX', 'Willa', 'Nieustalony'];
  const colorInw = (k) => dash.colors[INW.indexOf(k) < 0 ? 7 : INW.indexOf(k)];
  const colorTyp = (k) => (k === 'Nieustalony' ? 'var(--cds-chart-muted)' : dash.colors[TYPY.indexOf(k) < 0 ? 6 : TYPY.indexOf(k)]);
  let miara = 'sprzedaze';
  const fmtM = (m, v) => (m === 'wartosc' ? fmtMoney(v) : m === 'm2' ? fmtInt(Math.round(v)) + ' m²' : fmtInt(v));
  document.querySelectorAll('#seg-miara button').forEach((b) => b.addEventListener('click', () => {
    miara = b.dataset.m;
    document.querySelectorAll('#seg-miara button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    drawInw();
  }));
  const onSales = () => window.txPage === 'sprzedaz';
  const MON = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie', 'wrz', 'paź', 'lis', 'gru'];

  function kpiSales() {
    if (!onSales()) return;
    const d = dash.data('sprzedaz_inw');
    const tiles = document.querySelectorAll('#kpi-sprzedaz [data-k]');
    if (d.status !== 'ok') { if (d.status === 'error') tiles.forEach((t) => { t.classList.remove('dash-skeleton'); t.textContent = '—'; }); return; }
    const { okres, inw } = dash.params();
    const tot = d.data.find((r) => r.okres === okres && r.inw === inw);
    tiles.forEach((t) => {
      t.classList.remove('dash-skeleton');
      t.setAttribute('data-where', 'okres=' + encodeURIComponent(okres) + '&inw=' + encodeURIComponent(inw));
      const k = t.dataset.k; const v = tot ? tot[k] : null;
      t.textContent = v == null ? '—' : k === 'wartosc' ? fmtMoney(v) : fmtInt(v);
    });
  }

  function barsStacked(boxId, lgId, rows, keys, colorFn, field, labelX, tipHead) {
    const box = document.getElementById(boxId); const lg = document.getElementById(lgId);
    box.classList.remove('dash-skeleton');
    const xs = [...new Set(rows.map((r) => r.x))].sort();
    const byX = new Map(xs.map((x) => [x, Object.fromEntries(keys.map((k) => [k, 0]))]));
    rows.forEach((r) => { byX.get(r.x)[r.k] += r[field]; });
    const table = xs.map((x) => ({ x, ...byX.get(x) }));
    lg.replaceChildren(...keys.map((k) => { const sp = document.createElement('span'); const sw = document.createElement('span'); sw.className = 'tx-sw'; sw.style.background = colorFn(k); sp.append(sw, document.createTextNode(k)); return sp; }));
    box.querySelectorAll('svg, .tx-note').forEach((e) => e.remove());
    if (!xs.length) { const p = document.createElement('p'); p.className = 'tx-note'; p.textContent = 'Brak sprzedaży w tym wyborze.'; box.append(p); return; }
    const W = Math.max(280, box.clientWidth), H = 260;
    const ymax = d3.max(table, (r) => d3.sum(keys, (k) => r[k])) || 1;
    const y = d3.scaleLinear([0, ymax], [H - 24, 8]).nice();
    const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const yt = y.ticks(4);
    const fy = (v) => (field === 'wartosc' ? new Intl.NumberFormat('pl-PL', { notation: 'compact', maximumFractionDigits: 1 }).format(v) : fmtInt(v));
    const probe = svg.append('text').attr('font-size', 11).text(fy(d3.max(yt)));
    const ml = probe.node().getComputedTextLength() + 10; probe.remove();
    const x = d3.scaleBand(xs, [ml, W - 4]).padding(0.2);
    svg.append('g').selectAll('line').data(yt).join('line').attr('x1', ml).attr('x2', W - 4).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
    svg.append('g').selectAll('text').data(yt).join('text').attr('x', ml - 6).attr('y', (v) => y(v) + 4).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fy);
    const step = Math.max(1, Math.ceil(xs.length / Math.floor((W - ml) / 48)));
    svg.append('g').selectAll('text').data(xs.filter((v, i) => i % step === 0)).join('text')
      .attr('x', (v) => x(v) + x.bandwidth() / 2).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(labelX);
    svg.append('line').attr('x1', ml).attr('x2', W - 4).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--cds-chart-axis)');
    svg.append('g').selectAll('g').data(d3.stack().keys(keys)(table)).join('g').attr('fill', (s) => colorFn(s.key))
      .selectAll('rect').data((s) => s).join('rect')
      .attr('x', (p) => x(p.data.x)).attr('width', x.bandwidth()).attr('y', (p) => y(p[1])).attr('height', (p) => Math.max(0, y(p[0]) - y(p[1])));
    const tip = tipFor(box);
    svg.append('g').selectAll('rect').data(table).join('rect')
      .attr('x', (r) => x(r.x)).attr('width', x.bandwidth()).attr('y', 0).attr('height', H - 24).attr('fill', 'transparent')
      .on('mousemove', (ev, r) => showTip(box, tip, ev, tipHead(r.x), [['', 'Razem', fmtM(field, d3.sum(keys, (k) => r[k]))], ...keys.filter((k) => r[k]).map((k) => [colorFn(k), k, fmtM(field, r[k])])]))
      .on('mouseleave', () => { tip.hidden = true; });
  }

  function drawInw() {
    if (!onSales()) return;
    const d = dash.data('sprzedaz_mies_inw');
    const box = document.getElementById('ch-inw');
    if (d.status !== 'ok') { if (d.status === 'error') { box.classList.remove('dash-skeleton'); box.replaceChildren(); const f = document.createElement('div'); f.className = 'tx-fail'; f.textContent = 'Failed to load'; box.append(f); } return; }
    const { okres, inw } = dash.params();
    const sel = d.data.filter((r) => (inw === 'all' || r.inw === inw) && (okres === 'all' || r.miesiac.startsWith(okres)));
    const rows = okres === 'all'
      ? sel.map((r) => ({ x: r.miesiac.slice(0, 4), k: r.inw, [miara]: r[miara] }))
      : sel.map((r) => ({ x: r.miesiac, k: r.inw, [miara]: r[miara] }));
    const keys = INW.filter((k) => rows.some((r) => r.k === k)); rows.forEach((r) => { if (!keys.includes(r.k)) keys.push(r.k); });
    document.querySelector('#sprzedaz-inwestycje h2').textContent = okres === 'all' ? 'Sprzedaż rok po roku wg inwestycji' : 'Sprzedaż miesiąc po miesiącu wg inwestycji';
    barsStacked('ch-inw', 'lg-inw', rows, keys, colorInw, miara, (v) => (v.length === 4 ? v : MON[+v.slice(5) - 1]), (v) => (v.length === 4 ? v : MON[+v.slice(5) - 1] + ' ' + v.slice(0, 4)));
  }

  function drawTyp() {
    if (!onSales()) return;
    const d = dash.data('sprzedaz_typ');
    const box = document.getElementById('ch-typ');
    if (d.status !== 'ok') { if (d.status === 'error') { box.classList.remove('dash-skeleton'); box.replaceChildren(); const f = document.createElement('div'); f.className = 'tx-fail'; f.textContent = 'Failed to load'; box.append(f); } return; }
    const { okres, inw } = dash.params();
    const sel = d.data.filter((r) => r.inw === inw && (okres === 'all' || r.miesiac.startsWith(okres)));
    const rows = sel.map((r) => ({ x: okres === 'all' ? r.miesiac.slice(0, 4) : r.miesiac, k: r.typ, sprzedaze: r.sprzedaze }));
    const keys = TYPY.filter((k) => rows.some((r) => r.k === k)); rows.forEach((r) => { if (!keys.includes(r.k)) keys.push(r.k); });
    barsStacked('ch-typ', 'lg-typ', rows, keys, colorTyp, 'sprzedaze', (v) => (v.length === 4 ? v : MON[+v.slice(5) - 1]), (v) => (v.length === 4 ? v : MON[+v.slice(5) - 1] + ' ' + v.slice(0, 4)));
  }

  function tableTyp() {
    if (!onSales()) return;
    const d = dash.data('typy'); const tb = document.getElementById('t-typ').tBodies[0];
    if (d.status !== 'ok') { tb.replaceChildren(); return; }
    const { okres, inw } = dash.params();
    const rows = d.data.filter((r) => r.okres === okres && r.inw === inw).sort((a, b) => b.sprzedaze - a.sprzedaze);
    tb.replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr'); tr.dataset.key = [r.okres, r.inw, r.typ].map(encodeURIComponent).join(',');
      [r.typ, fmtInt(r.sprzedaze), window.txFmt.fmtPct(r.udzial), r.wartosc ? fmtMoney(r.wartosc) : '–', r.sr_m2 == null ? '–' : fmtInt(r.sr_m2) + ' m²', r.cena_m2 == null ? '–' : fmtInt(r.cena_m2), fmtInt(r.rezerwacje)].forEach((c, i) => {
        const td = document.createElement('td');
        if (i === 0) { const sw = document.createElement('span'); sw.className = 'tx-sw'; sw.style.background = colorTyp(r.typ); td.append(sw, document.createTextNode(c)); } else td.textContent = c;
        tr.append(td);
      });
      return tr;
    }));
  }

  function tableEtap() {
    if (!onSales()) return;
    const d = dash.data('etapy_sprzedaz'); const tb = document.getElementById('t-etap').tBodies[0];
    if (d.status !== 'ok') { tb.replaceChildren(); return; }
    const { okres, inw } = dash.params();
    const rows = d.data.filter((r) => r.okres === okres && r.inwf === inw).sort((a, b) => a.inw.localeCompare(b.inw, 'pl') || b.sprzedaze - a.sprzedaze);
    tb.replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr'); tr.dataset.key = [r.okres, r.inwf, r.etap].map(encodeURIComponent).join(',');
      [r.inw, r.etap, r.typ, fmtInt(r.sprzedaze), r.wartosc ? fmtMoney(r.wartosc) : '–', r.cena_m2 == null ? '–' : fmtInt(r.cena_m2), fmtInt(r.rezerwacje), fmtInt(r.anulowane), r.ostatnia || '–'].forEach((c) => {
        const td = document.createElement('td'); td.textContent = c; tr.append(td);
      });
      return tr;
    }));
  }

  window.txDrawers.push(kpiSales, drawInw, drawTyp, tableTyp, tableEtap);
  const named = location.hash.slice(1);
  if (named === 'sprzedaz') window.txShowPage('sprzedaz');

  window.txDrawers.push(
    etapy,""")

# existing marketing drawers must skip when hidden
rep("""  function drawTop() {
    const d = dash.data('kanaly');""", """  function drawTop() {
    if (window.txPage === 'sprzedaz') return;
    const d = dash.data('kanaly');""")
rep("""  function stacked(boxId, legendId, src, field, filterRow) {
    const box = document.getElementById(boxId);""", """  function stacked(boxId, legendId, src, field, filterRow) {
    if (window.txPage === 'sprzedaz') return;
    const box = document.getElementById(boxId);""")
rep("""  function lag() {
    const box = document.getElementById('lag');""", """  function lag() {
    if (window.txPage === 'sprzedaz') return;
    const box = document.getElementById('lag');""")
rep("""  function etapy() {
    const box = document.getElementById('ch-etapy');""", """  function etapy() {
    if (window.txPage === 'sprzedaz') return;
    const box = document.getElementById('ch-etapy');""")

open(p, 'w').write(s)
json.dump({'text': s}, open('index_doc.json', 'w'), ensure_ascii=False)
print('ok', len(s))
