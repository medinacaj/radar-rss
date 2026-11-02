"""Regresión de miniaturas editoriales y tamaño independiente de titulares."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NewsCardDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"web/index.html").read_text(encoding="utf-8")
        cls.app=(ROOT/"web/app.js").read_text(encoding="utf-8")
        cls.css=(ROOT/"web/dimension.css").read_text(encoding="utf-8")
        cls.library=(ROOT/"web/library.js").read_text(encoding="utf-8")

    def test_slider_has_range_output_and_description(self):
        self.assertRegex(self.html,r'id="settingCardTitleSize" type="range" min="14" max="22" step="1" value="16"')
        self.assertIn('id="cardTitleSizeValue"',self.html)
        self.assertIn('id="cardTitleSizeHelp"',self.html)

    def test_preference_is_persistent_and_validated(self):
        self.assertIn("storeGet('radar-card-title-size')",self.app)
        self.assertIn("state.cardTitleSize=size",self.app)
        self.assertIn("savePref('card-title-size',size)",self.app)
        self.assertIn("document.body.dataset.cardTitleSize=String(state.cardTitleSize)",self.app)
        self.assertIn("state.cardTitleSize=16;state.pageSize=36",self.app)
        self.assertIn("cardTitleSize:state.cardTitleSize",self.app)
        self.assertIn("cardTitleSize:state.cardTitleSize",self.library)
        self.assertIn("'card-title-size',state.cardTitleSize",self.library)

    def test_cover_is_editorial_only_when_missing_an_image(self):
        self.assertIn("el.append(editorialCover(item))",self.app)
        self.assertIn("el.prepend(editorialCover(item))",self.app)
        self.assertIn("if(allowPreview",self.app)
        self.assertIn("img.addEventListener('error'",self.app)
        self.assertIn("article-card.no-cover>.article-cover-placeholder",self.css)
        self.assertIn("height:148px;min-height:148px;max-height:148px;flex:0 0 148px",self.css)
        self.assertIn("height:96px;min-height:96px;max-height:96px;flex-basis:96px",self.css)
        self.assertIn(".article-grid.list-view>.article-card.no-cover>.article-cover-placeholder",self.css)

    def test_normal_title_size_matches_the_slider(self):
        self.assertIn("--radar-reading-title-size:calc(var(--radar-card-title-size) * var(--radar-title-scale))",self.css)

    def test_card_title_size_does_not_resize_article_body(self):
        for size in range(14,23):
            self.assertIn(f'[data-card-title-size="{size}"]',self.css)
        self.assertIn("font-size:var(--radar-reading-title-size)!important",self.css)
        self.assertNotRegex(self.css,r"\.article-excerpt\s*\{[^}]*radar-card-title-size")


if __name__=="__main__":
    unittest.main()
