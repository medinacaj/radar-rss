"""Publisher metadata is the only evidence for article classification."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect import make_item, group_related_articles


class PublisherContentTypeTests(unittest.TestCase):
    source = {'id':'publisher', 'name':'ANÁLISIS — Diario', 'category':'04 - Chile', 'is_radar':False}
    now = datetime(2026, 11, 9, tzinfo=timezone.utc)

    def article(self, **metadata):
        return make_item({'title':'Opinión: comunicado sobre nuevas medidas',
                          'link':'https://example.com/news', **metadata}, self.source, self.now)

    def test_unknown_is_not_inferred_from_title_source_or_summary(self):
        article = self.article(summary='Análisis de una noticia y opinión del editor')
        self.assertNotIn('content_type', article)

    def test_exact_publisher_category_terms_are_retained(self):
        for term, expected in [('Opinión','opinion'), ('Análisis','analysis'), ('Noticia','news'),
                               ('Comunicado de prensa','press_release')]:
            with self.subTest(term=term):
                article = self.article(tags=[{'term':term}, {'term':'Chile'}])
                self.assertEqual(article.get('content_type'), expected)
                self.assertEqual(article.get('content_type_label'), term)

    def test_direct_article_metadata_is_retained(self):
        self.assertEqual(self.article(content_type='analysis').get('content_type'), 'analysis')

    def test_mime_type_topic_and_ambiguous_terms_are_unknown(self):
        for metadata in [{'content_type':'text/html'}, {'tags':[{'term':'Opinión política de Chile'}]},
                         {'tags':[{'term':'Opinión'}, {'term':'Análisis'}]},
                         {'tags':'Opinión'}, {'content':[{'type':'text/html', 'value':'Opinión'}]}]:
            with self.subTest(metadata=metadata):
                self.assertNotIn('content_type', self.article(**metadata))

    def test_grouping_does_not_conflate_different_facts(self):
        title = 'Concepción anuncia nuevas obras para mejorar 12 escuelas de la ciudad'
        first = self.article(title=title, content_type='news')
        first.update(title=title, published_at='2026-11-09T10:00:00Z')
        for different in [title.replace('12','13'), title.replace('12','-12'), title.replace('anuncia','no anuncia'),
                          title.replace('Concepción','Monagas'), title.replace('anuncia','suspende')]:
            second = {**first, 'id':'second', 'url':'https://second.example/news',
                      'source_ids':['second'], 'publisher':'Second publisher', 'title':different}
            with self.subTest(title=different):
                self.assertEqual(len(group_related_articles([first, second])), 2)

    def test_grouped_alternative_keeps_its_own_publisher_type(self):
        first = self.article(content_type='news')
        first.update(title='El gobierno anuncia nuevas medidas para mejorar la red del transporte público',
                     published_at='2026-11-09T10:00:00Z')
        second = {**first, 'id':'second', 'url':'https://second.example/news',
                  'source_ids':['second'], 'publisher':'Second publisher', 'content_type':'opinion'}
        grouped = group_related_articles([first, second])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['content_type'], 'news')
        self.assertEqual(grouped[0]['also_in'][0].get('content_type'), 'opinion')


if __name__ == '__main__':
    unittest.main()
