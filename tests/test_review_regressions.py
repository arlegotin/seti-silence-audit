import json
from pathlib import Path

import numpy as np
import pytest

from test_freeze import frozen_smoke, small_protocol


def test_generated_shell_boundary_preserves_free_event_support():
    from seti_audit.theorem import _restricted_points, _evaluate_shell

    class BoundaryRng:
        def random(self, size):
            return np.tile([.49257486398512473,.1213237684909555,.019999999999999907],size//3)
        def normal(self, size):
            result=np.zeros(size);result[:,0]=1;return result
    counter={'open_uniform_rejections':0,'point_proposals':0}
    points=_restricted_points(BoundaryRng(),1,.02,True,.02,counter)
    result=_evaluate_shell(points,.02)
    assert not result['right_censored']
    assert 0 < result['free_arrival_delay'] <= .02
    assert 0 < result['arrival_delay'] <= .02


def test_shell_certain_endpoint_uses_analytic_identity_not_rounded_fractions():
    from seti_audit.contracts import ShellSummary
    from seti_audit.theorem import shell_joint_count

    sample=ShellSummary(1,1,0,.1,.2,np.array([np.nextafter(1.,2.)]),np.array([.5]),
                        np.array([1.]),np.array([.5]),{}, {})
    assert shell_joint_count(sample,1.,1.)==1


@pytest.mark.parametrize('event', ['start','progress','finish'])
def test_resource_journal_recovers_torn_tail_without_losing_complete_usage(tmp_path,event):
    from seti_audit.resources import ResourceLedger

    path=tmp_path/'resources.jsonl';ledger=ResourceLedger(path);job=ledger.start('G4')
    ledger.progress(job,1.,12)
    tail=('{"event":"'+event+'","job_id":').encode()
    with path.open('ab') as stream:stream.write(tail)
    assert ledger.usage()['history_evaluations']==12
    assert ledger.pending_jobs()[0]['job_id']==job
    evidence=list(tmp_path.glob('resources.jsonl.interrupted.*.bin'))
    assert len(evidence)==1 and evidence[0].read_bytes()==tail
    other=ledger.start('G6');ledger.finish(other,1.,1)
    assert ledger.usage()['history_evaluations']==13
    assert all(isinstance(json.loads(s),dict) for s in path.read_text().splitlines())


def test_resource_journal_rejects_corruption_in_complete_prefix(tmp_path):
    from seti_audit.resources import ResourceLedger

    path=tmp_path/'resources.jsonl';ledger=ResourceLedger(path);ledger.start('G4')
    with path.open('ab') as stream:stream.write(b'not-json\n{"event":"unfinished"')
    original=path.read_bytes()
    with pytest.raises(ValueError,match='corrupt|Corrupt'):ledger.records()
    assert path.read_bytes()==original


def test_resource_start_repairs_before_appending_and_preserves_valid_unterminated_record(tmp_path):
    from seti_audit.resources import ResourceLedger

    path=tmp_path/'resources.jsonl';ledger=ResourceLedger(path);job=ledger.start('G4');ledger.progress(job,1.,12)
    path.write_bytes(path.read_bytes().removesuffix(b'\n'))
    other=ledger.start('G6')
    assert ledger.usage()['history_evaluations']==12
    assert {r['job_id'] for r in ledger.pending_jobs()}=={job,other}
    with path.open('ab') as stream:stream.write(b'{"event":"progress"')
    third=ledger.start('G6')
    assert len(ledger.pending_jobs())==3
    assert ledger.records()[-1]['job_id']==third


def test_torn_resource_finish_recovers_an_already_published_batch(frozen_smoke,monkeypatch):
    import seti_audit.runner as runner
    from seti_audit.resources import ResourceLedger

    root=Path(frozen_smoke['_output_dir']);ledger=ResourceLedger(root/'usage.jsonl');finish=ledger.finish
    fired=False
    def crash(job,*args,**kwargs):
        nonlocal fired
        if not fired and kwargs.get('details',{}).get('batch_id'):
            fired=True;raise OSError('Crash before resource finish')
        return finish(job,*args,**kwargs)
    monkeypatch.setattr(ledger,'finish',crash)
    with pytest.raises(OSError,match='Crash'):runner.run_confirmation(frozen_smoke,False,ledger)
    monkeypatch.setattr(ledger,'finish',finish)
    with ledger.path.open('ab') as stream:stream.write(b'{"event":"finish","job_id":')
    result=runner.run_confirmation(frozen_smoke,True,ledger)
    assert result['status']=='smoke_complete'
    assert not ledger.pending_jobs()
    assert any(r.get('status')=='recovered_published' for r in ledger.records())


def test_store_identity_detects_complete_loss_before_a_summary_exists(tmp_path):
    import shutil
    from seti_audit.storage import commit_batch,load_committed_batches

    commit_batch(tmp_path,'first',{'protocol_hash':'fixed'}, {})
    shutil.rmtree(tmp_path/'checkpoints')
    with pytest.raises(FileNotFoundError,match='[Rr]estore.*checkpoint'):
        load_committed_batches(tmp_path,'fixed')


def test_refinement_resume_rejects_missing_legacy_store_with_compressed_evidence(frozen_smoke,tmp_path,monkeypatch):
    import shutil,gzip
    import seti_audit.refinement as refinement
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.artifacts import write_json_atomic,canonical_hash

    root=Path(frozen_smoke['_output_dir']);run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    target=tmp_path/'refined';lock=refinement.freeze_refinement(frozen_smoke,target,initial_histories=16,initial_subdomains=2)
    refinement.run_refinement(lock)
    raw=target/'checkpoint-1.json';raw.with_suffix('.json.gz').write_bytes(gzip.compress(raw.read_bytes(),mtime=0));raw.unlink()
    (target/'result.json').unlink();shutil.rmtree(target/'checkpoints');(target/'checkpoints').mkdir();(target/'checkpoint_store.json').unlink(missing_ok=True)
    (target/'resources.jsonl').unlink()
    state={'look':2,'protocol_hash':lock['protocol_hash']};state['content_hash']=canonical_hash(state);write_json_atomic(target/'state.json',state)
    def forbidden(*args,**kwargs):raise AssertionError('Missing prior evidence must not trigger simulation')
    monkeypatch.setattr(refinement,'_fresh_response_batch',forbidden)
    with pytest.raises(FileNotFoundError,match='[Rr]estore.*checkpoint'):
        refinement.run_refinement(lock,resume=True)


@pytest.mark.parametrize('mode',['resume','complete_checkpoint'])
def test_unfinished_original_paths_reject_missing_store_recorded_by_job_ledger(frozen_smoke,monkeypatch,mode):
    import shutil
    import seti_audit.runner as runner
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import finish_confirmation_checkpoint

    root=Path(frozen_smoke['_output_dir']);ledger=ResourceLedger(root/'usage.jsonl');compute=runner._compute_batch
    def stop_after_publication(*args,**kwargs):
        compute(*args,**kwargs);raise OSError('Stop after completed publication')
    monkeypatch.setattr(runner,'_compute_batch',stop_after_publication)
    with pytest.raises(OSError):runner.run_confirmation(frozen_smoke,False,ledger)
    shutil.rmtree(root/'checkpoints');(root/'checkpoints').mkdir();(root/'checkpoint_store.json').unlink(missing_ok=True)
    def forbidden(*args,**kwargs):raise AssertionError('Cannot replace committed evidence')
    monkeypatch.setattr(runner,'_compute_batch',forbidden)
    with pytest.raises(FileNotFoundError,match='[Rr]estore.*checkpoint'):
        if mode=='resume':runner.run_confirmation(frozen_smoke,True,ledger)
        else:finish_confirmation_checkpoint(frozen_smoke,ledger)


def test_advanced_original_state_requires_its_preceding_completed_counts(frozen_smoke,monkeypatch):
    import seti_audit.runner as runner
    from seti_audit.resources import ResourceLedger

    root=Path(frozen_smoke['_output_dir']);(root/'checkpoints').mkdir()
    looks={key:1 for key in runner._groups(frozen_smoke)};looks['interacting:0']=2
    runner._write_state(root/'run_state.json',frozen_smoke['protocol_hash'],looks)
    def forbidden(*args,**kwargs):raise AssertionError('Cannot rebuild a missing completed look')
    monkeypatch.setattr(runner,'_compute_batch',forbidden)
    with pytest.raises(FileNotFoundError,match='[Rr]estore.*checkpoint'):
        runner.run_confirmation(frozen_smoke,True,ResourceLedger(root/'usage.jsonl'))


def test_missing_refinement_state_cannot_relabel_advanced_counts_as_look_one(frozen_smoke,tmp_path,monkeypatch):
    import seti_audit.refinement as refinement
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger

    root=Path(frozen_smoke['_output_dir']);run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    target=tmp_path/'refined';lock=refinement.freeze_refinement(frozen_smoke,target,initial_histories=16,initial_subdomains=2)
    refinement.run_refinement(lock)
    refinement._fresh_response_batch(lock,frozen_smoke,0,1,16,ResourceLedger(target/'resources.jsonl'))
    (target/'result.json').unlink()
    def forbidden(*args,**kwargs):raise AssertionError('Cannot reset the checkpoint index')
    monkeypatch.setattr(refinement,'_refinement_intervals',forbidden)
    with pytest.raises(FileNotFoundError,match='[Rr]estore.*checkpoint'):
        refinement.run_refinement(lock,resume=True)
