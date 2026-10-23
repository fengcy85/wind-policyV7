"""Deterministic recovery contract tests; not live-government-network tests."""
import unittest
from datetime import date
from unittest.mock import patch
from urllib.parse import urljoin

import policy_scrape as ps
import policy_domestic_network35 as r

SOURCES = {s['id']: s for s in ps.read(ps.SOURCES, [])}
HTML = '''<html><head><title>政府正式文件目录</title></head><body>
<nav><a href='/menu'>关于风电发展的管理办法</a></nav>
<ul class='news'>
<li><a href='/2026/10/wind_notice.html'>关于海上风电项目开发建设管理的通知</a><span class='publish-date'>2026-10-12</span></li>
<li><a href='/2026/10/wind_price.html'>关于推动新能源绿电直连市场改革的通知</a><time datetime='2026-10-09'>2026-10-09</time></li>
<li><a href='/2026/10/no_date.html'>关于风电建设管理办法的通知</a></li>
<li><a href='/2026/10/old.html'>关于风电项目建设的批复</a><span>2025-09-05</span></li>
<li><a href='/2026/10/plain.html'>动态公告信息</a><span>2026-10-11</span></li>
</ul><a href='list_2.html' title='下一页'>下一页</a>
</body></html>'''


class Network35RecoveryTests(unittest.TestCase):
    def setUp(self):
        with r._CACHE_LOCK:
            r._CACHE.clear()

    def test_exactly_35_original_failed_ids_and_prior_shanxi_guard(self):
        self.assertGreaterEqual(len(r.ROUTES), 35)
        self.assertIn('cn_17bffa52408e',r.ROUTES)
        self.assertIn('cn_09b66c7ebd13',r.ROUTES)
        self.assertEqual(sum(bool(c.get('protected_previous_fix')) for c in r.ROUTES.values()), 1)
        self.assertTrue(r.ROUTES['cn_0cedc4affbe8']['protected_previous_fix'])
        self.assertTrue(all(SOURCES[k]['region']=='中国' for k in r.ROUTES))
        self.assertTrue(all(any(c['url'] for c in val['recovery_channels'])
                            for val in r.ROUTES.values() if not val.get('protected_previous_fix')))

    def test_recovery_channels_are_official_distinct_hosts(self):
        from urllib.parse import urlparse
        for sid, contract in r.ROUTES.items():
            for chan in contract['recovery_channels']:
                with self.subTest(site=sid):
                    host=urlparse(chan['url']).hostname
                    self.assertTrue(host and host.endswith('.gov.cn'))
                    self.assertNotEqual(chan['url'], SOURCES[sid]['url'])
                    self.assertIn(chan['evidence'], ('public_index_evidence','existing_config_candidate','baseline_verified_source'))
                    self.assertFalse(contract['original_coverage_can_be_proved_by_recovery'])

    def test_dated_rows_and_relative_policy_links(self):
        rows, pages, note = r.parse_official_backup(HTML,'https://fgw.hunan.gov.cn/xxgk/list.html',
            parse_date=ps.parse_date, normalize_url=ps.normalize_url)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['date'], '2026-10-12')
        self.assertEqual(rows[1]['date'], '2026-10-09')
        self.assertEqual(pages, ['https://fgw.hunan.gov.cn/xxgk/list_2.html'])
        self.assertEqual(note, 'dated_topic_rows')

    def test_navigation_and_undated_rows_not_accepted(self):
        rows, pages, reason = r.parse_official_backup(
            '<html><nav><a href="/rule">关于风电建设的管理办法通知</a></nav>'
            '<ul><li><a href="/rule">关于风电建设的管理办法通知</a></li></ul></html>',
            'https://www.cq.gov.cn/index.html', parse_date=ps.parse_date, normalize_url=ps.normalize_url)
        self.assertEqual(rows, [])
        self.assertEqual(reason, 'no_dated_wind_policy_rows')

    def test_challenge_is_not_a_policy(self):
        html='<html><title>安全验证</title><ul><li><a href="/x">关于风电建设管理的通知</a><time datetime="2026-10-10">日期</time></li></ul></html>'
        rows,pages,note=r.parse_official_backup(html,'https://www.cq.gov.cn/index.html',
                parse_date=ps.parse_date,normalize_url=ps.normalize_url)
        self.assertEqual(rows, [])
        self.assertEqual(note,'challenge_not_a_document_list')

    def test_different_dates_for_same_row_rejected(self):
        html='<ul><li><a href="/x">关于风电发展管理办法的通知</a>' \
             '<span>2026-10-05 2026-10-09</span></li></ul>'
        rows,_,_=r.parse_official_backup(html,'https://www.cq.gov.cn/index.html',
                parse_date=ps.parse_date,normalize_url=ps.normalize_url)
        self.assertEqual(rows, [])

    def test_only_real_publication_date_label_accepted(self):
        html='<ul><li><a href="/x">关于风电发展管理办法的通知</a>' \
             '<span>成文日期：2026-10-05 发布日期：2026-10-09</span></li></ul>'
        # Date label must be an independently identified element, not merged with an issue date.
        # After safe parser improvements this row may be date-labelled; never choose 10-05.
        rows,_,_=r.parse_official_backup(html,'https://www.cq.gov.cn/index.html',
                 parse_date=ps.parse_date, normalize_url=ps.normalize_url)
        self.assertTrue(not rows or rows[0]['date'] == '2026-10-09')

    def test_recovery_keeps_original_unverified_even_with_full_text(self):
        sid='cn_64dc11b10278'; src=SOURCES[sid]
        base=r.ROUTES[sid]['recovery_channels'][0]['url']
        calls=[]
        def fetch(url):
            calls.append(url)
            if url==base:return HTML,base,'html'
            if url.endswith('wind_notice.html') or url.endswith('wind_price.html'):
                return '<html><h1>风电建设管理通知</h1><p>正式文件正文。</p></html>',url,'html'
            raise ConnectionError('outbound route unavailable')
        def make_record(src, cand, html, final, kind, dims, cutoff, manual):
            return {'id':'id_'+final.rsplit('/',1)[-1], 'title':cand['title'],'url':final,'published_at':cand['date'],
                    'source_id':src['id'],'source_name':src['name'],'article_evidence_available':True},''
        with patch.object(r, 'listing_only_lead', create=True):
            out, report=r.recover_failed_domestic_source(
                src,date(2026,10,1),[],{},fetcher=fetch,parse_date=ps.parse_date,
                normalize_url=ps.normalize_url,make_record=make_record,
                listing_only_lead=lambda src,cand,cutoff,why:None,max_details=3)
        self.assertEqual(len(out),2)
        self.assertFalse(report['original_source_coverage_verified'])
        self.assertEqual(report['status'],'recovered_official_evidence')
        self.assertTrue(all(x['discovery_channel']=='official_cross_publisher_recovery' for x in out))
        self.assertTrue(all(x['original_failed_source_name']==src['name'] for x in out))
        self.assertTrue(all('official supplementary channel' in x['source_name'] for x in out))

    def test_hunan_public_browser_when_static_shell_has_no_rows(self):
        sid='cn_64dc11b10278';src=SOURCES[sid]
        base=r.ROUTES[sid]['recovery_channels'][0]['url']
        calls=[]
        def fetch(url):
            if url==base:return '<html><title>通知公告</title><ul></ul></html>',base,'html'
            raise ConnectionError('simulated blocked full article')
        def renderer(url):
            calls.append(url)
            return HTML,url,'html'
        items,report=r.recover_failed_domestic_source(
            src,date(2026,10,1),[],{},fetcher=fetch,renderer=renderer,
            parse_date=ps.parse_date,normalize_url=ps.normalize_url,
            make_record=lambda *a:(None,''),
            listing_only_lead=lambda src,cand,cutoff,why: {
                'id':cand['url'],'url':cand['url'],'title':cand['title'],
                'published_at':cand['date'],'article_evidence_available':False
            } if 'wind' in cand['url'] else None)
        self.assertEqual(calls,[base])
        self.assertTrue(items)
        self.assertEqual(report['status'],'recovered_official_evidence')
        self.assertTrue(any(x['status']=='public_browser' for x in report['attempts']))
        self.assertFalse(report['original_source_coverage_verified'])

    def test_fallback_error_does_not_claim_success(self):
        sid='cn_64dc11b10278';src=SOURCES[sid]
        def always_fail(url):raise ConnectionError('network is unreachable')
        items, diag=r.recover_failed_domestic_source(
            src, date(2026,10,1), [], {}, fetcher=always_fail,
            parse_date=ps.parse_date, normalize_url=ps.normalize_url,
            make_record=lambda *a:None,listing_only_lead=lambda *a:None)
        self.assertEqual(items,[])
        self.assertEqual(diag['status'],'no_recovery_documents')
        self.assertTrue(all(x['status']=='failed' for x in diag['attempts']))

    def test_prior_fixed_source_is_not_reprocessed(self):
        src=SOURCES['cn_0cedc4affbe8']
        items,diag=r.recover_failed_domestic_source(
            src,date(2026,10,1),[],{},fetcher=lambda url: self.fail('protected source fetched'),
            parse_date=ps.parse_date,normalize_url=ps.normalize_url,
            make_record=lambda *a:None,listing_only_lead=lambda *a:None)
        self.assertEqual(items,[])
        self.assertEqual(diag['status'],'skipped_prior_fix')

    def test_previously_fixed_original_scraper_never_attempts_backup(self):
        src=SOURCES['cn_0cedc4affbe8']
        with patch.object(ps,'_try_entry',side_effect=lambda url,adapter,main,attempts: (
                attempts.append({'url':url,'status':'failed','error_code':'connection_error','error':'network'}),None)[1]),\
             patch.object(ps,'recover_failed_domestic_source',side_effect=AssertionError('no backup for previously repaired sources')):
            _,_,st=ps.scrape_one(src,[],date(2026,10,1),{})
        self.assertNotIn('official_recovery',st)

    def test_out_of_window_not_accepted(self):
        sid='cn_64dc11b10278';src=SOURCES[sid]
        base=r.ROUTES[sid]['recovery_channels'][0]['url']
        def fetch(url):
            if url==base:return HTML,base,'html'
            raise ConnectionError('not needed')
        items,diag=r.recover_failed_domestic_source(
            src,date(2026,10,17),[],{},fetcher=fetch,parse_date=ps.parse_date,
            normalize_url=ps.normalize_url,make_record=lambda *a:(None,''),
            listing_only_lead=lambda *a: self.fail('old document should be skipped'))
        self.assertEqual(items,[])
        self.assertEqual(diag['status'],'no_recovery_documents')

    def test_source_gate_triggers_and_does_not_advance_checkpoint(self):
        sid='cn_64dc11b10278';src=SOURCES[sid]
        attempts=[]
        def fake_entry(url,*args,**kwargs):
            attempts.append(url)
            return None
        def fake_recovery(src,*args,**kwargs):
            return ([{'id':'one','title':'有关风电管理的政策','url':'https://fgw.hunan.gov.cn/document1.html'}],
                    {'status':'recovered_official_evidence','original_source_coverage_verified':False})
        with patch.object(ps,'_try_entry',side_effect=lambda url,adapter,main,a: (
                a.append({'url':url,'status':'failed','error_code':'connection_error','error':'Network unreachable'}),None)[1]),\
             patch.object(ps,'recover_failed_domestic_source',side_effect=fake_recovery):
            items,reviews,status=ps.scrape_one(src,[],date(2026,10,1),{})
        self.assertEqual(len(items),1)
        self.assertEqual(status['status'],'ok_with_results')
        self.assertTrue(status['fetch_success'])
        self.assertFalse(status['listing_parse_ok'])
        self.assertTrue(status['recovery_only'])
        self.assertIsNone(status['coverage_complete'])
        self.assertIsNone(status['listing_coverage_complete'])
        cp=ps.advance_checkpoint(ps.make_checkpoint(src,None,date(2026,10,18)),status,date(2026,10,18))
        self.assertFalse(cp['initialized'])

    def test_original_http_failure_kept_if_backup_empty(self):
        sid='cn_64dc11b10278';src=SOURCES[sid]
        with patch.object(ps,'_try_entry',side_effect=lambda url,adapter,main,a: (
                a.append({'url':url,'status':'failed','error_code':'connection_error','error':'network unavailable'}),None)[1]),\
             patch.object(ps,'recover_failed_domestic_source',return_value=([],{'status':'no_recovery_documents'})):
            _,_,st=ps.scrape_one(src,[],date(2026,10,1),{})
        self.assertEqual(st['status'],'connection_error')
        self.assertEqual(st['official_recovery']['status'],'no_recovery_documents')


if __name__=='__main__':
    unittest.main()
