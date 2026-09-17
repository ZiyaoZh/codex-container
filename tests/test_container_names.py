"""Exercise launcher naming and reuse without a Docker daemon."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / "codex-container"
FAKE_DOCKER = r'''#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import sys

state_path = Path(os.environ["FAKE_DOCKER_STATE"])
state = json.loads(state_path.read_text()) if state_path.exists() else {}
args = sys.argv[1:]
action = args[0]
with Path(os.environ["FAKE_DOCKER_LOG"]).open("a") as log:
    log.write(json.dumps(args) + "\n")

if action == "ps":
    if os.environ.get("FAKE_DOCKER_PS_ERROR"):
        sys.exit("Cannot connect to the Docker daemon")
    filters = [args[i + 1] for i, arg in enumerate(args) if arg == "--filter"]
    for name, container in state.items():
        if not container.get("running", True):
            continue
        if "label=dev.codex-container.repo" in filters and "repo" not in container:
            continue
        print("\t".join((container["id"], name, "Up 2 minutes", container.get("repo", ""))))
elif action == "inspect":
    name = args[-1]
    if name not in state:
        sys.exit(1)
    container = state[name]
    template = args[args.index("--format") + 1]
    if template == "{{.State.Running}}":
        print(str(container.get("running", True)).lower())
    elif '"dev.codex-container.repo"' in template:
        print(container["repo"])
    elif '"dev.codex-container.workdir"' in template:
        print(container["workdir"])
    elif '"/var/run/docker.sock"' in template:
        print("")
    else:
        sys.exit("Unexpected inspect format: " + template)
elif action == "run":
    name = args[args.index("--name") + 1]
    if name in state:
        sys.exit("Container name already exists: " + name)
    labels = dict(args[i + 1].split("=", 1)
                  for i, arg in enumerate(args) if arg == "--label")
    state[name] = {
        "id": hashlib.sha256(name.encode()).hexdigest(),
        "repo": labels["dev.codex-container.repo"],
        "workdir": labels["dev.codex-container.workdir"],
        "mounts": [args[i + 1] for i, arg in enumerate(args) if arg == "-v"],
    }
    state_path.write_text(json.dumps(state))
    print(json.dumps({"action": action, "name": name, **state[name]}))
elif action == "exec":
    name = args[args.index("gosu") - 1]
    print(json.dumps({"action": action, "name": name, **state[name]}))
elif action == "stop":
    if os.environ.get("FAKE_DOCKER_STOP_ERROR"):
        sys.exit("Docker failed to stop the container")
    target = args[-1]
    name = next((name for name, container in state.items()
                 if target in (name, container["id"])), None)
    if name is None:
        sys.exit("No such container: " + target)
    del state[name]
    state_path.write_text(json.dumps(state))
    print(target)
else:
    sys.exit("Unexpected Docker command: " + action)
'''


class LauncherTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codex-container-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "abc"
        self.other_repo = self.root / "xyz" / "abc"
        self.repo.mkdir()
        self.other_repo.mkdir(parents=True)
        self.state_path = self.root / "containers.json"
        self.log_path = self.root / "docker-calls.jsonl"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        # Suppress host config/cache directory creation during these dry runs.
        for name, source in (("docker", FAKE_DOCKER), ("mkdir", "#!/bin/sh\nexit 0\n")):
            executable = bin_dir / name
            executable.write_text(source)
            executable.chmod(0o755)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("CODEX_")}
        self.env.update({
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_DOCKER_STATE": str(self.state_path),
            "FAKE_DOCKER_LOG": str(self.log_path),
        })

    def invoke(self, *args, cwd=None, variables=None, stdin=subprocess.DEVNULL):
        return subprocess.run(
            [str(LAUNCHER), "--no-docker", *args],
            cwd=cwd or self.repo,
            env={**self.env, **(variables or {})},
            stdin=stdin,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def launch(self, *args, **kwargs):
        result = self.invoke(*args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def state(self):
        return json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def docker_calls(self):
        return [json.loads(line) for line in self.log_path.read_text().splitlines()] \
            if self.log_path.exists() else []


class ContainerNameTests(LauncherTestCase):
    def test_same_basename_in_different_directories_creates_separate_containers(self):
        first = self.launch()
        second = self.launch(cwd=self.other_repo)
        self.assertEqual((first["action"], second["action"]), ("run", "run"))
        self.assertNotEqual(first["name"], second["name"])
        self.assertIn(f"{self.repo}:/workspace/repo", first["mounts"])
        self.assertIn(f"{self.other_repo}:/workspace/repo", second["mounts"])
        for repo, expected in ((self.repo, first), (self.other_repo, second)):
            reused = self.launch(cwd=repo)
            self.assertEqual(reused["action"], "exec")
            self.assertEqual(reused["name"], expected["name"])

    def test_equivalent_paths_reuse_the_same_container(self):
        first = self.launch()
        alias = self.root / "shortcut"
        alias.symlink_to(self.repo, target_is_directory=True)
        for path in (str(self.repo), "../abc/", str(alias)):
            with self.subTest(path=path):
                reused = self.launch("--repo", path)
                self.assertEqual(reused["action"], "exec")
                self.assertEqual(reused["name"], first["name"])
                self.assertEqual(reused["repo"], str(self.repo))
        reused = self.launch(variables={"CODEX_REPO_DIR": str(self.repo)})
        self.assertEqual(reused["action"], "exec")
        self.assertEqual(reused["name"], first["name"])

    def test_sanitized_basenames_do_not_collide(self):
        names = []
        for basename in ("a b", "a-b"):
            repo = self.root / basename
            repo.mkdir()
            created = self.launch("--repo", str(repo))
            self.assertEqual(created["action"], "run")
            self.assertRegex(created["name"], r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
            names.append(created["name"])
        self.assertNotEqual(*names)

    def test_legacy_container_does_not_block_another_repository(self):
        legacy = self.launch("--name", "codex-abc")
        created = self.launch(cwd=self.other_repo)
        self.assertEqual(created["action"], "run")
        self.assertNotEqual(created["name"], legacy["name"])
        self.assertEqual(self.launch("--name", "codex-abc")["action"], "exec")

    def test_name_option_overrides_environment_name(self):
        variables = {"CODEX_CONTAINER_NAME": "environment-name"}
        first = self.launch("--name", "custom-name", variables=variables)
        reused = self.launch("--name", "custom-name", variables=variables)
        self.assertEqual(first["name"], "custom-name")
        self.assertEqual(reused["name"], "custom-name")
        self.assertEqual(reused["action"], "exec")

    def test_environment_name_is_preserved(self):
        variables = {"CODEX_CONTAINER_NAME": "environment-name"}
        first = self.launch(variables=variables)
        reused = self.launch(variables=variables)
        self.assertEqual(first["name"], "environment-name")
        self.assertEqual(reused["name"], "environment-name")
        self.assertEqual(reused["action"], "exec")

    def test_explicit_name_conflict_does_not_reuse_another_repository(self):
        self.launch("--name", "shared-name")
        result = self.invoke("--name", "shared-name", cwd=self.other_repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Container name is already used for another repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
