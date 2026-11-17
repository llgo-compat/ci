"""Keep every daily shard and its report generator on one compiler commit."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RevisionTests(unittest.TestCase):
    def test_every_llgo_checkout_uses_the_prepared_sha(self):
        for name in ("goroot", "std"):
            source = (ROOT / f".github/workflows/{name}.yml").read_text()
            jobs = dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)",
                                   source.split("jobs:\n", 1)[1], re.M | re.S))
            prepare = name + "-matrix"
            pinned = "${{ needs." + prepare + ".outputs.llgo-sha }}"
            self.assertIn("llgo-sha: ${{ steps.revision.outputs.sha }}", jobs[prepare])
            self.assertIn("uses: ./.github/actions/resolve-llgo", jobs[prepare])
            self.assertIn("ref: ${{ env.LLGO_REF }}", jobs[prepare])
            for job, body in jobs.items():
                with self.subTest(workflow=name, job=job):
                    if "repository: ${{ inputs.llgo_repository" in body:
                        self.assertIn("ref: " + pinned, body)
                        self.assertRegex(body, rf"needs:.*\b{prepare}\b")
                    if job.endswith("summary"):
                        self.assertIn('--revision "$LLGO_SHA"', body)
                        self.assertIn("/commit/$LLGO_SHA", body)
            if name == "goroot":
                self.assertIn("llgo_ref: " + pinned, jobs["core-regressions"])

    def test_each_uploaded_shard_records_its_actual_checkout(self):
        goroot = (ROOT / ".github/workflows/goroot.yml").read_text()
        std = (ROOT / ".github/workflows/std.yml").read_text()
        self.assertEqual(2, goroot.count('git rev-parse HEAD >"$report_dir/revision-$report_id.txt"'))
        self.assertIn('git rev-parse HEAD >"$report_dir/revision-$report_id.txt"', std)
        self.assertIn('git rev-parse HEAD >"$RUNNER_TEMP/revision.txt"', std)
        self.assertIn("${{ runner.temp }}/revision.txt", std)


if __name__ == "__main__":
    unittest.main()
