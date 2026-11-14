"""Folder controls: no ellipsis, but keep context menus accessible."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class FolderContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library=(ROOT/'web/library.js').read_text(encoding='utf-8')
        cls.css=(ROOT/'web/library.css').read_text(encoding='utf-8')
        cls.html=(ROOT/'web/index.html').read_text(encoding='utf-8')

    def test_no_redundant_ellipsis_buttons(self):
        self.assertNotIn("mk('button','folder-more')",self.library)
        self.assertNotIn("svgIcon('ellipsis')",self.library)
        self.assertNotIn('.folder-more{',self.css)
        self.assertIn("row.classList.add('folder-entry')",self.library)
        self.assertIn('folder-entry>.nav-link',self.css)

    def test_accessible_context_menu_on_every_folder(self):
        self.assertIn("row.addEventListener('contextmenu'",self.library)
        self.assertIn("e.shiftKey&&e.key==='F10'",self.library)
        self.assertIn("e.key==='ContextMenu'",self.library)
        self.assertIn("button.setAttribute('aria-keyshortcuts','Shift+F10')",self.library)
        self.assertIn("e.pointerType!=='touch'",self.library)
        self.assertIn("window.setTimeout",self.library)
        self.assertIn("e.stopImmediatePropagation()",self.library)
        self.assertIn("equipFolder(row,button,'default',id)",self.library)
        self.assertIn("equipFolder(wrapper,b,'manual',name)",self.library)
        self.assertIn("const menu=mk('div','folder-popup-menu')",self.library)

    def test_create_folder_only_from_context_menu(self):
        self.assertIn("['create','Crear carpeta']",self.library)
        self.assertIn("if(command==='create')createFolder()",self.library)
        self.assertIn("function createFolder(){openFolderEditor('manual',null,true);}",self.library)
        self.assertIn("forAll?!['read','unread','view','sources'].includes(command)",self.library)
        self.assertNotIn("add.title='Crear carpeta de fuentes'",self.library)
        self.assertNotIn("mk('button','settings-secondary','Crear carpeta')",self.library)
        self.assertIn('clic derecho sobre una carpeta o categoría',self.library)

    def test_updated_assets(self):
        self.assertRegex(self.html,r'<script src="\./library\.js\?v=[^"]+" defer></script>')
        self.assertRegex(self.html,r'<link rel="stylesheet" href="\./library\.css\?v=[^"]+">')
