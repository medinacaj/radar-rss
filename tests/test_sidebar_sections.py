"""Regresión del lateral: secciones plegables, apariencia plana y proyecto en el pie."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SidebarSectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        cls.library = (ROOT / 'web/library.js').read_text(encoding='utf-8')
        cls.layout = (ROOT / 'web/sidebar-layout.js').read_text(encoding='utf-8')
        cls.style = (ROOT / 'web/dimension.css').read_text(encoding='utf-8')
        cls.app = (ROOT / 'web/app.js').read_text(encoding='utf-8')

    def test_navigation_starts_expanded_with_accessible_toggle(self):
        self.assertRegex(self.html, r'id="sidebarNavigationToggle"[^>]*aria-controls="sidebarCoreContent"[^>]*aria-expanded="true"')
        self.assertIn('id="sidebarCoreContent"', self.html)
        self.assertNotIn('id="sidebarCoreContent" hidden', self.html)
        self.assertIn('id="categoryNav"', self.html)
        self.assertIn("navigationContent.hidden=!expanded", self.layout)
        self.assertIn("navigationToggle.setAttribute('aria-expanded',String(expanded))", self.layout)

    def test_source_folders_are_separate_and_start_expanded(self):
        self.assertIn("toggle.id='sourceFoldersToggle'", self.library)
        self.assertIn("toggle.setAttribute('aria-controls','libraryFolderNav')", self.library)
        self.assertIn("toggle.setAttribute('aria-expanded','true')", self.library)
        self.assertIn("nav.hidden=false", self.library)
        self.assertIn("toggle.addEventListener('click',()=>setExpanded(nav.hidden))", self.library)
        self.assertIn("$('sidebarCoreSection').after(foldersSection)", self.library)
        self.assertIn("add.addEventListener('click',()=>{setExpanded(true);createFolder();})", self.library)
        self.assertIn('#libraryFolderNav[hidden]{display:none!important}', self.style)
        self.assertNotIn('content:"Mostrar"', self.style)
        self.assertNotIn('content:"Ocultar"', self.style)

    def test_principal_has_reading_without_duplicate_all_news(self):
        feed = (ROOT / 'web/feed-ux.js').read_text(encoding='utf-8')
        self.assertIn("modes.id='sidebarReadingModes'",feed)
        self.assertIn("allMode.hidden=true",feed)
        self.assertIn("primaryNav.insertBefore(modes",feed)
        self.assertIn("const readingTitle=mk('span','','HERRAMIENTAS')",feed)
        self.assertIn("get('sidebarNavigation')?.append(readingNav)",feed)
        self.assertIn("if(entry.id==='all')state.mode='all'",self.app)
        self.assertIn("if(readingModes)nav.insertBefore(readingModes",self.app)
        self.assertIn('#sidebarReadingModes .mode-tab[hidden]',self.style)

    def test_footer_has_single_project_link_without_sidebar_button(self):
        footer = self.html[self.html.index('<footer class="footer">'):self.html.index('</footer>')]
        self.assertIn('id="footerInfo">Sobre el proyecto</a>', footer)
        self.assertNotIn('id="aboutButton"', self.html)
        self.assertIn("$('footerInfo').addEventListener('click',open)", self.app)
        self.assertIn('.footer #footerInfo', self.style)

    def test_flat_buttons_and_new_style_are_loaded_last(self):
        self.assertIn('border-radius:6px', self.style)
        self.assertIn('.nav-link.active::before', self.style)
        self.assertIn('.nav-glyph', self.style)
        self.assertIn('background:transparent', self.style)
        self.assertIn('dimension.css?v=', self.html)
        self.assertNotIn('sidebar-sections.css', self.html)
        self.assertIn('@media(prefers-reduced-motion:reduce)', self.style)


if __name__ == '__main__':
    unittest.main()
