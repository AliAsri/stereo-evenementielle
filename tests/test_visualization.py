"""The demonstration can render without host-specific font files."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.visualization import load_demo_font


class DemoFontTests(unittest.TestCase):
    def test_preferred_font_is_preserved(self):
        with patch.object(ImageFont, 'truetype', return_value='preferred') as load:
            self.assertEqual(load_demo_font(18), 'preferred')
        load.assert_called_once_with('C:/Windows/Fonts/arial.ttf', 18)

    def test_missing_windows_font_uses_alternative(self):
        with patch.object(ImageFont, 'truetype', side_effect=[OSError(), 'alternative']) as load:
            self.assertEqual(load_demo_font(16), 'alternative')
        self.assertEqual(load.call_args.args, ('DejaVuSans.ttf', 16))

    def test_missing_font_files_still_allow_actual_text_rendering(self):
        original = ImageFont.truetype
        def without_font_files(path, *args, **kwargs):
            if isinstance(path, (str, Path)):
                raise OSError('No font files on this host')
            return original(path, *args, **kwargs)
        with patch.object(ImageFont, 'truetype', side_effect=without_font_files):
            font = load_demo_font(16)
            image = Image.new('RGB', (500, 50))
            ImageDraw.Draw(image).text((0, 0), 'Mobile estimé / indéterminé', font=font, fill='white')
        self.assertIsNotNone(image.getbbox())


if __name__ == '__main__':
    unittest.main()
