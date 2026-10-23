"""Publication-row parsers for confirmed public government listings.

The public URLs/article paths are supported by current official pages; this module
is not a claim that the GitHub runner can fetch them. No access-control bypass.
Only the explicitly named domestic source IDs are eligible.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

NDRC_ID = 'cn_09b62684b798'
ZHEJIANG_NEA_ID = 'cn_a85889da2306'
LIAONING_IDS = frozenset({'cn_687800e62fca', 'cn_e8b37b376677'})

NDRC_DETAIL = re.compile(r'^/xxgk/zcfb/(?:tz|fzggwl|ghxwj|ghwb)/20\d{4}/t20\d{6}_\d+\.html$', re.I)
ZHEJIANG_NEA_DETAIL = re.compile(r'^/dtyw/tzgg/20\d{4}/t20\d{6}_\d+\.html$', re.I)
LIAONING_DETAIL = re.compile(r'^/(?:web/)?zwgkx/zfwj/(szfwj|szfbgtwj)/(?:20\d{2}n/)?\d+/index\.shtml$', re.I)
FULL_DATE = re.compile(r'(?<!\d)20\d{2}[-./\u5e74]\d{1,2}[-./\u6708]\d{1,2}\u65e5?(?!\d)')


def _plain(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _from_small_row(anchor, parse_date, *, allow_dual=False):
    """Only read text within a row containing a single article link."""
    for node in list(anchor.parents)[:7]:
        if node.name in ('body', 'html', 'main', 'nav', 'header', 'footer', 'aside'):
            break
        if len(node.select('a[href]')) != 1 or len(_plain(node.get_text(' ', strip=True))) > 500:
            continue
        clone = BeautifulSoup(str(node), 'html.parser')
        for a in clone.select('a'):
            a.decompose()
        remaining = _plain(clone.get_text(' ', strip=True))
        labeled = re.search(r'(?:\u53d1\u5e03\u65e5\u671f|\u53d1\u5e03\u65f6\u95f4)\s*[:\uff1a]?\s*('
                            r'20\d{2}[-./\u5e74]\d{1,2}[-./\u6708]\d{1,2})', remaining)
        if labeled and (value := parse_date(labeled.group(1))):
            return value
        # A <time datetime> element can keep its date in an attribute while
        # displaying only '日期' as visible text. This remains independent from
        # the article title, unlike extracting a year inside the headline.
        time_dates = [v for node_ in node.select('time[datetime]')
                      if (v := parse_date(node_.get('datetime', '')))]
        if allow_dual and len(time_dates) >= 2:
            return time_dates[-1]
        if len(set(time_dates)) == 1 and time_dates:
            return time_dates[0]
        dates = [d for match in FULL_DATE.finditer(remaining)
                 if (d := parse_date(match.group(0)))]
        if allow_dual and len(dates) >= 2:
            # Liaoning's heading states 'issue date' before 'publication date'.
            # This is a site-specific fact, not a global two-date assumption.
            return dates[-1]
        if len(set(dates)) == 1 and dates:
            return dates[0]
    return ''


def domestic_official_publication_listing(html, base, adapter, ordinary, *, parse_date, normalize_url):
    if adapter.id not in LIAONING_IDS and adapter.id not in (NDRC_ID, ZHEJIANG_NEA_ID):
        return None
    soup = BeautifulSoup(html, 'html.parser')
    seen, rows = set(), []
    for a in soup.select('a[href]'):
        if a.find_parent(['nav', 'header', 'footer', 'aside', 'menu']):
            continue
        target = normalize_url(urljoin(base, a.get('href', '')))
        if not target or target in seen:
            continue
        loc = urlsplit(target)
        if adapter.id == NDRC_ID:
            if loc.hostname != 'www.ndrc.gov.cn' or not NDRC_DETAIL.fullmatch(loc.path):
                continue
        elif adapter.id == ZHEJIANG_NEA_ID:
            if loc.hostname != 'zjb.nea.gov.cn' or not ZHEJIANG_NEA_DETAIL.fullmatch(loc.path):
                continue
        else:
            match = LIAONING_DETAIL.fullmatch(loc.path)
            intended = 'szfwj' if adapter.id == 'cn_687800e62fca' else 'szfbgtwj'
            if loc.hostname != 'www.ln.gov.cn' or not match or match.group(1) != intended:
                continue
        title = _plain(a.get_text(' ', strip=True)) or _plain(a.get('title'))
        # Zhejiang's notifications list may render the publication date at the
        # end of an anchor's visible text. Recognize only a terminal ISO date.
        heading_date = ''
        if adapter.id == ZHEJIANG_NEA_ID:
            trailing_date = re.search(r'\s(20\d{2}-\d{2}-\d{2})$', title)
            if trailing_date:
                heading_date = parse_date(trailing_date.group(1))
                title = title[:trailing_date.start()].strip()
        if not 7 <= len(title) <= 190:
            continue
        published = _from_small_row(a, parse_date, allow_dual=adapter.id in LIAONING_IDS) or heading_date
        # Publication title/date on the NDRC static list may be adjacent to
        # the same link, but a date *inside a document title* is not evidence.
        if not published and adapter.id == NDRC_ID:
            for sib in list(a.next_siblings)[:3]:
                txt = _plain(sib.get_text(' ', strip=True)) if hasattr(sib, 'get_text') else _plain(sib)
                if len(txt) < 70 and FULL_DATE.fullmatch(txt):
                    published = parse_date(txt)
                    if published:
                        break
        seen.add(target)
        rows.append({'url': target, 'title': title, 'date': published,
                     'rank': 8 if re.search(r'\u98ce\u7535|\u65b0\u80fd\u6e90|\u53ef\u518d\u751f\u80fd\u6e90|\u7535\u529b\u5e02\u573a|\u4e0a\u7f51\u7535\u4ef7', title) else 2})
    if not rows:
        return None
    valid_dates = [r['date'] for r in rows if r['date']]
    result = dict(ordinary)
    result.update({
        'links': rows,
        'selector_matched': True,
        'selectors': ['official_publication_rows:' + ('ndrc_notice' if adapter.id == NDRC_ID else 'zhejiang_nea_notice' if adapter.id == ZHEJIANG_NEA_ID else 'liaoning_separate_publication_date')],
        'eligible_rows': len(rows),
        'dated_rows': len(valid_dates),
        'undated_policy_rows': len(rows) - len(valid_dates),
        'oldest_date': min(valid_dates) if valid_dates else '',
        'newest_date': max(valid_dates) if valid_dates else '',
        'chronological': all(a >= b for a,b in zip(valid_dates, valid_dates[1:])),
        'future_dates': sum(value > date.today().isoformat() for value in valid_dates),
        'dom_samples': [{'title':r['title'], 'date':r['date'], 'url':r['url'], 'row_tag':'article_row',
                         'date_field_match': bool(r['date'])} for r in rows[:10]],
        'row_structure_evidence': 'confirmed_official_directory_article_paths',
        'row_structure_confidence': 'source_specific',
    })
    return result
