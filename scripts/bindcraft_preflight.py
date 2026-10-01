#!/usr/bin/env python3
"""BindCraft Stage 2 pre-flight compatibility gate.

Runs INSIDE the isolated Python 3.10 BindCraft conda env on the Colab GPU
runtime. Exit code 0 = environment is compatible; the smoke workflow may
proceed. Any failure -> exit 1 BEFORE the AlphaFold weights download and
before any BindCraft trajectory.

Version policy (evidence: reports/stage2_environment_failure_001.md):

- Python 3.10.x: upstream install_bindcraft.sh (BindCraft 7713aa0) creates a
  python=3.10 conda env. Python 3.13 cannot satisfy the pinned stack because
  numpy<2 has no cp313 wheels.
- jax/jaxlib >=0.4,<=0.6.0: ColabDesign's clear_mem() calls
  jax.lib.xla_bridge.get_backend(); those deprecated modules were removed in
  JAX 0.8.0 (2025-10-15). Colab's rolling image (JAX 0.11.1 on
  Python 3.13.15) therefore crashes inside the official PDL1 example.
- numpy<2 and flax<0.10: exact upstream pins.
- A GPU device must be visible to JAX and a trivial op must execute on it.

Stdlib-only at import time; jax/colabdesign are imported inside main() so the
policy functions are unit-testable on a machine without JAX.
"""
import argparse
import importlib
import importlib.metadata
import json
import platform
import sys

JAX_MIN = (0, 4)
JAX_MAX = (0, 6, 0)          # inclusive; xla_bridge removed in 0.8.0
PYTHON_REQUIRED = (3, 10)
NUMPY_MAX_MAJOR = 2          # numpy < 2.0
FLAX_MAX = (0, 10)           # flax < 0.10


def parse_version(text):
    """Parse leading dotted numeric version, ignoring dev/local suffixes."""
    nums = []
    tail = text.strip().split("+", 1)[0].split("-", 1)[0]
    for part in tail.split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        if not num:
            break
        nums.append(int(num))
    return tuple(nums)


def check_bounded(name, version, lo, hi):
    """lo <= version <= hi with component-wise tuple comparison."""
    v = parse_version(version)
    pad = max(len(v), len(lo), len(hi))
    vp = v + (0,) * (pad - len(v))
    lop = lo + (0,) * (pad - len(lo))
    hip = hi + (0,) * (pad - len(hi))
    if vp < lop:
        return False, f"{name} {version} below required >={'.'.join(map(str, lo))}"
    if vp > hip:
        return (False, f"{name} {version} ABOVE supported maximum "
                       f"<={'.'.join(map(str, hi))}; jax.lib.xla_bridge was "
                       f"removed in JAX 0.8.0 (this is the failure mode of "
                       f"environment failure 001 with Colab JAX 0.11.1)")
    return True, f"{name} {version} within [{'.'.join(map(str, lo))}," \
                 f"{'.'.join(map(str, hi))}]"


def check_python(version_text):
    vi = sys.version_info[:2]
    ok = vi == PYTHON_REQUIRED
    return ok, (f"python {version_text} -> {vi[0]}.{vi[1]} "
                f"(required {PYTHON_REQUIRED[0]}.{PYTHON_REQUIRED[1]}.x)")


def check_upper(name, version, forbidden):
    v = parse_version(version)
    ok = v < forbidden
    return ok, (f"{name} {version} "
                f"({'<' if ok else 'NOT <'}{'.'.join(map(str, forbidden))})")


def _result(checks, name, ok, detail):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write JSON report to this path too")
    args = ap.parse_args(argv)

    checks = []
    report = {"passed": False, "checks": checks, "versions": {}, "gpu": {}}

    _result(checks, "python", *check_python(platform.python_version()))

    jax = None
    try:
        jax = importlib.import_module("jax")
        import jax.numpy as jnp
        report["versions"]["jax"] = jax.__version__
        _result(checks, "jax_version",
                *check_bounded("jax", jax.__version__, JAX_MIN, JAX_MAX))
    except Exception as exc:  # environment must be treated as failed
        _result(checks, "jax_import", False, f"import jax failed: {exc!r}")
        jnp = None

    try:
        jaxlib_ver = importlib.metadata.version("jaxlib")
        report["versions"]["jaxlib"] = jaxlib_ver
        _result(checks, "jaxlib_version",
                *check_bounded("jaxlib", jaxlib_ver, JAX_MIN, JAX_MAX))
    except Exception as exc:
        _result(checks, "jaxlib_version", False,
                f"jaxlib distribution not found: {exc!r}")

    try:
        import numpy
        report["versions"]["numpy"] = numpy.__version__
        _result(checks, "numpy_below_2",
                *check_upper("numpy", numpy.__version__, (NUMPY_MAX_MAJOR, 0)))
    except Exception as exc:
        _result(checks, "numpy", False, f"import numpy failed: {exc!r}")

    try:
        flax_ver = importlib.metadata.version("flax")
        report["versions"]["flax"] = flax_ver
        _result(checks, "flax_below_0_10",
                *check_upper("flax", flax_ver, FLAX_MAX))
    except Exception as exc:
        _result(checks, "flax", False, f"flax distribution not found: {exc!r}")

    try:
        colabdesign = importlib.import_module("colabdesign")
        cd_ver = getattr(colabdesign, "__version__",
                         importlib.metadata.version("colabdesign"))
        report["versions"]["colabdesign"] = cd_ver
        _result(checks, "colabdesign_import", True,
                f"colabdesign {cd_ver} imports")
    except Exception as exc:
        _result(checks, "colabdesign_import", False,
                f"import colabdesign failed: {exc!r}")
        cd_ver = None

    # The exact call that crashed in failure 001:
    # colabdesign.shared.utils.clear_mem -> jax.lib.xla_bridge.get_backend()
    try:
        from colabdesign import clear_mem
        clear_mem()
        _result(checks, "clear_mem", True,
                "colabdesign.clear_mem() completed (jax.lib.xla_bridge alive)")
    except Exception as exc:
        _result(checks, "clear_mem", False, f"clear_mem() failed: {exc!r}")

    try:
        import jax.lib.xla_bridge as xla_bridge
        backend = xla_bridge.get_backend()
        report["xla_bridge"] = {
            "platform": backend.platform,
            "platform_version": backend.platform_version,
        }
        _result(checks, "xla_bridge_get_backend", True,
                f"{backend.platform} {backend.platform_version}")
    except Exception as exc:
        _result(checks, "xla_bridge_get_backend", False,
                f"jax.lib.xla_bridge.get_backend() failed: {exc!r}")

    if jax is not None:
        devices = jax.devices()
        gpus = [d for d in devices if d.platform == "gpu"]
        report["gpu"] = {
            "platform": gpus[0].platform if gpus else None,
            "device_kind": gpus[0].device_kind if gpus else None,
            "n_gpu": len(gpus),
            "all_devices": [f"{d.platform}:{d.device_kind}" for d in devices],
        }
        _result(checks, "gpu_visible", len(gpus) >= 1,
                report["gpu"]["all_devices"])

        matmul_ok = False
        if jnp is not None and gpus:
            try:
                x = jnp.ones((2048, 2048), dtype=jnp.float32)
                y = (x @ x).sum().block_until_ready()
                value = float(y)
                on_gpu = y.devices()[0].platform == "gpu"
                expected = float(2048 ** 3)
                matmul_ok = abs(value - expected) / expected < 1e-3 and on_gpu
                _result(checks, "trivial_gpu_matmul", matmul_ok,
                        f"2048x2048 matmul sum={value:.1f} on {y.devices()[0]}")
            except Exception as exc:
                _result(checks, "trivial_gpu_matmul", False,
                        f"GPU matmul failed: {exc!r}")
        if not matmul_ok:
            _result(checks, "trivial_gpu_matmul", False,
                    "GPU matmul not executed (jax or GPU unavailable above)")

    try:
        pyrosetta = importlib.import_module("pyrosetta")
        report["versions"]["pyrosetta"] = getattr(
            pyrosetta, "__version__", "installed (version attr absent)")
        _result(checks, "pyrosetta_import", True, "pyrosetta imports")
    except Exception as exc:
        _result(checks, "pyrosetta_import", False,
                f"import pyrosetta failed: {exc!r}")

    # guarantee every probe is reported even when earlier imports aborted
    recorded = {c["check"] for c in checks}
    for required in ("jax_import", "gpu_visible", "trivial_gpu_matmul"):
        if required not in recorded:
            _result(checks, required, False,
                    "not executed because an earlier prerequisite failed")

    report["versions"]["python"] = platform.python_version()
    report["passed"] = all(c["ok"] for c in checks)

    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
