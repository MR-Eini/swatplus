#!/usr/bin/env python3
"""Run one year of bundled Ames inputs in an isolated directory."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--require-console", action="store_true")
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    root = Path(__file__).resolve().parents[2]
    marker = "successfully completed"
    with tempfile.TemporaryDirectory(prefix="swatplus-smoke-") as work:
        model = Path(work) / "Ames_sub1"
        shutil.copytree(root / "refdata/Ames_sub1", model)
        for name in ("success.fin", "fort.6", "simulation.out"):
            (model / name).unlink(missing_ok=True)
        time_file = model / "time.sim"
        lines = time_file.read_text().splitlines()
        values = lines[2].split()
        year = values[1]
        values[0], values[2], values[3] = "0", "0", year
        lines[2] = " ".join(values)
        time_file.write_text("\n".join(lines) + "\n")
        print_file = model / "print.prt"
        lines = print_file.read_text().splitlines()
        values = lines[2].split()
        values[0], values[1], values[2], values[3], values[4] = "0", "0", year, "0", year
        lines[2] = " ".join(values)
        print_file.write_text("\n".join(lines) + "\n")
        result = subprocess.run([str(exe)], cwd=model, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, errors="replace", timeout=180)
        success = model / "success.fin"
        completed = success.exists() and marker in success.read_text(errors="replace").lower()
        console = marker in result.stdout.lower()
        report = dict(year=int(year), returncode=result.returncode,
                      fresh_success_fin=completed, stdout_completion=console,
                      fort6_present=(model / "fort.6").exists())
        print(json.dumps(report, indent=2), flush=True)
        if result.returncode != 0 or not completed or (args.require_console and not console):
            print(result.stdout[-12000:])
            print(result.stderr[-12000:])
            raise SystemExit("Ames smoke run failed")


if __name__ == "__main__":
    main()
