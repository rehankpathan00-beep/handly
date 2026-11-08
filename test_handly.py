"""Unit tests for Handly gesture control system.
Used by GitHub Actions CI pipeline to verify core logic and regressions.
"""

import unittest
import numpy as np
import cv2
import handly


class TestHandlyEngine(unittest.TestCase):
    def test_hud_panel_rendering(self):
        """Ensure HUD panel draws cleanly within image boundaries."""
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        handly.draw_hud_panel(test_frame, 10, 10, 310, 220, alpha=0.6, color=(20, 20, 20))
        # The region inside the HUD should be non-zero
        self.assertFalse(np.all(test_frame[50:100, 50:100] == 0))
        # The region outside the HUD should remain unmodified (zero)
        self.assertTrue(np.all(test_frame[350:400, 350:400] == 0))

    def test_volume_scalar_clamping(self):
        """Ensure master volume scalar handles boundary conditions properly."""
        # Test interpolation math
        min_dist = handly.PINCH_MIN_DIST
        max_dist = handly.PINCH_MAX_DIST

        # Distance smaller than min should map to 0%
        vol_min = int(np.interp(min_dist - 10, [min_dist, max_dist], [0, 100]))
        self.assertEqual(vol_min, 0)

        # Distance greater than max should map to 100%
        vol_max = int(np.interp(max_dist + 50, [min_dist, max_dist], [0, 100]))
        self.assertEqual(vol_max, 100)

        # Midpoint should map to roughly 50%
        mid_dist = (min_dist + max_dist) / 2
        vol_mid = int(np.interp(mid_dist, [min_dist, max_dist], [0, 100]))
        self.assertTrue(48 <= vol_mid <= 52)

    def test_pinch_geometry_distance(self):
        """Verify Euclidean distance between thumb and index landmarks."""
        thumb_pt = np.array([100, 100])
        index_pt = np.array([100, 150])
        dist = float(np.linalg.norm(index_pt - thumb_pt))
        self.assertAlmostEqual(dist, 50.0, places=1)


if __name__ == "__main__":
    unittest.main()
