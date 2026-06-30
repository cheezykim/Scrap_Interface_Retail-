import unittest

from app.scraper.parser import extract_info_from_text, has_structured_fields


class StructuredMessageParserTests(unittest.TestCase):
    def test_extracts_multiline_report(self):
        text = """Type: Visit
Call Plan: Follow up
Direction: North
Client Name: Dara Sok
Contact: 012345678
Category: Retail"""

        self.assertEqual(
            extract_info_from_text(text),
            {
                "Type": "Visit",
                "Call Plan": "Follow up",
                "Direction": "North",
                "Client Name": "Dara Sok",
                "Contact": "012345678",
                "Category": "Retail",
            },
        )

    def test_splits_labels_written_inline(self):
        text = "Type: Call Client Name: Chanthy Contact: 099 111 222"

        parsed = extract_info_from_text(text)

        self.assertEqual(parsed["Type"], "Call")
        self.assertEqual(parsed["Client Name"], "Chanthy")
        self.assertEqual(parsed["Contact"], "099 111 222")

    def test_accepts_supported_bullets_and_separators(self):
        text = "• Type： Visit\n- Direction – South\n* Category — SME"

        parsed = extract_info_from_text(text)

        self.assertEqual(parsed["Type"], "Visit")
        self.assertEqual(parsed["Direction"], "South")
        self.assertEqual(parsed["Category"], "SME")

    def test_keeps_continuation_lines_as_one_value(self):
        parsed = extract_info_from_text(
            "Call Plan: Call customer\nagain tomorrow\nCategory: Existing"
        )

        self.assertEqual(parsed["Call Plan"], "Call customer again tomorrow")

    def test_unstructured_message_is_not_a_report(self):
        text = "Customer visited the branch today."

        self.assertFalse(has_structured_fields(text))
        self.assertTrue(all(value == "" for value in extract_info_from_text(text).values()))


if __name__ == "__main__":
    unittest.main()
