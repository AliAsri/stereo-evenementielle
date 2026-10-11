from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.motion_review import validate_review,SCHEMA,TARGET


class MotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.manifest=dict(schema=SCHEMA,target=TARGET,manifest_id='abc',width=640,height=480,
            clips=[dict(id='c',start_us=0,end_us=60000,step_us=20000,window_us=20000,
                        frames=[dict(start_us=t-20000,end_us=t) for t in (20000,40000,60000)])])
        self.annotation=dict(clip_id='c',state='unknown',roi_xyxy=[10,20,40,80],frame_interval=[0,2],
            reviewed=True,annotator='test',notes='Synthetic test only',camera_state='unknown',
            source='manual_blind_event_clip',roi_valid_for_whole_interval=True)
        self.document=dict(schema=SCHEMA,target=TARGET,manifest_id='abc',annotations=[])

    def test_empty_is_pending_not_a_negative(self):
        self.assertEqual(validate_review(self.manifest,self.document)['status'],'PENDING_REVIEW')

    def test_explicit_unknown_not_counted_as_static(self):
        self.document['annotations']=[self.annotation]
        self.assertEqual(validate_review(self.manifest,self.document)['counts'],dict(moving=0,static=0,unknown=1))

    def test_mismatched_manifest_and_target_rejected(self):
        for key in ('schema','target','manifest_id'):
            d=deepcopy(self.document);d[key]='wrong'
            with self.assertRaises(ValueError):validate_review(self.manifest,d)

    def test_unreviewed_or_unsupported_label_rejected(self):
        for key,value in (('reviewed',False),('notes',''),('annotator',''),('source','prediction'),
                          ('roi_valid_for_whole_interval',False),('camera_state','auto')):
            a=deepcopy(self.annotation);a[key]=value;self.document['annotations']=[a]
            with self.assertRaises(ValueError):validate_review(self.manifest,self.document)

    def test_bad_roi_and_interval_rejected(self):
        for key,value in (('roi_xyxy',[0,0,0,10]),('roi_xyxy',[0,0,641,10]),
                          ('roi_xyxy',[float('nan'),0,20,30]),('frame_interval',[0,3]),
                          ('frame_interval',[2,1]),('frame_interval',[False,2])):
            a=deepcopy(self.annotation);a[key]=value;self.document['annotations']=[a]
            with self.assertRaises(ValueError):validate_review(self.manifest,self.document)

    def test_missing_frame_rejected_and_inputs_unchanged(self):
        before=deepcopy(self.manifest);validate_review(self.manifest,self.document)
        self.assertEqual(self.manifest,before)
        self.manifest['clips'][0]['frames'].pop(1)
        with self.assertRaises(ValueError):validate_review(self.manifest,self.document)


if __name__=='__main__':unittest.main()
