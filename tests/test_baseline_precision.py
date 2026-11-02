from pathlib import Path

import pytest

from test_freeze import frozen_smoke, small_protocol


def test_baseline_precision_uses_fresh_flags_and_preserves_the_total_error_pool(frozen_smoke,tmp_path):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import freeze_refinement,run_refinement
    from seti_audit.baseline_precision import refine_baselines

    root=Path(frozen_smoke['_output_dir'])
    original=run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    lock=freeze_refinement(frozen_smoke,root/'refinement',initial_histories=16,initial_subdomains=2)
    fresh=run_refinement(lock)
    result=refine_baselines(frozen_smoke,lock,root/'refinement/checkpoint-1.json',tmp_path/'baseline')
    pool=result['policy']['error_pool'];old=pool['original_pool']
    assert len(pool['donor_ids'])==2
    assert pool['A']==pytest.approx(old['A']*2/old['M'])
    assert all(e['trials']==16 for e in result['interval_evidence'].values())
    assert result['source_refinement_hash']==fresh['content_hash']
    assert result['upstream_result_hash']==original['content_hash']
    for sub in result['baseline_bounds']:
        old_row=next(r for r in original['summary']['rows'] if r['cell_id']==sub['parent_cell_id'])
        assert old_row['intervals']['R0'][0]<=sub['R0'][0]<=sub['R0'][1]<=old_row['intervals']['R0'][1]


def test_saved_report_binds_matched_baselines_to_the_completed_fresh_checkpoint(frozen_smoke,tmp_path):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.refinement import freeze_refinement,run_refinement
    from seti_audit.baseline_precision import refine_baselines
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import write_json_atomic,read_json_checked

    root=Path(frozen_smoke['_output_dir']);run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    lock=freeze_refinement(frozen_smoke,root/'refinement',initial_histories=16,initial_subdomains=2)
    run_refinement(lock)
    result=refine_baselines(frozen_smoke,lock,root/'refinement/checkpoint-1.json',root/'baseline_precision')
    write_json_atomic(root/'baseline_precision/result.json',result)
    report=render_report(root,root.parent/'report')
    assert 'baseline_table' in report['artifacts']
    assert read_json_checked(root/'family_envelopes.json')['baseline_precision_hash']==result['content_hash']


def test_report_resolves_zero_response_obstruction_without_fabricating_risk_precision(frozen_smoke):
    from seti_audit.experiments import run_confirmation
    from seti_audit.resources import ResourceLedger
    from seti_audit.reporting import render_report
    from seti_audit.artifacts import read_json_checked

    root=Path(frozen_smoke['_output_dir']);run_confirmation(frozen_smoke,False,ResourceLedger(root/'usage.jsonl'))
    render_report(root,root.parent/'report')
    envelopes=read_json_checked(root/'family_envelopes.json')
    assert envelopes['certificates']['interacting/E1/Duncal/k1']['0.05']=='nonmaterial'
    assert envelopes['envelopes']['interacting/E1/Duncal/k1']['0.05']['analytic_obstruction']=='admissible_zero_response'
    rows=read_json_checked(root/'model_rows.json')['rows']
    row=next(r for r in rows if r['cell_id']=='interacting:m0:k1:E1:Duncal')
    assert row['intervals']['R']==[0,1]
