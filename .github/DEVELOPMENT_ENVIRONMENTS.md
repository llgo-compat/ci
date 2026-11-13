Mise and Pixi are checked daily against the same resolved LLGo main commit on
Linux amd64/arm64, macOS amd64/arm64, and native Windows amd64. A checkout path
containing spaces also exercises activation and build scripts. Workflow PRs
run the same matrix; manual runs can select another LLGo repository/ref.

Linux jobs can use Qiniu after the runner group is available to this repository:
set the repository variable `QINIU_LINUX_RUNNER` to the JSON labels supplied by
the runner administrator, for example `["qiniu","ubuntu-24.04-large"]`.
Without that variable, jobs use GitHub-hosted Ubuntu 24.04. No runner settings
are changed by this contribution. Windows/macOS retain their native hosted
images; the bare Qiniu Windows image needs additional toolchain qualification.
