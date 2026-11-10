import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from queue_research.data import _read_pair, from_lobster_zip


class ReaderTests(unittest.TestCase):
    def pair(self, message, book):
        return _read_pair(io.StringIO(message),io.StringIO(book))

    def test_price_and_nanosecond_precision(self):
        x=self.pair('34200.000000123,4,1234,5,1000000,1\n',
                    '1000200,25,1000000,55\n')[0]
        self.assertEqual(x.time_ns,34200000000123)
        self.assertEqual(x.mid,1000100)
        self.assertEqual(x.side,1)
        self.assertEqual(x.imbalance,0.375)

    def test_row_pair_is_after_event_book(self):
        x=self.pair('34200.1,4,42,7,1000000,1\n',
                    '1000200,25,1000000,48\n')[0]
        self.assertEqual(x.bid_qty,48)
        self.assertEqual(x.kind,4)
        self.assertEqual(x.quantity,7)

    def test_read_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('AAPL_message_1.csv','34200.0,1,1,20,1000000,1\n')
                z.writestr('AAPL_orderbook_1.csv','1000200,55,1000000,90\n')
            self.assertEqual(len(from_lobster_zip(path)),1)

    def test_reject_misaligned_rows(self):
        with self.assertRaisesRegex(ValueError,'shorter'):
            self.pair('34200,1,1,20,1000000,1\n34201,1,2,20,1000000,1\n',
                      '1000200,55,1000000,90\n')

    def test_reject_crossed_book(self):
        with self.assertRaisesRegex(ValueError,'best quote'):
            self.pair('34200,1,1,20,1000000,1\n','1000000,55,1000100,90\n')

    def test_reject_out_of_order_time(self):
        with self.assertRaisesRegex(ValueError,'timestamp'):
            self.pair('34202,1,1,20,1000000,1\n34201,1,2,20,1000000,1\n',
                      '1000200,55,1000000,90\n'*2)

    def test_reject_wrong_schema(self):
        with self.assertRaisesRegex(ValueError,'columns'):
            self.pair('34200,1,1,20,1000000,1\n','1000200,55,1000000\n')

    def test_reject_unsupported_type(self):
        with self.assertRaisesRegex(ValueError,'invalid event'):
            self.pair('34200,9,1,20,1000000,1\n','1000200,55,1000000,90\n')

    def test_skip_auction_and_halt_without_shifting_alignment(self):
        x=self.pair('34200,7,0,0,0,-1\n34201,1,2,20,1000000,1\n',
                    '1000200,55,1000000,90\n'*2)
        self.assertEqual(len(x),1)
        self.assertEqual(x[0].seq,1)
        self.assertEqual(x[0].segment,1)

    def test_malformed_and_empty(self):
        with self.assertRaisesRegex(ValueError,'malformed'):
            self.pair('34200,1,NaN,20,1000000,1\n','1000200,55,1000000,90\n')
        with self.assertRaisesRegex(ValueError,'no usable'):
            self.pair('34200,7,0,0,0,-1\n','1000200,55,1000000,90\n')

    def test_reject_multiple_archive_pairs(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'multiple.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('message_1.csv','')
                z.writestr('message_2.csv','')
                z.writestr('orderbook_1.csv','')
            with self.assertRaisesRegex(ValueError,'exactly one'):
                from_lobster_zip(path)
