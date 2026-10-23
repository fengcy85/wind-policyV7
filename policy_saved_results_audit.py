"""Backend-only evidence audit of persisted domestic policy records.

This does not crawl, alter the website, or certify complete time coverage.
Run before and after a crawl to separate existing records from new attempts.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def _read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default

def report(root, *, label='after', lookback_days=30):
    root=Path(root)
    sources=_read(root/'policy_sources.json',[])
    current=_read(root/'site/data/policies.json',[])
    statuses=_read(root/'site/data/policy_source_status.json',[])
    if isinstance(current,dict):
        current=next((current[k] for k in ('policies','items','records') if isinstance(current.get(k),list)),[])
    if not isinstance(current,list):current=[]
    by_source=defaultdict(list)
    for item in current:
        if isinstance(item,dict) and item.get('source_id'):
            by_source[item['source_id']].append(item)
    lookup={x.get('id'):x for x in statuses if isinstance(x,dict)}
    cutoff=(date.today()-timedelta(days=lookback_days-1)).isoformat()
    rows=[]
    for src in sources:
        if src.get('region')!='中国':continue
        items=by_source[src['id']]
        status=lookup.get(src['id'],{})
        recent=[x for x in items if (x.get('published_at') or '')>=cutoff]
        original=[x for x in items if x.get('article_evidence_available')]
        media=[x for x in items if x.get('discovery_channel')=='professional_media' or src.get('source_type')=='政策线索']
        rows.append({
            'source_id':src['id'], 'source_name':src['name'], 'source_url':src['url'],
            'stored_policy_or_leads':len(items), 'records_in_rolling_window':len(recent),
            'records_with_body_evidence':len(original), 'media_leads':len(media),
            'previous_crawl_status':status.get('status','not_in_snapshot'),
            'previous_listing_readable':status.get('listing_parse_ok',False),
            'previous_listing_dated_rows':status.get('listing_rows_with_date',0),
            'previous_partial_coverage':status.get('status')=='partial_coverage',
            'sample_urls':' | '.join(str(x.get('url',''))[:250] for x in sorted(recent,key=lambda i:i.get('published_at',''),reverse=True)[:3]),
            'result':('has_stored_records' if items else 'no_records_in_local_snapshot'),
            'date_coverage_required':False,
            'notes':'旧日志显示已发现，不代表已入库；以此处保存记录和真实政策链接为准',
        })
    output=root/'diagnostics'/f'domestic_saved_records_{label}.csv'
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]) if rows else [])
        if rows:writer.writeheader();writer.writerows(rows)
    summary={
        'audit_label':label,'scanned_domestic_source_count':len(rows),
        'source_count_with_stored_records':sum(x['stored_policy_or_leads']>0 for x in rows),
        'all_stored_records':sum(x['stored_policy_or_leads'] for x in rows),
        'last_30d_records':sum(x['records_in_rolling_window'] for x in rows),
        'full_text_evidence_records':sum(x['records_with_body_evidence'] for x in rows),
        'media_lead_records':sum(x['media_leads'] for x in rows),
        'date_coverage_required':False,
        'warning':'本报告仅清点当前仓库已经保存的政策与证据；不证明每个官方渠道连通或文件完整覆盖。',
    }
    (root/'diagnostics'/f'domestic_saved_records_{label}.json').write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='after',choices=('before','after'))
    args=parser.parse_args()
    result=report(ROOT,label=args.label)
    print(json.dumps(result,ensure_ascii=False))
