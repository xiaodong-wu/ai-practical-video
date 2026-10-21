#!/usr/bin/env python3
"""Deterministic synthetic-data example; does not call an AI or customer service."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=here / 'input.csv')
    parser.add_argument('--output', type=Path, default=here / 'output')
    args = parser.parse_args()
    for name in ('cleaned.csv', 'review.csv', 'removed.csv', 'result.json'):
        if args.input.resolve() == (args.output / name).resolve():
            raise SystemExit('Output must not overwrite the original input')
    source = args.input.read_bytes()
    with args.input.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {'公司', '邮箱', '国家'}.issubset(rows[0]):
        raise SystemExit('Input requires 公司, 邮箱, 国家 columns and at least one record')
    seen, cleaned, review, removed = set(), [], [], []
    for line, row in enumerate(rows, 2):
        normalized = {**row, '公司': row['公司'].strip(), '邮箱': row['邮箱'].strip().lower()}
        email = normalized['邮箱']
        if not email:
            review.append({'原始行': line, **normalized, '原因': '缺少邮箱，保留并人工确认'})
            cleaned.append(normalized)
        elif email in seen:
            removed.append({'原始行': line, **normalized, '原因': '相同邮箱重复'})
        else:
            seen.add(email)
            cleaned.append(normalized)
    args.output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    write_csv(args.output / 'cleaned.csv', cleaned, fields)
    write_csv(args.output / 'review.csv', review, ['原始行', *fields, '原因'])
    write_csv(args.output / 'removed.csv', removed, ['原始行', *fields, '原因'])
    result = {'input': len(rows), 'output': len(cleaned), 'removed': len(removed), 'review': len(review),
              'input_sha256': hashlib.sha256(source).hexdigest(),
              'row_balance_ok': len(rows) == len(cleaned) + len(removed), 'synthetic_example': True}
    (args.output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.input.read_bytes() != source:
        raise RuntimeError('Original input changed during processing')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
