"""Generate compatibility jobs from the supported native host profiles."""

import argparse
import json
import re


HOSTS = (
    ("darwin/arm64", "macos-latest", "", ""),
    ("darwin/amd64", "macos-15-intel", "", ""),
    ("linux/amd64", "ubuntu-latest", "", ""),
    ("linux/arm64", "ubuntu-24.04-arm", "", ""),
    ("windows-msvc/amd64", "windows-2022", "msvc", "amd64"),
    ("windows-mingw/amd64", "windows-2022", "mingw", "amd64"),
    ("windows-msvc/386", "windows-2022", "msvc", "386"),
    ("windows-mingw/386", "windows-2022", "mingw", "386"),
    ("windows-msvc/arm64", "windows-11-arm", "msvc", "arm64"),
    ("windows-mingw/arm64", "windows-11-arm", "mingw", "arm64"),
)


def host_jobs():
    return [dict(platform=p, os=os, windows_abi=abi, windows_arch=arch)
            for p, os, abi, arch in HOSTS]


def native_matrix():
    return {"include": [{
        **host,
        "shard-index": str(index),
        "shard-total": "8",
        "paired-shard-index": str((index + 4) % 8),
    } for host in host_jobs() for index in range(8)]}


def regression_matrix():
    """One job per runtime/ABI risk, rather than per corpus shard."""
    native_cases = {
        "linux/amd64": ("fixedbugs/bug347.go", "fixedbugs/issue79186.go"),
        "linux/arm64": ("fixedbugs/bug347.go", "fixedbugs/issue79186.go", "tinyfin.go", "uintptrescapes3.go"),
        "darwin/amd64": ("inline_caller.go", "inline_callers.go", "abi/uglyfib.go", "rangegen.go"),
        "windows-msvc/arm64": ("env.go", "inline_caller.go", "tinyfin.go", "uintptrescapes3.go", "fixedbugs/issue79186.go"),
        "windows-mingw/arm64": ("env.go", "inline_caller.go", "tinyfin.go", "uintptrescapes3.go", "fixedbugs/issue79186.go"),
    }
    jobs = [dict(**host, go_version="1.27", wasm_profile="", case_paths=native_cases[host["platform"]])
            for host in host_jobs() if host["platform"] in native_cases]
    intel = next(job for job in jobs if job["platform"] == "darwin/amd64")
    jobs.append(dict(intel, go_version="1.26"))
    js_cases = ("clearfat.go", "stackobj2.go", "winbatch.go", "fixedbugs/issue79186.go", "fixedbugs/issue22662.go", "fixedbugs/issue5856.go", "rangegen.go", "fixedbugs/issue38093.go")
    wasi_cases = ("gcstring.go", "gcgort.go", "winbatch.go", "fixedbugs/issue34395.go", "fixedbugs/issue31419.go", "fixedbugs/issue14646.go", "fixedbugs/issue4618.go", "rangegen.go", "fixedbugs/issue78081.go")
    jobs.extend(dict(platform=profile, os="ubuntu-24.04", windows_abi="", windows_arch="", go_version="1.27",
                     wasm_profile=profile, case_paths=wasi_cases if profile == "W32-WASI" else js_cases)
                for profile in ("J32-GoJS", "J32-Emscripten", "J64-Emscripten", "W32-WASI"))
    for job in jobs:
        job["cases"] = "^(" + "|".join(re.escape(path) for path in job["case_paths"]) + ")$"
        job["artifact"] = job["platform"].replace("/", "-") + "-go" + job["go_version"]
    return {"include": jobs}


def std_matrix():
    jobs = []
    for host in host_jobs():
        platform = host["platform"]
        total = 2 if platform in ("linux/amd64", "windows-msvc/arm64") else 1
        common = dict(**host, llvm=22, lane="full", go_version="1.27",
                      host_go_arch="arm64" if host["windows_arch"] == "arm64" else "x64" if host["windows_arch"] else "",
                      check_symbols=platform == "linux/amd64", std_buildmodes=platform == "linux/amd64")
        jobs.extend(dict(**common, shard_index=str(i), shard_total=str(total)) for i in range(total))
        if platform == "linux/amd64":
            jobs.append(dict(common, lane="compatibility", go_version="1.20-1.26",
                             shard_index="0", shard_total="1", std_buildmodes=False))
    return {"include": jobs}


def embedded_matrix():
    return {"include": [dict(**host, mode="build-only" if host["os"] == "windows-11-arm" else "emulator")
                        for host in host_jobs()]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("goroot", "std", "embedded", "regressions"))
    suite = parser.parse_args().suite
    matrix = {"goroot": native_matrix, "std": std_matrix, "embedded": embedded_matrix, "regressions": regression_matrix}[suite]()
    print(json.dumps(matrix, separators=(",", ":")))
