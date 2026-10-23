"""V8.2: public dated policy records are ingested directly, not held in review.

Tests simulate public HTML only; they do not assert that a real runner has network access.
"""
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pathlib import Path
import json
import tempfile
import requests

import policy_scrape as ps
import build_site_data as display

SRC = next(s for s in ps.read(ps.SOURCES,[]) if s['name']=='北京市发展和改革委员会')
NDRC = next(s for s in ps.read(ps.SOURCES,[]) if s['id']=='cn_09b62684b798')
BJX = next(s for s in ps.read(ps.SOURCES,[]) if s['id']==ps.MEDIA_SOURCE_ID)
D = date.today() - timedelta(days=1)
DAY = D.isoformat()


def page_html(title, link, when=DAY):
    return f'<main><ul class="list"><li><a href="{link}">{title}</a><span class="date">{when}</span></li></ul></main>'


class DirectRecordTests(unittest.TestCase):
    def test_official_dated_document_stored_even_when_detail_budget_exhausted(self):
        root=SRC['url']
        first='https://fgw.beijing.gov.cn/zfxxgk/detail1.html'
        second='https://fgw.beijing.gov.cn/zfxxgk/detail2.html'
        t1='关于风电场项目建设和并网管理的通知'
        t2='关于新能源项目上网电价和交易规则的通知'
        html=(f'<main><ul class="list"><li><a href="{first}">{t1}</a><span class="date">{DAY}</span></li>'
              f'<li><a href="{second}">{t2}</a><span class="date">{DAY}</span></li></ul></main>')
        def fetch(url):
            if url == root:return html, root, 'html'
            raise requests.ConnectionError('detail request denied')
        with patch.object(ps,'adapter_urls',return_value=[root]),\
             patch.object(ps,'fetch',side_effect=fetch),\
             patch.object(ps,'MAX_DETAILS',1),\
             patch.object(ps,'BROWSER_ENABLED',False):
            docs,_,status=ps.scrape_one(SRC,[],D-timedelta(days=20),{})
        self.assertEqual(len(docs),2, 'both dated records enter the feed before details')
        self.assertEqual(status['status'],'ok_with_results')
        self.assertTrue(all(x['published_at']==DAY for x in docs))
        self.assertTrue(all(not x['article_evidence_available'] for x in docs))
        self.assertTrue(all('候选' not in x['doc_type'] for x in docs))
        self.assertTrue(status['detail_limit_hit'])

    def test_domestic_body_with_no_business_dimensions_is_stored(self):
        title='关于风电项目管理办法的通知'
        url='https://fgw.beijing.gov.cn/zfxxgk/2026/wind-policy.html'
        html=('<html><head><meta name="publishdate" content="'+DAY+'"></head><body>'
              '<h1>'+title+'</h1><div id="UCAP-CONTENT">'
              +('为了促进风电产业高质量发展，制定以下新能源项目建设管理规定。'*7)
              +'</div></body></html>')
        obj,reason=ps.make_record(SRC,{'title':title,'date':DAY,'url':url},html,url,'html',[],D-timedelta(days=10),{})
        self.assertIsNotNone(obj,reason)
        self.assertEqual(obj['dimensions'],[])
        self.assertTrue(obj['article_evidence_available'])
        self.assertNotIn('候选',obj['doc_type'])
        self.assertIn('风电',obj['source_excerpt'])

    def test_document_record_is_directly_shown_by_display_builder(self):
        title='关于风电场项目建设和并网管理的通知'
        link='https://fgw.beijing.gov.cn/wind-direct.html'
        record=ps.listing_only_lead(SRC,{'title':title,'date':DAY,'url':link},D-timedelta(days=21))
        self.assertIsNotNone(record)
        obj=display.normalize_policy(record,{SRC['id']:SRC},{})
        self.assertIsNotNone(obj)
        self.assertEqual(obj['evidence_type'],'directory_listing')
        self.assertTrue(obj['published_at'])
        self.assertNotIn('候选',obj['doc_type'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'site/data').mkdir(parents=True)
            (root/'policy_sources.json').write_text(json.dumps([SRC],ensure_ascii=False),encoding='utf-8')
            (root/'site/data/policies.json').write_text(json.dumps([record],ensure_ascii=False),encoding='utf-8')
            actual=display.build(root)
            self.assertEqual(len(actual),1)
            self.assertEqual(actual[0]['url'],link)

    def test_indirect_renewable_official_policy_is_directly_displayed(self):
        title='关于完善新能源发电机制电价和绿电直连的通知'
        link='https://fgw.beijing.gov.cn/zc/new-energy-pricing.html'
        rec=ps.listing_only_lead(SRC,{'title':title,'date':DAY,'url':link},D-timedelta(days=9))
        self.assertIsNotNone(rec)
        self.assertIsNotNone(display.normalize_policy(rec,{SRC['id']:SRC},{}))

    def test_bjx_report_is_displayed_without_reclassifying_as_official_law(self):
        title='江苏省风电项目开发与并网政策实施细则发布'
        link='https://news.bjx.com.cn/html/20261019/2026000.shtml'
        rec=ps.listing_only_lead(BJX,{'title':title,'date':DAY,'url':link},D-timedelta(days=15))
        self.assertIsNotNone(rec)
        entry=display.normalize_policy(rec,{BJX['id']:BJX},{})
        self.assertIsNotNone(entry)
        self.assertIn('媒体',entry['doc_type'])
        self.assertEqual(entry['evidence_type'],'directory_listing')
        self.assertIn('官方原文',entry['verification_status'])

    def test_ndrc_wap_official_dates_and_urls_from_public_example(self):
        html='''<ul>
        <li><a href="/xxgk/zcfb/tz/202610/t20261016_1408179.html">关于进一步完善价格形成机制推动普惠养老服务的指导意见</a>2026/10/16</li>
        <li><a href="/xxgk/zcfb/tz/202608/t20260803_1406883.html">关于印发新型电力系统建设十五五规划的通知</a>2026/08/03</li>
        </ul>'''
        result=ps._listing_page(html,NDRC['url'],ps.load_adapter(NDRC))
        self.assertEqual(result['dated_rows'],2)
        self.assertEqual(len(result['links']),2)
        self.assertEqual(result['links'][0]['date'],'2026-10-16')
        self.assertNotIn('date from headline',result['row_structure_evidence'])

    def test_ndrc_four_official_static_channels_accumulate_direct_records(self):
        from policy_scrape import adapter_urls
        configured=adapter_urls(NDRC)
        self.assertEqual(len(configured),4)
        self.assertTrue(all('/xxgk/zcfb/' in url and 'wap_index.html' in url for url in configured))
        t1='关于新能源发电电价与绿色电力交易规则的通知'
        t2='关于风电产业管理的规范性文件'
        notice='https://www.ndrc.gov.cn/xxgk/zcfb/tz/202610/t20261018_1408888.html'
        normative='https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202610/t20261018_1408899.html'
        listings={
            configured[0]:page_html(t1,notice),
            configured[1]:page_html(t2,normative),
            configured[2]:'<main>本月暂无相关通知</main>',
            configured[3]:'<main>本月暂无相关规划</main>',
        }
        def fetch(url):
            if url in listings:return listings[url],url,'html'
            raise requests.ConnectionError('detail inaccessible')
        with patch.object(ps,'fetch',side_effect=fetch),patch.object(ps,'BROWSER_ENABLED',False):
            docs,_,status=ps.scrape_one(NDRC,[],D-timedelta(days=10),{})
        self.assertEqual({x['url'] for x in docs},{notice,normative})
        self.assertEqual(status['status'],'ok_with_results')
        self.assertTrue(status['listing_parse_ok'])
        self.assertEqual(len(docs),2)

    def test_foreign_record_gate_not_changed(self):
        foreign=next(s for s in ps.read(ps.SOURCES,[]) if s['region'] != '中国')
        title='Wind power regulation 2026'
        url=foreign['url']
        self.assertNotEqual(foreign.get('region'),'中国')
        # No mainland shortcuts in foreign storage or review flow.
        with patch.object(ps,'get_dim_refs',return_value=[]),patch.object(ps,'extract_detail',return_value=(title,'Wind power regulation and licensing '*12)),\
             patch.object(ps,'publication_date',return_value=DAY):
            doc,reason=ps.make_record(foreign,{'title':title,'date':DAY,'url':url},'html',url,'html',[],D-timedelta(days=7),{})
        self.assertIsNone(doc)
        self.assertIn('18维度',reason)

if __name__=='__main__':unittest.main()
