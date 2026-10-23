"""Source-specific listing contracts based on publicly observed government URL patterns.

Fixtures emulate the documented URL/date layout. They are OFFLINE contract
checks and must never be represented as a successful live crawl.
"""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

import policy_scrape as crawler
from policy_domestic_profiles import DOMESTIC_PROFILES, specialized_listing
from policy_transport import PublicSiteChallenge, classify_error

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT/'policy_sources.json').read_text(encoding='utf-8'))
BY_ID = {x['id']:x for x in SOURCES}


class SourceSpecificContracts(unittest.TestCase):
    def row(self, base, path, title, date, wrapper='li'):
        return f'<{wrapper} class="gov-record"><a href="{path}">{title}</a><span class="publish-date">{date}</span></{wrapper}>'

    def listing(self, sid, base, paths, date='2026-10-15', next_url=None):
        titles = [f'关于印发新能源上网电价与风电项目管理办法第{i}条的通知' for i in range(len(paths))]
        body = ''.join(self.row(base,p,t,date) for p,t in zip(paths,titles))
        if next_url:
            body += f'<a class="next" title="下一页" href="{next_url}">下一页</a>'
        return crawler._listing_page('<html><main><ul>'+body+'</ul></main></html>', base,
                                     crawler.load_adapter(BY_ID[sid]))

    def test_public_source_specific_paths_and_row_dates(self):
        cases = [
            ('cn_61f329f622c8','https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index.html',
             '/zwgk/xxgkml/zdlyxx/xnygl/202609/t20260929_90000001.html'),
            ('cn_c3d9397ca287','https://fgw.sh.gov.cn/fgw_ny/index.html',
             '/fgw_ny/20260805/27ca3c27046b414992b0182cf8ed47a8.html'),
            ('cn_b85a8fe9fba8','https://fgw.fujian.gov.cn/zwgk/fgzd/sfgwgfxwj/',
             '/zwgk/fgzd/sfgwgfxwj/202608/t20260805_7196169.htm'),
            ('cn_eb58eb83050f','https://nyj.nmg.gov.cn/slh/zfwj/',
             '/slh/zfwj/202609/t20260908_2951227.html'),
            ('cn_0cedc4affbe8','https://nyj.shanxi.gov.cn/zfxxgk/fdzdgknr/sjwj/fdzdgknr_11759.html',
             '/zfxxgk/fdzdgknr/sjwj/202610/t20261016_10236977.shtml'),
            ('cn_642f1102f38a','https://fzggw.jiangsu.gov.cn/col/col51007/index.html',
             '/art/2026/9/21/art_51007_11832455.html'),
        ]
        for sid,base,path in cases:
            with self.subTest(source=sid):
                result=self.listing(sid,base,[path],date='2026-10-10')
                self.assertTrue(result['selector_matched'])
                self.assertEqual(result['eligible_rows'],1)
                self.assertEqual(result['dated_rows'],1)
                self.assertEqual(result['links'][0]['date'],'2026-10-10')
                self.assertEqual(result['dom_samples'][0]['row_class'],DOMESTIC_PROFILES[sid]['name'])

    def test_rejects_unrelated_links_even_with_date(self):
        sid='cn_c3d9397ca287';base='https://fgw.sh.gov.cn/fgw_ny/'
        html = '<ul><li><a href="https://untrusted.example.cn/fgw_ny/20260805/27ca3c27046b414992b0182cf8ed47a8.html">冒充政策的一条无效链接</a><span>2026-08-05</span></li></ul>'
        result=crawler._listing_page(html,base,crawler.load_adapter(BY_ID[sid]))
        self.assertEqual(result['eligible_rows'],0)
        self.assertFalse(result['selector_matched'])

    def test_article_title_date_is_not_publication_evidence(self):
        sid='cn_eb58eb83050f';base='https://nyj.nmg.gov.cn/slh/zfwj/'
        html='<ul><li><a href="/slh/zfwj/202609/t20260908_2951227.html">2026年09月08日新能源发展情况报告</a></li></ul>'
        result=crawler._listing_page(html,base,crawler.load_adapter(BY_ID[sid]))
        self.assertTrue(result['selector_matched'])
        self.assertEqual(result['dated_rows'],0)
        self.assertEqual(result['undated_policy_rows'],1)

    def test_guizhou_alternative_is_real_separate_regulator_category(self):
        src=BY_ID['cn_61f329f622c8']
        entries=crawler.adapter_urls(src)
        self.assertIn('https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index.html',entries)
        self.assertEqual(entries[0],src['url'])
        html = ('<ul><li><a href="/zwgk/xxgkml/zdlyxx/xnygl/202607/t20260721_90644524.html">'
                '贵州省能源局2026年4月-6月核准备案风电项目情况</a><span>2026-07-21</span></li></ul>')
        parsed=crawler._listing_page(html,entries[1],crawler.load_adapter(src))
        self.assertEqual(parsed['dated_rows'],1)

    def test_next_page_is_followed_only_when_observed(self):
        sid='cn_b85a8fe9fba8';base='https://fgw.fujian.gov.cn/zwgk/fgzd/sfgwgfxwj/'
        path='/zwgk/fgzd/sfgwgfxwj/202608/t20260805_7196169.htm'
        parsed=self.listing(sid,base,[path],next_url='index_1.htm')
        self.assertEqual(parsed['next_urls'],[base+'index_1.htm'])
        self.assertFalse(parsed['explicit_single_page'])


    def test_fujian_unresolved_vue_pages_cannot_prove_full_coverage(self):
        sid='cn_b85a8fe9fba8';base='https://fgw.fujian.gov.cn/zwgk/fgzd/sfgwgfxwj/'
        page=('''<ul><li><a href="/zwgk/fgzd/sfgwgfxwj/202608/t20260805_7196169.htm">'''
              '''福建省发展和改革委员会关于新能源管理办法的通知</a>'''
              '''<span>2026-08-05</span></li></ul><footer>共{{pageCount}}页</footer>''')
        result=crawler._listing_page(page,base,crawler.load_adapter(BY_ID[sid]))
        self.assertTrue(result['js_pagination'])
        self.assertEqual(result['dated_rows'],1)
        self.assertFalse(result['explicit_single_page'])

    def test_foreign_objects_and_adapters_are_not_rewritten(self):
        foreign=[src for src in SOURCES if src.get('region')!='中国']
        self.assertGreaterEqual(len(foreign),20)
        self.assertTrue(all(s['id'] not in DOMESTIC_PROFILES for s in foreign))
        for src in foreign:
            self.assertIsNone(specialized_listing('<html></html>',src['url'],
                crawler.load_adapter(src),{},parse_date=crawler.parse_date,
                normalize_url=crawler.normalize_url))

    def test_media_access_verification_is_not_policy_prose(self):
        code,status,hint=classify_error(PublicSiteChallenge('CF_APP_WAF'))
        self.assertEqual((code,status),('site_challenge',None))
        self.assertIn('核验',hint)

if __name__=='__main__':
    unittest.main()
