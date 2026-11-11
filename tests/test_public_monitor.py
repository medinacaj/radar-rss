"""Offline regression tests for the Pages health monitor."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_public_health import assess, MAX_ERRORS, STALE_HOURS

NOW = datetime(2026, 10, 18, 13, tzinfo=timezone.utc)
def docs(age=1, errors=0):
    stamp = (NOW - timedelta(hours=age)).isoformat().replace("+00:00", "Z")
    return ({"generated_at": stamp, "total_articles": 2300},
            {"checked_at": stamp,
             "feeds": [{"state": "error" if i < errors else "ok"} for i in range(150)]})

class MonitorTests(unittest.TestCase):
    def test_accepts_normal_publication(self):
        self.assertEqual(assess(*docs(), NOW, "success"), [])
        self.assertEqual(assess(*docs(errors=MAX_ERRORS - 1), NOW), [])

    def test_alerts_for_staleness_and_errors(self):
        reports = assess(*docs(age=STALE_HOURS + 1, errors=MAX_ERRORS), NOW)
        self.assertTrue(any("sin actualizar" in x for x in reports), reports)
        self.assertTrue(any("fuentes RSS" in x for x in reports), reports)

    def test_names_and_causes_are_reported_without_injected_newlines(self):
        meta, status = docs(errors=MAX_ERRORS)
        status["feeds"][0].update(name="Fuente Prueba", error="HTTP 403\nALERTA falsa")
        alerts = assess(meta, status, NOW)
        self.assertTrue(any("Fuente Prueba: HTTP 403 ALERTA falsa" in x for x in alerts), alerts)
        self.assertTrue(any("fuentes RSS con errores" in x for x in alerts), alerts)
        self.assertEqual(len(alerts), MAX_ERRORS + 1, alerts)

    def test_superseded_deploy_does_not_trigger_false_alarm(self):
        self.assertEqual(assess(*docs(), NOW, 'cancelled'), [])
        self.assertEqual(assess(*docs(), NOW, 'skipped'), [])

    def test_alerts_when_latest_deploy_fails(self):
        self.assertTrue(any("failure" in x for x in assess(*docs(), NOW, "failure")))

    def test_rejects_malformed_feed_status_without_crashing(self):
        for malformed in (None, "unexpected", {}, {"state": ""}, {"state": None}):
            with self.subTest(malformed=malformed):
                meta, status = docs()
                status["feeds"][0] = malformed
                reports = assess(meta, status, NOW)
                self.assertTrue(any("sin estado válido" in x for x in reports), reports)

    def test_rejects_boolean_article_count(self):
        meta, status = docs()
        meta["total_articles"] = True
        self.assertTrue(any("Historial público" in x for x in assess(meta, status, NOW)))

    def test_rejects_missing_or_inconsistent_metadata(self):
        meta, status = docs()
        del meta["generated_at"]
        self.assertTrue(assess(meta, status, NOW))
        meta, status = docs()
        status["feeds"] = []
        self.assertTrue(assess(meta, status, NOW))

if __name__ == "__main__":
    unittest.main()
