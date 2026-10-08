"""Solução inicial validada e redução de bobinas equivalentes."""
from collections import defaultdict


def prepare(project,engine):
    remaining={r['id']:engine.available(r) for r in project['bobinas']}
    blocked=engine.blocked_nodes(project['trechos'])
    cuts=[]
    for chain in engine.segments(project['trechos']):
        start=0
        while start<len(chain):
            best=None
            for end in range(start,len(chain)):
                rows=chain[start:end+1]
                if engine.end_allowed(rows[-1],blocked):
                    fixed={r.get('fixa') for r in rows if r.get('fixa')}
                    size=engine.length(rows)
                    reels=[r for r in project['bobinas'] if r['condutor']==rows[0]['condutor'] and r['tipo']==rows[0]['tipo'] and
                           remaining[r['id']]>=size and (not fixed or fixed=={r['id']})]
                    if reels:
                        reel=min(reels,key=lambda r:remaining[r['id']])
                        best=(end,rows,reel,size)
                if rows[-1]['corte_fim']=='OBRIGATORIO':break
            if best is None:return project['bobinas'],[]
            end,rows,reel,size=best
            cuts.append(engine.make_cut(rows,reel['id'],len(cuts)+1))
            remaining[reel['id']]-=size
            start=end+1
    if engine.validate(project,cuts):return project['bobinas'],[]
    # An optimum cannot use more reels than this feasible plan has launches.
    # Identical-capacity reels are interchangeable unless explicitly fixed or
    # associated with preserved launches outside the optimization scope.
    limit=len(cuts)
    protected={r.get('fixa') for r in project['trechos'] if r.get('fixa')}
    protected.update(c['bobina'] for c in project.get('_cortes_preservados_operacao',[]))
    seeded={c['bobina'] for c in cuts}
    groups=defaultdict(list)
    for reel in project['bobinas']:
        if reel['id'] in protected:continue
        groups[(reel['condutor'],reel['tipo'],engine.available(reel))].append(reel)
    keep=set(protected)
    for rows in groups.values():
        rows.sort(key=lambda r:(r['id'] not in seeded,r['id']))
        keep.update(r['id'] for r in rows[:limit])
    return [r for r in project['bobinas'] if r['id'] in keep],cuts
