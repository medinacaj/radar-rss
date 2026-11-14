"""Current theme, offline shell and theme preference contracts."""
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DimensionThemeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=(ROOT/'web/index.html').read_text();cls.css=(ROOT/'web/dimension.css').read_text();cls.app=(ROOT/'web/app.js').read_text();cls.sw=(ROOT/'web/sw.js').read_text()
 def test_all_active_styles_and_modules_have_offline_shell_entries(self):
  for file in re.findall(r'(?:href|src)="\./([^"?]+\.(?:css|js))(?:\?[^" ]*)?"',self.html):
   self.assertIn("'./"+file+"'",self.sw,file)
  for obsolete in ('editorial.css','hashnode-preview.css','radar-hybrid.css','copper-theme.css','home-editorial.css','cosmic-theme.css','iaadc-editorial.css'):
   self.assertNotIn("'./"+obsolete+"'",self.sw)
   self.assertNotIn('./'+obsolete+'?v=',self.html)
 def test_system_and_explicit_theme_are_preserved(self):
  initial=self.app[self.app.index('function initialTheme()'):self.app.index('const state =')]
  self.assertIn("return 'system';",initial);self.assertIn('THEME_EXPLICIT_KEY',initial)
  for mode in ('light','dark','system'):self.assertIn(mode,initial)
  self.assertIn('id="themeToggle"',self.html);self.assertIn('id="settingTheme"',self.html)
  self.assertIn('body.radar-hybrid.dimension.light',self.css)
 def test_reference_is_one_active_theme_without_remote_resources(self):
  for token in ('--bg:','--surface:','--text:','--muted:','9999px'):
   self.assertIn(token,self.css)
  self.assertNotIn('@import',self.css);self.assertNotIn('url(https:',self.css)
  styles=re.findall(r'href="\./([^"?]+\.css)\?',self.html)
  self.assertEqual(styles[-4:],['dimension.css','experience.css','editorial-ux.css','topbar-tools.css'])
 def test_accessibility_and_reader_components_survive_theme_replacement(self):
  for component in ('articleGrid','dashboardFeature','dashboardRecent','categoryNav','agendaView','settingsDialog','cardMenu','sidebarResizeHandle'):
   self.assertIn('id="'+component+'"',self.html)
  self.assertIn('prefers-reduced-motion:reduce',self.css);self.assertIn('forced-colors:active',self.css)
  self.assertIn('data-card-action="read"',self.html);self.assertIn('data-card-action="share"',self.html)
