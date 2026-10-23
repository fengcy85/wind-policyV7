"""V8 offline behavior contracts; no real-site access is implied by test success."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
import unittest
import requests

import policy_scrape as crawl
from policy_quality_summary import write_quality_summary

SOURCE = next(x for x in crawl.read(crawl.SOURCES, []) if x['name'] == '北京市发展和改革委员会')
OVERSEAS = next(x for x in crawl.read(crawl.SOURCES, []) if x.get('region') != '中国')
NOW = date.today()
NEW = (NOW-timedelta(days=1)).isoformat()
ISSUED = (NOW-timedelta(days=4)).isoformat()
OLD = (NOW-timedelta(days=50)).isoformat()
ROOT = SOURCE['url']
HOST = 'fgw.beijing.gov.cn'
DETAIL = f'https://{HOST}/fgwzwgk/2024zcwj/001.html'
TITLE = '关于风电项目并网和风电设备认证的通知'


def row_html(date_value=NEW, *, other='', next_link=''):
    return (f'<main><ul class="list"><li><a href="{DETAIL}">{TITLE}</a>'
            f'<span class="date">{date_value}</span></li></ul>{other}{next_link}</main>')


class RollingCollectionV8(unittest.TestCase):
    def fetch_as(self, pages):
        def fetch(url):
            if url in pages:
                return pages[url], url, 'html'
            raise requests.HTTPError('HTTP 403 Access Denied', response=self._http_response(403))
        return patch.object(crawl, 'fetch', side_effect=fetch)

    @staticmethod
    def _http_response(status):
        response=requests.Response()
        response.status_code=status
        return response

    def test_domestic_rolling_window_does_not_require_initialized_checkpoint(self):
        cp=crawl.make_checkpoint(SOURCE,{},NOW)
        mode,cutoff=crawl.window_for(cp,NOW,domestic=True)
        self.assertEqual(mode,'rolling_30_days')
        self.assertEqual(cutoff,NOW-timedelta(days=crawl.DOMESTIC_LOOKBACK_DAYS-1))
        self.assertFalse(cp['initialized'])

    def test_old_domestic_proof_is_archived_not_reused(self):
        old={'first_seen_on':'2026-09-10','initialized':True,
             'coverage_proof_version':2,'last_verified_date':'2026-10-15',
             'source_url':SOURCE['url']}
        cp=crawl.make_checkpoint(SOURCE,old,NOW)
        self.assertIsNone(cp['last_verified_date'])
        self.assertEqual(cp['legacy_last_verified_date'],'2026-10-15')
        self.assertNotIn('coverage_proof_version',cp)
        self.assertTrue(cp['initialized'])

    def test_foreign_initial_window_is_untouched(self):
        cp=crawl.make_checkpoint(OVERSEAS,{},NOW)
        self.assertEqual(crawl.window_for(cp,NOW,domestic=False)[0],'initial_month')
        cp.update(initialized=True,last_verified_date=(NOW-timedelta(days=4)).isoformat())
        phase,cutoff=crawl.window_for(cp,NOW,domestic=False)
        self.assertEqual(phase,'daily_increment')
        self.assertEqual(cutoff,NOW-timedelta(days=6))

    def test_domestic_checkpoint_no_false_proof_of_full_coverage(self):
        cp=crawl.make_checkpoint(SOURCE,{},NOW)
        after=crawl.advance_checkpoint(cp,{
            'status':'ok_with_results','fetch_success':True,'checked_at':'2026-10-19T01:00:00Z'
        }, NOW,domestic=True)
        self.assertTrue(after['initialized'])
        self.assertEqual(after['crawl_mode'],'rolling_recent_days')
        self.assertIsNone(after['last_verified_date'])
        self.assertNotIn('coverage_proof_version',after)

    def test_domestic_dated_policy_saved_despite_js_pagination(self):
        html=row_html(next_link='<a href="javascript:nextPage(2)">下一页</a>')
        with self.fetch_as({ROOT:html}),patch.object(crawl,'adapter_urls',return_value=[ROOT]),\
             patch.object(crawl,'BROWSER_ENABLED',False):
            docs,_,result=crawl.scrape_one(SOURCE,[],NOW-timedelta(days=29),{})
        self.assertEqual(result['status'],'ok_with_results')
        self.assertTrue(result['listing_parse_ok'])
        self.assertIsNone(result['coverage_complete'])
        self.assertFalse(result['date_coverage_required'])
        self.assertTrue(result['listing_warnings'])
        self.assertEqual(len(docs),1)
        self.assertFalse(docs[0]['article_evidence_available'])
        self.assertTrue(any(x.get('error_code')=='http_403' for x in result['attempts']))

    def test_domestic_valid_listing_without_wind_records_is_not_failure(self):
        other='<main><ul class="list"><li><a href="https://'+HOST+'/fgwzwgk/2024zcwj/002.html">关于道路维护和县城规划的通知</a><span class="date">'+NEW+'</span></li></ul></main>'
        with self.fetch_as({ROOT:other}),patch.object(crawl,'adapter_urls',return_value=[ROOT]),\
             patch.object(crawl,'BROWSER_ENABLED',False):
            docs,_,result=crawl.scrape_one(SOURCE,[],NOW-timedelta(days=29),{})
        self.assertEqual(len(docs),0)
        self.assertEqual(result['status'],'ok_no_recent')
        self.assertTrue(result['listing_parse_ok'])

    def test_domestic_issue_date_never_wins_over_labeled_publication_date(self):
        html=(f'<main><table><tr><td><a href="{DETAIL}">{TITLE}</a></td>'
              f'<td>成文日期：{ISSUED}</td><td>发布日期：{NEW}</td></tr></table></main>')
        record=crawl._listing_page(html,ROOT,crawl.load_adapter(SOURCE))
        self.assertEqual(record['dated_rows'],1)
        self.assertEqual(record['links'][0]['date'],NEW)

    def test_domestic_date_in_article_headline_not_accepted(self):
        html=f'<ul class="list"><li><a href="{DETAIL}">{NEW} {TITLE}</a></li></ul>'
        record=crawl._listing_page(html,ROOT,crawl.load_adapter(SOURCE))
        self.assertEqual(record['dated_rows'],0)

    def test_shandong_official_entry_has_issuer_date_warning(self):
        source=next(x for x in crawl.read(crawl.SOURCES,[]) if x['id']=='cn_fdb9ab86c4a9')
        adapter=crawl.load_adapter(source)
        self.assertTrue(source['url'].startswith('https://gb.shandong.gov.cn/'))
        self.assertEqual(adapter.config['official_url'],source['url'])
        self.assertIn('www.shandong.gov.cn',adapter.config['allowed_detail_hosts'])

    def test_official_central_and_media_search_entries_are_specific(self):
        sources={x['id']:x for x in crawl.read(crawl.SOURCES,[])}
        self.assertIn('/zhengce/zhengceku/bmwj/home.htm',sources['cn_d4013c1b2a1e']['url'])
        self.assertEqual(sources['cn_b637baec056a']['url'],'https://www.cnenergynews.cn/search')
        self.assertTrue(crawl.load_adapter(sources['cn_b637baec056a']).config['needs_browser_ui'])

    def test_media_full_text_does_not_claim_official_legal_verification(self):
        source=next(x for x in crawl.read(crawl.SOURCES,[]) if x['source_type']=='政策线索')
        candidate={'title':TITLE,'url':source['url'].rstrip('/')+'/article/test',
                   'date':NEW,'rank':9}
        lead=crawl.listing_only_lead(source,candidate,NOW-timedelta(days=29))
        self.assertIsNotNone(lead)
        self.assertFalse(lead['article_evidence_available'])
        self.assertIn('待',lead['verification_status'])

    def test_previous_official_full_text_survives_later_detail_denial(self):
        old={'id':'p_test','url':DETAIL,'title':TITLE,'published_at':NEW,
             'article_evidence_available':True,'source_id':SOURCE['id'],
             'source_excerpt':'经核实的法规正文'}
        later={'id':'p_test','url':DETAIL,'title':TITLE,'published_at':NEW,
             'article_evidence_available':False,'source_id':SOURCE['id'],
             'source_excerpt':'只有目录链接'}
        combined,stats=crawl.merge_legal_records([old],[later],{SOURCE['id']:SOURCE})
        self.assertEqual(stats['unchanged'],1)
        self.assertEqual(combined[0]['source_excerpt'],'经核实的法规正文')

    def test_domestic_quality_summary_does_not_call_missing_date_coverage_a_failure(self):
        source_state={'name':SOURCE['name'],'status':'ok_with_results','date_coverage_required':False,
                      'listing_parse_ok':True,'found_count':2,'full_text_records_found':1,
                      'checked_at':'2026-10-19T02:00:00Z','listing_warnings':['分页待复核']}
        report=write_quality_summary([source_state],state={'last_run':'2026-10-19','scope':'provincial'})
        self.assertIn('国内目录读取成功：1/1',report)
        self.assertIn('国内发现政策和线索：2',report)
        self.assertIn('无需完整时间覆盖证明',report)


if __name__ == '__main__':unittest.main()

class StoredRecordsAuditV8(unittest.TestCase):
    def test_pre_after_audit_counts_existing_records_without_overwriting_them(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from policy_saved_results_audit import report
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'site/data').mkdir(parents=True)
            (root/'policy_sources.json').write_text(json.dumps([SOURCE,OVERSEAS],ensure_ascii=False),encoding='utf-8')
            records=[{'url':DETAIL,'source_id':SOURCE['id'],'title':TITLE,'published_at':NEW,
                      'article_evidence_available':True}]
            (root/'site/data/policies.json').write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
            (root/'site/data/policy_source_status.json').write_text('[]',encoding='utf-8')
            result=report(root,label='before')
            self.assertEqual(result['scanned_domestic_source_count'],1)
            self.assertEqual(result['all_stored_records'],1)
            self.assertEqual(result['full_text_evidence_records'],1)
            self.assertEqual(records,json.loads((root/'site/data/policies.json').read_text()))
            self.assertTrue((root/'diagnostics/domestic_saved_records_before.csv').exists())
