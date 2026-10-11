import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.residual_regions import group_residual_regions


class RegionTests(unittest.TestCase):
    def test_separated_groups_preserve_original_indices(self):
        p=[[10,10],[20,20],[30,30],[200,200],[400,400],[410,410],[420,420]]
        regions=group_residual_regions(p,[4,5,6,np.nan,4,5,6],model_valid=True)
        self.assertEqual([r['point_indices'] for r in regions],[[0,1,2],[4,5,6]])
        self.assertEqual(regions[0]['xyxy'],[2,2,38,38])

    def test_threshold_unknown_and_insufficient_support(self):
        self.assertEqual(group_residual_regions([[10,10],[11,11],[12,12],[13,13]],
            [3,3.1,np.nan,4],model_valid=True),[])

    def test_invalid_model_abstains(self):
        self.assertEqual(group_residual_regions([[10,10]]*3,[4]*3,model_valid=False),[])

    def test_bounds_clipped(self):
        regions=group_residual_regions([[638,478],[639,479],[637,477]],[4]*3,model_valid=True)
        self.assertEqual(regions[0]['xyxy'],[629,469,640,480])

    def test_dilation_can_join_distant_surfaces(self):
        # Historical M03 rule: dilated cell 0 and cell 3 touch with 8-connectivity.
        regions=group_residual_regions([[1,10],[2,10],[3,10],[97,10],[98,10],[99,10]],
                                       [4]*6,model_valid=True)
        self.assertEqual(len(regions),1);self.assertEqual(regions[0]['support_points'],6)

    def test_empty_and_invalid_inputs(self):
        self.assertEqual(group_residual_regions(np.empty((0,2)),[],model_valid=True),[])
        for p,r in [([[640,1]],[4]),([[1,1]],[-1]),([[1,1]],[float('inf')])]:
            with self.assertRaises(ValueError):group_residual_regions(p,r,model_valid=True)


if __name__=='__main__':unittest.main()
