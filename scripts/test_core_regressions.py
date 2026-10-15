import re
import unittest

from check_core_regressions import check_results
from compatibility_matrix import regression_matrix


class CoreRegressionTests(unittest.TestCase):
    def test_selection_is_small_and_covers_runtime_variants(self):
        jobs = regression_matrix()["include"]
        self.assertEqual(10, len(jobs))
        self.assertEqual({"1.26", "1.27"}, {j["go_version"] for j in jobs if j["platform"] == "darwin/amd64"})
        self.assertEqual({"J32-GoJS", "J32-Emscripten", "J64-Emscripten", "W32-WASI"}, {j["wasm_profile"] for j in jobs if j["wasm_profile"]})
        for job in jobs:
            with self.subTest(platform=job["platform"]):
                self.assertLessEqual(len(job["case_paths"]), 9 if job["wasm_profile"] == "W32-WASI" else 8)
                if job["wasm_profile"] == "W32-WASI":
                    self.assertTrue({"gcstring.go", "gcgort.go"} <= set(job["case_paths"]))
                if job["wasm_profile"].startswith("J"):
                    self.assertIn("stackobj2.go", job["case_paths"])
                self.assertNotIn("/", job["artifact"])
                pattern = re.compile(job["cases"])
                self.assertTrue(all(pattern.fullmatch(path) for path in job["case_paths"]))
                self.assertIsNone(pattern.fullmatch(job["case_paths"][0].replace(".go", "Xgo")))

    def test_failures_and_classified_skips_cannot_pass(self):
        for result in ("expected-fail", "flaky-fail", "not-applicable", "host-skip", "resource-fail"):
            with self.subTest(result=result):
                self.assertTrue(check_results(f"GOROOT_CASE_RESULT\ta.go\trun\t{result}", ["a.go"]))

    def test_actual_success_is_required_for_every_selected_case(self):
        log = "GOROOT_CASE_RESULT\ta.go\trun\tpass\nGOROOT_CASE_RESULT\tb.go\trun\tflaky-pass"
        self.assertEqual([], check_results(log, ["a.go", "b.go"]))
        self.assertTrue(check_results(log, ["a.go", "b.go", "c.go"]))
        self.assertTrue(check_results(log + "\n" + log, ["a.go", "b.go"]))


if __name__ == "__main__":
    unittest.main()
