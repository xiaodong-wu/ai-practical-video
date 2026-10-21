import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skill/ai-practical-video/scripts'))
from editorial_audio import SAMPLE_RATE, duck_envelope, mix_audio, synth_bed


class EditorialAudio(unittest.TestCase):
    def test_deterministic_stereo_composition(self):
        a, accents = synth_bed(SAMPLE_RATE * 2, [.5, 1])
        b, _ = synth_bed(SAMPLE_RATE * 2, [.5, 1])
        self.assertEqual(a.shape, (SAMPLE_RATE * 2, 2))
        np.testing.assert_array_equal(a, b)
        self.assertGreater(np.max(np.abs(a[:, 0] - a[:, 1])), .01)
        self.assertEqual(float(np.max(np.abs(a[-1]))), 0)
        self.assertGreater(float(np.max(np.abs(accents))), 0)

    def test_speech_ducks_music(self):
        speech = np.zeros((SAMPLE_RATE * 4, 2))
        speech[SAMPLE_RATE:SAMPLE_RATE * 3] = .1
        levels = duck_envelope(speech)
        self.assertLess(float(levels[SAMPLE_RATE * 2]), float(levels[SAMPLE_RATE // 2]) * .5)
        self.assertGreater(float(levels[-1]), float(levels[SAMPLE_RATE * 2]))

    def test_rounding_tail_and_no_truncation(self):
        speech = np.full((SAMPLE_RATE, 2), .1)
        bed, mixed, meta = mix_audio(speech, SAMPLE_RATE + 1000)
        self.assertEqual(mixed.shape, (SAMPLE_RATE + 1000, 2))
        self.assertAlmostEqual(meta['rounding_tail_seconds'], 1000 / SAMPLE_RATE)
        np.testing.assert_allclose(mixed[:SAMPLE_RATE] - bed[:SAMPLE_RATE], speech, atol=1e-15)
        with self.assertRaisesRegex(ValueError, 'truncate'):
            mix_audio(speech, SAMPLE_RATE - 1)
        with self.assertRaisesRegex(ValueError, '40 ms'):
            mix_audio(speech, SAMPLE_RATE + 3000)

    def test_peak_ceiling(self):
        speech = np.full((SAMPLE_RATE, 2), .99)
        _, mixed, meta = mix_audio(speech, SAMPLE_RATE)
        self.assertLessEqual(float(np.max(np.abs(mixed))), .940000001)
        self.assertLess(meta['ceiling_gain'], 1)


if __name__ == '__main__':
    unittest.main()
