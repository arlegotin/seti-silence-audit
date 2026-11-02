"""Continuous shared-efficiency refinement within the original error pool.

The original confirmation remains immutable. Subdomains cover the entire
declared efficiency interval; no monotonicity of conditional risk is assumed.
"""

from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import math
from pathlib import Path
import time

import numpy as np

from .contracts import WeightBounds
from .artifacts import canonical_hash, read_json_checked, write_json_atomic
from .detection import _ReceivedInterval
from .inference import alpha_at_checkpoint, exact_interval, partition_risk, summarize


def refinement_alpha(A, M, look, subdomains):
    if look < 1 or not isinstance(subdomains, int) or subdomains < 1:
        raise ValueError("Positive refinement look and subdomain count required")
    return alpha_at_checkpoint(A, M, look) / subdomains


def _donor_allocation(upstream):
    """Reassign provably zero-error ideal-S1 intervals, never a data-picked tail.

    The hard gap is geometric and holds for every history and checkpoint.
    Their CP intervals always contain the exact risk zero. Thus their allocated
    share can fund new events while the original total error bound is unchanged.
    """
    models={m['model_id']:m for m in upstream['config']['models']}
    minimum_radius=min(upstream['geometry']['radii_ly'])
    donors=sorted({c['interval_ids']['R'] for c in upstream['cells']
                   if c.get('ideal_reference') and models[c['model_id']]['speed_id']=='S1'
                   and minimum_radius*9>upstream['config']['horizon_years']})
    if not donors:
        raise ValueError('No analytically proved zero-risk confidence allocations available')
    registry=upstream['bound_registry'];pool=registry['pools']['diagnostics']
    if any(registry['items'][key]['pool']!='diagnostics' for key in donors):
        raise ValueError('Confidence donor pool mismatch')
    parents=sorted({item for c in _refinement_parents(upstream) if c['model_kind']=='interacting'
                    for q,item in c['interval_ids'].items() if q!='R0'})
    return {'A':pool['A']*len(donors)/pool['M'],'M':len(parents),'donor_ids':donors,
            'parent_ids':parents,'original_pool':pool,'minimum_S1_gap_years':minimum_radius*9,
            'proof':'Each ideal-S1 risk is identically zero for h=100. Its all-zero CP interval contains zero at every look; actual noncoverage probability is zero.'}


def response_counts(batch, geometry, schedule, emission):
    """Compact sufficient factors for the F1 single/repeated-source products."""
    if schedule.schedule_grade != "coarsened_F1":
        raise ValueError("Compact response requires F1")
    by_site = defaultdict(list)
    for visit in schedule.bounded_visits:
        by_site[visit.site_id].append(visit)
    if sum(len(v) > 1 for v in by_site.values()) > 1:
        raise ValueError("Compact catalog representation supports one repeated site")
    if len({v.duration_year for v in schedule.bounded_visits}) > 1:
        raise ValueError("Compact response requires equal integration durations")
    result = np.zeros((len(batch.arrival_years), 4), dtype=np.uint16)
    events = []
    for index, site_id in enumerate(geometry.site_ids):
        visits = by_site[site_id]
        rows = np.flatnonzero(batch.accepted_mask[:, index])
        if not visits or not len(rows):
            continue
        births = batch.birth_years[rows, index]
        radius = float(geometry.radii_ly[index])
        start = births + radius + emission.delay_years
        end = np.full(len(rows), np.inf) if emission.lifetime_years is None else start + emission.lifetime_years
        tol = np.maximum(1e-12, 64*np.finfo(float).eps*np.maximum.reduce(
            (np.ones(len(rows)), np.abs(births), np.full(len(rows), max(radius, emission.delay_years, emission.lifetime_years or 0)))))
        possible_count = np.zeros(len(rows), dtype=np.uint16)
        certain_count = np.zeros(len(rows), dtype=np.uint16)
        for visit in visits:
            certain, possible = np.ones(len(rows), dtype=bool), np.zeros(len(rows), dtype=bool)
            uncertain = np.zeros(len(rows), dtype=bool)
            for a,b in visit.allowed_intervals:
                length = np.minimum(end,b)-np.maximum(start,a)
                certain &= (start <= a) & (end >= b)
                possible |= length >= 2*visit.duration_year
                uncertain |= ((np.abs(start-a)<=tol) | (np.abs(end-b)<=tol)
                              | (np.abs(length-2*visit.duration_year)<=tol))
            for j in np.flatnonzero(uncertain):
                received = _ReceivedInterval(float(births[j]), radius, emission)
                certain[j] = all(received.contains(o) for o in visit.allowed_intervals)
                possible[j] = any(received.intersection_at_least(o,2*visit.duration_year) for o in visit.allowed_intervals)
                events.append({"history_index":int(rows[j]),"site_id":site_id,"visit_id":visit.visit_id,
                               "comparisons":received.rechecks})
            possible_count += possible
            certain_count += certain
        if len(visits)==1:
            result[rows,0] += possible_count
            result[rows,1] += certain_count
        else:
            result[rows,2] = possible_count
            result[rows,3] = certain_count > 0
    return result, {"source_precision_rechecks":len(events),"recheck_events":events}


def response_weights(counts, emission, p_low, p_high, duration_year=150/(365.25*86400)):
    if not 0 <= p_low <= p_high <= 1:
        raise ValueError("Invalid efficiency subdomain")
    certain_activity = possible_activity = 1.
    if emission.activity == "ctmc":
        f=emission.on_fraction
        survival=math.exp(-(1-f)/(emission.corr_days/365.25)*2*duration_year)
        certain_activity,possible_activity=f*f*survival,f*survival
    z=emission.zeta
    low=(1-z*p_high*possible_activity)**counts[:,0]
    low*=1-z*np.minimum(1.,p_high*possible_activity*counts[:,2])
    high=(1-z*p_low*certain_activity)**counts[:,1]
    high*=1-z*p_low*certain_activity*counts[:,3]
    return low,high


def refined_summary(lock, original_rows, subdomains):
    grouped=defaultdict(list)
    for sub in subdomains:
        grouped[sub['parent_cell_id']].append(sub)
    known={c['cell_id'] for c in lock['cells']}
    if set(grouped)-known:
        raise ValueError('Unregistered refinement parent')
    raw={r['cell_id']:r for r in original_rows}
    cells=[]
    for original in lock['cells']:
        cid=original['cell_id']
        if cid in grouped:
            ordered=sorted(grouped[cid],key=lambda r:r['p_interval'])
            point = original.get('detector_id') == 'Dweak'
            cursor=.44
            for i,sub in enumerate(ordered):
                a,b=sub['p_interval']
                if abs(a-cursor)>1e-12 or (b<=a and not point) or b>.94+1e-12 or (point and (a!=.44 or b!=.44 or len(ordered)!=1)):
                    raise ValueError('Efficiency subdomains must cover the range without gaps/overlap')
                cursor=b
                cell=original | {'cell_id':cid+f':pbin{i}', 'deterministic':sub['intervals'] | {'status':'validated'}}
                cell.pop('numerical_errors',None)
                cells.append(cell)
            if not point and abs(cursor-.94)>1e-12:
                raise ValueError('Efficiency subdomains do not cover the full range')
        else:
            cell=dict(original)
            if cid in raw:
                cell['deterministic']=raw[cid]['intervals'] | {'status':'validated','estimates':raw[cid].get('estimates',{})}
                cell.pop('numerical_errors',None)
            cells.append(cell)
    return summarize({},lock | {'cells':cells},{})


def _checked_upstream(lock):
    from .experiments import verify_protocol_lock
    upstream = read_json_checked(Path(lock['upstream_protocol_path']))
    upstream['_output_dir'] = str(Path(lock['upstream_protocol_path']).parent)
    verify_protocol_lock(upstream)
    result = read_json_checked(Path(lock['upstream_result_path']))
    if (result['content_hash'] != lock['upstream_result_hash'] or
        canonical_hash({k:v for k,v in result.items() if k!='content_hash'}) != result['content_hash']):
        raise ValueError('Upstream confirmation changed after refinement freeze')
    return upstream,result


def finish_confirmation_checkpoint(upstream, ledger):
    """Finish the already prescribed look before replacing a loose estimator.

    Uses the original frozen batch engine, seeds, cumulative sizes, and error
    registry. This is a completed checkpoint, not a declaration that its coarse
    nuisance calculation has resolved the research.
    """
    from .experiments import verify_protocol_lock
    from .storage import load_committed_batches
    from .runner import (_run_lock,_recover_usage,_read_state,_write_state,_objects,
                         _groups,_oracle_rows,_compute_batch,_snapshot,precision_requests)
    verify_protocol_lock(upstream);root=Path(upstream['_output_dir'])
    with _run_lock(root):
        batches=list(load_committed_batches(root,upstream['protocol_hash']))
        _recover_usage(ledger,batches,upstream['protocol_hash'])
        groups=_groups(upstream);objects=_objects(upstream);state_path=root/'run_state.json'
        if state_path.exists():looks=_read_state(state_path,upstream['protocol_hash'])['looks']
        else:
            looks={key:1 for key in groups};_write_state(state_path,upstream['protocol_hash'],looks)
        oracles=_oracle_rows(upstream,objects,ledger)
        for key,group in groups.items():
            target=group['initial']*2**(looks[key]-1)
            progress=sum(b['sample_size'] for b in batches if b['group_id']==key)
            while progress<target:
                index=sum(b['group_id']==key for b in batches)
                size=min(upstream['logical_batch_size'],target-progress)
                batches.append(_compute_batch(upstream,group,index,size,looks[key],objects,ledger));progress+=size
        batches.sort(key=lambda b:b['_batch_id'])
        summary,counts,references=_snapshot(upstream,batches,looks,oracles)
        result={'protocol_hash':upstream['protocol_hash'],'status':'checkpoint_complete_refinement_pending',
                'analysis_pending':True,'looks':looks,'summary':asdict(summary),'reference_checks':references,
                'coarse_precision_requests':sorted(precision_requests(summary,upstream,counts,looks)),
                'batch_hashes':[b['_batch_hash'] for b in batches],
                'checkpoint_history':sorted(p.stem for p in (root/'summaries').glob('*.json')),
                'batches':[{k:b[k] for k in ('seed_roots','group_id','sample_size')} |
                           {'batch_id':b['_batch_id'],'protocol_hash':b['protocol_hash']} for b in batches],
                'replay_samples':[b['replay_sample']|{'seed_roots':b['seed_roots'],'batch_hash':b['_batch_hash']}
                                  for b in batches if 'replay_sample' in b],
                'execution_totals':{'groups':{key:{'sampled_histories':sum(b['sample_size'] for b in batches if b['group_id']==key),
                  'attempted_proposals':sum(b['attempts'] for b in batches if b['group_id']==key),
                  'history_evaluations':sum(b['history_evaluations']+b.get('nested_history_evaluations',0) for b in batches if b['group_id']==key)} for key in groups}},
                'method_transition':'Complete prescribed checkpoint; retain all old evidence and replace only computationally loose nuisance/weak-detector precision work with independently confirmed continuous shared-p subdomains.'}
        result['content_hash']=canonical_hash(result)
        path=root/'confirmation.json'
        if path.exists() and read_json_checked(path)!=result:
            raise ValueError('A different confirmation result already exists; preserve it')
        write_json_atomic(path,result)
        return read_json_checked(path)


def freeze_refinement(upstream, output_dir, *, initial_histories=100000, initial_subdomains=16):
    from .experiments import correctness_components, execution_identity, verify_protocol_lock
    verify_protocol_lock(upstream)
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True)
    original_root=Path(upstream['_output_dir']).resolve()
    result=read_json_checked(original_root/'confirmation.json')
    if result['content_hash']!=canonical_hash({k:v for k,v in result.items() if k!='content_hash'}):
        raise ValueError('Invalid upstream result hash')
    if any(not isinstance(n,int) or isinstance(n,bool) or n<1 for n in (initial_histories,initial_subdomains)):
        raise ValueError('Positive integer refinement checkpoints required')
    if upstream['purpose']=='research':
        if initial_histories<100000:
            raise ValueError('Research refinement requires at least the primary initial precision')
        check=read_json_checked(root/'correctness.json')
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in correctness_components()}
        if check['status']!='passed' or check['scope']!='full' or check['component_hashes']!=hashes:
            raise ValueError('Current complete refinement correctness evidence required')
    else:
        check={'scope':'synthetic smoke only'}
    body={'purpose':upstream['purpose'],'upstream_protocol_hash':upstream['protocol_hash'],
          'upstream_protocol_path':str(original_root/'protocol.lock.json'),
          'upstream_result_path':str(original_root/'confirmation.json'),'upstream_result_hash':result['content_hash'],
          'reserved_through':max(result['looks'].values()),'initial_histories':initial_histories,
          'initial_subdomains':initial_subdomains,'logical_batch_size':4096,
          'seed_policy':[20261101,1,8,'model_id','purpose','batch_index'],
          'precision_policy':'Double cumulative histories and halve efficiency subdomains at each further look; no maximum look.',
          'error_pool':_donor_allocation(upstream),
          'error_policy':'Reassign only analytically zero-noncoverage ideal-S1 allocations. Divide this pool among unique refinement parents, checkpoints j*(j+1), and all current efficiency subdomains. Do not reclaim data-dependent unused look tails.',
          'component_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'execution_identity':execution_identity(),'correctness_evidence':check.get('evidence_id',check)}
    frozen=body | {'protocol_hash':canonical_hash(body)}
    path=root/'protocol.lock.json'
    if path.exists() and read_json_checked(path)!=frozen:
        raise ValueError('Refinement lock is immutable')
    if not path.exists():write_json_atomic(path,frozen)
    return frozen | {'_output_dir':str(root.resolve())}


def _refinement_parents(upstream):
    return [c for c in upstream['cells'] if c.get('emission_id') in ('E1','E3')
            and (c.get('detector_id')=='Dpositive' or
                 (c.get('detector_id')=='Dweak' and c['model_kind']=='interacting'))]


def _fresh_response_batch(lock, upstream, group, index, count, ledger):
    from .model import sample_clock_batch, simulate_batch, _uniform_open
    from .contracts import ClockBatch
    from .experiments import paired_future_batches
    from .runner import _objects
    from .storage import commit_batch
    protocol,g,s=_objects(upstream)
    m=next(m for m in protocol.models if m.model_id==group)
    seeds={name:[20261101,1,8,group,purpose,index] for name,purpose in (('prefix',10),('future',20),('audit',30))}
    rngs={name:np.random.default_rng(seed) for name,seed in seeds.items()}
    start=time.perf_counter();job=ledger.start('G5',ensemble_id=group,details={'protocol_hash':lock['protocol_hash'],'batch_index':index})
    work,attempts,remaining=0,0,count;births=[];speeds=[];gaps=[];events=[];clock_diagnostics=[]
    try:
        while remaining:
            clocks=sample_clock_batch(m,g,rngs['prefix'],remaining,'lower_cone',0)
            clock_diagnostics.append(clocks.diagnostics)
            h=simulate_batch(clocks,g);attempts+=remaining;work+=remaining
            work+=len(h.diagnostics.get('scalar_rechecks',{}))
            events.extend({'context':f'prefix_through_{attempts}','history_index':i,'diagnostics':value}
                          for i,value in h.diagnostics.get('scalar_rechecks',{}).items())
            keep=h.survives
            births.append(clocks.birth_years[keep]);speeds.append(clocks.speeds[keep]);gaps.append(clocks.speed_gaps[keep])
            remaining-=int(np.sum(keep))
            ledger.progress(job,time.perf_counter()-start,work,details={'attempts':attempts,'survivors_pending':remaining})
        prefix=ClockBatch(np.concatenate(births),np.concatenate(speeds),np.concatenate(gaps))
        future=paired_future_batches(prefix,m,g,rngs['future'],(0.,1.,10.) if group<16 else (1.,))
        work+=count*len(future)
        for k,h in future.items():
            work+=len(h.diagnostics.get('scalar_rechecks',{}))
            events.extend({'context':f'future_k{k}','history_index':i,'diagnostics':value}
                          for i,value in h.diagnostics.get('scalar_rechecks',{}).items())
        uniforms,rejections=_uniform_open(rngs['audit'],count)
        arrays={'uniforms':uniforms}
        for k,h in future.items():arrays[f'flags_{k:g}']=h.arrives_within_horizon
        for eid in ('E1','E3'):
            e=next(e for e in protocol.emissions if e.emission_id==eid)
            arrays[eid],diagnostics=response_counts(future[1.],g,s,e)
            events.extend({'context':eid,**event} for event in diagnostics['recheck_events'])
        payload={'protocol_hash':lock['protocol_hash'],'model_id':group,'sample_size':count,'batch_index':index,
                 'seed_roots':seeds,'rng_states':{name:rng.bit_generator.state for name,rng in rngs.items()},
                 'attempts':attempts,'history_evaluations':work,'boundary_rechecks':events,
                 'clock_diagnostics':clock_diagnostics,'future_clock_diagnostics':future[1.].diagnostics.get('batch_clock_diagnostics',{}),
                 'audit_open_uniform_rejections':rejections,'elapsed_seconds':time.perf_counter()-start,'job_id':job}
        identifier=f'refinement-{group:02d}-{index:09d}'
        digest=commit_batch(Path(lock['_output_dir']),identifier,payload,arrays)
    except BaseException as exc:
        ledger.finish(job,time.perf_counter()-start,work,status='interrupted',details={'exception':type(exc).__name__,'attempts':attempts})
        raise
    ledger.finish(job,time.perf_counter()-start,work,details={'batch_id':identifier,'batch_hash':digest,'attempts':attempts})
    return payload | {'_batch_id':identifier,'_batch_hash':digest,'_arrays':arrays}


def _refinement_intervals(lock, upstream, original, batches, look):
    from dataclasses import replace
    from .runner import _objects
    from .oracles import independent_oracle
    protocol,g,s=_objects(upstream)
    raw={r['cell_id']:r for r in original['summary']['rows']}
    bins=lock['initial_subdomains']*2**(look-1)
    edges=np.linspace(.44,.94,bins+1)
    parent_look=look
    evidence={};subdomains=[]
    cache_path=Path(lock['_output_dir'])/f'oracles-look-{look}.json'
    cached=read_json_checked(cache_path) if cache_path.exists() else {'rows':{}}
    if cache_path.exists() and (cached.get('protocol_hash')!=lock['protocol_hash'] or cached.get('content_hash')!=canonical_hash(cached['rows'])):
        raise ValueError('Refinement oracle cache hash mismatch')
    for cell in _refinement_parents(upstream):
        cid=cell['cell_id'];mid=cell['model_id'];eid=cell['emission_id'];k=cell['future_multiplier']
        e=next(e for e in protocol.emissions if e.emission_id==eid)
        ranges=[(.44,.44)] if cell['detector_id']=='Dweak' else list(zip(edges[:-1],edges[1:]))
        parts=[b for b in batches if b['model_id']==mid]
        for index,(a,b) in enumerate(ranges):
            if cell['model_kind']=='independent_sites':
                key=f'{cid}:bin{index}'
                if key not in cached['rows']:
                    model=replace(next(m for m in protocol.models if m.model_id==mid),future_multiplier=k)
                    detector=replace(next(d for d in protocol.detectors if d.detector_id=='Dpositive'),pair_low=float(a),pair_high=float(b))
                    oracle=independent_oracle(model,g,s,e,detector)
                    if oracle.status!='validated':raise ArithmeticError('Refinement quadrature requires repair')
                    cached['rows'][key]={'C':oracle.joint_bounds.get('C',[oracle.C,oracle.C]),
                                         'R0':[oracle.R0.low,oracle.R0.high], 'R':[oracle.R.low,oracle.R.high],
                                         'likelihood':[oracle.likelihood.low,oracle.likelihood.high]}
                intervals=cached['rows'][key]
            else:
                integer=Counter();n=0;sums=Counter()
                for part in parts:
                    arrays=part['_arrays'];flags=arrays[f'flags_{k:g}'];u=arrays['uniforms']
                    low,high=response_weights(arrays[eid],e,float(a),float(b))
                    # Outward numerical guard exceeds the validated <=61-factor
                    # binary64 product error; time-boundary decisions use MP.
                    low=np.maximum(0.,low-1e-12);high=np.minimum(1.,high+1e-12)
                    zlo,zhi=u<=low,u<=high;n+=len(u)
                    for q,value in (('null_low',zlo),('null_high',zhi),('J_low',flags&zlo),
                                    ('J_high',flags&zhi),('K_low',(~flags)&zlo),('K_high',(~flags)&zhi)):
                        integer[q]+=int(np.sum(value))
                    sums['null_low']+=float(np.sum(low));sums['null_high']+=float(np.sum(high))
                limits={}
                for q,successes in integer.items():
                    parent=cell['interval_ids'][q];item=upstream['bound_registry']['items'][parent]
                    pool=lock['error_pool']
                    alpha=refinement_alpha(pool['A'],pool['M'],parent_look,len(ranges))
                    key=f'{parent}:refined-bin{index}:look{parent_look}'
                    record={'parent_interval_id':parent,'successes':successes,'trials':n,'alpha':alpha,
                            'parent_look':parent_look,'subdomains':len(ranges),'p_interval':[float(a),float(b)]}
                    if key in evidence and evidence[key]!=record:raise ValueError('Shared refinement interval inputs disagree')
                    evidence[key]=record;limits[q]=exact_interval(successes,n,alpha)
                risk=partition_risk(*(limits[q] for q in ('J_low','J_high','K_low','K_high')))
                intervals={'C':raw[cid]['intervals']['C'],'R0':raw[cid]['intervals']['R0'],
                           'likelihood':[limits['null_low'].low,limits['null_high'].high],'R':[risk.low,risk.high]}
            subdomains.append({'parent_cell_id':cid,'p_interval':[float(a),float(b)],'intervals':intervals})
    cached.update(protocol_hash=lock['protocol_hash'],content_hash=canonical_hash(cached['rows']))
    write_json_atomic(cache_path,cached)
    return subdomains,evidence


def run_refinement(lock, *, resume=False):
    from .resources import ResourceLedger
    from .storage import load_committed_batches
    from .runner import _run_lock, _recover_usage
    body={k:v for k,v in lock.items() if k!='protocol_hash' and not k.startswith('_')}
    if canonical_hash(body)!=lock['protocol_hash'] or hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=lock['component_hash']:
        raise ValueError('Refinement code/lock identity changed')
    upstream,original=_checked_upstream(lock);root=Path(lock['_output_dir'])
    with _run_lock(root):
        ledger=ResourceLedger(root/'resources.jsonl')
        batches=list(load_committed_batches(root,lock['protocol_hash']))
        _recover_usage(ledger,batches,lock['protocol_hash'])
        result_path=root/'result.json'
        if result_path.exists():
            if not resume:raise ValueError('Existing refinement requires resume')
            result=read_json_checked(result_path)
            if result['content_hash']!=canonical_hash({k:v for k,v in result.items() if k!='content_hash'}):
                raise ValueError('Refinement result hash mismatch')
            if sorted((b['_batch_id'],b['_batch_hash']) for b in batches)!=sorted((b['_batch_id'],b['_batch_hash']) for b in result['batches']):
                raise ValueError('Refinement evidence/batch hash mismatch')
            return result
        if batches and not resume:raise ValueError('Existing refinement batches require resume')
        models=sorted({c['model_id'] for c in _refinement_parents(upstream) if c['model_kind']=='interacting'})
        state_path=root/'state.json';look=1
        if state_path.exists():
            state=read_json_checked(state_path)
            if state.get('protocol_hash')!=lock['protocol_hash'] or state.get('content_hash')!=canonical_hash({k:v for k,v in state.items() if k!='content_hash'}):
                raise ValueError('Refinement checkpoint state hash mismatch')
            look=state['look']
        while True:
            target=lock['initial_histories']*2**(look-1)
            for mid in models:
                progress=sum(b['sample_size'] for b in batches if b['model_id']==mid)
                while progress<target:
                    index=sum(b['model_id']==mid for b in batches)
                    size=min(lock['logical_batch_size'],target-progress)
                    batches.append(_fresh_response_batch(lock,upstream,mid,index,size,ledger));progress+=size
            subdomains,evidence=_refinement_intervals(lock,upstream,original,batches,look)
            summary=refined_summary(upstream,original['summary']['rows'],subdomains)
            affected={f for c in _refinement_parents(upstream) for f in c['families']
                      if '/Dpositive/' in f or '/Dweak/' in f or '/positive_detectors/' in f}
            pending=sorted(f for f in affected if summary.certificates[f]['0.05']=='inconclusive')
            result={'protocol_hash':lock['protocol_hash'],'upstream_protocol_hash':upstream['protocol_hash'],
                    'upstream_result_hash':original['content_hash'],'look':look,'parent_look':look,
                    'subdomains':subdomains,'interval_evidence':evidence,'summary':asdict(summary),'analysis_pending':pending,
                    'batches':[{k:b[k] for k in ('_batch_id','_batch_hash','model_id','sample_size','seed_roots','attempts','history_evaluations')} for b in batches]}
            result['content_hash']=canonical_hash(result)
            write_json_atomic(root/f'checkpoint-{look}.json',result)
            if not pending or lock['purpose']=='smoke':
                write_json_atomic(result_path,result);return read_json_checked(result_path)
            look+=1;state={'look':look,'protocol_hash':lock['protocol_hash']};state['content_hash']=canonical_hash(state)
            write_json_atomic(state_path,state)


def main(argv=None):
    import argparse
    import json
    import sys
    from .resources import ResourceLedger

    parser=argparse.ArgumentParser(description='Preserved-checkpoint continuous-efficiency refinement')
    commands=parser.add_subparsers(dest='command',required=True)
    checkpoint=commands.add_parser('checkpoint',help='Complete the current frozen look before method replacement')
    checkpoint.add_argument('--protocol',type=Path,required=True)
    freeze=commands.add_parser('freeze',help='Bind the fresh method, zero-error donors, upstream evidence and seeds')
    freeze.add_argument('--protocol',type=Path,required=True)
    freeze.add_argument('--out',type=Path,default=Path('results/refinement'))
    run=commands.add_parser('run',help='Complete or resume independent refinement confirmation')
    run.add_argument('--protocol',type=Path,required=True)
    run.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv)
    try:
        lock=read_json_checked(args.protocol)|{'_output_dir':str(args.protocol.resolve().parent)}
        if args.command=='checkpoint':
            result=finish_confirmation_checkpoint(lock,ResourceLedger(args.protocol.parent/'resources.jsonl'))
            brief={k:result[k] for k in ('status','protocol_hash','coarse_precision_requests')}
        elif args.command=='freeze':
            result=freeze_refinement(lock,args.out)
            brief={'status':'refinement_frozen','protocol_hash':result['protocol_hash'],'error_pool':result['error_pool']}
        else:
            result=run_refinement(lock,resume=args.resume)
            brief={k:result[k] for k in ('protocol_hash','look','analysis_pending')}
        print(json.dumps(brief));return 0
    except FileNotFoundError as exc:
        print(json.dumps({'status':'blocking_input','error':str(exc)}),file=sys.stderr);return 3
    except (ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'invalid_configuration','error':str(exc)}),file=sys.stderr);return 2
    except ArithmeticError as exc:
        print(json.dumps({'status':'invalid_correctness','error':str(exc)}),file=sys.stderr);return 4


if __name__=='__main__':
    raise SystemExit(main())
