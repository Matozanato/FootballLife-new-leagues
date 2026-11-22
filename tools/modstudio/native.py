"""Optional PyO3 tools supplied by the Rust mod manager."""
import json
import os

try:
    from . import _fl27mm
except ImportError:
    _fl27mm = None


def available():
    return _fl27mm is not None


def scan(ini_path, addons_path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.scan(os.fspath(ini_path), os.fspath(addons_path))


def verify(ini_path, addons_path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.verify(os.fspath(ini_path), os.fspath(addons_path))


def conflicts(packs_root):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.conflicts(os.fspath(packs_root))


def sorted_roots(ini_path, addons_path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.sorted_roots(os.fspath(ini_path), os.fspath(addons_path))


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


def game_map(game):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.game_map(os.fspath(game)))


def archive_map(archive, depth=3):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.archive_map(os.fspath(archive), depth))


def explain_path(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.explain_path(path))


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


def patch_binary(path, offset, hex_bytes):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.patch_binary(os.fspath(path), offset, hex_bytes))


def assets_list(root, limit=600):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.assets_list(os.fspath(root), limit))


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


def animation_read(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.animation_read(os.fspath(path))


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


def studio_tree(root):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_tree(os.fspath(root)))


def studio_read(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_read(os.fspath(path)))


def studio_write(path, text):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.studio_write(os.fspath(path), text)


def studio_new_pack(addons, name, kind):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_new_pack(os.fspath(addons), name, kind))


def studio_check_pack(directory, addons):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_check_pack(
        os.fspath(directory), os.fspath(addons)
    ))


def studio_install(source, addons):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_install(os.fspath(source), os.fspath(addons)))


def studio_entries(addons):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_entries(os.fspath(addons)))


def studio_kinds():
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_kinds())


def studio_create_file(path):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.studio_create_file(os.fspath(path))


def studio_rename(source, destination, workspace):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.studio_rename(
        os.fspath(source), os.fspath(destination), os.fspath(workspace)
    )


def studio_remove(path, workspace):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return _fl27mm.studio_remove(os.fspath(path), os.fspath(workspace))


def studio_edit(addons, key, value, mode, apply=False):
    if _fl27mm is None:
        raise RuntimeError("The Rust manager extension is not built")
    return json.loads(_fl27mm.studio_edit(
        os.fspath(addons), key, value, mode, apply
    ))
