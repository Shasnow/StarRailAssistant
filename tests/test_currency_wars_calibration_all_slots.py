"""Real-image regressions for all nine bench slots and all five shop slots."""
import hashlib
from collections import Counter
import json
from pathlib import Path
from tests.currency_wars_replays import REPLAY_ROOT, require_frames
import sys
import unittest
from unittest.mock import Mock
from PIL import Image
from test_currency_wars_calibration import ROOT, BATCH as FIRST_BATCH, CALIBRATION, ReplayOperator, vision
from test_currency_wars_flow import load_isolated_task, FakeOperator

BATCH = REPLAY_ROOT / "bench_shop_training"
HAND = [(x,.844) for x in (.229,.297,.358,.426,.488,.556,.618,.684,.749)]
STORE = [(x,.18) for x in (.25,.40,.55,.68,.80)]

class AllBenchShopCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_frames(*(BATCH / (state + "_client.png") for state in ("empty", "occupied")))
        require_frames(*(FIRST_BATCH / (name + "_client.png") for name in (
            "01_bench_right_occupied", "02_bench_right_empty", "03_shop_occupied", "04_shop_left_empty")))
        cls.frames = {}
        for state in ("empty","occupied"):
            with Image.open(BATCH/(state+"_client.png")) as image:
                cls.frames[state]=image.convert("RGB").copy()
        cls.holdouts=[]
        for name in ("01_bench_right_occupied","02_bench_right_empty",
                     "03_shop_occupied","04_shop_left_empty"):
            with Image.open(FIRST_BATCH/(name+"_client.png")) as image:
                cls.holdouts.append(image.convert("RGB").copy())
        cls.raw=json.loads((CALIBRATION/"profile.json").read_text(encoding="utf-8"))

    def detector(self,frame):
        return vision.CurrencyWarsVision(ReplayOperator(frame),CALIBRATION/"profile.json",
            BATCH/"unused-diagnostics",max_samples=0)

    def production_task(self):
        module,characters,logic,names=load_isolated_task()
        self.addCleanup(lambda:[sys.modules.pop(name,None) for name in names])
        operator=FakeOperator()
        operator.screenshot=lambda **kwargs:self.frames["empty"].copy()
        task=module.CurrencyWars(operator,runtimes=1)
        task._vision.max_samples=0
        return task,characters,logic


    def test_all_occupied_training_slots_are_not_empty(self):
        detector=self.detector(self.frames["occupied"])
        for area,positions in (("in_hand",HAND),("store",STORE)):
            for index,position in enumerate(positions):
                with self.subTest(area=area,index=index):
                    self.assertIs(detector.slot_is_empty(area,index,position),False)

    def test_all_empty_training_slots_are_empty(self):
        detector=self.detector(self.frames["empty"])
        for area,positions in (("in_hand",HAND),("store",STORE)):
            for index,position in enumerate(positions):
                with self.subTest(area=area,index=index):
                    self.assertIs(detector.slot_is_empty(area,index,position),True)

    def test_first_batch_mixed_bench_holdouts_are_correct(self):
        # Explicit visual review of the earlier four full images, left to right.
        occupied_sets=({0,1,2,8},{0,1,2,3},{0,1,2,3},{0,1,2,3,4})
        for frame_number,(frame,occupied) in enumerate(zip(self.holdouts,occupied_sets),1):
            detector=self.detector(frame)
            for index,position in enumerate(HAND):
                with self.subTest(frame=frame_number,index=index):
                    answer=detector.slot_is_empty("in_hand",index,position)
                    if index in occupied:self.assertIsNot(answer,True)
                    else:self.assertIs(answer,True)

    def test_first_batch_mixed_shop_holdouts_are_correct(self):
        for frame_number,occupied in ((2,set(range(5))),(3,{1,2,3,4})):
            detector=self.detector(self.holdouts[frame_number])
            for index,position in enumerate(STORE):
                with self.subTest(frame=frame_number+1,index=index):
                    answer=detector.slot_is_empty("store",index,position)
                    if index in occupied:self.assertIsNot(answer,True)
                    else:self.assertIs(answer,True)

    def test_all_shop_slots_are_unknown_when_shop_is_closed(self):
        for frame in self.holdouts[:2]:
            detector=self.detector(frame)
            for index,position in enumerate(STORE):
                self.assertIsNone(detector.slot_is_empty("store",index,position))

    def test_unfamiliar_occupied_portraits_do_not_need_to_match_a_character_template(self):
        # Huohuo/Wandi in the old batch differ from the new March7th/Herta controls.
        self.assertIsNone(self.detector(self.holdouts[0]).slot_is_empty("in_hand",8,HAND[8]))
        self.assertIsNone(self.detector(self.holdouts[2]).slot_is_empty("store",0,STORE[0]))


    def test_real_all_empty_frame_reaches_production_shop_empty_state(self):
        task,_,logic=self.production_task()
        result=task._scan_store()
        self.assertEqual(result.state,logic.ShopState.EMPTY)
        self.assertEqual(result.reason,"verified_empty_slots")

    def test_real_all_empty_frame_reaches_production_bench_empty_state(self):
        task,_,logic=self.production_task()
        for index in range(9):
            with self.subTest(index=index):
                observation=task._observe_slot("in_hand",index,count_stars=True)
                self.assertEqual(observation.state,logic.SlotState.EMPTY)

    def test_real_empty_bench_frame_can_confirm_sale_result_without_coin_guess(self):
        task,characters,logic=self.production_task()
        task.get_coins=Mock(return_value=None)
        result=task._confirm_sale(8,characters.Characters.get_character("藿藿"),None)
        self.assertEqual(result,logic.ActionResult.CONFIRMED)

    def test_training_originals_and_client_pixels_match_manifest(self):
        manifest=json.loads((BATCH/"input_manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["records"]:
            for kind in ("original","client"):
                self.assertEqual(hashlib.sha256((BATCH/entry[kind]).read_bytes()).hexdigest(),
                                 entry[kind+"_sha256"])
            with Image.open(BATCH/entry["original"]) as full, Image.open(BATCH/entry["client"]) as client:
                self.assertEqual(full.crop(tuple(entry["client_box"])).convert("RGB").tobytes(),
                                 client.convert("RGB").tobytes())





class ShippedSlotStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((CALIBRATION / "profile.json").read_text(encoding="utf-8"))

    def test_all_fourteen_slots_have_explicit_positive_and_negative_templates(self):
        expected={("in_hand",i) for i in range(9)}|{("store",i) for i in range(5)}
        self.assertEqual({(s["area"],s["index"]) for s in self.raw["slots"]},expected)
        self.assertEqual(self.raw["version"],2)
        self.assertTrue(all(slot.get("require_empty_structure") is True for slot in self.raw["slots"]))
        self.assertEqual(self.raw["window_size"],[1920,1080])
        self.assertEqual(self.raw["scale_tolerance"],0.0)
        vision.validate_profile(self.raw,CALIBRATION)

    def test_profile_positions_match_actual_production_coordinates(self):
        module,_,_,names = load_isolated_task()
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in names])
        task = module.CurrencyWars(FakeOperator(), runtimes=1)
        for slot in self.raw["slots"]:
            self.assertEqual(tuple(slot["position"]),getattr(task,slot["area"]+"_area")[slot["index"]])

    def test_flat_background_without_empty_marker_never_counts_as_empty(self):
        profile=vision.validate_profile(self.raw,CALIBRATION)
        for key,slot in profile.slots.items():
            sample=slot.empty_images[0]
            data=sample.tobytes()
            dominant=Counter(tuple(data[i:i+3]) for i in range(0,len(data),3)).most_common(1)[0][0]
            for color in (dominant,(0,0,0),(17,17,17),(32,32,43)):
                with self.subTest(slot=key,color=color):
                    blank=Image.new("RGB",sample.size,color)
                    self.assertIsNot(vision.CurrencyWarsVision._classify(blank,slot),True)

    def test_v2_profile_cannot_silently_omit_structure_guard(self):
        invalid=json.loads(json.dumps(self.raw))
        invalid["slots"][0].pop("require_empty_structure")
        with self.assertRaises(ValueError):
            vision.validate_profile(invalid,CALIBRATION)


if __name__=="__main__":
    unittest.main()
