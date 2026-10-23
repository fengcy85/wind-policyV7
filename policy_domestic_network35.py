"""Offline-audited fallback routes for the 2026-10-18 network-failed sources.

Original issuers and URLs are preserved. Alternate publisher lists are used for
supplementary discovery only; they NEVER validate the original source's cursor.
No login, CAPTCHA, cookie spoofing, private endpoints, or access-control bypass.
"""
from __future__ import annotations

from concurrent.futures import Future
from datetime import date
from pathlib import Path
from threading import Lock
from urllib.parse import urljoin, urlsplit
import json
import re

from bs4 import BeautifulSoup

ROUTES = json.loads((Path(__file__).resolve().parent /
                     'diagnostics/network35_official_recovery_routes.json').read_text(encoding='utf-8'))

# A failed official mirror is fetched once per job, not once per agency.
_CACHE = {}
_CACHE_LOCK = Lock()
POLICY_SIGNAL = re.compile(r'\u98ce\u7535|\u98ce\u529b\u53d1\u7535|\u98ce\u5149|\u65b0\u80fd\u6e90|\u7eff\u7535|\u53ef\u518d\u751f\u80fd\u6e90|\u6d77\u4e0a\u98ce|\u5e76\u7f51|\u6d88\u7eb3|\u7535\u529b\u5e02\u573a|\u7535\u4ef7|\u7535\u7f51|\u50a8\u80fd')
LEGAL_SIGNAL = re.compile(r'\u653f\u7b56|\u6cd5\u89c4|\u901a\u77e5|\u516c\u544a|\u6279\u590d|\u529e\u6cd5|\u7ba1\u7406|\u5b9e\u65bd|\u6307\u6807|\u89c4\u5212|\u65b9\u6848|\u516c\u793a|\u5f81\u6c42\u610f\u89c1|\u7ade\u914d|\u7533\u62a5|\u76f8\u5173\u4e8b\u9879|\u6807\u51c6|\u610f\u89c1|\u6587\u4ef6|\u9879\u76ee|\u6e05\u5355|\u89c4\u5b9a|\u6539\u9769')
PAGE_TERMS = {'next', 'next page', '\u4e0b\u4e00\u9875', '\u4e0b\u9875', '\u203a', '\u00bb'}


def cached_public_fetch(url, fetcher):
    with _CACHE_LOCK:
        existing = _CACHE.get(url)
        if existing is None:
            existing = Future()
            _CACHE[url] = existing
            leader = True
        else:
            leader = False
    if leader:
        try:
            result = fetcher(url)
            existing.set_result(result)
        except BaseException as exc:
            existing.set_exception(exc)
    return existing.result()


def _plain(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def _date_from_row(node, parse_date):
    # Do not infer date from document title or a whole parent list.
    markers = node.select('time[datetime],.publish-date,.pubtime,.pubDate,.publish_time,td[class*=date],span[class*=date],span[class*=time]')
    for elem in markers[:6]:
        d = parse_date(elem.get('datetime') or elem.get('content') or elem.get_text(' ', strip=True))
        if d:
            return d
    shadow = BeautifulSoup(str(node), 'html.parser')
    for anchor in shadow.select('a'):
        anchor.decompose()
    text = _plain(shadow.get_text(' ', strip=True))
    if len(text) > 500:
        return ''
    labelled = re.search(r'(?:\u53d1\u5e03\u65e5\u671f|\u516c\u5f00\u65e5\u671f|\u53d1\u5e03\u65f6\u95f4)\s*[:\uff1a]?\s*([0-9]{4}[-./\u5e74][0-9]{1,2}[-./\u6708][0-9]{1,2})', text)
    if labelled:
        return parse_date(labelled.group(1))
    matches = re.findall(r'(?<!\d)(?:20[0-3]\d|2\d)[-./\u5e74][01]?\d[-./\u6708][0-3]?\d\u65e5?(?!\d)', text)
    valid = [d for match in matches if (d := parse_date(match))]
    if not valid:
        return ''
    # Multiple mismatched dates are not evidence of a particular publication date.
    return valid[0] if len(set(valid)) == 1 else ''


def parse_official_backup(html, base, *, parse_date, normalize_url):
    """Find dated document rows without mistaking site menus for policies."""
    soup = BeautifulSoup(html, 'html.parser')
    title = _plain(soup.title.get_text(' ', strip=True)).lower() if soup.title else ''
    if any(x in title for x in ('captcha', 'access denied', '\u5b89\u5168\u9a8c\u8bc1', '\u8bbf\u95ee\u9a8c\u8bc1')):
        return [], [], 'challenge_not_a_document_list'
    known = set()
    rows = []
    for a in soup.select('a[href]'):
        if a.find_parent(['nav', 'header', 'footer', 'aside', 'menu']):
            continue
        headline = _plain(a.get_text(' ', strip=True)) or _plain(a.get('title'))
        if not 7 <= len(headline) <= 180 or not POLICY_SIGNAL.search(headline) or not LEGAL_SIGNAL.search(headline):
            continue
        dest = normalize_url(urljoin(base, a.get('href', '')))
        if not dest or urlsplit(dest).hostname != urlsplit(base).hostname or dest in known:
            continue
        if not re.match(r'^https?://', dest) or re.search(r'\.(?:jpg|jpeg|png|gif|js|css|zip)(?:$|\?)', dest, re.I):
            continue
        node = a
        for parent in list(a.parents)[:5]:
            if parent.name in ('li', 'tr', 'article'):
                node = parent
                break
            if parent.name in ('html', 'body', 'main', 'nav', 'footer', 'header'):
                break
            if (parent.name in ('div', 'p', 'section') and
                len(parent.select('a[href]')) <= 2 and len(_plain(parent.get_text(' ',strip=True))) <= 500):
                node = parent
        publish = _date_from_row(node, parse_date)
        if not publish:
            continue
        known.add(dest)
        rows.append({'title': headline, 'url': dest, 'date': publish,
                     'rank': 8 if '\u98ce\u7535' in headline else 4})
    next_urls = []
    for a in soup.select('a[href]'):
        text = _plain(a.get_text(' ', strip=True)).lower()
        if not (text in PAGE_TERMS or a.get('rel') == ['next']):
            continue
        href = (a.get('href') or '').strip()
        if href.startswith(('#', 'javascript:')):
            continue
        url = normalize_url(urljoin(base, href))
        if url and url != base and urlsplit(url).hostname == urlsplit(base).hostname and url not in next_urls:
            next_urls.append(url)
    return rows, next_urls[:1], 'dated_topic_rows' if rows else 'no_dated_wind_policy_rows'


def _from_backup(doc, src, channel, *, detail):
    """Do not attribute another authority's documents to the failed publisher."""
    copy = dict(doc)
    copy['source_id'] = src['id']
    copy['source_name'] = channel['publisher_host'] + ' (official supplementary channel)'
    copy['discovery_channel'] = 'official_cross_publisher_recovery'
    copy['original_failed_source_name'] = src['name']
    copy['original_failed_url'] = src['url']
    copy['recovery_directory_url'] = channel['url']
    copy['recovery_document_scope'] = 'complementary_only_not_equivalent'
    copy['article_evidence_available'] = bool(detail and doc.get('article_evidence_available'))
    copy['verification_status'] = (
        '\u5b98\u65b9\u5907\u7528\u6765\u6e90\u53d1\u73b0\uff1b\u539f\u90e8\u95e8\u76ee\u5f55\u65f6\u95f4\u8986\u76d6\u5c1a\u672a\u6838\u9a8c\uff1b\u8bf7\u6309\u6587\u4ef6\u771f\u5b9e\u53d1\u5e03\u673a\u6784\u6838\u5bf9'
        if detail else '\u5b98\u65b9\u5907\u7528\u76ee\u5f55\u7ebf\u7d22\uff1b\u672a\u53d6\u5f97\u5b8c\u6574\u6b63\u6587\uff1b\u4e0d\u4ee3\u8868\u539f\u673a\u5173\u76ee\u5f55\u8986\u76d6'
    )
    return copy


def recover_failed_domestic_source(src, cutoff, dims, manual, *, fetcher, parse_date,
                                   normalize_url, make_record, listing_only_lead, renderer=None,
                                   max_pages_per_channel=2, max_details=3):
    """Return (documents, diagnostics); upstream preserves the original failure.

    The pre-fixed Shanxi energy bureau is protected and never invoked here.
    Only sources with baseline connection failures have recovery routes.
    """
    contract = ROUTES.get(src.get('id'))
    if not contract or contract.get('protected_previous_fix'):
        return [], {'status': 'skipped_prior_fix', 'attempts': []}
    documents = {}
    attempts = []
    budget = max_details
    for channel in contract.get('recovery_channels', [])[:2]:
        if channel['url'] == src['url']:
            continue
        queue = [channel['url']]
        visited = set()
        channel_count = 0
        while queue and len(visited) < max_pages_per_channel:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                body, actual, kind = cached_public_fetch(url, fetcher)
                if kind != 'html' or urlsplit(actual).hostname != urlsplit(url).hostname:
                    raise ValueError('invalid fallback redirect or document kind')
                found, next_urls, evidence = parse_official_backup(
                    body, actual, parse_date=parse_date, normalize_url=normalize_url)
                attempts.append({'url': url, 'status': 'read', 'found_topic_rows': len(found),
                                 'parser_evidence': evidence, 'publisher': channel['publisher_host'],
                                 'evidence_level': channel['evidence']})
                if (not found and evidence == 'no_dated_wind_policy_rows'
                        and channel.get('render_when_empty') and renderer):
                    try:
                        rendered, render_url, render_kind = cached_public_fetch(
                            'browser:'+url, lambda _key: renderer(url))
                        if (render_kind != 'html' or
                                urlsplit(render_url).hostname != urlsplit(url).hostname):
                            raise ValueError('public browser redirected outside official host')
                        browser_found, browser_next, browser_evidence = parse_official_backup(
                            rendered, render_url, parse_date=parse_date, normalize_url=normalize_url)
                        found = browser_found
                        next_urls = browser_next
                        evidence = browser_evidence
                        attempts.append({'url':url,'status':'public_browser',
                                         'found_topic_rows':len(found),
                                         'parser_evidence':evidence,
                                         'publisher':channel['publisher_host']})
                    except Exception as exc:
                        attempts.append({'url':url,'status':'public_browser_failed',
                                         'error':type(exc).__name__+': '+str(exc)[:140]})
            except Exception as exc:
                attempts.append({'url': url, 'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)[:140],
                                 'evidence_level': channel['evidence']})
                break
            for cand in found:
                if cand['date'] < cutoff.isoformat() or cand['date'] > date.today().isoformat():
                    continue
                if cand['url'] in documents:
                    continue
                channel_count += 1
                doc = None
                if budget > 0:
                    budget -= 1
                    try:
                        detail_body, final, detail_kind = cached_public_fetch(cand['url'], fetcher)
                        if urlsplit(final).hostname != urlsplit(cand['url']).hostname:
                            raise ValueError('document redirected outside official publisher')
                        doc, _ = make_record(src, cand, detail_body, final, detail_kind, dims, cutoff, manual)
                    except Exception as exc:
                        attempts.append({'url': cand['url'], 'status': 'detail_pending',
                                         'error': type(exc).__name__ + ': ' + str(exc)[:140]})
                if doc:
                    doc = _from_backup(doc, src, channel, detail=True)
                else:
                    doc = listing_only_lead(src, cand, cutoff, 'alternate_official_detail_pending')
                    if doc:
                        doc = _from_backup(doc, src, channel, detail=False)
                if doc:
                    documents[cand['url']] = doc
            if budget <= 0:
                break
            queue.extend(n for n in next_urls if n not in visited)
        # Only attempt the second channel when the first has no topic documents.
        if documents:
            break
    return list(documents.values()), {
        'status': 'recovered_official_evidence' if documents else 'no_recovery_documents',
        'attempts': attempts,
        'recovered_documents': len(documents),
        'original_source_coverage_verified': False,
    }
