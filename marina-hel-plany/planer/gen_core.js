/* Generator zabudowy – czysta funkcja bez dostępu do DOM (da się uruchomić w Node i w Web Workerze).
   Jednostki: metry, oś x na wschód, oś y na północ.
   generate(input) -> { area_m2, variants:[{name, angle_deg, items:[{t, x, y, rot}], stats}], ms }
   input = { site:[[x,y]...], excl:[wielokąty], build:[wielokąty], types:[{id, outline, axis_deg, lokale, pu, zab, kond}],
             params:{ sb, se, dist, step, goal, maxCover, maxVariants } } */
var GenCore = (function () {
  'use strict';
  function inside(x, y, v) { var r = false; for (var i = 0, j = v.length - 1; i < v.length; j = i++) { var p = v[i], q = v[j];
    if ((p[1] > y) !== (q[1] > y) && x < (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]) + p[0]) r = !r; } return r; }
  function orient(p, q, r) { return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]); }
  function segX(a, b, c, d) { var d1 = orient(c, d, a), d2 = orient(c, d, b), d3 = orient(a, b, c), d4 = orient(a, b, d);
    return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0)); }
  function area(v) { var s = 0; for (var i = 0; i < v.length; i++) { var q = v[(i + 1) % v.length]; s += v[i][0] * q[1] - q[0] * v[i][1]; } return s / 2; }
  function ptSeg2(p, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], l = dx * dx + dy * dy, t = l ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l : 0;
    t = t < 0 ? 0 : t > 1 ? 1 : t; var x = a[0] + t * dx - p[0], y = a[1] + t * dy - p[1]; return x * x + y * y; }
  /* Obrys odsunięty na zewnątrz o d (wierzchołki wzdłuż dwusiecznych). */
  function offsetPoly(p, d) {
    if (d <= 0) return p;
    var sg = area(p) > 0 ? 1 : -1, n = p.length, out = [];
    for (var i = 0; i < n; i++) {
      var p0 = p[(i + n - 1) % n], p1 = p[i], p2 = p[(i + 1) % n];
      var e1x = p1[0] - p0[0], e1y = p1[1] - p0[1], e2x = p2[0] - p1[0], e2y = p2[1] - p1[1];
      var l1 = Math.hypot(e1x, e1y) || 1, l2 = Math.hypot(e2x, e2y) || 1; e1x /= l1; e1y /= l1; e2x /= l2; e2y /= l2;
      var nx = sg * (e1y + e2y), ny = -sg * (e1x + e2x), l = Math.hypot(nx, ny);
      if (l < 1e-6) { nx = sg * e1y; ny = -sg * e1x; } else { nx /= l; ny /= l; }
      var ch = Math.max(0.35, Math.sqrt(Math.max(0, (1 + e1x * e2x + e1y * e2y) / 2)));
      out.push([p1[0] + nx * d / ch, p1[1] + ny * d / ch]);
    }
    return out;
  }
  function rot(p, a) { var c = Math.cos(a), s = Math.sin(a); return p.map(function (q) { return [q[0] * c - q[1] * s, q[0] * s + q[1] * c]; }); }
  function shift(p, x, y) { var o = new Array(p.length); for (var i = 0; i < p.length; i++) o[i] = [p[i][0] + x, p[i][1] + y]; return o; }
  function edgesOf(polys) { var e = []; polys.forEach(function (v) { for (var i = 0; i < v.length; i++) e.push([v[i], v[(i + 1) % v.length]]); }); return e; }
  function crosses(pts, edges) { for (var i = 0, n = pts.length; i < n; i++) { var a = pts[i], b = pts[(i + 1) % n]; for (var k = 0; k < edges.length; k++) if (segX(a, b, edges[k][0], edges[k][1])) return true; } return false; }
  /* Czy dwa wielokąty są bliżej niż d (albo się przecinają / zawierają). */
  function tooClose(P, Q, d) {
    var d2 = d * d, i, k, n = P.length, m = Q.length;
    for (i = 0; i < n; i++) for (k = 0; k < m; k++) if (segX(P[i], P[(i + 1) % n], Q[k], Q[(k + 1) % m])) return true;
    if (inside(P[0][0], P[0][1], Q) || inside(Q[0][0], Q[0][1], P)) return true;
    for (i = 0; i < n; i++) for (k = 0; k < m; k++) if (ptSeg2(P[i], Q[k], Q[(k + 1) % m]) < d2) return true;
    for (k = 0; k < m; k++) for (i = 0; i < n; i++) if (ptSeg2(Q[k], P[i], P[(i + 1) % n]) < d2) return true;
    return false;
  }
  /* Przygotowanie typu: obrys wyśrodkowany i ustawiony długą osią wzdłuż +x, cztery obroty co 90°. */
  function prepType(t, prm) {
    if (t.parts) {                       // typ złożony (zespół budynków): części już w układzie lokalnym
      var r0 = 0; t.parts.forEach(function (p) { p.forEach(function (q) { r0 = Math.max(r0, Math.hypot(q[0], q[1])); }); });
      return { t: t, c: [0, 0], parts: t.parts, r: r0 };
    }
    var cx = 0, cy = 0; t.outline.forEach(function (q) { cx += q[0]; cy += q[1]; }); cx /= t.outline.length; cy /= t.outline.length;
    var loc = rot(t.outline.map(function (q) { return [q[0] - cx, q[1] - cy]; }), -(t.axis_deg || 0) * Math.PI / 180), r = 0;
    loc.forEach(function (q) { r = Math.max(r, Math.hypot(q[0], q[1])); });
    return { t: t, c: [cx, cy], parts: [loc], r: r };
  }
  /* Czy wielokąt jest bliżej niż d od odcinka a-b (albo go przecina). */
  function polySegClose(P, a, b, d) {
    var d2 = d * d, n = P.length, i;
    for (i = 0; i < n; i++) if (segX(P[i], P[(i + 1) % n], a, b)) return true;
    if (inside(a[0], a[1], P)) return true;
    for (i = 0; i < n; i++) if (ptSeg2(P[i], a, b) < d2 || ptSeg2(a, P[i], P[(i + 1) % n]) < d2 || ptSeg2(b, P[i], P[(i + 1) % n]) < d2) return true;
    return false;
  }
  function roadSegs(inp) { var o = []; (inp.roads || []).forEach(function (r) { for (var i = 0; i + 1 < r.pts.length; i++) o.push([r.pts[i], r.pts[i + 1], r.d]); }); return o; }
  function buildableArea(site, excl, build, sb, se) {       // powierzchnia obszaru do zabudowy po odsunięciach, liczona na siatce 1 m
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; site.forEach(function (q) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); });
    var se_ = edgesOf([site]), ee = edgesOf(excl), n = 0, st = Math.max(1, Math.sqrt((x1 - x0) * (y1 - y0) / 40000));
    for (var y = y0 + st / 2; y < y1; y += st) for (var x = x0 + st / 2; x < x1; x += st) {
      if (!inside(x, y, site)) continue; var ok = true, k, p = [x, y];
      for (k = 0; k < excl.length && ok; k++) if (inside(x, y, excl[k])) ok = false;
      if (ok && build.length) { ok = false; for (k = 0; k < build.length; k++) if (inside(x, y, build[k])) { ok = true; break; } }
      if (ok && sb > 0) for (k = 0; k < se_.length; k++) if (ptSeg2(p, se_[k][0], se_[k][1]) < sb * sb) { ok = false; break; }
      if (ok && se > 0) for (k = 0; k < ee.length; k++) if (ptSeg2(p, ee[k][0], ee[k][1]) < se * se) { ok = false; break; }
      if (ok) n++;
    }
    return n * st * st;
  }
  function stats(items, types, terrain) {
    var s = { n: items.length, lokale: 0, pu: 0, zab: 0, kub: 0, byType: {}, unk: 0 };
    items.forEach(function (it) { var t = types[it.t]; s.byType[t.id] = (s.byType[t.id] || 0) + 1; s.zab += t.zab; s.kub += t.zab * (t.kond || 1);
      if (t.lokale == null) s.unk++; else { s.lokale += t.lokale; s.pu += t.pu || 0; } });
    s.pokrycie = terrain ? s.zab / terrain : 0; s.intensywnosc = terrain ? s.kub / terrain : 0; s.lok_ha = terrain ? s.lokale / (terrain / 1e4) : 0;
    return s;
  }
  var GOAL = { lokale: function (s) { return s.lokale; }, pu: function (s) { return s.pu; }, budynki: function (s) { return s.n; }, zabudowa: function (s) { return s.zab; } };
  function value(goal, s) { return (GOAL[goal] || GOAL.lokale)(s); }

  /* Raster terenu (komórka cs): 1 = wolno stawiać (w granicy, poza strefami wyłączonymi, z odsunięciami). Niezależny od kierunku siatki. */
  function makeGrid(inp) {
    var site = inp.site, excl = inp.excl || [], build = inp.build || [], sb = inp.params.sb, se = inp.params.se;
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; site.forEach(function (q) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); });
    var cs = Math.max(1, Math.sqrt((x1 - x0) * (y1 - y0) / 250000)), W = Math.ceil((x1 - x0) / cs) + 2, H = Math.ceil((y1 - y0) / cs) + 2, ok = new Uint8Array(W * H);
    var sE = edgesOf([site]), eE = edgesOf(excl), rS = roadSegs(inp), k, sb2 = sb * sb, se2 = se * se;
    for (var j = 0; j < H; j++) for (var i = 0; i < W; i++) {
      var x = x0 + (i - 0.5) * cs, y = y0 + (j - 0.5) * cs, p = [x, y], g = inside(x, y, site);
      for (k = 0; k < excl.length && g; k++) if (inside(x, y, excl[k])) g = false;
      if (g && build.length) { g = false; for (k = 0; k < build.length; k++) if (inside(x, y, build[k])) { g = true; break; } }
      if (g && sb > 0) for (k = 0; k < sE.length; k++) if (ptSeg2(p, sE[k][0], sE[k][1]) < sb2) { g = false; break; }
      if (g && se > 0) for (k = 0; k < eE.length; k++) if (ptSeg2(p, eE[k][0], eE[k][1]) < se2) { g = false; break; }
      if (g) for (k = 0; k < rS.length; k++) if (ptSeg2(p, rS[k][0], rS[k][1]) < rS[k][2] * rS[k][2]) { g = false; break; }
      ok[j * W + i] = g ? 1 : 0;
    }
    return { x0: x0 - cs, y0: y0 - cs, cs: cs, W: W, H: H, ok: ok };
  }
  function samples(p) {         // wierzchołki + punkty na bokach co ok. 2 m
    var o = [], n = p.length; for (var i = 0; i < n; i++) { var a = p[i], b = p[(i + 1) % n], m = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 2));
      for (var t = 0; t < m; t++) o.push([a[0] + (b[0] - a[0]) * t / m, a[1] + (b[1] - a[1]) * t / m]); } return o;
  }
  /* Jeden wariant: kierunek siatki alpha, kolejność typów i obrotów. Zachłanne wypełnianie rząd po rzędzie.
     Szybkie odrzucanie na rastrze (teren + zajętość), a każde udane ustawienie jest potwierdzane dokładnym testem na obrysach. */
  function fill(inp, P, alpha, order, rots, terrain, G) {
    var prm = inp.params, site = inp.site, excl = inp.excl || [], build = inp.build || [], sb = prm.sb, se = prm.se, dist = prm.dist, step = prm.step || 4;
    var siteE = edgesOf([site]), exclE = edgesOf(excl), buildE = edgesOf(build), ca = Math.cos(alpha), sa = Math.sin(alpha);
    var u0 = 1e9, u1 = -1e9, v0 = 1e9, v1 = -1e9;
    site.forEach(function (q) { var u = q[0] * ca + q[1] * sa, v = -q[0] * sa + q[1] * ca; u0 = Math.min(u0, u); u1 = Math.max(u1, u); v0 = Math.min(v0, v); v1 = Math.max(v1, v); });
    var rS = roadSegs(inp), view = prm.viewAngle, Lx = view == null ? 0 : -Math.sin(view), Ly = view == null ? 0 : Math.cos(view);
    var shapes = P.map(function (p) { var ks = p.t.fixedRot != null ? [p.t.fixedRot] : [0, 1, 2, 3].map(function (k) { return alpha + k * Math.PI / 2; });
      return ks.map(function (a) { var parts = p.parts.map(function (loc) { var raw = rot(loc, a);
          return { raw: raw, sb: sb > 0 ? rot(offsetPoly(loc, sb), a) : raw, se: se > 0 ? rot(offsetPoly(loc, se), a) : raw }; }), smp = [], lo = 1e9, hi = -1e9;
        parts.forEach(function (pt) { samples(pt.raw).forEach(function (q) { smp.push(q); var l = q[0] * Lx + q[1] * Ly; lo = Math.min(lo, l); hi = Math.max(hi, l); }); });
        return { parts: parts, smp: smp, a: a, lo: lo, hi: hi }; }); });
    var items = [], placed = [], zab = 0, cap = (prm.maxCover == null ? 1 : prm.maxCover) * terrain;
    var W = G.W, H = G.H, cs = G.cs, gx = G.x0, gy = G.y0, free = new Uint8Array(G.ok);       // kopia: 1 = wolne
    function rasterOK(smp, x, y) { for (var i = 0; i < smp.length; i++) { var ci = Math.floor((smp[i][0] + x - gx) / cs), cj = Math.floor((smp[i][1] + y - gy) / cs);
      if (ci < 0 || cj < 0 || ci >= W || cj >= H || !free[cj * W + ci]) return false; } return true; }
    function block(pts) {          // zajmij komórki w odległości < dist od obrysu (i w jego wnętrzu)
      var bx0 = 1e9, by0 = 1e9, bx1 = -1e9, by1 = -1e9, i; for (i = 0; i < pts.length; i++) { bx0 = Math.min(bx0, pts[i][0]); by0 = Math.min(by0, pts[i][1]); bx1 = Math.max(bx1, pts[i][0]); by1 = Math.max(by1, pts[i][1]); }
      var d = Math.max(0, dist - cs), d2 = d * d, i0 = Math.max(0, Math.floor((bx0 - dist - gx) / cs)), i1 = Math.min(W - 1, Math.ceil((bx1 + dist - gx) / cs)), j0 = Math.max(0, Math.floor((by0 - dist - gy) / cs)), j1 = Math.min(H - 1, Math.ceil((by1 + dist - gy) / cs));
      for (var j = j0; j <= j1; j++) for (i = i0; i <= i1; i++) { if (!free[j * W + i]) continue; var x = gx + (i + 0.5) * cs, y = gy + (j + 0.5) * cs, hit = inside(x, y, pts);
        for (var k = 0; k < pts.length && !hit; k++) if (ptSeg2([x, y], pts[k], pts[(k + 1) % pts.length]) < d2) hit = true;
        if (hit) free[j * W + i] = 0; }
    }
    function exact(ti, k, x, y) {
      var sh = shapes[ti][k], i, j, out = [], pi, r = P[ti].r;
      if (view != null) { var s0 = x * Lx + y * Ly;          // zasada widoku: nikt nie stoi przed nikim (rzuty na kierunek drogi się nie nakładają)
        for (j = 0; j < placed.length; j++) if (s0 + sh.lo < placed[j].hi + dist && s0 + sh.hi > placed[j].lo - dist) return null; }
      for (pi = 0; pi < sh.parts.length; pi++) { var pt = sh.parts[pi], pS = shift(pt.sb, x, y);
        for (i = 0; i < pS.length; i++) if (!inside(pS[i][0], pS[i][1], site)) return null;
        if (crosses(pS, siteE)) return null;
        var raw = shift(pt.raw, x, y);
        if (build.length) { var okb = false; for (j = 0; j < build.length && !okb; j++) { okb = true; for (i = 0; i < raw.length; i++) if (!inside(raw[i][0], raw[i][1], build[j])) { okb = false; break; } } if (!okb || crosses(raw, buildE)) return null; }
        if (excl.length) { var pE = pt.se === pt.raw ? raw : shift(pt.se, x, y);
          for (j = 0; j < excl.length; j++) { for (i = 0; i < pE.length; i++) if (inside(pE[i][0], pE[i][1], excl[j])) return null; if (inside(excl[j][0][0], excl[j][0][1], pE)) return null; }
          if (crosses(pE, exclE)) return null; }
        for (j = 0; j < rS.length; j++) if (polySegClose(raw, rS[j][0], rS[j][1], rS[j][2])) return null;
        for (j = 0; j < placed.length; j++) { var q = placed[j], dx = q.x - x, dy = q.y - y, rr = r + q.r + dist;
          if (dx * dx + dy * dy < rr * rr) for (i = 0; i < q.parts.length; i++) if (tooClose(raw, q.parts[i], dist)) return null; }
        out.push(raw); }
      return out;
    }
    for (var v = v0; v <= v1; v += step) for (var u = u0; u <= u1; u += step) {
      var x = u * ca - v * sa, y = u * sa + v * ca, done = false;
      for (var oi = 0; oi < order.length && !done; oi++) { var ti = order[oi], t = P[ti].t;
        if (zab + t.zab > cap + 1e-6) continue;
        for (var ri = 0; ri < rots.length && !done; ri++) { var k = rots[ri]; if (k >= shapes[ti].length) continue;
          if (!rasterOK(shapes[ti][k].smp, x, y)) continue;
          var parts = exact(ti, k, x, y);
          if (parts) { var s1 = x * Lx + y * Ly; placed.push({ x: x, y: y, r: P[ti].r, parts: parts, lo: s1 + shapes[ti][k].lo, hi: s1 + shapes[ti][k].hi }); zab += t.zab; done = true; parts.forEach(block);
            items.push({ t: ti, id: t.id, x: x, y: y, rot: shapes[ti][k].a, pts: parts[0], parts: parts }); } } }
    }
    return items;
  }
  function generate(inp) {
    var t0 = Date.now(), prm = inp.params, types = inp.types, site = inp.site;
    if (!site || site.length < 3 || !types.length) return { area_m2: 0, variants: [], ms: 0 };
    var P = types.map(function (t) { return prepType(t, prm); });
    var terrain = buildableArea(site, inp.excl || [], inp.build || [], 0, 0), areaSb = buildableArea(site, inp.excl || [], inp.build || [], prm.sb, prm.se);
    var G = makeGrid(inp);
    // kierunki siatki: boki granicy (od najdłuższego) i obroty co 15 stopni; obrót o 90 daje ten sam zestaw
    var edges = site.map(function (q, i) { var b = site[(i + 1) % site.length]; return { l: Math.hypot(b[0] - q[0], b[1] - q[1]), a: Math.atan2(b[1] - q[1], b[0] - q[0]) }; }).sort(function (a, b) { return b.l - a.l; });
    var angs = [], names = [], H = Math.PI / 2, norm = function (a) { a %= H; return a < 0 ? a + H : a; };
    function addAng(a, name) { a = norm(a); for (var i = 0; i < angs.length; i++) { var d = Math.abs(angs[i] - a); if (Math.min(d, H - d) < 0.035) return; } angs.push(a); names.push(name); }
    edges.forEach(function (e, i) { if (e.l >= 0.4 * edges[0].l) addAng(e.a, i ? 'wzdłuż boku ' + Math.round(e.l) + ' m' : 'wzdłuż najdłuższego boku'); });
    for (var d = 0; d < 90; d += 15) addAng(d * Math.PI / 180, 'obrót ' + d + '°');
    if (prm.scanAngle != null) { angs = [prm.scanAngle]; names = [prm.name || 'rząd z widokiem']; }
    // kolejności typów: od najcenniejszego według celu, od najgęstszego, od najmniejszego
    var idx = types.map(function (t, i) { return i; }), val = function (i) { var s = stats([{ t: i }], types, 1); return value(prm.goal, s); };
    var orders = [['duże najpierw', idx.slice().sort(function (a, b) { return val(b) - val(a) || types[b].zab - types[a].zab; })],
                  ['gęste najpierw', idx.slice().sort(function (a, b) { return val(b) / types[b].zab - val(a) / types[a].zab; })],
                  ['małe najpierw', idx.slice().sort(function (a, b) { return types[a].zab - types[b].zab; })]];
    var seen = {}; orders = orders.filter(function (o) { var k = o[1].join(','); if (seen[k]) return false; seen[k] = 1; return true; });
    var rotSets = [['', [0, 2, 1, 3]], [' / poprzecznie', [1, 3, 0, 2]]], out = [], limit = prm.maxVariants || 60;
    if (prm.scanAngle != null) { rotSets = [['', [0, 1, 2, 3]]]; orders = [['', orders[0][1]]]; }
    for (var ai = 0; ai < angs.length; ai++) for (var oi = 0; oi < orders.length; oi++) for (var ri = 0; ri < rotSets.length; ri++) {
      if (out.length >= limit || (prm.budgetMs && Date.now() - t0 > prm.budgetMs && out.length)) break;
      var items = fill(inp, P, angs[ai], orders[oi][1], rotSets[ri][1], terrain, G), s = stats(items, types, terrain);
      out.push({ name: prm.scanAngle != null ? names[ai] : names[ai] + ', ' + orders[oi][0] + rotSets[ri][0], angle_deg: angs[ai] * 180 / Math.PI, items: items, stats: s, value: value(prm.goal, s) });
    }
    out.sort(function (a, b) { return b.value - a.value || b.stats.n - a.stats.n; });
    return { area_m2: areaSb, terrain_m2: terrain, variants: out, centers: P.map(function (p) { return p.c; }), ms: Date.now() - t0 };
  }
  return { generate: generate, tooClose: tooClose, inside: inside, offsetPoly: offsetPoly, edgesOf: edgesOf, crosses: crosses, stats: stats, buildableArea: buildableArea };
})();
if (typeof module !== 'undefined') module.exports = GenCore;
