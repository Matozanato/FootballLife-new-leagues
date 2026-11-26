"""Optional PyO3 tools from mod-manager-rust: CPK archives, textures, models and animations.

Mod Studio runs without them: available() is False when the module was not built, and the
pages that use them say so. Nothing here writes sider.ini."""
import json
import os

import functools

try:
    from . import _fl27mm as _raw
except ImportError:
    _raw = None


class NativeError(RuntimeError):
    """A Rust panic, reported as an ordinary error the worker already handles."""


def _is_panic(error):
    # pyo3_runtime.PanicException derives from BaseException, so a plain
    # `except Exception` in the worker never sees it and the window stays busy.
    return type(error).__name__ == "PanicException"


class _Guarded:
    """Every native call goes through here, so a panic can never escape as a
    BaseException. KeyboardInterrupt and SystemExit are left alone."""

    def __init__(self, module):
        self._module = module

    def __getattr__(self, name):
        target = getattr(self._module, name)
        if not callable(target):
            return target

        @functools.wraps(target)
        def call(*args, **kwargs):
            try:
                return target(*args, **kwargs)
            except BaseException as error:
                if _is_panic(error):
                    raise NativeError(
                        f"The native tool failed on this file ({name}): {error}"
                    ) from None
                raise

        setattr(self, name, call)
        return call


_fl27mm = _Guarded(_raw) if _raw is not None else None





def available():
    return _fl27mm is not None


def cpk_inspect(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.cpk_inspect(os.fspath(path))


def cpk_extract(path, output, filter_text=None):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.cpk_extract(os.fspath(path), os.fspath(output), filter_text)


def cpk_pack(source, destination, compress=True):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.cpk_pack(os.fspath(source), os.fspath(destination), compress)


def convert_texture(source, destination):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.convert_texture(os.fspath(source), os.fspath(destination))


def archive_map(archive, depth=3):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.archive_map(os.fspath(archive), depth))


def texture_info(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.texture_info(os.fspath(path))


def texture_preview(path, level=0):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    width, height, rgba = _fl27mm.texture_preview(os.fspath(path), level)
    return width, height, bytes(rgba)


def convert_textures(input_path, output_path, kind="diffuse"):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.convert_textures(
        os.fspath(input_path), os.fspath(output_path), kind
    ))


def assets_list(root, limit=600, family=None):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.assets_list(os.fspath(root), limit, family))


def asset_preview(model, view="three-quarter", size=512):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.asset_preview(os.fspath(model), view, size)


def asset_replace(path, width, height, rgba):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.asset_replace(
        os.fspath(path), width, height, rgba
    ))


def animation_report(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.animation_report(os.fspath(path)))


def animation_set_key(path, unit, segment, key, parts, signs):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.animation_set_key(
        os.fspath(path), unit, segment, key, parts, signs
    ))


def animation_set_rate(path, rate):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.animation_set_rate(os.fspath(path), rate)


def rig_inspect(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.rig_inspect(os.fspath(path))
