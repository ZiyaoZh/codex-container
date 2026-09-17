"""Verify container listing, target selection, and stopping with a fake daemon."""

import json
import os
import pty
import unittest

from test_container_names import LauncherTestCase


class ContainerManagementTests(LauncherTestCase):
    def interactive_down(self, selection, **kwargs):
        master, slave = pty.openpty()
        try:
            os.write(master, selection.encode())
            return self.invoke("down", stdin=slave, **kwargs)
        finally:
            os.close(master)
            os.close(slave)

    def assert_stopped_only(self, container):
        stops = [call for call in self.docker_calls() if call[0] == "stop"]
        self.assertEqual(stops, [["stop", "--", container["id"]]])
        self.assertNotIn(container["name"], self.state())

    def assert_no_stop(self):
        self.assertFalse(any(call[0] == "stop" for call in self.docker_calls()))

    def test_list_shows_only_running_managed_containers(self):
        first = self.launch()
        second = self.launch("--name", "custom-session", cwd=self.other_repo)
        state = self.state()
        state["codex-unrelated"] = {"id": "1" * 64}
        state["stopped-session"] = {"id": "2" * 64, "repo": str(self.repo), "running": False}
        self.state_path.write_text(json.dumps(state))
        for command in ("list", "--list"):
            result = self.invoke(command, variables={"CODEX_REPO_DIR": "/missing-repo"})
            self.assertEqual(result.returncode, 0, result.stderr)
            for container in (first, second):
                self.assertIn(container["name"], result.stdout)
                self.assertIn(container["id"][:12], result.stdout)
                self.assertIn(container["repo"], result.stdout)
            self.assertIn("Up 2 minutes", result.stdout)
            self.assertNotIn("codex-unrelated", result.stdout)
            self.assertNotIn("stopped-session", result.stdout)
        self.assertEqual(state, self.state())

    def test_empty_list(self):
        result = self.invoke("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No running Codex containers", result.stdout)
        self.assertEqual([call[0] for call in self.docker_calls()], ["ps"])

    def test_noninteractive_down_defaults_to_current_repository(self):
        current = self.launch()
        other = self.launch(cwd=self.other_repo)
        result = self.invoke("down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(current)
        self.assertIn(other["name"], self.state())

    def test_enter_defaults_to_current_repository(self):
        self.launch(cwd=self.other_repo)
        current = self.launch()
        result = self.interactive_down("\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REPOSITORY", result.stdout)
        self.assertIn("Enter:", result.stderr)
        self.assert_stopped_only(current)

    def test_number_selects_another_repository(self):
        current = self.launch()
        other = self.launch(cwd=self.other_repo)
        result = self.interactive_down("2\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(other)
        self.assertIn(current["name"], self.state())

    def test_interactive_name_selects_another_repository(self):
        other = self.launch("--name", "other-session", cwd=self.other_repo)
        result = self.interactive_down("other-session\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(other)

    def test_numeric_id_can_be_selected_interactively(self):
        self.launch()
        other = self.launch(cwd=self.other_repo)
        state = self.state()
        other["id"] = "123456789012" + "a" * 52
        state[other["name"]]["id"] = other["id"]
        self.state_path.write_text(json.dumps(state))
        result = self.interactive_down("123456789012\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(other)

    def test_explicit_name_and_id_work_without_a_repository(self):
        for target_kind in ("name", "id"):
            with self.subTest(target_kind=target_kind):
                container = self.launch("--name", "custom-session")
                target = container["name"] if target_kind == "name" else container["id"][:12]
                result = self.invoke("down", target, variables={"CODEX_REPO_DIR": "/missing-repo"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(container["name"], self.state())

    def test_explicit_name_options_and_environment_are_respected(self):
        for args, variables in (
            (("down", "--name", "selected"), {"CODEX_CONTAINER_NAME": "wrong-name"}),
            (("--name", "selected", "--down"), {}),
            (("--down",), {"CODEX_CONTAINER_NAME": "selected"}),
        ):
            with self.subTest(args=args, variables=variables):
                selected = self.launch("--name", "selected", cwd=self.other_repo)
                result = self.invoke(*args, variables=variables)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(selected["name"], self.state())

    def test_repo_option_and_symlink_choose_the_same_directory(self):
        current = self.launch()
        other = self.launch(cwd=self.other_repo)
        alias = self.root / "shortcut"
        alias.symlink_to(self.other_repo, target_is_directory=True)
        result = self.invoke("down", "--repo", str(alias))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(other)
        self.assertIn(current["name"], self.state())

    def test_default_down_finds_legacy_or_custom_names(self):
        for name in ("codex-abc", "custom-session"):
            with self.subTest(name=name):
                self.launch("--name", name)
                result = self.invoke("down")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(name, self.state())

    def test_default_name_is_preferred_when_repository_has_multiple_containers(self):
        self.launch("--name", "custom-session")
        current = self.launch()
        result = self.invoke("down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_stopped_only(current)
        self.assertIn("custom-session", self.state())

    def test_ambiguous_repository_requires_selection(self):
        self.launch("--name", "one")
        self.launch("--name", "two")
        result = self.invoke("down")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Multiple running Codex containers", result.stderr)
        self.assert_no_stop()

    def test_missing_current_repository_is_a_noop(self):
        other = self.launch(cwd=self.other_repo)
        result = self.invoke("down")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No running Codex container for repository", result.stdout)
        self.assertIn(other["name"], self.state())
        self.assert_no_stop()

    def test_cancel_or_eof_does_not_stop_any_container(self):
        self.launch()
        for selection in ("q\n", "\x04"):
            with self.subTest(selection=selection):
                result = self.interactive_down(selection)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Cancelled", result.stdout)
        self.assert_no_stop()

    def test_invalid_selection_never_falls_back_to_current_repository(self):
        self.launch()
        for selection in ("0\n", "99\n", "999999999999999999999999\n", "missing\n"):
            with self.subTest(selection=selection):
                result = self.interactive_down(selection)
                self.assertNotEqual(result.returncode, 0)
        self.assert_no_stop()

    def test_unmanaged_or_missing_target_is_rejected(self):
        self.launch()
        state = self.state()
        state["codex-unrelated"] = {"id": "1" * 64}
        self.state_path.write_text(json.dumps(state))
        for target in ("codex-unrelated", "1" * 12, "missing"):
            result = self.invoke("down", target)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No running Codex container matches", result.stderr)
        self.assert_no_stop()

    def test_ambiguous_id_is_rejected(self):
        self.launch("--name", "one")
        self.launch("--name", "two")
        state = self.state()
        state["one"]["id"] = "a" * 64
        state["two"]["id"] = "a" * 63 + "b"
        self.state_path.write_text(json.dumps(state))
        result = self.invoke("down", "a" * 12)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambiguous", result.stderr)
        self.assert_no_stop()

    def test_invalid_command_combinations_are_rejected(self):
        for args in (("list", "extra"), ("down", "one", "two"),
                     ("--update", "list"), ("--update", "down"), ("list", "down")):
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertEqual(result.returncode, 2)
        self.assertEqual(self.docker_calls(), [])

    def test_container_commands_can_use_reserved_words_after_double_dash(self):
        for command in ("list", "down"):
            result = self.launch("--", command)
            self.assertIn(result["action"], ("run", "exec"))
            self.assertEqual(self.docker_calls()[-1][-1], command)
        self.assert_no_stop()

    def test_docker_errors_are_propagated(self):
        container = self.launch()
        for action in ("list", "down"):
            result = self.invoke(action, variables={"FAKE_DOCKER_PS_ERROR": "1"})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cannot connect", result.stderr)
        self.assert_no_stop()
        result = self.invoke("down", variables={"FAKE_DOCKER_STOP_ERROR": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed to stop", result.stderr)
        self.assertIn(container["name"], self.state())


if __name__ == "__main__":
    unittest.main()
