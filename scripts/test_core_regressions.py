import re
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from check_core_regressions import check_results
from compatibility_matrix import regression_matrix


class CoreRegressionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("go") and shutil.which("bash"), "requires Go and Bash")
    def test_runtime_build_modes_use_the_active_go_language_version(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/regressions.yml"
        step = workflow.read_text().split("      - name: Check runtime C build modes\n", 1)[1]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1].split("\n      - ", 1)[0])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".github").mkdir()
            (root / "dev").mkdir()
            (root / "go.mod").write_text("module example.com/test\n\ngo 1.20\n")
            (root / ".github/test-go.mod").write_text("module example.com/test\n\ngo 1.20\n")
            (root / ".github/test-go.sum").touch()
            # The real Go tool edits the staged module; the compile stand-in
            # rejects the original stale language version before any tests run.
            (root / "dev/test_std_buildmodes.sh").write_text(
                'set -eu\nversion="$(go env GOVERSION)"\n'
                'grep -Fx "go ${version#go}" "$LLGO_TEST_MODFILE"\n'
                'grep -F "github.com/xgo-dev/llgo/runtime =>" "$LLGO_TEST_MODFILE"\n')
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=root,
                                    env=dict(os.environ, RUNNER_TEMP=temp), text=True,
                                    capture_output=True, timeout=15)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_selection_is_small_and_covers_runtime_variants(self):
        jobs = regression_matrix()["include"]
        self.assertEqual(10, len(jobs))
        self.assertEqual({"1.26", "1.27"}, {j["go_version"] for j in jobs if j["platform"] == "darwin/amd64"})
        self.assertEqual({"J32-GoJS", "J32-Emscripten", "J64-Emscripten", "W32-WASI"}, {j["wasm_profile"] for j in jobs if j["wasm_profile"]})
        for job in jobs:
            with self.subTest(platform=job["platform"]):
                self.assertLessEqual(len(job["case_paths"]), 10 if job["wasm_profile"] == "W32-WASI" else 8)
                if job["wasm_profile"] == "W32-WASI":
                    self.assertTrue({"gcstring.go", "fixedbugs/issue79186.go"} <= set(job["case_paths"]))
                if job["platform"] == "darwin/amd64":
                    self.assertIn("ken/chan.go", job["case_paths"])
                if job["wasm_profile"].startswith("J"):
                    self.assertIn("stackobj2.go", job["case_paths"])
                self.assertNotIn("/", job["artifact"])
                pattern = re.compile(job["cases"])
                self.assertTrue(all(pattern.fullmatch(path) for path in job["case_paths"]))
                self.assertIsNone(pattern.fullmatch(job["case_paths"][0].replace(".go", "Xgo")))

    def test_wasi_gc_coverage_executes_the_bounded_regression(self):
        jobs = regression_matrix()["include"]
        wasi = next(job for job in jobs if job["wasm_profile"] == "W32-WASI")
        self.assertNotIn("gcgort.go", wasi["case_paths"])
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/regressions.yml").read_text()
        step = workflow.split("      - name: Run bounded WASI concurrent GC coverage\n", 1)[1].split("\n      - ", 1)[0]
        self.assertIn("if: matrix.wasm_profile == 'W32-WASI'", step)
        self.assertIn("test -target wasi -emulator", step)
        self.assertIn("-run '^TestGCConcurrentTypedMutation$' ./test/go", step)
        self.assertNotIn("continue-on-error", step)

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
