/* Testy generatora: node planer/test_gen.js. Sprawdza, że żaden budynek nie wychodzi poza obszar, nie wchodzi w strefę
   wyłączoną ani w inny budynek oraz że odległości i odsunięcia są zachowane (z niezależnie liczoną odległością). */
const G = require('./gen_core.js'), kit = require('./kit.json');
const T = k => { const b = kit.buildings[k]; return { id: k, outline: b.outline, axis_deg: 17.12, lokale: b.lokale, pu: b.pu, zab: b.pow_zabudowy, kond: Math.round((b.z[1] - b.z[0]) / 3.2) }; };
const d2seg = (p, a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], l = dx * dx + dy * dy; let t = l ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1]); };
const polyDist = (P, Q) => { let m = 1e9; for (const p of P) for (let i = 0; i < Q.length; i++) m = Math.min(m, d2seg(p, Q[i], Q[(i + 1) % Q.length])); for (const q of Q) for (let i = 0; i < P.length; i++) m = Math.min(m, d2seg(q, P[i], P[(i + 1) % P.length])); return m; };
const dense = P => { const o = []; for (let i = 0; i < P.length; i++) { const a = P[i], b = P[(i + 1) % P.length]; for (let t = 0; t < 1; t += 0.1) o.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); } return o; };
// teren testowy: pas ok. 280 x 78 m obrócony o -35 stopni z wypustką, strefa wyłączona w środku
const R = a => p => [p[0] * Math.cos(a) - p[1] * Math.sin(a), p[0] * Math.sin(a) + p[1] * Math.cos(a)];
const site = [[0, 0], [280, 0], [280, 78], [230, 78], [230, 148], [112, 148], [112, 78], [0, 78]].map(R(-0.6));
const excl = [[[120, 20], [180, 20], [180, 60], [120, 60]].map(R(-0.6))];
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('BŁĄD:', m); } };
for (const [name, types, prm] of [
  ['A2+C3+B, cel lokale', ['A2', 'C3', 'B'], { sb: 4, se: 0, dist: 8, step: 4, goal: 'lokale' }],
  ['A2+C3+B, cel budynki', ['A2', 'C3', 'B'], { sb: 4, se: 6, dist: 16, step: 4, goal: 'budynki' }],
  ['tylko B, limit zabudowy 20%', ['B'], { sb: 2, se: 0, dist: 8, step: 4, goal: 'zabudowa', maxCover: 0.2 }]]) {
  const inp = { site, excl, build: [], types: types.map(T), params: prm }, r = G.generate(inp), siteE = G.edgesOf([site]), exE = G.edgesOf(excl);
  console.log(name, '| warianty', r.variants.length, '| czas', r.ms, 'ms | najlepszy:', r.variants[0].name, '| budynków', r.variants[0].stats.n, JSON.stringify(r.variants[0].stats.byType), 'lokali', r.variants[0].stats.lokale, 'pokrycie', (100 * r.variants[0].stats.pokrycie).toFixed(1) + '%', '| obszar', Math.round(r.area_m2), 'z', Math.round(r.terrain_m2));
  ok(r.variants[0].stats.n > 3, 'za mało budynków');
  for (const v of r.variants) {
    v.items.forEach((a, i) => {
      const pts = dense(a.pts);
      ok(pts.every(p => G.inside(p[0], p[1], site)), v.name + ': budynek poza granicą');
      ok(pts.every(p => !excl.some(e => G.inside(p[0], p[1], e))), v.name + ': budynek w strefie wyłączonej');
      ok(Math.min(...pts.map(p => Math.min(...siteE.map(e => d2seg(p, e[0], e[1]))))) >= prm.sb - 0.05, v.name + ': za blisko granicy');
      if (prm.se) ok(Math.min(...pts.map(p => Math.min(...exE.map(e => d2seg(p, e[0], e[1]))))) >= prm.se - 0.05, v.name + ': za blisko strefy wyłączonej');
      for (let j = 0; j < i; j++) ok(polyDist(a.pts, v.items[j].pts) >= prm.dist - 1e-6, v.name + ': budynki za blisko siebie ' + polyDist(a.pts, v.items[j].pts).toFixed(2));
    });
    if (prm.maxCover) ok(v.stats.pokrycie <= prm.maxCover + 1e-9, v.name + ': przekroczony limit zabudowy');
  }
}
{ // układ z widokiem: zespół U otwarty na widok, droga wzdłuż jednego boku, nikt nie stoi przed nikim
  const V = kit.variants.v3, ax = kit.axis_deg * Math.PI / 180, c = V.center, rl = (p, a) => p.map(q => [q[0] * Math.cos(a) - q[1] * Math.sin(a), q[0] * Math.sin(a) + q[1] * Math.cos(a)]);
  const parts = V.b.map(k => rl(kit.buildings[k].outline.map(q => [q[0] - c[0], q[1] - c[1]]), -ax));
  const strip = [[0, 0], [300, 0], [300, 90], [0, 90]], road = { pts: [[0, 95], [300, 95]], d: 6 }, view = -Math.PI / 2;       // widok na południe, droga od północy
  const inp = { site: strip, excl: [], build: [], roads: [road], types: [{ id: 'Z', parts, fixedRot: view - Math.PI, lokale: 262, pu: 11192, zab: 4783, kond: 6 }], params: { sb: 0, se: 0, dist: 8, step: 2, goal: 'lokale', scanAngle: view - Math.PI / 2, viewAngle: view } };
  const r = G.generate(inp), it = r.variants[0].items;
  console.log('układ z widokiem: zespołów', it.length, 'czas', r.ms, 'ms');
  ok(it.length >= 2, 'za mało zespołów w układzie z widokiem');
  it.forEach((a, i) => { a.parts.forEach(P => { ok(dense(P).every(p => G.inside(p[0], p[1], strip)), 'zespół poza granicą'); ok(Math.min(...dense(P).map(p => d2seg(p, road.pts[0], road.pts[1]))) >= road.d - 0.05, 'zespół za blisko drogi'); });
    const xs = a.parts.flat().map(p => p[0]); for (let j = 0; j < i; j++) { const xj = it[j].parts.flat().map(p => p[0]); ok(Math.min(...xs) >= Math.max(...xj) + 8 - 1e-6 || Math.max(...xs) <= Math.min(...xj) - 8 + 1e-6, 'zespoły zasłaniają sobie widok'); } });
}
{ // duży teren ok. 10 ha: czas
  const big = [[0, 0], [354, 15], [378, 300], [27, 324]], inp = { site: big, excl: [[[156, 114], [222, 111], [225, 168], [159, 171]]], build: [], types: ['A2', 'C3', 'B'].map(T), params: { sb: 4, se: 0, dist: 8, step: 4, goal: 'lokale' } };
  const q = G.generate(Object.assign({}, inp, { params: Object.assign({}, inp.params, { maxVariants: 2 }) })), r = G.generate(inp);
  console.log('teren 10 ha: szybki wynik', q.ms, 'ms (', q.variants[0].stats.n, 'bud.), pełny', r.ms, 'ms,', r.variants.length, 'wariantów, najlepszy', r.variants[0].stats.n, 'bud.', r.variants[0].stats.lokale, 'lok.');
  ok(q.ms < 1500, 'szybki wynik za wolny'); }
console.log(fail ? 'NIEZALICZONE: ' + fail : 'WSZYSTKIE TESTY ZALICZONE');
process.exit(fail ? 1 : 0);
