"""Minimal `blender` command-line stand-in backed by the official `bpy` wheel (PyPI bpy==<pinned version>).

Used where download.blender.org is unreachable (cloud containers). Supports only what the pipeline uses:
    blender_shim.py [-b|--background] [--factory-startup] [--version] [-P script.py] [-- script args...]
Run it with the Python that has bpy installed, e.g.  ~/bpyenv/bin/python tools/render_bench/blender_shim.py ...
The bpy module is Blender itself (same Cycles/OIDN build); the script sees sys.argv with the usual "--" separator."""
import runpy
import sys


def main():
    argv = sys.argv[1:]
    rest = []
    if "--" in argv:
        i = argv.index("--")
        argv, rest = argv[:i], argv[i + 1:]
    script = None
    k = 0
    while k < len(argv):
        a = argv[k]
        if a in ("-P", "--python"):
            script = argv[k + 1]
            k += 2
            continue
        if a in ("--version", "-v"):
            import bpy
            print(f"Blender {bpy.app.version_string} (bpy module)")
            return 0
        k += 1  # -b, --factory-startup, --python-exit-code N are implicit/ignored
    if script is None:
        return 0
    import bpy  # noqa: F401  (initialise Blender before the script runs)
    sys.argv = ["blender", "-b", "-P", script, "--"] + rest
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
