"""Produce per-source *actual runtime* diagnostics without claiming crawl coverage.

A GitHub Actions runner is independent of the operator's laptop VPN unless
explicitly configured to use their local proxy/self-hosted runner. HTTP 403,
HTTP 412, TLS and routing failures must never be merged into one status.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
FIELDS = ('来源ID', '名称', '地区', '来源网址', '本次状态', '是否得到政策记录', '政策记录数',
          '成功读取正文数', '是否读取到可信目录', '原始失败码', '原始HTTP状态码',
          '访问尝试次数', '失败访问地址', '失败详情', '原因分类', '下步处理')


def classify(row):
    attempts = row.get('attempts') or []
    bad = [a for a in attempts if isinstance(a, dict) and a.get('status') == 'failed']
    # Prefer first actual network/HTTP error, not a later browser challenge.
    first = next((a for a in bad if a.get('error_code')), {})
    code = row.get('first_failure_code') or first.get('error_code') or ''
    http = row.get('first_failure_http_status') or first.get('http_status') or ''
    state = row.get('status', 'not_checked')
    if state == 'ok_with_results':
        return code, http, '已获取政策记录', '核对记录是否写入展示数据库；待补正文的保留来源链接'
    if state == 'ok_no_recent':
        return code, http, '目录解析成功、本次无新增', '保持滚动复查，不应误报抓取失败'
    if code in ('http_403', 'http_412', 'http_429') or state in ('blocked', 'robots_denied', 'access_restricted'):
        return code, http, 'HTTP访问受限', '核对真实HTTP码和官方公开访问条件；按已确认的官方备用目录补查'
    if code in ('dns_error', 'connection_error', 'tls_error') or state == 'connection_error':
        return code, http, '网络/DNS/TLS连接错误', 'GitHub与国内Mac对同一官网执行合规连通性测试，不能靠CSS选择器修复'
    if code == 'timeout' or state == 'timeout':
        return code, http, '连接或响应超时', '分别检查TCP连接/正文读取时长，合理减并发及使用可核实官方入口'
    if code == 'http_404' or state == 'http_error':
        return code, http, 'HTTP入口失效/错误', '优先查找现行正式发布栏目，按实际文件路径替换旧URL'
    if state in ('needs_adapter', 'partial_coverage', 'search_adapter_required'):
        return code, http, '网页目录解析待改进', '定位真实列表行、发布日期、分页与正文；国内不要求时间窗覆盖证明'
    return code, http, '其他/尚未运行', '根据该站原始尝试详情继续核对'


def write_diagnosis(statuses, sources, output):
    sources_by_id = {s['id']: s for s in sources if isinstance(s, dict) and s.get('id')}
    result = []
    for item in statuses:
        if not isinstance(item, dict):
            continue
        src = sources_by_id.get(item.get('id'), {})
        if src.get('region') != '中国':
            continue
        attempts = item.get('attempts') or []
        bad = [a for a in attempts if isinstance(a, dict) and a.get('status') == 'failed']
        code, http, category, action = classify(item)
        result.append(dict(zip(FIELDS, (
            item.get('id', ''), src.get('name', item.get('name', '')),
            src.get('province', ''), src.get('url', ''), item.get('status', ''),
            '是' if item.get('found_count', 0) else '否', item.get('found_count', 0),
            item.get('full_text_records_found', 0), '是' if item.get('listing_parse_ok') else '否',
            code, http, len(attempts), ' | '.join(str(a.get('url', '')) for a in bad[:3]),
            ' | '.join(str(a.get('error', ''))[:100] for a in bad[:3]), category, action,
        ))))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(result)
    return result


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--root', default=str(ROOT))
    p.add_argument('--output', default=None)
    args = p.parse_args()
    root = Path(args.root)
    def read(name):
        try:
            return json.loads((root / name).read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return []
    statuses = read('site/data/policy_source_status.json')
    sources = read('policy_sources.json')
    path = Path(args.output) if args.output else root/'diagnostics/source_failure_diagnosis.csv'
    rows = write_diagnosis(statuses, sources, path)
    print(f'Domestic runtime source diagnostics: {len(rows)} source rows -> {path}')


if __name__ == '__main__':
    main()
