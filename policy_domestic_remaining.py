"""Targeted parsers for official domestic sites that failed in 2026-10-18 logs.

This file deliberately DOES NOT contain any of the seven V7.1 completed IDs.
Article-path evidence comes from published official document examples, not an
invented 'common government parser'. Publication dates must be independently
visible in the directory row. Nothing here bypasses access restrictions or
claims that GitHub has fetched a live page.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


# Restrict every URL by publisher hostname and documented article path.
# source IDs never change, so historical legal records and crawl cursors survive.
REMAINING_PROFILES = {
    'cn_3c9957b26c3c': (
        'xxgk.jl.gov.cn', r'/zcbm/fgw/xxgkmlqy/20\d{4}/t\d+_\d+\.html',
        'jilin_drc_information_disclosure',
    ),
    'cn_d6be9d4b18a8': (
        'nyj.jl.gov.cn', r'/zwgk/tzgg/20\d{4}/t\d+_\d+\.html',
        'jilin_energy_notice',
    ),
    'cn_687800e62fca': (
        'www.ln.gov.cn', r'/(?:web/)?zwgkx/zfwj/szfwj/(?:\d{4}n/)?\d+/index\.shtml',
        'liaoning_government_separate_publication_date',
    ),
    'cn_e8b37b376677': (
        'www.ln.gov.cn', r'/(?:web/)?zwgkx/zfwj/szfbgtwj/(?:\d{4}n/)?\d+/index\.shtml',
        'liaoning_government_office_publication_date',
    ),
    'cn_c9be69562225': (
        'fgw.ln.gov.cn', r'/fgw/zc/zxzc/\d+/index\.shtml',
        'liaoning_drc_recent_policy',
    ),
    'cn_a85889da2306': (
        'www.nea.gov.cn', r'/20\d{6}/[a-f0-9]{24,}/c\.html',
        'zhejiang_regulator_official_nea_citations',
    ),
    'cn_7beeafa4d326': (
        'www.xizang.gov.cn',
        r'/zwgk/zfxxgk/fdzdgknr/zc/xzgfxwj/20\d{4}/t\d+_\d+\.html',
        'xizang_government_administrative_normative_files',
    ),
    'cn_96f475fd98fa': (
        'www.jiangsu.gov.cn', r'/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html',
        'jiangsu_government_document_iframe',
    ),
    'cn_c37e9b9f7acf': (
        'gxt.jiangsu.gov.cn', r'/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html',
        'jiangsu_industry_policy_documents_iframe',
    ),
    'cn_7239ba11c55b': (
        'drc.gd.gov.cn', r'/(?:gdsnyj/gkmlpt/content/\d+/\d+/|snyj/tzgg/content/)post_\d+\.html',
        'guangdong_energy_disclosure',
    ),
    'cn_385aa60c445a': (
        'www.xinjiang.gov.cn', r'/xinjiang/c112543/20\d{4}/[a-f0-9]{24,}\.shtml',
        'xinjiang_government_publication_column',
    ),
    'cn_2b0fcb94d833': (
        'www.xinjiang.gov.cn', r'/xinjiang/c112545/20\d{4}/[a-f0-9]{24,}\.shtml',
        'xinjiang_government_office_column',
    ),
    'cn_fdb9ab86c4a9': (
        ('www.shandong.gov.cn', 'gb.shandong.gov.cn'), r'(?:/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html|/jpaas-jpolicy-web-server/front/info/declaresource)',
        'shandong_government_documents',
    ),
    'cn_354fb314969b': (
        'gxt.nx.gov.cn', r'/zwgk/fdzdgknr/zcfg/gxtwj/20\d{4}/t\d+_\d+\.html',
        'ningxia_industry_official_documents',
    ),
    'cn_44abb54d7339': (
        'fzggw.nx.gov.cn', r'/zcgh/fgwwj/20\d{4}/t\d+_\d+\.html',
        'ningxia_drc_publication_and_validity',
    ),
    'cn_3a9624d397b1': (
        'drc.xizang.gov.cn', r'/zwgk_1941/xzgfxwj/20\d{4}/t\d+_\d+\.html',
        'xizang_drc_short_dates',
    ),
    'cn_18e109d08abf': (
        'gxt.fujian.gov.cn',
        r'/zwgk/zfxxgk/fdzdgknr/(?:gzdt|gfxwj)/20\d{4}/t\d+_\d+\.htm',
        'fujian_industry_documents',
    ),
}

# Confirmed HTML category evidence is distinct from a verified live adapter.
REMAINING_PROFILES = {
    id: {'host': host, 'path': re.compile(pattern, re.I), 'name': name}
    for id, (host, pattern, name) in REMAINING_PROFILES.items()
}

DUAL_DATE_COLUMNS = frozenset({'cn_687800e62fca', 'cn_e8b37b376677', 'cn_3c9957b26c3c', 'cn_18e109d08abf'})


def _text(x):
    return re.sub(r'\s+', ' ', str(x or '')).strip()


def _article(url, profile):
    try:
        loc = urlsplit(url)
        return (loc.scheme in ('http', 'https') and
                (loc.hostname in profile['host'] if isinstance(profile['host'], tuple) else loc.hostname == profile['host']) and
                bool(profile['path'].fullmatch(loc.path)))
    except ValueError:
        return False


def _publication_in_row(node, anchor, parse_date, *, prefer_last=False):
    """Extract only a row's independent date, never a date in its headline.

    Liaoning and some other public tables show '成文日期' followed by '发布日期'.
    If both dates appear in a single row, the latter (publication date) wins.
    If two dates are present without this supported column structure, fail
    closed instead of guessing.
    """
    # Dedicated table header/labels, then date markers, then stripped row text.
    tagged = []
    for item in node.select('time[datetime],td[class*=date],span[class*=date],'
                            'span[class*=time],.publish-date,.pubtime,.pubDate')[:12]:
        published = parse_date(item.get('datetime') or item.get('content') or item.get_text(' ', strip=True))
        if published:
            tagged.append(published)
    stripped = BeautifulSoup(str(node), 'html.parser')
    for link in stripped.select('a'):
        link.decompose()
    content = _text(stripped.get_text(' ', strip=True))
    if len(content) > 700:
        return ''
    # A labelled publication date has the highest evidential weight.
    labelled = re.search(r'(?:发布日期|发布时间)\s*[:：]?\s*'
                         r'(20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}|2\d[-./]\d{1,2}[-./]\d{1,2})',
                         content)
    if labelled:
        return parse_date(labelled.group(1))
    all_dates = []
    for match in re.finditer(r'(?<!\d)(?:20\d{2}|2\d)[-./年]\d{1,2}[-./月]\d{1,2}日?(?!\d)', content):
        valid = parse_date(match.group())
        if valid:
            all_dates.append(valid)
    if prefer_last and len(all_dates) >= 2:
        return all_dates[-1]
    if len(set(all_dates)) == 1:
        return all_dates[0]
    if len(all_dates) == 1:
        return all_dates[0]
    if tagged and len(set(tagged)) == 1:
        return tagged[0]
    return ''


def _row_for(anchor, profile, base, parse_date, source_id):
    """Find a small container containing exactly one relevant document link."""
    incomplete = None
    for node in list(anchor.parents)[:8]:
        if node.name in ('html', 'body', 'main', 'nav', 'header', 'footer', 'aside', 'menu'):
            break
        if len(_text(node.get_text(' ', strip=True))) > 850:
            continue
        article_links = {
            urljoin(base, a.get('href', ''))
            for a in node.select('a[href]')
            if _article(urljoin(base, a.get('href', '')), profile)
        }
        if len(article_links) != 1:
            continue
        if incomplete is None:
            incomplete = node
        pub = _publication_in_row(node, anchor, parse_date,
                                  prefer_last=source_id in DUAL_DATE_COLUMNS)
        if pub:
            return node, pub
    return incomplete, ''


def domestic_remaining_listing(html, base, adapter, ordinary, *, parse_date, normalize_url):
    """Return a narrowly supported listing or None for original parser.

    The original seven V7.1 profiles and all international domains are never
    inspected by this module.
    """
    profile = REMAINING_PROFILES.get(adapter.id)
    if profile is None:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    seen = set()
    for a in soup.select('a[href]'):
        if a.find_parent(['nav', 'header', 'footer', 'aside', 'menu']):
            continue
        dest = normalize_url(urljoin(base, a.get('href', '')))
        if not dest or dest in seen or not _article(dest, profile):
            continue
        title = _text(a.get_text(' ', strip=True)) or _text(a.get('title'))
        if not 7 <= len(title) <= 190:
            continue
        seen.add(dest)
        node, published = _row_for(a, profile, base, parse_date, adapter.id)
        found.append({'title': title, 'url': dest, 'date': published,
                      'rank': int(bool(re.search('风电|风力|新能源|可再生能源|电力|绿电|并网|电价', title))) * 8,
                      'dom_profile': profile['name']})
    if not found:
        return None
    dates = [row['date'] for row in found if row['date']]
    chronological = all(l >= r for l, r in zip(dates, dates[1:]))
    answer = dict(ordinary)
    answer.update({
        'links': found,
        'selector_matched': True,
        'selectors': ['source-specific:' + profile['name']],
        'dated_rows': len(dates),
        'eligible_rows': len(found),
        'undated_policy_rows': len(found)-len(dates),
        'oldest_date': min(dates) if dates else '',
        'newest_date': max(dates) if dates else '',
        'future_dates': sum(d > date.today().isoformat() for d in dates),
        'chronological': chronological,
        'row_structure_evidence': 'official_specific_article_URL_and_separate_row_date',
        'row_structure_confidence': 'official_article_path',
        'dom_samples': [{
            'title': r['title'][:110], 'url': r['url'], 'date': r['date'],
            'row_tag': '', 'row_class': profile['name'], 'date_field_match': bool(r['date'])
        } for r in found[:12]],
    })
    # Xinjiang exposes paginated public-search listings. A screenshot or
    # browser page-1 response is not proof that 31+ pages were traversed.
    if adapter.id in ('cn_385aa60c445a', 'cn_2b0fcb94d833'):
        raw = _text(soup.get_text(' ', strip=True))
        paged = re.search(r'共\s*\d+\s*页\s*当前第\s*\d+\s*页', raw)
        if paged and not answer.get('next_urls'):
            answer['js_pagination'] = True
            answer['explicit_pagination'] = True
    return answer
