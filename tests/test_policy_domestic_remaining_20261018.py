"""Offline path/row/date test fixtures; not live HTTP acceptance tests."""
import unittest

from adapters.registry import load_adapter
import policy_scrape as ps
from policy_domestic_remaining import REMAINING_PROFILES, domestic_remaining_listing
from policy_domestic_profiles import DOMESTIC_PROFILES

SOURCE_MAP={s['id']:s for s in ps.read(ps.SOURCES, [])}


class DomesticOldRunRegression(unittest.TestCase):
    def parsed(self, sid, links, row_template='<li><a href="{url}">{title}</a><span>{date}</span></li>',
               headers='', footer=''):
        src=SOURCE_MAP[sid]
        html=f'<html><head><title>{src["name"]}</title></head><body>{headers}<ul>'+''.join(
            row_template.format(**row) for row in links)+f'</ul>{footer}</body></html>'
        return ps._listing_page(html,src['url'],load_adapter(src))

    def test_previous_seven_never_changed(self):
        old={'cn_61f329f622c8','cn_c3d9397ca287','cn_b85a8fe9fba8',
             'cn_eb58eb83050f','cn_642f1102f38a','cn_0cedc4affbe8','cn_5555c1d4376e'}
        self.assertFalse(old & set(REMAINING_PROFILES))
        self.assertFalse(set(REMAINING_PROFILES) & set(DOMESTIC_PROFILES))
        self.assertTrue(all(SOURCE_MAP[k]['region']=='中国' for k in REMAINING_PROFILES))
        self.assertTrue(all(k.startswith('cn_') for k in REMAINING_PROFILES))

    def test_two_separate_dates_take_publication_not_document_issue(self):
        sid='cn_687800e62fca'
        entry=[{'title':'辽宁省人民政府关于完善新能源电价机制的通知',
           'url':'https://www.ln.gov.cn/web/zwgkx/zfwj/szfwj/2026n/2026100912314500011/index.shtml',
           'date':'2026-10-05 11:02:00 <span>2026-10-09 12:31:45</span>'}]
        got=self.parsed(sid,entry)
        self.assertEqual(got['dated_rows'],1)
        self.assertEqual(got['links'][0]['date'],'2026-10-09')

    def test_jilin_drc_wind_project_has_publication_date(self):
        sid='cn_3c9957b26c3c'
        entry=[{'title':'关于吉林油田扶余65万千瓦风电项目核准的批复',
           'url':'https://xxgk.jl.gov.cn/zcbm/fgw/xxgkmlqy/202606/t20260603_9644826.html',
           'date':'2026年05月29日 <span>2026年06月03日</span>'}]
        got=self.parsed(sid,entry)
        self.assertEqual(got['dated_rows'],1)
        self.assertEqual(got['links'][0]['date'],'2026-06-03')

    def test_jilin_energy_article(self):
        got=self.parsed('cn_d6be9d4b18a8',[{
            'title':'吉林省绿电直连项目开发建设实施方案（试行）',
            'url':'https://nyj.jl.gov.cn/zwgk/tzgg/202603/t20260306_3593738.html',
            'date':'2026-03-06'}])
        self.assertTrue(got['selector_matched'])
        self.assertEqual(got['links'][0]['date'],'2026-03-06')

    def test_xinjiang_office_page_unverified_until_pagination(self):
        item={'title':'自治区人民政府办公厅关于深化可再生能源发展的通知',
              'url':'https://www.xinjiang.gov.cn/xinjiang/c112545/202606/1703a8c28b7747ab8212d5bbbce9cb56.shtml',
              'date':'2026-06-17'}
        parsed=self.parsed('cn_2b0fcb94d833',[item],footer='共 308 条 每页 10 条 共 31 页 当前第 1 页')
        self.assertTrue(parsed['js_pagination'])
        self.assertEqual(parsed['dated_rows'],1)

    def test_jiangsu_article_and_no_navigation_leak(self):
        item={'title':'江苏省政府关于推进海上风电项目开发的通知',
              'url':'https://www.jiangsu.gov.cn/art/2026/9/15/art_84242_11830063.html',
              'date':'2026-09-15'}
        got=self.parsed('cn_96f475fd98fa',[item])
        self.assertEqual(got['dated_rows'],1)
        self.assertEqual(got['eligible_rows'],1)

    def test_official_articles_from_proven_paths(self):
        samples={
            'cn_c9be69562225':'https://fgw.ln.gov.cn/fgw/zc/zxzc/2026073115014473464/index.shtml',
            'cn_7239ba11c55b':'https://drc.gd.gov.cn/gdsnyj/gkmlpt/content/4/4911/post_4911188.html',
            'cn_385aa60c445a':'https://www.xinjiang.gov.cn/xinjiang/c112543/202605/1e7de9050bcd403ea0042d396b060aad.shtml',
            'cn_fdb9ab86c4a9':'https://www.shandong.gov.cn/art/2026/4/30/art_267492_79694.html',
            'cn_354fb314969b':'https://gxt.nx.gov.cn/zwgk/fdzdgknr/zcfg/gxtwj/202610/t20261008_5364027.html',
            'cn_44abb54d7339':'https://fzggw.nx.gov.cn/zcgh/fgwwj/202602/t20260213_5172985.html',
            'cn_3a9624d397b1':'https://drc.xizang.gov.cn/zwgk_1941/xzgfxwj/202610/t20261008_561596.html',
            'cn_18e109d08abf':'https://gxt.fujian.gov.cn/zwgk/zfxxgk/fdzdgknr/gzdt/202610/t20261013_7224650.htm',
        }
        for sid,url in samples.items():
            with self.subTest(site=sid):
                got=self.parsed(sid,[{'url':url,'date':'2026-10-08',
                                    'title':'关于新能源市场及电网建设相关政策工作的通知'}])
                self.assertTrue(got['selector_matched'])
                self.assertEqual(got['eligible_rows'],1)
                self.assertEqual(got['links'][0]['url'],url)

    def test_mismatched_host_ignored_for_profile(self):
        src=SOURCE_MAP['cn_3c9957b26c3c']
        html='<ul><li><a href="https://evil.invalid/zcbm/fgw/xxgkmlqy/202606/t20260603_9644826.html">伪造的风电法规政策</a><span>2026-06-03</span></li></ul>'
        parser=domestic_remaining_listing(html,src['url'],load_adapter(src),{},parse_date=ps.parse_date,normalize_url=ps.normalize_url)
        self.assertIsNone(parser)

    def test_undated_policy_is_never_covered(self):
        got=self.parsed('cn_354fb314969b',[{
            'url':'https://gxt.nx.gov.cn/zwgk/fdzdgknr/zcfg/gxtwj/202610/t20261008_5364027.html',
            'title':'自治区工业和信息化厅关于能源领域发展的通知', 'date':''}])
        self.assertEqual(got['dated_rows'],0)
        self.assertEqual(got['undated_policy_rows'],1)

if __name__=='__main__':unittest.main()

class RemainingNewSourceTests(unittest.TestCase):
    def _render(self,source_id,rows):
        source=SOURCE_MAP[source_id]
        html='<ul>'+''.join('<li><a href="%s">%s</a><span class="publish-date">%s</span></li>' % row for row in rows)+'</ul>'
        return ps._listing_page(html,source['url'],load_adapter(source))

    def test_xizang_government_normative_file_real_shape(self):
        got=self._render('cn_7beeafa4d326',[(
            'https://www.xizang.gov.cn/zwgk/zfxxgk/fdzdgknr/zc/xzgfxwj/202601/t20260105_517564.html',
            '关于进一步降低用电成本助力高原特色产业高质量发展的通知','2026-01-05')])
        self.assertEqual(got['dated_rows'],1)
        self.assertEqual(got['links'][0]['date'],'2026-01-05')

    def test_jiangsu_provincial_industry_policy_is_not_previous_drc_adapter(self):
        source=SOURCE_MAP['cn_c37e9b9f7acf']
        got=self._render(source['id'],[(
            'https://gxt.jiangsu.gov.cn/art/2026/1/29/art_80179_11723369.html',
            '关于印发促进产业创新发展的若干政策措施的通知','2026-01-29')])
        self.assertEqual(got['dated_rows'],1)
        self.assertIn('工业和信息化厅',source['name'])
        self.assertNotIn('工信部',source['name'])
        self.assertTrue(load_adapter(source).config['allow_iframe'])
        self.assertTrue(load_adapter(source).config['needs_browser_ui'])

    def test_zhejiang_regulator_can_link_to_verified_nea_official_document(self):
        source=SOURCE_MAP['cn_a85889da2306']
        got=self._render(source['id'],[(
            'https://www.nea.gov.cn/20260520/9e1c4277ce324c8ab82a84da98da7980/c.html',
            '关于有序推动多用户绿电直连发展有关事项的通知','2026-05-20')])
        self.assertEqual(got['dated_rows'],1)
        self.assertTrue(ps.allowed_detail_link(source['url'],got['links'][0]['url'],load_adapter(source)))

    def test_zhejiang_regulator_cannot_link_to_arbitrary_remote_host(self):
        source=SOURCE_MAP['cn_a85889da2306']
        got=self._render(source['id'],[(
            'https://unapproved.example.com/20260520/9e1c4277ce324c8ab82a84da98da7980/c.html',
            '关于推进浙江新能源建设的政策','2026-05-20')])
        self.assertEqual(got['dated_rows'],0)
        self.assertFalse(any(x['url'].startswith('https://unapproved.example.com') for x in got['links']))

    def test_public_iframe_merge_only_for_named_domestic_sites(self):
        from unittest.mock import patch
        import sys,types
        parent=types.SimpleNamespace(url='https://gxt.jiangsu.gov.cn/col/col80179/index.html')
        parent.content=lambda:'<html><body>PUBLIC MAIN PAGE</body></html>'
        frame=types.SimpleNamespace(url='https://gxt.jiangsu.gov.cn/col/col80179/iframe.html')
        frame.content=lambda:'<html><body><ul><li><a href="/art/2026/1/29/art_80179_11723369.html">江苏省支持制造业绿色用电通知</a><span>2026-01-29</span></li></ul></body></html>'
        outside=types.SimpleNamespace(url='https://unapproved.example.com/data')
        outside.content=lambda:'<a href="https://unapproved.example.com/a">REJECT ME</a>'
        page=types.SimpleNamespace(url=parent.url,frames=[parent,frame,outside],main_frame=parent)
        page.goto=lambda *args,**kwargs:types.SimpleNamespace(status=200)
        page.wait_for_timeout=lambda *args,**kwargs:None
        page.content=parent.content
        class FakeLocator:
            def count(self):return 0
        page.locator=lambda *args:FakeLocator()
        browser=types.SimpleNamespace(new_page=lambda **kwargs:page,close=lambda:None)
        fake_p=types.SimpleNamespace(chromium=types.SimpleNamespace(launch=lambda **kw:browser))
        class FakeCtx:
            def __enter__(self):return fake_p
            def __exit__(self,*a):return False
        fake_sync_api=types.ModuleType('playwright.sync_api')
        fake_sync_api.sync_playwright=lambda:FakeCtx()
        with patch.dict(sys.modules,{'playwright.sync_api':fake_sync_api}):
            content,actual,kind=ps.browser_fetch(parent.url,'cn_c37e9b9f7acf')
            self.assertIn('https://gxt.jiangsu.gov.cn/art/2026/1/29/art_80179_11723369.html',content)
            self.assertNotIn('REJECT ME',content)
            other,_,_=ps.browser_fetch(parent.url,'cn_7239ba11c55b')
            self.assertNotIn('11723369.html',other)

    def test_action_save_uses_rebase_autostash(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/update.yml').read_text(encoding='utf-8')
        self.assertIn('git -c rebase.autoStash=true pull --rebase origin main',workflow)

