from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from test_detection import D, emission
from test_detection_bounds import bounded_schedule
from test_freeze import frozen_smoke, small_protocol


def test_refinement_spends_only_its_proved_zero_error_donor_pool():
    from seti_audit.refinement import refinement_alpha

    A, M = .025*12/2536, 600
    for j in (1, 6, 100):
        assert 32 * refinement_alpha(A, M, j, 32) == pytest.approx(A / (M*j*(j+1)))
    assert sum(32*refinement_alpha(A, M, j, 32) for j in range(1, 10000)) < A/M
    with pytest.raises(ValueError):
        refinement_alpha(A, M, 0, 32)


@pytest.mark.parametrize("e", [emission(), emission(zeta=.1), emission(delay=100),
                               emission(lifetime=100), emission(activity="ctmc")])
def test_compact_response_preserves_full_shared_efficiency_and_linked_visits(tiny_geometry, e):
    from seti_audit.contracts import ClockBatch, DetectorConfig
    from seti_audit.detection import batch_null_weights
    from seti_audit.model import simulate_batch
    from seti_audit.refinement import response_counts, response_weights

    g = tiny_geometry([[1., 0, 0]])
    births = np.array([-200., -30., -2., -1.5, -1., -.5, np.inf])[:, None]
    b = simulate_batch(ClockBatch(births, np.full(births.shape, .1), np.full(births.shape, 9.)), g)
    s = bounded_schedule(repeats=2)
    counts, diagnostics = response_counts(b, g, s, e)
    assert diagnostics["source_precision_rechecks"] >= 0
    for lo, hi in ((.44, .94), (.44, .5), (.5, .71), (.71, .94), (.733, .733)):
        actual = response_weights(counts, e, lo, hi)
        expected = batch_null_weights(b, g, s, e, DetectorConfig("subdomain", lo, hi, False))
        np.testing.assert_allclose(actual[0], expected[0], rtol=1e-13, atol=1e-15)
        np.testing.assert_allclose(actual[1], expected[1], rtol=1e-13, atol=1e-15)


def test_response_counts_match_multisite_accelerator(repo_root, tmp_path):
    from seti_audit.contracts import load_protocol, DetectorConfig
    from seti_audit.data import load_catalog, load_schedule
    from seti_audit.model import sample_clock_batch, simulate_batch
    from seti_audit.refinement import response_counts, response_weights
    from seti_audit.detection import batch_null_weights

    p=load_protocol(repo_root/'config/protocol.json');c=load_catalog(repo_root/'docs/blueprint.md',tmp_path/'data')
    s=load_schedule(c,tmp_path/'inputs',tmp_path/'data')
    b=simulate_batch(sample_clock_batch(p.models[15],c.geometry,np.random.default_rng(428),129),c.geometry)
    for e in p.emissions[1:]:
        counts,_=response_counts(b,c.geometry,s,e)
        for lo,hi in ((.44,.5),(.5,.94),(.621,.621)):
            x=response_weights(counts,e,lo,hi);y=batch_null_weights(b,c.geometry,s,e,DetectorConfig('sub',lo,hi,False))
            np.testing.assert_allclose(x[0],y[0],rtol=1e-12,atol=1e-15)
            np.testing.assert_allclose(x[1],y[1],rtol=1e-12,atol=1e-15)


def test_refined_family_keeps_every_parameter_subdomain_and_compatibility():
    from seti_audit.refinement import refined_summary

    base={"cell_id":"parent", "model_kind":"interacting", "model_id":0, "families":["family"],
          "baseline_id":"base", "thresholds":[.05], "deterministic":{"C":[1,1],"R0":[.1,.1],"R":[0,1],"likelihood":[0,1]}}
    lock={"cells":[base],"thresholds":[.05],"bound_registry":{"items":{},"pools":{"diagnostics":{"A":.025,"M":0}}}}
    subs=[{"parent_cell_id":"parent","p_interval":[.44,.69],"intervals":{"C":[1,1],"R0":[.1,.1],"R":[.02,.03],"likelihood":[.2,.4]}},
          {"parent_cell_id":"parent","p_interval":[.69,.94],"intervals":{"C":[1,1],"R0":[.1,.1],"R":[.8,.9],"likelihood":[0,.01]}}]
    s=refined_summary(lock,[],subs)
    assert s.certificates['family']['0.05']=='material'
    assert s.envelopes['family']['0.05']['post_upper']==[.02,.03]
    with pytest.raises(ValueError,match="cover|gap"):
        refined_summary(lock,[],subs[:1])


def test_fresh_refinement_resumes_and_preserves_upstream_evidence(frozen_smoke, tmp_path):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import freeze_refinement, run_refinement
    from seti_audit.artifacts import read_json_checked

    root=Path(frozen_smoke['_output_dir'])
    upstream=run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    before=(root/'confirmation.json').read_bytes()
    lock=freeze_refinement(frozen_smoke,tmp_path/'refined',initial_histories=16,initial_subdomains=2)
    assert lock['reserved_through']==max(upstream['looks'].values())
    pool=lock['error_pool'];original_pool=pool['original_pool']
    assert pool['A']==pytest.approx(original_pool['A']*len(pool['donor_ids'])/original_pool['M'])
    assert pool['minimum_S1_gap_years']>100
    result=run_refinement(lock)
    assert (root/'confirmation.json').read_bytes()==before
    assert result['subdomains']
    assert all(s['p_interval'][0]>=.44 and s['p_interval'][1]<=.94 for s in result['subdomains'])
    assert all(r[2]==8 for b in result['batches'] for r in b['seed_roots'].values())
    repeat=run_refinement(lock,resume=True)
    assert repeat==result
    assert read_json_checked(tmp_path/'refined/result.json')['content_hash']==result['content_hash']
    batch_path=next((tmp_path/'refined/checkpoints').glob('*/arrays.npz'))
    batch_path.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='hash'):
        run_refinement(lock,resume=True)


def test_refinement_recovers_publication_interruption_without_duplicate_samples(frozen_smoke,tmp_path,monkeypatch):
    import seti_audit.storage as storage
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import freeze_refinement,run_refinement

    root=Path(frozen_smoke['_output_dir'])
    run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    lock=freeze_refinement(frozen_smoke,tmp_path/'refined',initial_histories=16,initial_subdomains=2)
    publish=storage.commit_batch
    def crash(*args,**kwargs):
        publish(*args,**kwargs)
        raise OSError('Injected crash after publication')
    monkeypatch.setattr(storage,'commit_batch',crash)
    with pytest.raises(OSError,match='Injected'):
        run_refinement(lock)
    monkeypatch.setattr(storage,'commit_batch',publish)
    result=run_refinement(lock,resume=True)
    assert sum(b['sample_size'] for b in result['batches'])==16
    assert len(result['batches'])==1
    assert ResourceLedger(tmp_path/'refined/resources.jsonl').pending_jobs()==[]


def test_replacement_method_finishes_the_prescribed_checkpoint_without_changing_seeds(frozen_smoke,monkeypatch):
    import seti_audit.runner as runner
    from seti_audit.refinement import finish_confirmation_checkpoint
    from seti_audit.resources import ResourceLedger

    root=Path(frozen_smoke['_output_dir']);ledger=ResourceLedger(root/'usage.jsonl')
    publish=runner.commit_batch
    def crash(*args,**kwargs):
        publish(*args,**kwargs)
        raise OSError('Preserved operational interruption')
    monkeypatch.setattr(runner,'commit_batch',crash)
    with pytest.raises(OSError):runner.run_confirmation(frozen_smoke,False,ledger)
    monkeypatch.setattr(runner,'commit_batch',publish)
    snapshot=finish_confirmation_checkpoint(frozen_smoke,ledger)
    assert snapshot['status']=='checkpoint_complete_refinement_pending'
    assert all(r['completion_status']!='pending' for r in snapshot['summary']['rows'])
    assert len(snapshot['batch_hashes'])==len(set(snapshot['batch_hashes']))
    assert all(seed[2] in (4,5,6,7) for batch in snapshot['batches'] for seed in batch['seed_roots'].values())


def test_report_uses_saved_refinement_and_checks_its_upstream_binding(frozen_smoke,monkeypatch):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import freeze_refinement,run_refinement
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked,write_json_atomic,canonical_hash

    root=Path(frozen_smoke['_output_dir']);run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    lock=freeze_refinement(frozen_smoke,root/'refinement',initial_histories=16,initial_subdomains=2)
    result=run_refinement(lock)
    def forbidden(*args,**kwargs):raise AssertionError('Saved-only report cannot simulate')
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    manifest=render_report(root,root.parent/'report')
    assert 'refinement_table' in manifest['artifacts']
    assert read_json_checked(root/'family_envelopes.json')['refinement_hash']==result['content_hash']
    text=(root.parent/'report/REPORT.md').read_text()
    assert 'continuous shared' in text.lower()
    import gzip
    saved_table=(root/'tables/refined_subdomains.csv').read_bytes()
    compressed=root/'refinement/result.json.gz'
    compressed.write_bytes(gzip.compress((root/'refinement/result.json').read_bytes(),mtime=0))
    (root/'refinement/result.json').unlink()
    render_report(root,root.parent/'report')
    assert (root/'tables/refined_subdomains.csv').read_bytes()==saved_table
    assert read_json_checked(root/'evidence.json')['evidence']['refinement_result']['path'].endswith('.json.gz')
    result['upstream_result_hash']='changed';result.pop('content_hash');result['content_hash']=canonical_hash(result)
    compressed.write_bytes(gzip.compress((__import__('json').dumps(result)+'\n').encode(),mtime=0))
    with pytest.raises(ValueError,match='refinement|upstream'):
        render_report(root,root.parent/'report')


def test_refinement_cli_has_reproducible_dispatch_and_missing_input_status(tmp_path):
    from seti_audit.refinement import main

    for command in ('checkpoint','freeze','run'):
        with pytest.raises(SystemExit) as done:main([command,'--help'])
        assert done.value.code==0
    assert main(['freeze','--protocol',str(tmp_path/'absent.json')])==3
