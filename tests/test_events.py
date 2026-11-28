"""Offline event contract, extraction, retention and bounded collection."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
if importlib.util.find_spec('events'):
    import events
else:
    events = None
if importlib.util.find_spec('collect_events'):
    import collect_events
else:
    collect_events = None

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
SOURCE = {'id':'src1','name':'Cultura','category':'07 - Concepción',
          'url':'https://cultura.example/feed/','website':'https://cultura.example/',
          'timezone':'America/Santiago'}

class EventTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(events, 'The event implementation must exist')

    def entry(self, **updates):
        return {'link':'https://cultura.example/concierto','title':'Concierto de primavera',
                'published':'Mon, 01 Jun 2026 12:00:00 GMT', **updates}

    def event(self, **updates):
        result = events.extract_event(self.entry(ev_startdate='2026-11-01'), SOURCE, NOW)
        return {**result, **updates}

    def test_pubdate_alone_does_not_confirm_event(self):
        result = events.extract_event(self.entry(), SOURCE, NOW)
        self.assertIsNone(result['start_date'])
        self.assertEqual(result['reason'], 'date_unverified')
        self.assertIsNone(events.extract_event(self.entry(title='Balance económico de octubre'), SOURCE, NOW))

    def test_rss_explicit_dates_preserve_old_announcement(self):
        result = self.event()
        self.assertEqual(result['start_date'], '2026-11-01')
        self.assertIsNone(result['end_date'])
        self.assertEqual(result['announced_at'], '2026-06-01T12:00:00Z')
        self.assertEqual(result['date_evidence']['kind'], 'rss')

    def test_event_jsonld_graph_but_not_newsarticle(self):
        page = '<script type="application/ld+json">'+json.dumps({'@graph':[
            {'@type':'NewsArticle','datePublished':'2026-10-29'},
            {'@type':'MusicEvent','name':'Concierto','url':self.entry()['link'],'startDate':'2026-11-02T01:00:00Z',
             'endDate':'2026-11-04','location':{'name':'Teatro'}}]})+'</script>'
        result = events.extract_event(self.entry(), SOURCE, NOW, html=page)
        self.assertEqual(result['start_date'], '2026-11-01')
        self.assertEqual(result['end_date'], '2026-11-04')
        self.assertEqual(result['location'], 'Teatro')
        result = events.extract_event(self.entry(), SOURCE, NOW,
            html='<script type="application/ld+json">{"@type":"NewsArticle","startDate":"2026-11-01"}</script>')
        self.assertIsNone(result['start_date'])

    def test_text_requires_activity_title_realization_context_and_explicit_year(self):
        good = self.entry(summary='El concierto se realizará el 4 de noviembre de 2026 en el teatro.')
        self.assertEqual(events.extract_event(good, SOURCE, NOW)['start_date'], '2026-11-04')
        for summary in ('El concierto se realizará el 4 de noviembre.',
                        'El concierto fue anunciado el 4 de noviembre de 2026.',
                        'La noticia fue publicada el 2026-11-04.'):
            self.assertIsNone(events.extract_event(self.entry(summary=summary), SOURCE, NOW)['start_date'])
        self.assertIsNone(events.extract_event(self.entry(title='Municipio informa presupuesto',summary=good['summary']),SOURCE,NOW))

    def test_yearless_text_date_is_anchored_to_the_announcement(self):
        # Anuncio del 20-11-2026: «6 de diciembre» es el próximo 6 de diciembre (16 días).
        recent = {'published':'Fri, 20 Nov 2026 12:00:00 GMT'}
        later = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
        result = events.extract_event(self.entry(summary='El concierto se realizará el próximo sábado 6 de diciembre en la plaza.', **recent), SOURCE, later)
        self.assertEqual(result['start_date'], '2026-12-06')
        self.assertEqual(result['date_evidence']['kind'], 'text')
        self.assertIs(result['date_evidence']['year_inferred'], True)
        events.validate_document(events.merge_events(None, [result], [], later))
        # El cruce de año toma la siguiente ocurrencia: un anuncio de diciembre para el 10 de enero.
        december = {'published':'Mon, 21 Dec 2026 12:00:00 GMT'}
        result = events.extract_event(self.entry(summary='El festival se realizará el 10 de enero.', **december), SOURCE, datetime(2026, 12, 22, tzinfo=timezone.utc))
        self.assertEqual(result['start_date'], '2027-01-10')
        # Un año explícito nunca se marca como deducido.
        explicit = events.extract_event(self.entry(summary='El concierto se realizará el 6 de diciembre de 2026.', **recent), SOURCE, later)
        self.assertNotIn('year_inferred', explicit['date_evidence'])

    def test_yearless_text_date_stays_pending_without_safe_anchor(self):
        later = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
        summary = 'El concierto se realizará el 6 de diciembre.'
        cases = (
            # Sin fecha de publicación no hay referencia para el año.
            ({'published': None}, later),
            # Más de 90 días después del anuncio: fuera del margen.
            ({'published':'Mon, 01 Jun 2026 12:00:00 GMT'}, later),
        )
        for updates, now in cases:
            entry = {k: v for k, v in {**self.entry(summary=summary), **updates}.items() if v is not None}
            self.assertIsNone(events.extract_event(entry, SOURCE, now)['start_date'])
        # Sin cláusula de realización («fue anunciado») tampoco se deduce nada.
        announced = self.entry(summary='El concierto fue anunciado el 6 de diciembre.', published='Fri, 20 Nov 2026 12:00:00 GMT')
        self.assertIsNone(events.extract_event(announced, SOURCE, later)['start_date'])
        # Dos fechas alternativas siguen siendo una contradicción.
        alternative = self.entry(summary='El concierto se realizará el 6 de diciembre o el 13 de diciembre.', published='Fri, 20 Nov 2026 12:00:00 GMT')
        self.assertIsNone(events.extract_event(alternative, SOURCE, later)['start_date'])
        # Una fecha de publicación futura no sirve de referencia: se usa la hora actual.
        future = self.entry(summary=summary, published='Fri, 01 Oct 2027 12:00:00 GMT')
        self.assertEqual(events.extract_event(future, SOURCE, later)['start_date'], '2026-12-06')

    def test_year_inferred_flag_is_validated(self):
        recent = self.entry(summary='El concierto se realizará el 6 de diciembre.', published='Fri, 20 Nov 2026 12:00:00 GMT')
        later = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
        doc = events.merge_events(None, [events.extract_event(recent, SOURCE, later)], [], later)
        doc['items'][0]['date_evidence']['year_inferred'] = 'sí'
        with self.assertRaises(ValueError):
            events.validate_document(doc)

    def test_malformed_dates_missing_timezone_and_reversed_ranges_pending(self):
        for values in ({'ev_startdate':'2026-02-30'}, {'ev_startdate':'11/02'},
                       {'ev_startdate':'2026-11-01','ev_enddate':'2026-10-30'}):
            self.assertIsNone(events.extract_event(self.entry(**values),SOURCE,NOW)['start_date'])
        self.assertIsNone(events.extract_event(self.entry(ev_startdate='2026-11-01'),
            {**SOURCE,'timezone':''},NOW)['start_date'])
        self.assertIsNone(events.extract_event(self.entry(ev_startdate='2026-11-01'),
            {**SOURCE,'timezone':'Wrong/Zone'},NOW)['start_date'])

    def test_midnight_dst_and_caracas_expire_at_local_end_of_day(self):
        ch = self.event(start_date='2026-09-06')
        self.assertTrue(events.is_upcoming(ch,datetime(2026,9,7,2,59,tzinfo=timezone.utc)))
        self.assertFalse(events.is_upcoming(ch,datetime(2026,9,7,3,0,tzinfo=timezone.utc)))
        ve = self.event(start_date='2026-10-25',timezone='America/Caracas')
        self.assertTrue(events.is_upcoming(ve,datetime(2026,10,26,3,59,tzinfo=timezone.utc)))
        self.assertFalse(events.is_upcoming(ve,datetime(2026,10,26,4,0,tzinfo=timezone.utc)))

    def test_multiday_and_inclusive_ninety_day_horizon(self):
        self.assertTrue(events.is_upcoming(self.event(start_date='2026-10-01',end_date='2026-10-26'),NOW))
        self.assertTrue(events.is_upcoming(self.event(start_date='2027-01-23'),NOW))
        self.assertFalse(events.is_upcoming(self.event(start_date='2027-01-24'),NOW))
        self.assertFalse(events.is_upcoming(self.event(status='cancelled'),NOW))

    def test_merge_preserves_active_items_when_feed_fails_or_omits_old_article(self):
        previous = events.merge_events(None,[self.event()],[],NOW)
        merged = events.merge_events(previous,[],[{'source_id':'src1','source_name':'Cultura','url':SOURCE['url'],'timezone':SOURCE['timezone'],'status':'error','checked_at':'2026-10-25T12:00:00Z','error':'offline'}],NOW)
        self.assertEqual(len(merged['items']),1)
        self.assertEqual(merged['items'][0]['announced_at'],'2026-06-01T12:00:00Z')
        events.validate_document(merged)

    def test_rescheduling_same_url_updates_in_place_preserving_first_seen(self):
        first = self.event(first_seen_at='2026-10-01T12:00:00Z')
        previous = events.merge_events(None,[first],[],NOW)
        new = events.extract_event(self.entry(ev_startdate='2026-11-10'),SOURCE,NOW)
        changed = events.merge_events(previous,[new],[],NOW)
        self.assertEqual(len(changed['items']),1)
        self.assertEqual(changed['items'][0]['start_date'],'2026-11-10')
        self.assertEqual(changed['items'][0]['first_seen_at'],'2026-10-01T12:00:00Z')
        tracked = events.extract_event(self.entry(link=self.entry()['link']+'?utm_source=a',ev_startdate='2026-11-10'),SOURCE,NOW)
        self.assertEqual(tracked['id'],new['id'])

    def test_cancellation_and_postponement_remove_upcoming_without_resurrection(self):
        previous = events.merge_events(None,[self.event()],[],NOW)
        cancelled = events.extract_event(self.entry(title='Concierto cancelado'),SOURCE,NOW)
        merged = events.merge_events(previous,[cancelled],[],NOW)
        self.assertEqual(merged['items'][0]['status'],'cancelled')
        self.assertFalse(events.is_upcoming(merged['items'][0],NOW))
        postponed = events.extract_event(self.entry(title='Concierto aplazado hasta nuevo aviso'),SOURCE,NOW)
        merged = events.merge_events(previous,[postponed],[],NOW)
        self.assertEqual(merged['items'],[])
        self.assertEqual(merged['pending'][0]['status'],'postponed')
        self.assertIsNone(merged['pending'][0]['start_date'])
        self.assertEqual(events.merge_events(merged,[],[],NOW)['items'],[])

    def test_jsonld_postponed_date_is_old_until_explicit_reschedule(self):
        page = '<script type="application/ld+json">'+json.dumps({'@type':'Event',
            'name':'Concierto','url':self.entry()['link'],'startDate':'2026-11-01','eventStatus':'https://schema.org/EventPostponed'})+'</script>'
        item = events.extract_event(self.entry(),SOURCE,NOW,html=page)
        self.assertEqual(item['status'],'postponed')
        self.assertIsNone(item['start_date'])
        page = page.replace('EventPostponed','EventRescheduled')
        self.assertEqual(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'],'2026-11-01')

    def test_corrupt_history_rejected_and_pending_not_unbounded(self):
        doc = events.merge_events(None,[self.event()],[],NOW)
        for field,value in [('version',2),('items',{}),('generated_at','nope')]:
            invalid=copy.deepcopy(doc);invalid[field]=value
            with self.assertRaises(ValueError): events.validate_document(invalid)
        invalid=copy.deepcopy(doc);invalid['items'][0]['start_date']='2026-02-30'
        with self.assertRaises(ValueError): events.validate_document(invalid)
        old = events.extract_event(self.entry(),SOURCE,datetime(2025,1,1,tzinfo=timezone.utc))
        self.assertEqual(events.merge_events(None,[old],[],NOW)['pending'],[])

    def test_malformed_entry_values_never_abort_extraction(self):
        for entry in (None, [], {'title': 'Concierto', 'link': ['bad']},
                      {'title': {}, 'link': 'https://cultura.example/a'},
                      self.entry(content=[None, 'bad']), self.entry(published_parsed=['bad'])):
            result=events.extract_event(entry,SOURCE,NOW)
            self.assertTrue(result is None or result['start_date'] is None)

    def test_rescheduled_text_with_explicit_new_date_is_scheduled(self):
        entry=self.entry(title='Concierto reprogramado',summary='La nueva fecha: el concierto se realizará el 12 de noviembre de 2026, tras ser pospuesto.')
        item=events.extract_event(entry,SOURCE,NOW)
        self.assertEqual(item['status'],'scheduled')
        self.assertEqual(item['start_date'],'2026-11-12')

    def test_newsarticle_nested_events_do_not_hijack_article(self):
        page='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle',
            'mainEntity':{'@type':'Event','startDate':'2026-11-01'}})+'</script>'
        self.assertIsNone(events.extract_event(self.entry(title='Informe de economía'),SOURCE,NOW,html=page))

    def test_ambiguous_multiple_dates_stay_pending(self):
        entry=self.entry(summary='Se realizará el 4 de noviembre de 2026 o se realizará el 5 de noviembre de 2026.')
        self.assertIsNone(events.extract_event(entry,SOURCE,NOW)['start_date'])
        page='<script type="application/ld+json">'+json.dumps([
            {'@type':'Event','startDate':'2026-11-01'},
            {'@type':'Event','startDate':'2026-11-02'}])+'</script>'
        self.assertIsNone(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'])

    def test_negated_or_alternative_text_never_confirms_an_activity_date(self):
        for summary in (
            'El concierto no se realizará el 4 de noviembre de 2026.',
            'El concierto no tendrá lugar el 4 de noviembre de 2026.',
            'El concierto se realizará el 4 de noviembre de 2026 o el 5 de noviembre de 2026.',
            'El concierto se realizará el 2026-11-04 o el 2026-11-05.',
            'El concierto se realizará el 04/11/2026 o el 05/11/2026.',
        ):
            with self.subTest(summary=summary):
                item=events.extract_event(self.entry(summary=summary),SOURCE,NOW)
                self.assertIsNone(item['start_date'])
                self.assertIsNone(item['end_date'])
                self.assertIsNone(item['date_evidence'])
                self.assertEqual(item['reason'],'date_unverified')
                self.assertEqual(item['status'],'scheduled')  # No invented cancellation/postponement.
                self.assertFalse(events.is_upcoming(item,NOW))

    def test_merge_does_not_rescue_a_date_rejected_by_updated_text(self):
        original=events.extract_event(self.entry(summary='El concierto se realizará el 4 de noviembre de 2026.'),SOURCE,NOW)
        previous=events.merge_events(None,[original],[],NOW)
        for summary in (
            'El concierto no se realizará el 4 de noviembre de 2026.',
            'El concierto se realizará el 4 de noviembre de 2026 o el 5 de noviembre de 2026.',
            'Se realizará el 4 de noviembre de 2026 o se realizará el 5 de noviembre de 2026.',
        ):
            with self.subTest(summary=summary):
                incoming=events.extract_event(self.entry(summary=summary),SOURCE,NOW)
                merged=events.merge_events(previous,[incoming],[],NOW)
                self.assertEqual(merged['items'],[])
                self.assertEqual(len(merged['pending']),1)
                pending=merged['pending'][0]
                self.assertEqual(pending['id'],original['id'])
                self.assertEqual(pending['first_seen_at'],original['first_seen_at'])
                self.assertEqual(pending['reason'],'date_unverified')
                self.assertNotIn('_date_rejected',pending)
                self.assertFalse(events.is_upcoming(pending,NOW))
                # A later incomplete repeat must not bring the withdrawn date back.
                repeated=events.merge_events(merged,[events.extract_event(self.entry(),SOURCE,NOW)],[],NOW)
                self.assertEqual(repeated['items'],[])
                self.assertIsNone(repeated['pending'][0]['start_date'])
        # Ordinary omission still preserves a verified date.
        incomplete=events.merge_events(previous,[events.extract_event(self.entry(),SOURCE,NOW)],[],NOW)
        self.assertEqual(incomplete['items'][0]['start_date'],'2026-11-04')

    def test_jsonld_location_normalizes_optional_blank_or_padded_text(self):
        for status in ('EventScheduled','EventRescheduled'):
            for location,expected in (
                ('',None),('   ',None),({'name':''},None),({'name':' \t '},None),
                ('  Teatro  ','Teatro'),({'name':'  Teatro  '},'Teatro'),
            ):
                with self.subTest(status=status,location=location):
                    page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
                        'url':self.entry()['link'],'startDate':'2026-11-04',
                        'eventStatus':'https://schema.org/'+status,'location':location})+'</script>'
                    item=events.extract_event(self.entry(),SOURCE,NOW,html=page)
                    self.assertEqual(item['location'],expected)
                    doc=events.merge_events(None,[item],[],NOW)
                    self.assertEqual(doc['items'][0]['start_date'],'2026-11-04')
        invalid=events.merge_events(None,[self.event()],[],NOW)
        invalid['items'][0]['location']='   '
        with self.assertRaisesRegex(ValueError,'location'):events.validate_document(invalid)

    def test_pending_reason_only_accepts_the_v1_browser_enum(self):
        pending=events.extract_event(self.entry(),SOURCE,NOW)
        doc=events.merge_events(None,[pending],[],NOW)
        for reason in ('date_unverified','timezone_missing','postponed'):
            valid=copy.deepcopy(doc);valid['pending'][0]['reason']=reason
            events.validate_document(valid)
        for reason in ('not_a_v1_reason','',None,[],True):
            with self.subTest(reason=reason):
                invalid=copy.deepcopy(doc);invalid['pending'][0]['reason']=reason
                with self.assertRaisesRegex(ValueError,'pending reason'):events.validate_document(invalid)
                with self.assertRaisesRegex(ValueError,'pending reason'):
                    events.merge_events(None,[invalid['pending'][0]],[],NOW)

    def test_page_widget_text_and_unrelated_jsonld_do_not_confirm(self):
        page='<aside>Festival se realizará el 12 de noviembre de 2026</aside>'
        self.assertIsNone(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'])
        page='<script type="application/ld+json">'+json.dumps({'@type':'Event','name':'Feria de empleo','startDate':'2026-11-12','url':'https://cultura.example/other'})+'</script>'
        self.assertIsNone(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'])

    def test_cancellation_title_beats_stale_scheduled_jsonld(self):
        page='<script type="application/ld+json">'+json.dumps({'@type':'Event','name':'Concierto','url':self.entry()['link'],
            'startDate':'2026-11-01','eventStatus':'https://schema.org/EventScheduled'})+'</script>'
        self.assertEqual(events.extract_event(self.entry(title='Concierto cancelado'),SOURCE,NOW,html=page)['status'],'cancelled')

    def test_document_size_limit_fails_instead_of_dropping_active_items(self):
        item=self.event()
        with patch.object(events,'MAX_DOCUMENT_BYTES',100):
            with self.assertRaises(ValueError):events.merge_events(None,[item],[],NOW)

    def test_document_rejects_incomplete_metadata_missing_fields_and_duplicate_ids(self):
        doc=events.merge_events(None,[self.event()],[],NOW)
        for field in ('end_date','timezone','date_evidence'):
            invalid=copy.deepcopy(doc);del invalid['items'][0][field]
            with self.assertRaises(ValueError):events.validate_document(invalid)
        for source in ({'source_id':'x','status':'ok'},
                       {'source_id':'x','source_name':'X','url':'javascript:evil()',
                        'timezone':'America/Caracas','checked_at':'2026-10-25T12:00:00Z','status':'ok','error':None}):
            invalid=copy.deepcopy(doc);invalid['sources']=[source]
            with self.assertRaises(ValueError):events.validate_document(invalid)
        invalid=copy.deepcopy(doc);invalid['items']*=2
        with self.assertRaises(ValueError):events.validate_document(invalid)
        invalid=copy.deepcopy(doc);invalid['items'][0]['first_seen_at']='2026-12-01T00:00:00Z'
        with self.assertRaises(ValueError):events.validate_document(invalid)

    def test_expired_events_pruned_but_far_future_remains_in_cache(self):
        incoming=[self.event(start_date='2026-10-24'),self.event(id='far',start_date='2027-10-01')]
        doc=events.merge_events(None,incoming,[],NOW)
        self.assertEqual([i['id'] for i in doc['items']],['far'])
        self.assertFalse(events.is_upcoming(doc['items'][0],NOW))

    def test_review1_jsonld_status_without_start_date_restricts_cached_event(self):
        previous=events.merge_events(None,[self.event()],[],NOW)
        for status,expected in [('EventCancelled','cancelled'),('EventPostponed','postponed')]:
            with self.subTest(status=status):
                page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
                    'url':self.entry()['link'],'eventStatus':'https://schema.org/'+status})+'</script>'
                update=events.extract_event(self.entry(),SOURCE,NOW,html=page)
                self.assertEqual(update['status'],expected)
                merged=events.merge_events(previous,[update],[],NOW)
                records=merged['items']+merged['pending']
                self.assertEqual(records[0]['status'],expected)
                self.assertFalse(events.is_upcoming(records[0],NOW))
                if expected=='cancelled':self.assertEqual(records[0]['start_date'],'2026-11-01')
                else:self.assertIsNone(records[0]['start_date'])

    def test_review2_stale_rss_cannot_reactivate_restrictive_status(self):
        previous=events.merge_events(None,[self.event()],[],NOW)
        for word,expected in [('cancelado','cancelled'),('aplazado','postponed')]:
            with self.subTest(status=expected):
                update=events.extract_event(self.entry(title='Concierto '+word),SOURCE,NOW)
                restricted=events.merge_events(previous,[update],[],NOW)
                stale=events.extract_event(self.entry(ev_startdate='2026-11-01'),SOURCE,NOW)
                merged=events.merge_events(restricted,[stale],[],NOW)
                records=merged['items']+merged['pending']
                self.assertEqual(records[0]['status'],expected)
                self.assertFalse(events.is_upcoming(records[0],NOW))
                # A verified explicit reschedule may reactivate the identity.
                page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
                    'url':self.entry()['link'],'startDate':'2026-11-12',
                    'eventStatus':'https://schema.org/EventRescheduled'})+'</script>'
                rescheduled=events.extract_event(self.entry(),SOURCE,NOW,html=page)
                self.assertIs(rescheduled['status_explicit'],True)
                restored=events.merge_events(restricted,[rescheduled],[],NOW)
                self.assertEqual(restored['items'][0]['start_date'],'2026-11-12')
                self.assertTrue(events.is_upcoming(restored['items'][0],NOW))
        # A changed structured date is verifiable for a previously dated cancellation.
        cancelled=events.merge_events(previous,[self.event(status='cancelled')],[],NOW)
        changed=events.extract_event(self.entry(ev_startdate='2026-11-15'),SOURCE,NOW)
        self.assertEqual(events.merge_events(cancelled,[changed],[],NOW)['items'][0]['status'],'scheduled')
        invalid=events.merge_events(None,[self.event()],[],NOW)
        invalid['items'][0]['status_explicit']='true'
        with self.assertRaises(ValueError):events.validate_document(invalid)

    def test_review3_conflicting_url_and_generic_name_never_identify_event(self):
        for obj in (
            {'@type':'Event','url':'https://cultura.example/other','name':'Concierto'},
            {'@type':'Event','url':'https://cultura.example/other','name':'Concierto de primavera'},
            {'@type':'Event','name':'Concierto'},
        ):
            with self.subTest(obj=obj):
                page='<script type="application/ld+json">'+json.dumps({**obj,'startDate':'2026-11-12'})+'</script>'
                self.assertIsNone(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'])
        page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
            'name':'Concierto de primavera','startDate':'2026-11-12'})+'</script>'
        self.assertEqual(events.extract_event(self.entry(),SOURCE,NOW,html=page)['start_date'],'2026-11-12')

    def test_review4_secondary_registration_dates_are_not_activity_dates(self):
        for text in (
            'El concierto se realizará en noviembre; las inscripciones se abrieron el 1 de junio de 2026.',
            'El concierto se realizará en noviembre; las inscripciones se abrirán el 1 de noviembre de 2026.',
            'El concierto se realizará en noviembre, las inscripciones se abrirán el 1 de noviembre de 2026.',
            'La inscripción al concierto se realizará el 1 de noviembre de 2026.',
        ):
            with self.subTest(text=text):
                self.assertIsNone(events.extract_event(self.entry(summary=text),SOURCE,NOW)['start_date'])
        positive=self.entry(summary='El concierto se realizará el día miércoles 4 de noviembre de 2026.')
        self.assertEqual(events.extract_event(positive,SOURCE,NOW)['start_date'],'2026-11-04')

    def test_round2_rescheduled_jsonld_date_supersedes_stale_rss_date(self):
        page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
            'url':self.entry()['link'],'startDate':'2026-11-12','endDate':'2026-11-13',
            'eventStatus':'https://schema.org/EventRescheduled'})+'</script>'
        incoming=events.extract_event(self.entry(ev_startdate='2026-11-01'),SOURCE,NOW,html=page)
        self.assertEqual(incoming['start_date'],'2026-11-12')
        self.assertEqual(incoming['end_date'],'2026-11-13')
        self.assertEqual(incoming['date_evidence']['kind'],'jsonld')
        self.assertIs(incoming['status_explicit'],True)
        previous=events.merge_events(None,[self.event(status='cancelled')],[],NOW)
        merged=events.merge_events(previous,[incoming],[],NOW)
        self.assertEqual(merged['items'][0]['start_date'],'2026-11-12')
        self.assertTrue(events.is_upcoming(merged['items'][0],NOW))

    def test_round2_ambiguous_or_missing_reschedule_date_stays_pending(self):
        old=events.merge_events(None,[self.event()],[],NOW)
        for objects in (
            [{'@type':'Event','startDate':'2026-11-12','eventStatus':'https://schema.org/EventRescheduled'},
             {'@type':'Event','startDate':'2026-11-14','eventStatus':'https://schema.org/EventRescheduled'}],
            [{'@type':'Event','eventStatus':'https://schema.org/EventRescheduled'}],
            [{'@type':'Event','startDate':'invalid','eventStatus':'https://schema.org/EventRescheduled'}],
        ):
            with self.subTest(objects=objects):
                page='<script type="application/ld+json">'+json.dumps([
                    {**obj,'url':self.entry()['link']} for obj in objects])+'</script>'
                incoming=events.extract_event(self.entry(ev_startdate='2026-11-01'),SOURCE,NOW,html=page)
                self.assertIsNone(incoming['start_date'])
                self.assertIs(incoming['status_explicit'],False)
                merged=events.merge_events(old,[incoming],[],NOW)
                self.assertEqual(merged['items'],[])
                self.assertEqual(len(merged['pending']),1)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(collect_events,'The collector implementation must exist')

    def test_config_registered_sources_only_and_zones(self):
        selected = collect_events.load_sources(ROOT/'sources/feeds.opml',ROOT/'sources/events.json')
        self.assertGreaterEqual(len(selected),8)
        self.assertLessEqual(len(selected),12)
        self.assertTrue(all(not s['is_radar'] for s in selected))
        self.assertTrue(any(s['timezone']=='America/Caracas' for s in selected))
        with tempfile.TemporaryDirectory() as temp:
            config=Path(temp)/'config.json'
            config.write_text(json.dumps({'version':1,'sources':[{'url':'https://unregistered.example/feed','timezone':'America/Santiago'}]}))
            with self.assertRaises(ValueError):collect_events.load_sources(ROOT/'sources/feeds.opml',config)

    def test_html_only_for_registered_public_https_hosts_robots(self):
        with patch.object(collect_events.collect,'is_public_host',return_value=True), \
             patch.object(collect_events.collect,'page_image_allowed',return_value=True), \
             patch.object(collect_events.collect,'read_bounded_response',return_value=('text/html','<html>ok</html>')) as read:
            self.assertEqual(collect_events.fetch_event_page('https://cultura.example/event',SOURCE),'<html>ok</html>')
            for url in ('http://cultura.example/event','https://other.example/event','https://127.0.0.1/event','https://cultura.example:444/event'):
                self.assertIsNone(collect_events.fetch_event_page(url,SOURCE))
            self.assertEqual(read.call_count,1)
        with patch.object(collect_events.collect,'is_public_host',return_value=False):
            self.assertIsNone(collect_events.fetch_event_page('https://cultura.example/event',SOURCE))
        with patch.object(collect_events.collect,'is_public_host',return_value=True),patch.object(collect_events.collect,'page_image_allowed',return_value=False):
            self.assertIsNone(collect_events.fetch_event_page('https://cultura.example/event',SOURCE))

    def test_collector_caps_entries_and_pages_preserves_cache_on_network_error(self):
        rss = ('<rss version="2.0"><channel>'+''.join('<item><title>Concierto %d</title><link>https://cultura.example/%d</link></item>'%(i,i) for i in range(55))+'</channel></rss>').encode()
        with patch.object(collect_events,'fetch_feed',return_value=rss),patch.object(collect_events,'fetch_event_page',return_value='') as page:
            doc=collect_events.collect_document([SOURCE],None,NOW)
            self.assertEqual(len(doc['pending']),50)
            self.assertEqual(page.call_count,12)
            self.assertEqual(doc['sources'][0]['status'],'ok')
        item=events.extract_event({'title':'Concierto','link':'https://cultura.example/one','ev_startdate':'2026-11-01'},SOURCE,NOW)
        previous=events.merge_events(None,[item],[],NOW)
        with patch.object(collect_events,'fetch_feed',side_effect=OSError('offline')):
            doc=collect_events.collect_document([SOURCE],previous,NOW)
            self.assertEqual(len(doc['items']),1)
            self.assertEqual(doc['sources'][0]['status'],'error')

    def test_dated_rss_candidate_still_checks_jsonld_status_update(self):
        rss=b'<rss version="2.0" xmlns:ev="https://events.example/schema"><channel><item><title>Concierto de primavera</title><link>https://cultura.example/concierto</link><ev:startdate>2026-11-01</ev:startdate></item></channel></rss>'
        item=events.extract_event({'title':'Concierto de primavera','link':'https://cultura.example/concierto','ev_startdate':'2026-11-01'},SOURCE,NOW)
        previous=events.merge_events(None,[item],[],NOW)
        page='<script type="application/ld+json">'+json.dumps({'@type':'Event',
            'url':item['url'],'eventStatus':'https://schema.org/EventCancelled'})+'</script>'
        with patch.object(collect_events,'fetch_feed',return_value=rss),patch.object(collect_events,'fetch_event_page',return_value=page):
            doc=collect_events.collect_document([SOURCE],previous,NOW)
        self.assertEqual(doc['items'][0]['status'],'cancelled')
        self.assertFalse(events.is_upcoming(doc['items'][0],NOW))

    def test_blank_jsonld_location_does_not_block_collector_output_or_other_events(self):
        rss=b'<rss version="2.0"><channel><item><title>Concierto de primavera</title><link>https://cultura.example/concierto</link></item><item><title>Festival local</title><link>https://cultura.example/festival</link></item></channel></rss>'
        cached=events.extract_event({'title':'Taller previo','link':'https://cultura.example/taller',
            'ev_startdate':'2026-11-10'},SOURCE,NOW)
        for location in ('','   ',{'name':''},{'name':' \t '}):
            with self.subTest(location=location),tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/'events.json'
                out.write_text(json.dumps(events.merge_events(None,[cached],[],NOW)))
                def page(url,source):
                    return '<script type="application/ld+json">'+json.dumps({'@type':'Event',
                        'url':url,'startDate':'2026-11-04',
                        'location':location if url.endswith('/concierto') else {'name':'Teatro'}})+'</script>'
                with patch.object(collect_events,'load_sources',return_value=[SOURCE]), \
                     patch.object(collect_events,'fetch_feed',return_value=rss), \
                     patch.object(collect_events,'fetch_event_page',side_effect=page):
                    self.assertEqual(collect_events.main(['--out',str(out),'--generation','2026-10-25T12:00:00Z']),0)
                doc=json.loads(out.read_text())
                events.validate_document(doc)
                self.assertEqual(len(doc['items']),3)
                self.assertEqual(doc['pending'],[])
                by_url={item['url']:item for item in doc['items']}
                self.assertIsNone(by_url['https://cultura.example/concierto']['location'])
                self.assertEqual(by_url['https://cultura.example/festival']['location'],'Teatro')
                self.assertIn(cached['url'],by_url)
                self.assertEqual(doc['sources'][0]['status'],'ok')
                self.assertFalse(out.with_name('events.json.tmp').exists())

    def test_feed_no_redirects_and_bounded_body(self):
        class Response:
            status_code=302
            def close(self): pass
            def iter_content(self,chunk_size):yield b'never'
        with patch.object(collect_events.collect,'is_public_host',return_value=True),patch.object(collect_events.requests,'get',return_value=Response()) as get:
            with self.assertRaises(ValueError):collect_events.fetch_feed(SOURCE['url'])
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
        Response.status_code=200
        with patch.object(collect_events.collect,'is_public_host',return_value=True),patch.object(collect_events.requests,'get',return_value=Response()),patch.object(collect_events,'FEED_BYTE_LIMIT',3):
            with self.assertRaises(ValueError):collect_events.fetch_feed(SOURCE['url'])

    def test_cli_corrupt_history_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'events.json';out.write_text('{corrupt')
            with self.assertRaises(ValueError):collect_events.main(['--out',str(out),'--catalog',str(ROOT/'sources/feeds.opml'),'--config',str(ROOT/'sources/events.json')])
            self.assertEqual(out.read_text(),'{corrupt')
            out.unlink()
            with patch.object(collect_events,'fetch_feed',side_effect=OSError('offline')):
                collect_events.main(['--out',str(out),'--catalog',str(ROOT/'sources/feeds.opml'),'--config',str(ROOT/'sources/events.json'),'--generation','2026-10-25T12:00:00Z'])
            doc=json.loads(out.read_text())
            self.assertEqual(doc['generated_at'],'2026-10-25T12:00:00Z')
            self.assertEqual(doc['items'],[])
            self.assertTrue(doc['sources'])
            events.validate_document(doc)

    def test_generation_from_metadata_and_invalid_generation_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'events.json';meta=Path(temp)/'meta.json'
            meta.write_text(json.dumps({'generated_at':'2026-10-25T12:00:00Z'}))
            argv=['--out',str(out),'--catalog',str(ROOT/'sources/feeds.opml'),'--config',str(ROOT/'sources/events.json'),'--generation-from',str(meta)]
            with patch.object(collect_events,'fetch_feed',side_effect=OSError('offline')):
                collect_events.main(argv)
            self.assertEqual(json.loads(out.read_text())['generated_at'],'2026-10-25T12:00:00Z')
            before=out.read_text();meta.write_text('{"generated_at":"tomorrow"}')
            with self.assertRaises(ValueError):collect_events.main(argv)
            self.assertEqual(out.read_text(),before)

if __name__=='__main__':unittest.main()
