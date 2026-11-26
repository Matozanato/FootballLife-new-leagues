"""Optional PyO3 tools from mod-manager-rust: CPK archives, textures, models and animations,
the game map, PES tables, WESYS containers, binaries and menu flows.

Mod Studio runs without them: available() is False when the module was not built, and the
pages that use them say so. Nothing here writes sider.ini. The calls that change a file in
place (patch_binary, menu_link, asset_replace, animation_set_*) are made by Game file tools
after a restore point of that file."""
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


def game_map(game):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.game_map(os.fspath(game)))


def explain_path(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.explain_path(path))


def pesdb_report(directory):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.pesdb_report(os.fspath(directory)))


def container_report(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.container_report(os.fspath(path)))


def container_unwrap(source, destination):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.container_unwrap(os.fspath(source), os.fspath(destination))


def container_rewrap(body, original, destination):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.container_rewrap(
        os.fspath(body), os.fspath(original), os.fspath(destination)
    ))


def inspect_binary(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.inspect_binary(os.fspath(path)))


def binary_hex(path, offset=0, length=512):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.binary_hex(os.fspath(path), offset, length)


def binary_section(path, index, length=512):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.binary_section(os.fspath(path), index, length)


def binary_section_table(path, index):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.binary_section_table(os.fspath(path), index))


def patch_binary(path, offset, hex_bytes):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.patch_binary(os.fspath(path), offset, hex_bytes))


def menu_check(root, bases=()):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.menu_check(os.fspath(root), [os.fspath(path) for path in bases]))


def menu_link(root, bases, screen, event, target):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.menu_link(
        os.fspath(root), [os.fspath(path) for path in bases], screen, event, target
    )


def menu_clone(root, screen, target):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.menu_clone(os.fspath(root), screen, target)


def menu_screen_path(root, screen):
    """the flow file menu_link rewrites for this screen (nothing is written), so a restore point
    of it can be taken first"""
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.menu_screen_path(os.fspath(root), screen)
