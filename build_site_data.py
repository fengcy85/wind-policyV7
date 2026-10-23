"""Build a stable, auditable display schema from mixed historical/V6.1 policy records.

Never infer a publication date from crawling time, fabricate law text, or invent effects.
Raw crawler output remains in policies.json; the website reads policies_display.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'site' / 'data'
WIND = re.compile(r'风(?:力)?电|风机|风力发电机组|wind[\s-]?(?:power|energy|farm|turbine|generation)|offshore wind|onshore wind|éolien|e[oó]lic|r[uü]zgar|điện gió|ветр', re.I)
REGULATION = re.compile(r'法规|政策|通知|标准|并网|可再生能源|绿电|电力交易|电力市场|条例|办法|规定|规划|认证|招标|law|regulat|directive|policy|tender|standard|permit|grid', re.I)
# The BJX wind-policy category contains a few general electricity / pricing
# policy leads. Do not mark them as wind-applicable law when their public list
# title does not explicitly say wind; show only as visibly unverified media lead.
MEDIA_WIND_POLICY = re.compile(r'新能源|可再生能源|绿电|电力市场|上网电价|机制电价|绿色电力|能源项目|电力交易|直连|并网|消纳')
MEDIA_POLICY_KIND = re.compile(r'政策|通知|规定|办法|措施|征求意见|细则|公告|公示|申报|竞价|竞配|规划|清单|核准')
# Some policy rules genuinely affect wind operators without saying "风电".
# This exception applies ONLY to traceable Chinese government documents, and
# is explicitly marked as an unverified wind-applicability lead.
INDIRECT_WIND_TOPIC = re.compile(r'新能源|可再生能源|绿电|绿色电力|电力现货|电力市场|电力交易|电力并网|电力辅助服务|电力监管|电力调度|上网电价|机制电价|电网接入|绿证|增量配电|发电侧|源网荷储|绿电直连')
POLICY_HEADLINE = re.compile(r'政策|通知|规定|办法|措施|意见|实施方案|细则|公告|公示|竞价|竞配|交易规则|规划|批复|发文|核准')
NOT_A_POLICY = re.compile(r'行政处罚|人事任免|招聘公告|考试报名|干部公示|煤矿事故|广交会|展会|安全生产许可证处罚')
CHALLENGE_TEXT = re.compile(r'CF_APP_WAF|requestInfo\.userUserId|Just a moment|人机安全验证', re.I)
DESIGN_TERMS = ('技术标准', '设计', '认证', '并网', '网络安全', '海上', '运输', '极端', '环境适应', '运维', '退役', '技术规范')
CSV_FIELDS = ['发布日期', '法规名称', '国家/地区', '发布来源', '原文节选', '法规维度标签', '产品设计影响分析', '商业模式影响', '核验状态', '原文链接']


def read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return default


def save(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(p.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(p)


def string(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def safe_url(url):
    try:
        parsed = urlsplit(string(url))
        return string(url) if parsed.scheme.lower() in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:
        return ''


def valid_day(raw):
    value = string(raw)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return ''
    try:
        parsed = date.fromisoformat(value)
        return value if parsed <= date.today() else ''
    except ValueError:
        return ''


def pick_excerpt(item):
    return string(item.get('source_excerpt') or item.get('evidence') or item.get('requirements_excerpt') or item.get('excerpt'))[:800]


def canonical_region(region):
    return '国内' if region in ('国内', '中国', 'CN') else '海外/国际' if region in ('海外', '海外/国际', '国际') else '待核验'


def normalize_country(value, region, province=''):
    value = string(value)
    if region == '国内':
        return string(province) or (next((x for x in reversed(value.split('·')) if x not in ('中国', '中华人民共和国')), '') or '中国')
    return value or '地区待核验'


def record_score(item):
    return (int(bool(valid_day(item.get('published_at'))))*5 +
            int(bool(pick_excerpt(item)))*5 +
            len(item.get('dimensions') or [])*2 +
            int(bool(item.get('impact_design') or item.get('product_impact')))*2 +
            int(bool(item.get('clauses'))))


def source_rows(source_file=None):
    configured = read(source_file or ROOT / 'policy_sources.json', [])
    return configured if isinstance(configured, list) else []


def normalize_policy(item, source_map, ai_cache, today=None, rejection_notes=None):
    def reject(reason):
        if rejection_notes is not None:
            rejection_notes.append(reason)
        return None

    if not isinstance(item, dict):
        return reject('invalid_record')
    title, url, excerpt = string(item.get('title')), safe_url(item.get('url')), pick_excerpt(item)
    if len(title) < 6 or not url:
        return reject('invalid_title_or_original_url')
    source = source_map.get(item.get('source_id'), {})
    region = canonical_region(item.get('region') or item.get('source_region') or source.get('region'))
    if region == '待核验' and source:
        region = canonical_region(source.get('region'))
    is_domestic = region == '国内'
    is_government_url = (urlsplit(url).hostname or '').lower().endswith('.gov.cn')
    wind_evidence = bool(WIND.search(title + ' ' + excerpt))
    media_hint = (item.get('source_id') == 'cn_5555c1d4376e' and
                  (urlsplit(url).hostname or '').endswith('bjx.com.cn') and
                  source.get('source_type') == '政策线索' and
                  bool((WIND.search(title) or MEDIA_WIND_POLICY.search(title)) and MEDIA_POLICY_KIND.search(title)))
    indirect_official = bool(is_domestic and is_government_url and
                             INDIRECT_WIND_TOPIC.search(title) and POLICY_HEADLINE.search(title) and
                             not NOT_A_POLICY.search(title) and not wind_evidence)
    if NOT_A_POLICY.search(title) and not WIND.search(title):
        return reject('unrelated_administrative_or_industry_news')
    if not (wind_evidence or media_hint or indirect_official):
        return reject('wind_relevance_not_evidenced')
    if not (REGULATION.search(title + ' ' + excerpt) or media_hint or indirect_official):
        return reject('policy_nature_not_evidenced')
    # A dated policy list item should be discoverable even if its detail page is
    # blocked. Its evidence_type remains directory_listing; no invented excerpt.
    is_media = source.get('source_type') == '政策线索'
    usable_media_report = bool(is_media and len(excerpt) >= 48 and
                               not excerpt.startswith(('政策发布线索：', '已从公开目录采集政策条目：')) and
                               not CHALLENGE_TEXT.search(excerpt))
    listing_only = (not usable_media_report and
                    (item.get('article_evidence_available') is False or len(excerpt) < 28 or
                     bool(CHALLENGE_TEXT.search(excerpt))))
    if listing_only and not is_domestic:
        return reject('insufficient_excerpt')
    if listing_only and not (POLICY_HEADLINE.search(title) and
                             (WIND.search(title) or indirect_official or media_hint)):
        return reject('listing_title_needs_more_evidence')
    country = normalize_country(item.get('country') or source.get('country'), region, item.get('province'))
    dimensions = item.get('dimensions') or []
    if not isinstance(dimensions, list):
        dimensions = []
    dimensions = list(dict.fromkeys(string(x) for x in dimensions if string(x)))[:6]
    day = valid_day(item.get('published_at'))
    if not day:
        # Keep undated/future documents in raw review data, not the dated policy feed.
        return reject('missing_invalid_or_future_publication_date')
    # Do not replace missing official publication dates with scrape/issued/effective dates.
    content_hash = string(item.get('content_hash')) or hashlib.sha256(
        (title + '\n' + (day or '') + '\n' + excerpt).encode('utf-8')).hexdigest()
    ai_entry = (ai_cache.get(url) or {}) if isinstance(ai_cache, dict) else {}
    verified_ai = (ai_entry.get('content_hash') == content_hash and
                   ai_entry.get('status') == 'completed')
    ai = ai_entry.get('result', {}) if verified_ai else {}
    if not isinstance(ai, dict):
        ai = {}
    ai_dimensions = ai.get('dimensions') if verified_ai else []
    if isinstance(ai_dimensions, list):
        dimensions = list(dict.fromkeys(dimensions + [string(d) for d in ai_dimensions if string(d)]))[:6]
    # Rule guidance is shown as conditional text, never as a confirmed legal requirement.
    design = string(ai.get('product_design_impact')) if verified_ai else ''
    design = design or string(item.get('impact_design') or item.get('product_impact'))
    if not design:
        design = '当前节选尚不足以确认对机组设计的直接要求；需核对适用主体、设计标准、测试认证与并网条件。'
    business = string(item.get('impact_business') or item.get('commercial_impact'))
    review = string(item.get('verification_status') or item.get('evidence_status')) or '效力和适用范围待核对'
    if indirect_official:
        review = '该官方文件涉及新能源、电价或电力市场，但是否适用于风电尚待核对正文。' + review
    if media_hint and not wind_evidence:
        review = '行业媒体报道；风电具体适用性尚未核实，须追溯官方原文。' + review
    if listing_only:
        review = '政策已直接收录展示；仅取得标题、日期、出处，正文待补充；' + review
        excerpt = '已收录目录条目：' + title + '。正文尚未取得，点击来源可查看对应发布页面。'
    evidence_type = 'directory_listing' if listing_only else ('media_report' if source.get('source_type') == '政策线索' else 'article_text')
    importance = item.get('importance') or {}
    score = importance.get('score') if isinstance(importance, dict) else None
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        score = item.get('importance_score')
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        score = None
    result = {
        'id': string(item.get('id')) or hashlib.sha256(url.encode()).hexdigest()[:18],
        'title': title[:240], 'url': url, 'published_at': day,
        'date_evidence': string(item.get('date_evidence')) or '发布日期依据待核对',
        'region': region, 'country': country, 'source_name': string(item.get('source_name') or source.get('name')),
        'doc_type': ('媒体政策（官方原文待补充）' if listing_only and is_media
                     else '政策文件（正文待补充）' if listing_only
                     else '新能源/电力政策（风电适用性待核对）' if indirect_official
                     else ('媒体政策报道' if usable_media_report
                           else ('政策文件' if is_domestic and '候选' in string(item.get('doc_type') or item.get('document_type'))
                                 else string(item.get('doc_type') or item.get('document_type')) or '政策文件'))),
        'evidence_type': evidence_type,
        'validity_status': string(item.get('validity_status') or item.get('document_status')) or '效力待核验',
        'verification_status': review, 'source_excerpt': excerpt,
        'dimensions': dimensions,
        'impact_design': design[:850], 'impact_business': business[:600],
        'next_step': string(item.get('next_step')) or '核对官方全文、发布日期、法律效力及产品适用范围。',
        'analysis_method': '已收录·AI辅助业务影响分析' if verified_ai else '已收录·规则辅助业务影响分析',
        'ai_application_note': string(ai.get('application_note')) if verified_ai else '',
        'content_hash': content_hash, 'importance_score': score,
        'importance_level': string(importance.get('priority') if isinstance(importance, dict) else item.get('priority')),
        'design_relevance': sum(any(term in d for term in DESIGN_TERMS) for d in dimensions),
        'clauses': item.get('clauses', []) if isinstance(item.get('clauses'), list) else [],
    }
    return result


def build(root=ROOT):
    root = Path(root)
    data = root / 'site' / 'data'
    sources = read(root / 'policy_sources.json', [])
    dims = read(root / 'regulatory_dimensions.json', [])
    raw = read(data / 'policies.json', [])
    cache = read(data / 'policy_ai.json', {})
    if isinstance(cache, dict):
        cache = cache.get('analyses', {})
    else:
        cache = {}
    source_map = {s['id']: s for s in sources if isinstance(s, dict) and 'id' in s}
    chosen = {}
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        url = safe_url(item.get('url'))
        if url and (url not in chosen or record_score(item) > record_score(chosen[url])):
            chosen[url] = item
    records, visibility = [], []
    for item in chosen.values():
        reasons = []
        record = normalize_policy(item, source_map, cache, rejection_notes=reasons)
        visibility.append({
            '来源ID': string(item.get('source_id')),
            '政策标题': string(item.get('title')),
            '发布日期': string(item.get('published_at')),
            '原文链接': safe_url(item.get('url')),
            '是否展示': '是' if record else '否',
            '展示/排除原因': ((record.get('doc_type') or 'policy_document') if record else
                             '; '.join(reasons) or 'other'),
        })
        if record:
            records.append(record)
    with (data / 'policy_display_decisions.csv').open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['来源ID', '政策标题', '发布日期', '原文链接', '是否展示', '展示/排除原因'])
        writer.writeheader()
        writer.writerows(visibility)
    records.sort(key=lambda r: (r['published_at'], r['title']), reverse=True)
    save(data / 'policies_display.json', records)
    public_sources = [dict(src, region=canonical_region(src.get('region'))) for src in sources if isinstance(src, dict)]
    save(data / 'policy_source_registry.json', public_sources)
    # Previous site releases used another ID namespace (policy_001...), whereas
    # the active crawler uses cn_*/intl_* modules. Bring historical states forward
    # by an explicit URL-checked alias table, without claiming a fresh crawl.
    aliases = read(root / 'legacy_policy_source_aliases.json', {})
    stored_statuses = read(data / 'policy_source_status.json', [])
    canonical_ids = {src['id'] for src in public_sources}
    migrated = []
    for status in stored_statuses if isinstance(stored_statuses, list) else []:
        if not isinstance(status, dict):
            continue
        prev = status.get('id')
        actual = aliases.get(prev, prev) if isinstance(aliases, dict) else prev
        if actual not in canonical_ids:
            continue
        new_status = dict(status, id=actual)
        if actual != prev:
            new_status['historical_source_id'] = prev
            new_status['status_origin'] = '上一版来源状态，待新抓取更新'
            new_status['message'] = '上一版检测（非本版重新抓取）：' + string(status.get('message') or status.get('status_message') or status.get('status'))
        migrated.append(new_status)
    if migrated and len({s['id'] for s in migrated}) == len(migrated):
        save(data / 'policy_source_status.json', migrated)
    save(data / 'regulatory_dimensions.json', dims)
    with (data / 'policies.csv').open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(dict(zip(CSV_FIELDS, [r['published_at'] or '待核实', r['title'], r['country'],
                r['source_name'], r['source_excerpt'], '、'.join(r['dimensions']),
                r['impact_design'], r['impact_business'], r['verification_status'], r['url']])))
    print(f'Display data generated: {len(records)} wind policy records, {len(sources)} configured sources; raw input retained.')
    return records


if __name__ == '__main__':
    build()
