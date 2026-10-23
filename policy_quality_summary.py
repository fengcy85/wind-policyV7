"""Backend-only GitHub Actions quality gate report; no frontend changes."""
from __future__ import annotations
import json,os
from datetime import datetime,timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent

def write_quality_summary(statuses,runner_label='GitHub Actions',state=None,started_at=None):
    total=len(statuses)
    fresh=[x for x in statuses if not x.get('not_refreshed_in_this_run') and x.get('checked_at')]
    listing_verified=sum(bool(row.get('listing_coverage_complete',row.get('coverage_complete'))) for row in fresh)
    full_verified=sum(bool(row.get('coverage_complete')) for row in fresh)
    blocked=sum(row['status']=='blocked' for row in statuses)
    network=sum(row['status'] in ('connection_error','timeout') for row in statuses)
    pending=sum(int(row.get('detail_retry_count') or 0) for row in fresh)
    state=state or {}
    last_run=state.get('last_run','')
    valid_new_run=bool(last_run and (not started_at or last_run>=started_at))
    domestic=[x for x in fresh if x.get('date_coverage_required') is False]
    foreign=[x for x in fresh if x.get('date_coverage_required') is not False]
    parsed=sum(bool(x.get('listing_parse_ok')) for x in domestic)
    discoveries=sum(int(x.get('found_count') or 0) for x in domestic)
    articles=sum(int(x.get('full_text_records_found') or 0) for x in domestic)
    lines=[f'## 风电法规抓取质量｜{runner_label}', '',
           '本轮新抓取数据：'+('已生成' if valid_new_run else '未能证明本轮新结果已写入'),
           '执行范围：'+str(state.get('scope','旧版未标注')), '',
           f'- 本轮尝试来源：{len(fresh)} / 已配置：{total}',
           f'- 国内目录读取成功：{parsed}/{len(domestic)}（无需完整时间覆盖证明）',
           f'- 国内发现政策和线索：{discoveries}；取得完整正文：{articles}',
           f'- 海外原有完整覆盖核验：{sum(bool(x.get("coverage_complete")) for x in foreign)}/{len(foreign)}',
           f'- 访问受限：{blocked}；连接/超时异常：{network}；详情待重试：{pending}',
           '', '> 国内按有效政策发现与原文证据验收。日期缺失、分页失败列为风险提示，不会阻止收录；海外原有规则未修改。',
           '', '| 来源 | 真实状态 | 目录可读 | 政策/线索 | 正文 | 问题说明 |',
           '|---|---|---|---|---|---|']
    for row in statuses:
        status=row.get('status','')
        if status in ('ok_no_recent','ok_with_results') and not row.get('listing_warnings'):
            continue
        msg=str(row.get('message','')).replace('|','/').replace('\n',' ')[:110]
        if row.get('not_refreshed_in_this_run'):
            msg='本轮未运行；'+msg
        lines.append(f"| {row.get('name','')} | {status} | {row.get('listing_parse_ok',False)} | "
                     f"{row.get('found_count',0)} | {row.get('full_text_records_found',0)} | {msg} |")
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    file=BASE/'site/data/policy_source_status.json'
    statuses=json.loads(file.read_text()) if file.exists() else []
    state_file=BASE/'site/data/policy_crawl_state.json'
    state=json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
    marker=BASE/'diagnostics/this_job_started_utc.txt'
    started_at=marker.read_text(encoding='utf-8').strip() if marker.exists() else None
    text=write_quality_summary(statuses,state=state,started_at=started_at)
    out=BASE/'diagnostics/last_run_quality.md'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text)
    path=os.getenv('GITHUB_STEP_SUMMARY')
    if path:
        with open(path,'a',encoding='utf-8') as f:f.write(text)
    print('Wrote',out,'with',len(statuses),'source records')
