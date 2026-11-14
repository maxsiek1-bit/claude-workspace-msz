import bpy, sys, json, numpy as np, os
from mathutils import Vector
out = sys.argv[-1]; bpy.ops.wm.open_mainfile(filepath=sys.argv[-2])
dg = bpy.context.evaluated_depsgraph_get(); res = {}
def meshdata(o):
    me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
    n = len(me.vertices); co = np.empty(n * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world); co = co @ M[:3, :3].T + M[:3, 3]
    t = np.empty(len(me.loop_triangles) * 3, dtype=np.int32); me.loop_triangles.foreach_get('vertices', t); t = t.reshape(-1, 3)
    mi = np.empty(len(me.loop_triangles), dtype=np.int32); me.loop_triangles.foreach_get('material_index', mi)
    return co, t, mi
for name in ['Budynek_A', 'Budynek_B', 'Budynek_C']:
    o = bpy.data.objects[name]; co, t, mi = meshdata(o)
    a, b, c = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]; nrm = np.cross(b - a, c - a); area = np.linalg.norm(nrm, axis=1) / 2
    up = np.abs(nrm[:, 2]) / (2 * area + 1e-12) > 0.98; zc = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
    h, e = np.histogram(zc[up], bins=np.arange(-1, 22.01, 0.1), weights=area[up])
    top = sorted([(round(float(e[i]), 1), round(float(h[i]))) for i in np.argsort(h)[::-1][:22]])
    mats = [s.material.name if s.material else None for s in o.material_slots]
    ma = {mats[i]: round(float(area[mi == i].sum())) for i in range(len(mats))}
    res[name] = dict(loc=list(o.location), rot=list(o.rotation_euler), scale=list(o.scale), bbmin=co.min(0).tolist(), bbmax=co.max(0).tolist(), tris=len(t), zlevels=top, mat_area=ma,
                     matcol={m.name: list(m.diffuse_color) for m in [s.material for s in o.material_slots] if m})
    np.savez_compressed(os.path.join(out, name + '.npz'), co=co.astype(np.float32), t=t, mi=mi)
refs = []
for o in bpy.data.collections['MH_Referencja_dewelopera'].objects:
    bb = np.array([o.matrix_world @ Vector(c) for c in o.bound_box])
    refs.append(dict(name=o.name, mn=bb.min(0).tolist(), mx=bb.max(0).tolist(), hide=o.hide_viewport, hr=o.hide_render))
res['refs'] = refs
res['coll_hidden'] = {c.name: [c.hide_viewport, c.hide_render] for c in bpy.data.collections}
json.dump(res, open(os.path.join(out, 'analysis.json'), 'w'), indent=1)
