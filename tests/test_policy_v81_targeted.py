"""Offline reproduction using representative shapes of publicly indexed pages.

These are parser contracts, NOT a claim of successful live GitHub fetches.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import policy_scrape as crawl
from build_site_data import normalize_policy, build
from policy_failure_diagnosis import classify, write_diagnosis

SOURCES = {s['id']: s for s in crawl.read(crawl.SOURCES, [])}
TODAY = date.today().isoformat()


class DatedPublicDirectoryTests(unittest.TestCase):
    def parse(self, source_id, html):
        src = SOURCES[source_id]
        return crawl._listing_page(html, src['url'], crawl.load_adapter(src))

    def test_ndrc_public_notice_directory_has_dated_policy_row(self):
        html = '''<ul class="list"><li><a href="/xxgk/zcfb/tz/202607/t20260723_1406641.html">关于印发《可再生能源发展“十五五”规划》的通知</a>2026/07/23</li></ul>'''
        r=self.parse('cn_09b62684b798',html)
        self.assertTrue(r['selector_matched'])
        self.assertEqual(len(r['links']),1)
        self.assertEqual(r['links'][0]['date'],'2026-07-23')
        self.assertEqual(r['row_structure_confidence'],'source_specific')

    def test_liaoning_separates_issue_and_publication_dates(self):
        html = '''<table><tr><th>文件名</th><th>成文日期</th><th>发布日期</th></tr>
        <tr><td><a href="/web/zwgkx/zfwj/szfwj/2026n/2026101021205617877/index.shtml">辽宁省人民政府关于发布新的绿色电力发展办法的通知</a></td>
        <td>2026-09-30 21:17</td><td>2026-10-10 21:17</td></tr></table>'''
        r=self.parse('cn_687800e62fca',html)
        self.assertEqual(r['links'][0]['date'],'2026-10-10')
        self.assertTrue(r['selector_matched'])

    def test_liaoning_office_document_path(self):
        html = '''<ul><li><a href="/web/zwgkx/zfwj/szfbgtwj/2026n/20261011123456/index.shtml">辽宁省人民政府办公厅关于有序推进绿电直连建设的通知</a><span>2026-10-11</span></li></ul>'''
        r=self.parse('cn_e8b37b376677',html)
        self.assertEqual(r['links'][0]['date'],'2026-10-11')

    def test_jilin_government_current_document_list_has_dates(self):
        html = '''<ul><li><a href="/zwgk/zcxx/zfwj/202610/t20261016_123.html">吉林省人民政府关于印发新能源发展规划的通知</a><span>2026.10.16</span></li></ul>'''
        r=self.parse('cn_fcdd8a95a7df',html)
        self.assertEqual(SOURCES['cn_fcdd8a95a7df']['url'],'https://www.jl.gov.cn/zcxx/zfwj/wap.html')
        self.assertTrue(r['selector_matched'])
        self.assertEqual(r['links'][0]['date'],'2026-10-16')

    def test_zhejiang_regulator_direct_article_date_in_row(self):
        html = '''<ul><li><a href="/dtyw/tzgg/202609/t20260930_309794.html">关于公开征求《浙江电力市场监管实施办法（征求意见稿）》等意见的公告</a><time datetime="2026-09-30">日期</time></li></ul>'''
        r=self.parse('cn_a85889da2306',html)
        self.assertEqual(r['links'][0]['date'],'2026-09-30')
        self.assertTrue(r['selector_matched'])
        self.assertEqual(SOURCES['cn_a85889da2306']['url'],'https://zjb.nea.gov.cn/dtyw/tzgg/')

    def test_zhejiang_list_date_in_anchor_can_be_separated_safely(self):
        html = '''<div><ul><li><a href="/dtyw/tzgg/202609/t20260930_309794.html">关于公开征求《浙江电力市场监管实施办法（征求意见稿）》等意见的公告 2026-09-30</a></li></ul></div>'''
        r=self.parse('cn_a85889da2306',html)
        self.assertEqual(r['links'][0]['date'],'2026-09-30')
        self.assertNotIn('2026-09-30',r['links'][0]['title'])

    def test_other_sites_cannot_reuse_ndrc_parser(self):
        html = '''<ul><li><a href="https://www.ndrc.gov.cn/xxgk/zcfb/tz/202607/t20260723_1406641.html">关于可再生能源发展规划的通知</a><time datetime="2026-07-23">日期</time></li></ul>'''
        r=self.parse('cn_a85889da2306',html)
        self.assertFalse(any(row['url'].startswith('https://www.ndrc.gov.cn/') for row in r['links']))


class DirectDisplayTests(unittest.TestCase):
    def normalize(self, source_id, title, url, excerpt='', **extras):
        return normalize_policy(dict(
            source_id=source_id, title=title, url=url, published_at=TODAY,
            region='中国', source_excerpt=excerpt, **extras), SOURCES, {})

    def test_related_renewable_pricing_official_document_displayed_with_scope_warning(self):
        out=self.normalize('cn_236457835be8',
             '广东省发展改革委关于完善新能源项目机制电价有关事项的通知',
             'https://drc.gd.gov.cn/ywtz/content/post_4967040.html',
             '价格机制应当符合新能源发电就近消纳要求，电网公司应当执行实施方案。')
        self.assertIsNotNone(out)
        self.assertIn('风电适用性待核对',out['doc_type'])

    def test_related_power_grid_rules_included(self):
        out=self.normalize('cn_124239bfeb82',
            '关于印发《山东省电力并网运行管理实施细则》的通知',
            'https://sdb.nea.gov.cn/dtyw/tzgg/202610/t20261010_310115.html',
            '电力并网运行规范对各类新能源发电项目可能具有实施要求。')
        self.assertIsNotNone(out)

    def test_only_dated_official_directory_row_can_show_as_lead(self):
        out=self.normalize('cn_236457835be8',
             '广东省发展改革委关于新增风电项目建设指标的通知',
             'https://drc.gd.gov.cn/example/20261019.html', '',
             article_evidence_available=False)
        self.assertEqual(out['evidence_type'],'directory_listing')
        self.assertIn('正文待补充',out['doc_type'])
        self.assertIn('仅取得',out['verification_status'])
        self.assertNotIn('CF_APP_WAF',out['source_excerpt'])

    def test_antibot_html_not_treated_as_media_body(self):
        out=self.normalize('cn_5555c1d4376e',
            '广东启动2026年机制电价竞价：陆上风电不参与',
            'https://news.bjx.com.cn/html/20261010/1512948.shtml',
            'CF_APP_WAF requestInfo.userUserId token security',
            article_evidence_available=False)
        self.assertIsNotNone(out)
        self.assertEqual(out['evidence_type'],'directory_listing')
        self.assertIn('媒体政策',out['doc_type'])
        self.assertNotIn('候选',out['doc_type'])
        self.assertNotIn('CF_APP_WAF',out['source_excerpt'])

    def test_unrelated_mining_penalty_not_shown(self):
        self.assertIsNone(self.normalize('cn_61f329f622c8',
            '贵州省能源局行政处罚公告（煤矿企业）',
            'https://nyj.guizhou.gov.cn/xwzx/gsgg/a.html',
            '关于煤矿安全生产许可证管理及有关煤矿重大隐患处罚的处理决定。'))

    def test_undated_directory_does_not_invent_date(self):
        data=dict(source_id='cn_236457835be8',title='关于风电政策的通知',
                  url='https://drc.gd.gov.cn/ywtz/test.html',published_at='',region='中国')
        self.assertIsNone(normalize_policy(data,SOURCES,{}))

    def test_external_media_is_not_mislabeled_as_official(self):
        out=self.normalize('cn_5555c1d4376e',
             '山东风电项目招标政策通知',
             'https://news.bjx.com.cn/html/20261001/1511291.shtml',
             '',article_evidence_available=False)
        self.assertIsNotNone(out)
        self.assertIn('媒体',out['doc_type'])
        self.assertNotIn('official_document',out['evidence_type'])

    def test_build_creates_display_decisions_with_reasons(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'site/data').mkdir(parents=True)
            (p/'policy_sources.json').write_text(json.dumps([SOURCES['cn_236457835be8']],ensure_ascii=False),'utf-8')
            raw=[{
                'source_id':'cn_236457835be8', 'region':'中国',
                'title':'广东省发改委关于推动新能源上网电价政策的通知',
                'url':'https://drc.gd.gov.cn/ywtz/a.html',
                'published_at':TODAY,
            },{
                'source_id':'cn_236457835be8', 'region':'中国',
                'title':'2026年度机关食堂车辆采购公告',
                'url':'https://drc.gd.gov.cn/ywtz/b.html',
                'published_at':TODAY,
            }]
            (p/'site/data/policies.json').write_text(json.dumps(raw,ensure_ascii=False),'utf-8')
            rows=build(root=p)
            self.assertEqual(len(rows),1)
            contents=(p/'site/data/policy_display_decisions.csv').read_text('utf-8-sig')
            self.assertIn('wind_relevance_not_evidenced',contents)
            self.assertIn('广东省发改委',contents)


class FailureDiagnosisTests(unittest.TestCase):
    def test_code_is_separated_from_category(self):
        blocked={'status':'blocked','attempts':[{'status':'failed','error_code':'http_412','http_status':412,'url':'https://x.gov.cn'}]}
        code,http,reason,action=classify(blocked)
        self.assertEqual(code,'http_412')
        self.assertEqual(http,412)
        self.assertIn('HTTP',reason)

    def test_export_does_not_change_foreign_status(self):
        with tempfile.TemporaryDirectory() as td:
            data=[{'id':'cn_236457835be8','status':'connection_error','attempts':[{'status':'failed','error_code':'connection_error','error':'Network is unreachable','url':'https://drc.gd.gov.cn'}]},
                  {'id':next(x['id'] for x in SOURCES.values() if x['region']!='中国'),'status':'blocked'}]
            report=write_diagnosis(data,list(SOURCES.values()),Path(td)/'report.csv')
            self.assertEqual(len(report),1)
            self.assertIn('网络',report[0]['原因分类'])


if __name__=='__main__':
    unittest.main()
