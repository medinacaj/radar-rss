"""Actualidad continua: real DOM/reader, local fixtures, no publisher network."""
from pathlib import Path
import unittest
from playwright.sync_api import expect
import dimension_regressions as baseline

class AhoraRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):baseline.DimensionRegressions.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):baseline.DimensionRegressions.tearDownClass.__func__(cls)
    def setUp(self):baseline.DimensionRegressions.setUp(self)
    def tearDown(self):baseline.DimensionRegressions.tearDown(self)

    def test_pulso_default_navigation_and_saved_sidebar_choice(self):
        expect(self.page.locator('#menuToggle')).to_have_attribute('aria-expanded','false')
        expect(self.page.locator('.pulso-nav')).to_be_visible()
        self.page.locator('.pulso-nav a[href="#agenda"]').click()
        expect(self.page.locator('.pulso-nav a[href="#agenda"]')).to_have_attribute('aria-current','page')
        self.page.locator('.pulso-nav a[href="#inicio"]').click()
        expect(self.page.locator('.pulso-nav a[href="#inicio"]')).to_have_attribute('aria-current','page')
        self.page.locator('#pulsoSources').click()
        expect(self.page.locator('#sidebarNavigationToggle')).to_be_focused()
        expect(self.page.locator('#menuToggle')).to_have_attribute('aria-expanded','true')
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        expect(self.page.locator('#menuToggle')).to_have_attribute('aria-expanded','true')
        self.page.locator('#menuToggle').click()
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        expect(self.page.locator('#menuToggle')).to_have_attribute('aria-expanded','false')

    def test_compact_home_chronology_dates_and_reader(self):
        expect(self.page.locator('#dashboardTitle')).to_have_text('Lo que pasa. Ahora.')
        self.page.evaluate("""()=>{
          const base=state.items[0],now=Date.now();
          state.items=[{...base,id:'old',coverage:20,published_at:new Date(now-7200000).toISOString()},
            {...base,id:'new',coverage:1,published_at:new Date(now-60000).toISOString(),first_seen_at:new Date(now-30000).toISOString()}];
          renderDashboard();
        }""")
        expect(self.page.locator('#dashboardFeature .now-story')).to_have_attribute('data-article-id','new')
        expect(self.page.locator('#dashboardFeature .article-meta')).to_contain_text('Publicado')
        expect(self.page.locator('#dashboardFeature .article-meta')).to_contain_text('Detectado')
        expect(self.page.locator('#dashboardView .cover,#dashboardView .article-cover-placeholder')).to_have_count(0)
        self.page.locator('#dashboardFeature .article-title a').click()
        expect(self.page.locator('#articleReaderDialog')).to_be_visible()
        self.page.keyboard.press('Escape')

    def test_now_is_not_filtered_by_old_home_personalization_but_mine_is(self):
        category=self.page.evaluate('state.categories[0]')
        self.page.evaluate("cat=>localStorage.setItem('radar-v12-preferences',JSON.stringify({mine:true,categories:[cat]}))",category)
        self.page.reload();self.page.wait_for_function('()=>state.ready')
        self.assertGreater(self.page.locator('#dashboardView .now-story').count(),3)
        self.page.locator('[data-now-view="mine"]').click()
        self.assertEqual(self.page.locator('#dashboardView .now-story').count(),3)
        self.page.locator('[data-now-view="zone"]').click()
        expect(self.page.locator('#nowZone')).to_be_visible()
        options=self.page.locator('#nowZone option').evaluate_all('nodes=>nodes.map(n=>n.value)')
        self.assertTrue(options)
        self.page.locator('#nowZone').select_option(options[-1])
        ids=self.page.locator('#dashboardView .now-story').evaluate_all('nodes=>nodes.map(n=>n.dataset.articleId)')
        allowed=self.page.evaluate('cat=>state.items.filter(x=>x.categories.includes(cat)).map(x=>x.id)',options[-1])
        self.assertTrue(ids);self.assertTrue(set(ids)<=set(allowed))
        self.page.reload();self.page.wait_for_function('()=>state.ready');self.page.locator('[data-now-view="zone"]').click()
        expect(self.page.locator('#nowZone')).to_have_value(options[-1])
        self.page.locator('#nowPreferences').click()
        expect(self.page.locator('#v12MineCategories')).to_be_visible()
        expect(self.page.locator('#v12MyRadarTitle')).to_have_text('Intereses de Mi Radar')

    def test_more_and_publication_notice_preserve_reading_until_explicit_apply(self):
        self.page.evaluate("""()=>{
          const base=state.items[0],now=Date.now();
          state.items=Array.from({length:50},(_,i)=>({...base,id:'row-'+i,
            published_at:new Date(now-(i+1)*60000).toISOString(),first_seen_at:new Date(now-(i+1)*60000+1000).toISOString()}));
          renderDashboard();
        }""")
        self.assertEqual(self.page.locator('#dashboardView .now-story').count(),36)
        self.page.locator('#nowMore').click()
        self.assertEqual(self.page.locator('#dashboardView .now-story').count(),50)
        expect(self.page.locator('#dashboardRecent .now-story').nth(35).locator('.article-title a')).to_be_focused()
        docs=self.page.evaluate("""()=>{
          const stamp=new Date(Date.now()+60000).toISOString();
          window.originalNowRow=document.querySelector('#dashboardFeature .now-story');
          const items=[{...state.items[0],id:'incoming',published_at:new Date(Date.now()-1000).toISOString()},...state.items];
          return {'meta.json':{version:2,generated_at:stamp,total_articles:items.length,latest_count:items.length,archive_files:[]},
            'latest.json':{version:2,generated_at:stamp,items},
            'sources.json':{sources:state.sources,categories:state.categories},
            'status.json':{checked_at:stamp,feeds:state.health}};
        }""")
        import json
        def route(request):
            name=request.request.url.split('/')[-1].split('?')[0]
            if name in docs:request.fulfill(content_type='application/json',body=json.dumps(docs[name]))
            else:request.fallback()
        self.page.route('**/data/*.json*',route)
        before=self.page.evaluate('scrollY')
        self.page.evaluate('refreshPublishedData()')
        expect(self.page.locator('#publicationNotice')).to_be_visible()
        self.assertTrue(self.page.evaluate("document.querySelector('#dashboardFeature .now-story')===window.originalNowRow"))
        self.assertAlmostEqual(self.page.evaluate('scrollY'),before,delta=2)
        self.page.locator('#publicationApply').click()
        expect(self.page.locator('#dashboardFeature .now-story')).to_have_attribute('data-article-id','incoming')
        expect(self.page.locator('#publicationNotice')).to_be_hidden()

    def test_age_filter_uses_detection_when_publication_is_missing_or_invalid(self):
        self.page.evaluate("""()=>{
          const base=state.items[0],now=Date.now();state.maxAge=1;
          state.items=[{...base,id:'no-date',published_at:null,first_seen_at:new Date(now-60000).toISOString()},
            {...base,id:'bad-date',published_at:'invalid',first_seen_at:new Date(now-120000).toISOString()},
            {...base,id:'too-old',published_at:null,first_seen_at:new Date(now-172800000).toISOString()}];
          renderDashboard();
        }""")
        self.assertEqual(self.page.locator('#dashboardView .now-story').count(),2)
        meta=self.page.locator('#dashboardFeature .article-meta')
        expect(meta).to_contain_text('Detectado')
        expect(meta).not_to_contain_text('Publicado')

    def test_developing_context_and_mobile_topics(self):
        self.page.locator('[data-now-view="developing"]').click()
        self.assertGreater(self.page.locator('#dashboardView .now-story').count(),0)
        expect(self.page.locator('#nowViewHint')).to_contain_text('agrupación automática')
        for theme in ('light','dark'):
            self.page.evaluate('(theme)=>setTheme(theme,true)',theme)
            for width in (320,390,768,1440):
                self.page.set_viewport_size({'width':width,'height':900})
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
                expect(self.page.locator('.topbar-brand strong')).to_be_visible()
                for button in self.page.locator('[data-now-view]').all():self.assertGreaterEqual(button.bounding_box()['height'],44)
        self.page.set_viewport_size({'width':1440,'height':1000})
        expect(self.page.locator('#radarFigure')).to_be_hidden()
        self.page.locator('#nowContext>summary').click()
        expect(self.page.locator('#radarFigure')).to_be_visible()
        self.page.locator('[data-now-view="now"]').click()
        self.page.emulate_media(reduced_motion='reduce')
        self.page.locator('#nowContext').evaluate('node=>node.open=false')
        self.page.evaluate('scrollTo(0,0)')
        Path('test-results/ahora').mkdir(parents=True,exist_ok=True)
        self.page.screenshot(path='test-results/ahora/desktop-dark.png',full_page=False)
        self.page.evaluate("setTheme('light',true)")
        self.page.screenshot(path='test-results/ahora/desktop-light.png',full_page=False)
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.screenshot(path='test-results/ahora/mobile-light.png',full_page=False)

if __name__=='__main__':unittest.main(verbosity=2)
