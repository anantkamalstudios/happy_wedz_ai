"""Orchestrate geocoding pipeline over multiple batches.

Usage:
    python scripts/run_pipeline.py --batches 25 --batch_size 200

For each batch:
 - prepare batch -> scripts/geocode_batch_{i}.json
 - run geocode -> results/geocode_batch_{i}_results.json
 - clean & retry -> scripts/geocode_batch_{i}_retry.json & results/geocode_batch_{i}_retry_results.json
 - apply results for both initial and retry
 - report counts and stop early if no vendors prepared
"""
import argparse
import subprocess
import sys
import json
from pathlib import Path

PY = sys.executable

def run(cmd):
    print('>',' '.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.returncode != 0:
        print('ERR:', proc.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def count_results(path: Path):
    if not path.exists():
        return {'ok':0,'cached':0,'not_found':0,'total':0}
    data = json.loads(path.read_text(encoding='utf-8'))
    c_ok=c_cached=c_nf=0
    for r in data:
        s = r.get('status')
        if s=='ok': c_ok+=1
        elif s=='cached': c_cached+=1
        elif s=='not_found': c_nf+=1
    return {'ok':c_ok,'cached':c_cached,'not_found':c_nf,'total':len(data)}


def main(batches=25, batch_size=200):
    for i in range(1, batches+1):
        print('\n===== Batch', i, 'of', batches, '=====')
        batch_file = Path(f'scripts/geocode_batch_{i}.json')
        results_file = Path(f'results/geocode_batch_{i}_results.json')
        retry_batch = Path(f'scripts/geocode_batch_{i}_retry.json')
        retry_results = Path(f'results/geocode_batch_{i}_retry_results.json')

        # 1) prepare
        rc,_,_ = run([PY, 'scripts/prepare_geocode_batch.py', '--limit', str(batch_size), '--out', str(batch_file)])
        if rc!=0:
            print('Prepare failed; stopping')
            break
        # if batch file empty or contains [] -> stop
        try:
            bf = json.loads(batch_file.read_text(encoding='utf-8'))
        except Exception:
            bf = []
        if not bf:
            print('No vendors prepared in this batch; stopping early')
            break

        # 2) run geocode
        rc,_,_ = run([PY, 'scripts/run_geocode_batch.py', '--in', str(batch_file), '--out', str(results_file)])
        if rc!=0:
            print('Geocode run failed; continuing to next batch')

        # 3) apply initial results
        rc,_,_ = run([PY, 'scripts/apply_geocode_results.py', '--results', str(results_file)])
        # ignore rc

        # 4) clean and retry
        rc,_,_ = run([PY, 'scripts/clean_and_retry_geocode.py', '--results', str(results_file), '--out_batch', str(retry_batch), '--out_results', str(retry_results), '--limit', str(batch_size)])
        if rc!=0:
            print('Clean+retry failed; continuing')

        # 5) apply retry results
        rc,_,_ = run([PY, 'scripts/apply_geocode_results.py', '--results', str(retry_results)])

        # 6) report counts
        r1 = count_results(results_file)
        r2 = count_results(retry_results)
        total_ok = r1['ok'] + r1['cached'] + r2['ok'] + r2['cached']
        total_nf = r1['not_found'] + r2['not_found']
        print(f"Batch {i} summary: initial(total={r1['total']}, ok={r1['ok']}, cached={r1['cached']}, not_found={r1['not_found']}), "
              f"retry(total={r2['total']}, ok={r2['ok']}, cached={r2['cached']}, not_found={r2['not_found']})")
        print(f"Applied this batch: ok+cached={total_ok}, remaining not_found={total_nf}")

    print('\nPipeline finished')

if __name__=='__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--batches', type=int, default=25)
    p.add_argument('--batch_size', type=int, default=200)
    args = p.parse_args()
    main(batches=args.batches, batch_size=args.batch_size)
