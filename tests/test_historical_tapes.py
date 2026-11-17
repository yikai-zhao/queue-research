"""Synthetic ZIP fixtures exercise the real-input gate, not finance results."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validate_historical_tapes", ROOT / "scripts/validate_historical_tapes.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_sample(folder: Path, ticker="AAPL", day="2012-06-21", count=120):
    name = ticker + "_" + day + "_34200000_57600000"
    path = folder / (name + ".zip")
    messages = []
    books = []
    for i in range(count):
        messages.append(str(34200 + i / 10) + ",1," + str(i + 1) + ",1,1000100,1")
        books.append("1000200,50,1000000,50")
    with ZipFile(path, "w") as archive:
        archive.writestr(name + "_message_1.csv", "\n".join(messages) + "\n")
        archive.writestr(name + "_orderbook_1.csv", "\n".join(books) + "\n")
    return path


class HistoricalTapeTests(unittest.TestCase):
    def test_single_day_does_not_imply_independent_day_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_sample(Path(tmp))
            report = module.evaluate([path], research=False, max_events=None)
            self.assertEqual(report["archive_count"], 1)
            self.assertFalse(report["independent_day_validation"])
            self.assertEqual(report["reports"][0]["data_quality"]["usable_events"], 120)
            self.assertEqual(report["reports"][0]["data_quality"]["spread_ticks_median"], 2)

    def test_two_dates_and_no_mislabeled_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = make_sample(Path(tmp), day="2012-06-21")
            b = make_sample(Path(tmp), day="2012-06-22")
            report = module.evaluate([a, b], research=False, max_events=60)
            self.assertTrue(report["independent_day_validation"])
            self.assertEqual(report["distinct_dates"], 2)
            self.assertTrue(all(r["data_quality"]["usable_events"] == 60
                                for r in report["reports"]))

    def test_duplicate_session_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_sample(Path(tmp))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                module.evaluate([path, path], research=False, max_events=60)

    def test_different_symbols_same_date_not_independent_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = make_sample(Path(tmp), ticker="AAPL")
            b = make_sample(Path(tmp), ticker="MSFT")
            report = module.evaluate([a, b], research=False, max_events=60)
            self.assertFalse(report["independent_day_validation"])


if __name__ == "__main__":
    unittest.main()
