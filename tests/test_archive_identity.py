"""Adversarial input-pair identity tests for point-in-time research."""
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from queue_research.data import from_lobster_zip

M = '34200,1,42,10,1000100,1\n'
B = '1000200,50,1000000,50\n'

class ArchiveIdentityTests(unittest.TestCase):
    def paired(self, message_name, book_name, *, message=M, book=B):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        archive = Path(tmp.name) / 'events.zip'
        with ZipFile(archive, 'w') as z:
            z.writestr(message_name, message)
            z.writestr(book_name, book)
        return from_lobster_zip(archive)

    def test_matching_official_identity(self):
        rows = self.paired('AAPL_2012-06-21_34200000_57600000_message_1.csv',
                           'AAPL_2012-06-21_34200000_57600000_orderbook_1.csv')
        self.assertEqual(len(rows), 1)

    def test_reject_cross_ticker(self):
        with self.assertRaisesRegex(ValueError, 'different instruments|mismatched'):
            self.paired('AAPL_message_1.csv', 'MSFT_orderbook_1.csv')

    def test_reject_cross_date(self):
        with self.assertRaisesRegex(ValueError, 'different instruments|mismatched'):
            self.paired('AAPL_2012-06-21_34200000_57600000_message_1.csv',
                        'AAPL_2012-06-22_34200000_57600000_orderbook_1.csv')

    def test_reject_depth_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'depth|mismatched'):
            self.paired('AAPL_message_1.csv', 'AAPL_orderbook_10.csv',
                        book='1000200,50,1000000,50\n' * 1)

    def test_reject_incompatible_schema_depth(self):
        with self.assertRaisesRegex(ValueError, 'depth|columns'):
            self.paired('AAPL_message_5.csv', 'AAPL_orderbook_5.csv')

    def test_reject_bare_unidentifiable_archive(self):
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.paired('message.csv', 'orderbook.csv')

    def test_no_false_rejection_short_depth_sample(self):
        self.assertEqual(len(self.paired('AAPL_message_1.csv', 'AAPL_orderbook_1.csv')), 1)

if __name__ == '__main__': unittest.main()
