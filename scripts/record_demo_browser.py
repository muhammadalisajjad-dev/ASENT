#!/usr/bin/env python3
"""Drive the ASENT defense workflow through Firefox's built-in Marionette."""
import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time


class Marionette:
    def __init__(self, port, timeout=30):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = b""
        # Firefox sends its protocol version before accepting commands.
        self._read_message()
        self.command_id = 0
        result = self.command("WebDriver:NewSession", {
            "capabilities": {"alwaysMatch": {"acceptInsecureCerts": True}}
        })
        # Firefox 83's Marionette WebDriver:NewSession result can wrap the
        # session object in `value`, while other versions return it directly.
        # In the older response the value itself may be a scalar session ID,
        # so do not assume it is a mapping before calling .get().
        self.session_id = None
        if isinstance(result, dict):
            self.session_id = result.get("sessionId")
            value = result.get("value")
            if not self.session_id and isinstance(value, dict):
                self.session_id = value.get("sessionId")
            elif not self.session_id and isinstance(value, (str, int)):
                self.session_id = value
        elif isinstance(result, (str, int)):
            self.session_id = result
        if not self.session_id:
            raise RuntimeError("Firefox Marionette did not create a WebDriver session; NewSession response was %r" % (result,))
        self.session_id = str(self.session_id)

    def _read_message(self):
        while b":" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("Firefox closed the Marionette connection")
            self.buffer += chunk
        colon = self.buffer.index(b":")
        length = int(self.buffer[:colon])
        needed = colon + 1 + length
        while len(self.buffer) < needed:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("Firefox closed the Marionette connection mid-message")
            self.buffer += chunk
        payload = self.buffer[colon + 1:needed]
        self.buffer = self.buffer[needed:]
        return json.loads(payload.decode("utf-8"))

    def command(self, name, params=None):
        self.command_id += 1
        packet = [self.command_id, name, params or {}]
        encoded = json.dumps(packet, separators=(",", ":")).encode("utf-8")
        self.sock.sendall(str(len(encoded)).encode("ascii") + b":" + encoded)
        response = self._read_message()
        if not isinstance(response, list) or response[0] != self.command_id:
            raise RuntimeError("Unexpected Firefox Marionette response: %r" % (response,))
        error, result = response[1], response[2]
        if error:
            raise RuntimeError("Firefox Marionette %s: %s" % (name, error.get("message", error)))
        return result

    def js(self, script, args=None):
        result = self.command("WebDriver:ExecuteScript", {
            "script": script, "args": args or [], "newSandbox": True,
            "sandbox": "asent-record-demo"
        })
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        return result

    def js_async(self, script, args=None):
        result = self.command("WebDriver:ExecuteAsyncScript", {
            "script": script, "args": args or [], "newSandbox": True,
            "sandbox": "asent-record-demo"
        })
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        return result

    def navigate(self, url):
        self.command("WebDriver:Navigate", {"url": url})

    def close(self):
        try:
            self.command("WebDriver:DeleteSession")
        except Exception:
            pass
        self.sock.close()


def say(message):
    print("[BROWSER] " + message, flush=True)


def wait_js(driver, script, description, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if driver.js(script):
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for " + description)


def click_nav(driver, label):
    result = driver.js("""
      const b = [...document.querySelectorAll('button.nav-item')]
        .find(x => x.innerText.trim().replace(/\\s+/g,' ') === arguments[0]);
      if (!b) return false; b.click(); return true;
    """, [label])
    if not result:
        raise RuntimeError("The real UI navigation item was not found: " + label)
    time.sleep(1.4)


def click_safe_run(driver):
    result = driver.js("""
      const b = [...document.querySelectorAll('button.button.primary')]
        .find(x => x.innerText.includes('Run safe scenario') && !x.disabled);
      if (!b) return false; b.click(); return true;
    """)
    if not result:
        raise RuntimeError("The real 'Run safe scenario' UI action was not available")


def click_experiment(driver, title):
    result = driver.js("""
      const card = [...document.querySelectorAll('.experiment-card')]
        .find(x => x.querySelector('h3')?.innerText.trim() === arguments[0]);
      const b = card && [...card.querySelectorAll('button')]
        .find(x => x.innerText.includes('Run scenario') && !x.disabled);
      if (!b) return false; b.click(); return true;
    """, [title])
    if not result:
        raise RuntimeError("The bundled controlled reproduction UI action was not found: " + title)


def latest_run(driver):
    return driver.js_async("""
      const done = arguments[arguments.length - 1];
      fetch('/api/runs').then(r => r.json()).then(r => done(r[0] || null))
        .catch(e => done({__error: String(e)}));
    """)


def run_to_completion(driver, previous_id, label, timeout=900):
    say("Waiting for actual analysis completion: " + label)
    deadline = time.monotonic() + timeout
    seen_id = None
    while time.monotonic() < deadline:
        state = latest_run(driver)
        if state and state.get("run_id") != previous_id:
            seen_id = state.get("run_id")
            if state.get("lifecycle") in ("COMPLETE", "ERROR"):
                if state.get("lifecycle") == "ERROR":
                    raise RuntimeError("Analysis ended with an error: " + str(state.get("error")))
                say("Analysis complete; final decision: " + str(state.get("final_decision")))
                return state
        time.sleep(1.0)
    raise RuntimeError("Timed out waiting for " + label + (" (run " + str(seen_id) + ")" if seen_id else " to start"))


def visit_review_screens(driver, labels=("CAVR", "SATRA-RV", "SABLE", "Integrated evidence", "Final trust gate")):
    for label in labels:
        click_nav(driver, label)
        if label == "CAVR":
            wait_js(driver, "return !!document.querySelector('.detail-status, .empty')", "CAVR details")
        elif label == "SATRA-RV":
            wait_js(driver, "return !!document.querySelector('.detail-status, .empty')", "SATRA-RV results")
        elif label == "SABLE":
            wait_js(driver, "return !!document.querySelector('.detail-status, .empty')", "SABLE results")
        elif label == "Integrated evidence":
            wait_js(driver, "return !!document.querySelector('table tbody, .empty')", "integrated evidence")
        else:
            wait_js(driver, "return !!document.querySelector('.decision-banner')", "final trust gate")
        time.sleep(3.0)


def launch_firefox(url, startup_timeout=60):
    profile = tempfile.mkdtemp(prefix="asent-record-firefox-")
    # Firefox 83 reliably honors its explicit Marionette port. Prefer the
    # standard dedicated port, falling back to an available localhost port.
    port = 2828
    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", port))
    except OSError:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    finally:
        probe.close()
    command = ["firefox", "--no-remote", "--profile", profile,
               "--marionette", "--marionette-port", str(port), url]
    log = open("/tmp/asent-record-firefox.log", "w")
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
    deadline = time.monotonic() + startup_timeout
    driver = None
    last_error = None
    # The `firefox` command may be a wrapper that exits or changes state
    # before the browser child has opened Marionette. Keep polling the
    # selected port for the full startup window, independent of that PID.
    while time.monotonic() < deadline:
        try:
            # Do not attempt Marionette protocol reads until Firefox has
            # opened this exact port. The probe is only a TCP readiness check.
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                pass
            driver = Marionette(port, timeout=4)
            say("Marionette listening on 127.0.0.1:%d; WebDriver:NewSession succeeded" % port)
            break
        except (OSError, ValueError, RuntimeError) as exc:
            last_error = exc
            time.sleep(0.5)
    if driver is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        if process.poll() is None:
            process.wait()
        log.close()
        shutil.rmtree(profile, ignore_errors=True)
        raise RuntimeError("Could not launch and control Firefox with Marionette: %s. See /tmp/asent-record-firefox.log" % last_error)
    return process, profile, log, driver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=("full", "cavr", "satra", "sable", "integrated"), default="full")
    args = parser.parse_args()
    process = profile = log = driver = None
    try:
        say("Launching isolated Firefox with its built-in Marionette control port")
        process, profile, log, driver = launch_firefox(args.url)
        driver.navigate(args.url)
        wait_js(driver, "return !!document.querySelector('.app-shell')", "ASENT frontend to load", 90)
        say("Firefox is controlled; ASENT's actual UI is loaded")
        if args.smoke:
            return 0

        click_nav(driver, "Project intake")
        wait_js(driver, "return !!document.querySelector('textarea')", "Project intake context")
        time.sleep(3.0)

        click_nav(driver, "Live development")
        before = latest_run(driver)
        before_id = before.get("run_id") if before else None
        click_safe_run(driver)
        safe = run_to_completion(driver, before_id, "Normal first build")
        if args.mode == "full":
            visit_review_screens(driver)
        else:
            target = {"cavr":"CAVR", "satra":"SATRA-RV", "sable":"SABLE", "integrated":"Integrated evidence"}[args.mode]
            visit_review_screens(driver, (target,))

        if args.mode != "full":
            say("Defense replay capture finished on " + target)
            return 0

        click_nav(driver, "Experiment library")
        wait_js(driver, "return !!document.querySelector('.experiment-card')", "bundled experiments")
        # This exact title is supplied by the current scenarios/catalog.json.
        before_id = safe.get("run_id")
        click_experiment(driver, "Dormant capability violation")
        controlled = run_to_completion(driver, before_id, "Dormant capability violation controlled reproduction")
        say("Controlled reproduction source: " + str(controlled.get("evidence_source")))
        visit_review_screens(driver)
        say("Defense path finished on the current Final trust gate")
        return 0
    except Exception as exc:
        say("ERROR: " + str(exc))
        return 1
    finally:
        if driver:
            driver.close()
        if process:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                if process.poll() is None:
                    process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            if process.poll() is None:
                process.wait()
        if log:
            log.close()
        if profile:
            shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
