#!/usr/bin/env python3
"""BindCraft Stage 2 pre-flight compatibility gate (canonical module).

Runs INSIDE the isolated Python 3.10 BindCraft conda env on the Colab GPU
runtime. Exit 0 = environment compatible; any failure -> exit 1 BEFORE the
AlphaFold weights download and before any BindCraft trajectory.

Version policy (evidence: reports/stage2_environment_failure_001.md,
BUG 001-003 in reports/stage2_reliability_consolidation.md):

- Python 3.10.x, jax/jaxlib >=0.4,<=0.6.0 (jax.lib.xla_bridge removed in
  JAX 0.8.0), numpy<2, flax<0.10, pinned ColabDesign, PyRosetta import.
- clear_mem() and a direct jax.lib.xla_bridge.get_backend() must succeed.
- Default backend must be gpu; a real 2048x2048 fp32 matmul must run on a
  GPU. For all-ones A with A@A, EACH output element equals 2048 (we test an
  element ~2048; the sum is 2048**3 but that is a weaker, different check).
- jax.Array.devices() returns set[Device] (not indexable); device
  collections are always iterated, never indexed.
- Downstream probes that cannot run are reported as SKIP, never as extra
  synthetic root failures.

Stdlib-only at import time so the policy functions are unit-testable on a
machine without JAX.
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
MATMUL_SIZE = 2048
MATMUL_REL_TOL = 1e-3


def parse_version(text):
    nums = []
    tail = text.strip().split("+", 1)[0].split("-", 1)[0]
    for part in tail.split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        if not num:
            break
        nums.append(int(num))
    return tuple(nums)


def check_bounded(name, version, lo, hi):
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
                       f"removed in JAX 0.8.0 (failure mode of BUG 001 with "
                       f"Colab JAX 0.11.1)")
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


def gpu_devices(devices):
    """GPU devices from ANY iterable collection.

    jax.devices() returns a list; jax.Array.devices() returns set[Device]
    (BUG 002). Always iterate; indexing a set raises TypeError.
    """
    return [d for d in devices if getattr(d, "platform", None) == "gpu"]


def array_on_gpu(array):
    try:
        return bool(gpu_devices(array.devices()))
    except Exception:
        return False


def run_gpu_matmul_check(jax, jnp, size=MATMUL_SIZE):
    """Real GPU compute probe. Returns (ok, detail, info).

    Verifies: default backend == gpu; size x size fp32 A@A completes; each
    output element ~= size (all-ones product, NOT size**3 which is the sum);
    result resident on at least one GPU device (iterated, never indexed).
    """
    backend = jax.default_backend()
    info = {"backend": backend, "size": size,
            "expected_element": size, "expected_sum": float(size ** 3)}
    if backend != "gpu":
        return False, f"JAX default backend is {backend!r}, expected 'gpu'", info
    a = jnp.ones((size, size), dtype=jnp.float32)
    c = (a @ a).block_until_ready()
    element = float(c[0, 0])               # each element of ones@ones == size
    devices = list(c.devices())            # set[Device]: iterate, never index
    gpu_devs = [str(d) for d in gpu_devices(devices)]
    elem_ok = abs(element - size) / size < MATMUL_REL_TOL
    info.update({"element_value": element, "element_ok": elem_ok,
                 "devices": [str(d) for d in devices], "gpu_devices": gpu_devs})
    if not elem_ok:
        return False, (f"matmul element wrong: c[0,0]={element} "
                       f"expected ~{size}"), info
    if not gpu_devs:
        return False, (f"matmul result not resident on any GPU device: "
                       f"devices={info['devices']}"), info
    return True, (f"backend=gpu; {size}x{size} fp32 A@A; element c[0,0]="
                  f"{element:.1f} ~ {size}; resident on GPU {gpu_devs}"), info


def _result(checks, name, ok, detail):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def _skip(skipped, name, reason):
    skipped.append({"check": name, "status": "SKIP", "detail": reason})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write JSON report to this path too")
    args = ap.parse_args(argv)

    checks, skipped = [], []
    report = {"passed": False, "checks": checks, "skipped": skipped,
              "versions": {}, "gpu": {}}

    _result(checks, "python", *check_python(platform.python_version()))

    jax = jnp = None
    try:
        jax = importlib.import_module("jax")
        import jax.numpy as jnp
        report["versions"]["jax"] = jax.__version__
        _result(checks, "jax_version",
                *check_bounded("jax", jax.__version__, JAX_MIN, JAX_MAX))
    except Exception as exc:
        _result(checks, "jax_import", False, f"import jax failed: {exc!r}")

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
        report["xla_bridge"] = {"platform": backend.platform,
                                "platform_version": backend.platform_version}
        _result(checks, "xla_bridge_get_backend", True,
                f"{backend.platform} {backend.platform_version}")
    except Exception as exc:
        _result(checks, "xla_bridge_get_backend", False,
                f"jax.lib.xla_bridge.get_backend() failed: {exc!r}")

    if jax is not None:
        devices = jax.devices()
        gpus = gpu_devices(devices)
        report["gpu"] = {
            "platform": gpus[0].platform if gpus else None,
            "device_kind": gpus[0].device_kind if gpus else None,
            "n_gpu": len(gpus),
            "all_devices": [f"{d.platform}:{d.device_kind}" for d in devices],
        }
        gpu_visible = _result(checks, "gpu_visible", len(gpus) >= 1,
                              report["gpu"]["all_devices"])
        if jnp is not None and gpu_visible:
            try:
                ok, detail, info = run_gpu_matmul_check(jax, jnp)
                report["gpu"]["matmul"] = info
                _result(checks, "trivial_gpu_matmul", ok, detail)
            except Exception as exc:
                _result(checks, "trivial_gpu_matmul", False,
                        f"GPU matmul failed: {exc!r}")
        else:
            _skip(skipped, "trivial_gpu_matmul",
                  "jax.numpy or GPU unavailable above; see the real failed "
                  "check (jax_import / gpu_visible) for the root cause")
    else:
        _skip(skipped, "gpu_visible",
              "jax unavailable; root cause is the jax_import failure above")
        _skip(skipped, "trivial_gpu_matmul",
              "jax unavailable; root cause is the jax_import failure above")

    try:
        pyrosetta = importlib.import_module("pyrosetta")
        report["versions"]["pyrosetta"] = getattr(
            pyrosetta, "__version__", "installed (version attr absent)")
        _result(checks, "pyrosetta_import", True, "pyrosetta imports")
    except Exception as exc:
        _result(checks, "pyrosetta_import", False,
                f"import pyrosetta failed: {exc!r}")

    report["versions"]["python"] = platform.python_version()
    report["passed"] = bool(checks) and all(c["ok"] for c in checks)

    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
