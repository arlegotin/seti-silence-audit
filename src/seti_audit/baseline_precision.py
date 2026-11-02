"""Matched-baseline precision from the existing fresh confirmation histories."""

from collections import Counter
import hashlib
from pathlib import Path
import time

import numpy as np

from .artifacts import canonical_hash, read_json_checked, write_json_atomic
from .inference import alpha_at_checkpoint, exact_interval
from .refinement import _checked_upstream, _donor_allocation, _refinement_parents, refined_summary
from .resources import ResourceLedger
from .storage import _load_one


def baseline_summary(upstream, original_rows, fresh, baseline):
    overrides={r['parent_cell_id']:r['R0'] for r in baseline['baseline_bounds']}
    subs=[s | {'intervals':s['intervals'] | ({'R0':overrides[s['parent_cell_id']]} if s['parent_cell_id'] in overrides else {})}
          for s in fresh['subdomains']]
    return refined_summary(upstream,original_rows,subs)


def refine_baselines(upstream, refinement_lock, checkpoint_path, output_dir):
    actual,original=_checked_upstream(refinement_lock)
    if actual['protocol_hash']!=upstream['protocol_hash']:
        raise ValueError('Baseline upstream protocol mismatch')
    fresh=read_json_checked(Path(checkpoint_path))
    if (fresh['protocol_hash']!=refinement_lock['protocol_hash'] or
        fresh['content_hash']!=canonical_hash({k:v for k,v in fresh.items() if k!='content_hash'})):
        raise ValueError('Baseline source checkpoint hash mismatch')
    registry=upstream['bound_registry'];old_pool=registry['pools']['diagnostics']
    # At (z,u)=(1,1), the conditional free-shell CDF is identically one:
    # a sampled B_h point guarantees H<=h, and D>T implies A-D<A-T.
    donors=sorted(key for key in registry['items'] if key in ('shell:0:z1:u1','shell:1:z1:u1'))
    if len(donors)!=2 or any(registry['items'][key]['pool']!='diagnostics' for key in donors):
        raise ValueError('Both analytically certain free-shell endpoint donors required')
    weight_pool=_donor_allocation(upstream)
    if set(donors)&set(weight_pool['donor_ids']):raise ValueError('Confidence donors overlap')
    quantities={c['interval_ids']['R0']:(c['model_id'],c['future_multiplier']) for c in upstream['cells'] if c['model_kind']=='interacting'}
    pool={'A':old_pool['A']*len(donors)/old_pool['M'],'M':len(quantities),'original_pool':old_pool,'donor_ids':donors,
          'proof':'Conditional free-shell CDF F(1,1)=1 at both registered horizons. Every endpoint interval contains one at every look, with zero actual noncoverage probability.'}
    remaining=old_pool['A']*(old_pool['M']-len(donors)-len(weight_pool['donor_ids']))/old_pool['M']
    assert abs(remaining+pool['A']+weight_pool['A']-old_pool['A'])<1e-15
    policy={'upstream_protocol_hash':upstream['protocol_hash'],'refinement_protocol_hash':refinement_lock['protocol_hash'],
            'component_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'error_pool':pool,
            'quantities':{key:list(value) for key,value in sorted(quantities.items())},
            'rule':'Use all declared interacting baselines and every deterministic fresh checkpoint N_j=N_1*2^(j-1). Alpha=A/[M*j*(j+1)]. No new simulation or model choice; dependency with null audits is covered by the joint union bound.'}
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=True)
    path=root/'policy.json'
    if path.exists() and read_json_checked(path)!=policy:raise ValueError('Baseline policy is immutable')
    if not path.exists():write_json_atomic(path,policy)
    ledger=ResourceLedger(root/'resources.jsonl');job=ledger.start('G6',details={'scope':'matched baseline confidence, saved fresh flags'});start=time.perf_counter()
    counts=Counter();trials=Counter()
    try:
        for meta in fresh['batches']:
            batch=_load_one(Path(refinement_lock['_output_dir'])/'checkpoints'/meta['_batch_id'],refinement_lock['protocol_hash'])
            if batch['_batch_hash']!=meta['_batch_hash']:raise ValueError('Baseline source batch hash mismatch')
            mid=batch['model_id'];trials[mid]+=batch['sample_size']
            for name,flags in batch['_arrays'].items():
                if name.startswith('flags_'):
                    if len(flags)!=batch['sample_size']:raise ValueError('Baseline flag count mismatch')
                    counts[mid,float(name.removeprefix('flags_'))]+=int(np.sum(flags))
        look=fresh['look'];target=refinement_lock['initial_histories']*2**(look-1)
        alpha=alpha_at_checkpoint(pool['A'],pool['M'],look)
        evidence={}
        for name,(mid,k) in quantities.items():
            if trials[mid]!=target:raise ValueError('Baseline requires the complete fixed checkpoint')
            bound=exact_interval(counts[mid,k],trials[mid],alpha)
            evidence[name]={'successes':counts[mid,k],'trials':trials[mid],'look':look,'alpha':alpha,'interval':[bound.low,bound.high]}
        raw={r['cell_id']:r for r in original['summary']['rows']};cells={c['cell_id']:c for c in upstream['cells']}
        bounds=[]
        for cid in sorted({s['parent_cell_id'] for s in fresh['subdomains']}):
            cell=cells[cid]
            if cell['model_kind']!='interacting':continue
            new=evidence[cell['interval_ids']['R0']]['interval'];old=raw[cid]['intervals']['R0']
            intersection=[max(new[0],old[0]),min(new[1],old[1])]
            if intersection[0]>intersection[1]:raise ArithmeticError('Disjoint baseline confidence sets require investigation')
            bounds.append({'parent_cell_id':cid,'R0':intersection})
        result={'policy':policy,'upstream_protocol_hash':upstream['protocol_hash'],'upstream_result_hash':original['content_hash'],
                'source_refinement_hash':fresh['content_hash'],'source_refinement_filename':Path(checkpoint_path).name,
                'look':look,'interval_evidence':evidence,'baseline_bounds':bounds}
        summary=baseline_summary(upstream,original['summary']['rows'],fresh,result)
        affected={f for c in _refinement_parents(upstream) for f in c['families'] if '/Dpositive/' in f or '/Dweak/' in f or '/positive_detectors/' in f}
        result['analysis_pending']=sorted(f for f in affected if summary.certificates[f]['0.05']=='inconclusive')
        result['certificates']=summary.certificates;result['content_hash']=canonical_hash(result)
        write_json_atomic(root/f'checkpoint-{look}.json',result)
        if not result['analysis_pending']:write_json_atomic(root/'result.json',result)
    except BaseException as exc:
        ledger.finish(job,time.perf_counter()-start,0,status='failed',details={'exception':type(exc).__name__});raise
    ledger.finish(job,time.perf_counter()-start,0,details={'look':look,'baseline_intervals':len(evidence)})
    return result
