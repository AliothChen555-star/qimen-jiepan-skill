"""Independent focused retest; never touches original defect evidence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(r'X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from rule_evaluator import PURPOSES, evaluate_application, rule_by_id


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli_retest(directory):
    rows = []
    raw = (ROOT / 'evals' / 'fixtures' / 'base.json').read_bytes()
    for script, extra, output_key in (
        ('inspect_patterns.py', [], 'analysis_version'),
        ('timing_candidates.py', ['--palaces', '4', '--unit', 'day', '--days', '1'], 'candidates'),
    ):
        case_dir = directory / Path(script).stem
        case_dir.mkdir()
        source = case_dir / 'frozen-chart.json'
        source.write_bytes(raw)
        before = digest(source)
        hardlink = case_dir / 'hardlink-alias.json'
        os.link(source, hardlink)
        (case_dir / 'nested').mkdir()
        normalized_alias = str(case_dir / 'nested') + os.sep + '..' + os.sep + source.name
        for mode, output in (
            ('same_path', str(source)),
            ('normalized_path_alias', normalized_alias),
            ('hardlink_alias', str(hardlink)),
            ('new_distinct_output', str(case_dir / 'derived.json')),
            ('existing_distinct_output', str(case_dir / 'existing-derived.json')),
        ):
            output_path = Path(output)
            if mode == 'existing_distinct_output':
                output_path.write_text('previous-derived-output', encoding='utf-8')
            process = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'scripts' / script), str(source), *extra, '--output', output],
                capture_output=True, encoding='utf-8',
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            after = digest(source)
            should_reject = mode in ('same_path', 'normalized_path_alias', 'hardlink_alias')
            valid_output = False
            if not should_reject and process.returncode == 0:
                valid_output = output_key in json.loads(output_path.read_text(encoding='utf-8'))
            passed = (process.returncode != 0 if should_reject else process.returncode == 0 and valid_output)
            passed = passed and source.read_bytes() == raw and digest(hardlink) == before
            rows.append({'script': script, 'case': mode, 'source': str(source), 'output': output,
                         'returncode': process.returncode, 'stderr': process.stderr,
                         'stdout': process.stdout, 'source_sha256_before': before,
                         'source_sha256_after': after, 'source_bytes_unchanged': source.read_bytes() == raw,
                         'hardlink_bytes_unchanged': hardlink.read_bytes() == raw,
                         'distinct_output_valid': valid_output if not should_reject else None,
                         'passed': passed})
    return rows


def api_retest():
    rows = []
    for value in ('false', 'true', 'unknown', 0, 1, [], {}):
        try:
            result = evaluate_application(rule_by_id('PAIR_乙丁'), {}, geometry=value)
            rows.append({'case': 'invalid_geometry', 'input': value, 'unexpected_result': result, 'passed': False})
        except ValueError as exc:
            rows.append({'case': 'invalid_geometry', 'input': value, 'error': str(exc), 'passed': True})
    for value in (False, '', [], 'confirmed', 0, 1):
        try:
            result = evaluate_application(rule_by_id('PAIR_乙丁'), {}, context=value)
            rows.append({'case': 'invalid_context', 'input': value, 'unexpected_result': result, 'passed': False})
        except ValueError as exc:
            rows.append({'case': 'invalid_context', 'input': value, 'error': str(exc), 'passed': True})
    contexts = {
        'PAIR_乙丁': {},
        'GEOM_乙辛': {
            'checks': {'GEOM_乙辛': {
                'domain_scope_confirmed': {'value': True, 'basis': '虚构程序复验：已显式声明本事范围。'},
                'host_guest_role_bound': {'value': True, 'basis': '虚构程序复验：主客已显式固定。'}}},
            'exception_bindings': {'GEOM_乙辛': {'host_guest_relief': {
                'source_id': 'MJ-P', 'role': '主', 'basis': '虚构程序复验：显式选用例外来源和角色。'}}},
        },
    }
    for rule_id, context in contexts.items():
        for geometry in (None, False, True):
            result = evaluate_application(rule_by_id(rule_id), {}, context=context, geometry=geometry)
            if geometry is None:
                passed = result['geometry_match'] == 'unknown' and set(result['eligibility'].values()) == {'unknown'}
            elif geometry is False:
                passed = result['geometry_match'] == 'false' and set(result['eligibility'].values()) == {'false'}
            else:
                passed = result['geometry_match'] == 'true' and result['eligibility']['interpretation'] == 'true'
                if rule_id == 'GEOM_乙辛':
                    passed = passed and result['eligibility']['exception'] == 'true'
            rows.append({'case': 'valid_geometry', 'rule_id': rule_id, 'input': geometry,
                         'geometry_match': result['geometry_match'], 'eligibility': result['eligibility'],
                         'passed': passed})
    return rows


if __name__ == '__main__':
    directory = Path(tempfile.mkdtemp(prefix='retest-two-fixes-', dir=OUT))
    report = {'scope': '仅复验两个已确认程序缺陷，不重复广时区遍历',
              'tested_at_utc': datetime.now(timezone.utc).isoformat(), 'artifacts': str(directory),
              'cli_cases': cli_retest(directory), 'api_cases': api_retest(),
              'source_sha256': {str(path.relative_to(ROOT)): digest(path) for path in (
                  ROOT / 'scripts' / 'file_outputs.py', ROOT / 'scripts' / 'rule_evaluator.py',
                  ROOT / 'scripts' / 'inspect_patterns.py', ROOT / 'scripts' / 'timing_candidates.py',
                  ROOT / 'evals' / 'test_output_preservation.py', ROOT / 'evals' / 'test_rule_evaluator.py')}}
    report['all_passed'] = all(row['passed'] for row in report['cli_cases'] + report['api_cases'])
    path = OUT / 'retest-two-fixes-result.json'
    with path.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'all_passed': report['all_passed'], 'cli_case_count': len(report['cli_cases']),
                      'api_case_count': len(report['api_cases']), 'result': str(path),
                      'source_sha256': report['source_sha256']}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['all_passed'] else 1)
