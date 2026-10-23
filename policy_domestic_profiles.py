"""Conservative, site-specific official policy listing extraction.

These profiles describe URL structures corroborated with public official article
pages. They do NOT claim that the HTML DOM has been tested on GitHub Actions.
Dates must appear outside article headline links and pagination is not invented.
Only the named mainland source IDs are affected; international adapters are untouched.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


# An article URL observed on a public page is stronger evidence than arbitrary
# navigation <a> elements. Keep host+path checks specific to each publisher.
DOMESTIC_PROFILES = {
    'cn_61f329f622c8': {
        'host': 'nyj.guizhou.gov.cn',
        'path': re.compile(r'^/zwgk/xxgkml/(?:zdlyxx/xnygl|zcwj_2/jnwj/ptwj_2)/20\d{4}/t\d+_\d+\.html$', re.I),
        'name': 'guizhou_energy_renewables_table',
    },
    'cn_c3d9397ca287': {
        'host': 'fgw.sh.gov.cn',
        'path': re.compile(r'^/fgw_ny/20\d{6}/[0-9a-f]{20,}\.(?:html|htm)$', re.I),
        'name': 'shanghai_drc_energy_policy',
    },
    'cn_b85a8fe9fba8': {
        'host': 'fgw.fujian.gov.cn',
        'path': re.compile(
            r'^/(?:zwgk/fgzd/sfgwgfxwj|zfxxgkzl/zfxxgkzc/gfwjk)/20\d{4}/t\d+_\d+\.(?:htm|html)$',
            re.I,
        ),
        'name': 'fujian_drc_policy_list',
    },
    'cn_eb58eb83050f': {
        'host': 'nyj.nmg.gov.cn',
        'path': re.compile(r'^/slh/zfwj/20\d{4}/t\d+_\d+\.html$', re.I),
        'name': 'inner_mongolia_energy_official',
    },
    'cn_642f1102f38a': {
        'host': 'fzggw.jiangsu.gov.cn',
        'path': re.compile(r'^/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html$', re.I),
        'name': 'jiangsu_drc_normative_documents',
    },
    'cn_0cedc4affbe8': {
        'host': 'nyj.shanxi.gov.cn',
        'path': re.compile(r'^/zfxxgk/fdzdgknr/(?:gg|sjwj)/20\d{4}/t\d+_\d+\.shtml$', re.I),
        'name': 'shanxi_energy_notice',
    },
}

# These exact URLs have been observed as publicly linked category pages.
# Unlike a heuristic "try page 2", no unknown next-page URL is constructed.
KNOWN_PAGES = {
    'https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index.html':
      'https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index_1.html',
    'https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index_1.html':
      'https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index_2.html',
}


def _clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _is_article(url, profile):
    parsed = urlsplit(url)
    return (parsed.scheme in ('http', 'https') and
            parsed.hostname == profile['host'] and
            bool(profile['path'].fullmatch(parsed.path)))


def _row_for_anchor(anchor, profile, base, parse_date):
    """The smallest local record with a separate date, not a whole list."""
    fallback = None
    for node in list(anchor.parents)[:7]:
        if node.name in ('html', 'body', 'main', 'nav', 'header', 'footer', 'aside'):
            break
        # Do not associate a different article's date with this headline.
        article_count = sum(_is_article(urljoin(base, a.get('href', '')), profile)
                            for a in node.select('a[href]'))
        if article_count != 1:
            continue
        if len(_clean(node.get_text(' ', strip=True))) > 950:
            continue
        if fallback is None:
            fallback = node
        clone = BeautifulSoup(str(node), 'html.parser')
        for a in clone.select('a'):
            a.decompose()
        text = _clean(clone.get_text(' ', strip=True))
        published = parse_date(text)
        if published:
            return node, published
    return fallback, ''


def specialized_listing(html, base, adapter, ordinary, *, parse_date, normalize_url):
    """Return strictly selected dated catalogue rows or None for legacy fallback.

    Does not depend on international parsing; record evidence is visible in the
    existing site probe and source-run diagnostics. A valid article without a
    dated sibling remains an *undated* row and cannot verify a full interval.
    """
    profile = DOMESTIC_PROFILES.get(adapter.id)
    if profile is None:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    seen = set()
    for a in soup.select('a[href]'):
        if a.find_parent(['nav', 'header', 'footer', 'aside', 'menu']):
            continue
        target = normalize_url(urljoin(base, a.get('href', '')))
        if not target or not _is_article(target, profile) or target in seen:
            continue
        title = _clean(a.get_text(' ', strip=True)) or _clean(a.get('title'))
        if not 7 <= len(title) <= 190:
            continue
        seen.add(target)
        container, published = _row_for_anchor(a, profile, base, parse_date)
        rows.append({'title': title, 'url': target, 'date': published,
                     'rank': 0, 'dom_profile': profile['name']})
    if not rows:
        return None
    dates = [item['date'] for item in rows if item['date']]
    next_urls = list(ordinary.get('next_urls') or [])
    # Use a known, publicly observed pagination link when ordinary anchor
    # inspection misses it. This does not prove a final page or date coverage.
    known = KNOWN_PAGES.get(base)
    if known and known not in next_urls:
        next_urls = [known]
    ranks = []
    for item in rows:
        # Ranking is only used for detail-fetch priority, never listing proof.
        heading = item['title']
        rank = 10 if re.search(r'风(?:力)?电|风光|风机|风电场|海上风|陆上风', heading) else 0
        rank += 4 if re.search(r'新能源|可再生能源|电力|电价|绿电|并网|能源', heading) else 0
        item['rank'] = rank
        ranks.append(rank)
    # A normative-document archive may show *issue dates* (成文日期) rather
    # than publication dates; do not certify a publication-day time window.
    issue_only = (adapter.id == 'cn_b85a8fe9fba8' and
                  '/zfxxgkzl/zfxxgkzc/gfwjk/' in urlsplit(base).path)
    result = dict(ordinary)
    result.update({
        'links': rows,
        'selector_matched': bool(rows),
        'selectors': [profile['name'] + '+official_article_path+separate_date'],
        'oldest_date': min(dates) if dates else '',
        'newest_date': max(dates) if dates else '',
        'dated_rows': len(dates),
        'eligible_rows': len(rows),
        'undated_policy_rows': len(rows)-len(dates),
        'next_urls': next_urls[:1],
        'explicit_pagination': bool(next_urls) or ordinary.get('explicit_pagination', False),
        'chronological': all(left >= right for left, right in zip(dates, dates[1:])),
        'future_dates': sum(d > date.today().isoformat() for d in dates),
        'row_structure_evidence': 'official_publisher_article_url_with_separate_row_date',
        'row_structure_confidence': 'specific_official_path',
        'date_semantics': 'document_issue_date' if issue_only else 'published_date',
        'dom_samples': [{
            'title': item['title'][:105], 'url': item['url'], 'date': item['date'],
            'row_tag': '', 'row_class': profile['name'],
            'date_field_match': bool(item['date']),
        } for item in rows[:10]],
    })
    return result
