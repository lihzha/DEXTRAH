#!/usr/bin/env python3
"""Download and convert MolmoAct2 bimanual YAM assets for DEXTRAH."""

from __future__ import annotations

import argparse
import math
import os
import shutil
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

from isaaclab.app import AppLauncher


HF_REPO_ID = "TreeePlanter/molmoact2-sim-eval-assets"
YAM_MJCF_NAME = "bimanual_yam_linear_flattened.xml"
YAM_ISAAC_MJCF_NAME = "bimanual_yam_linear_flattened_isaac.xml"
YAM_USD_NAME = "bimanual_yam_linear_flattened.usd"
SINGLE_YAM_MJCF_NAME = "yam_linear.xml"
SINGLE_YAM_ISAAC_MJCF_NAME = "yam_linear_isaac.xml"
SINGLE_YAM_USD_NAME = "yam_linear.usd"
YAM_ISAAC_MESH_DIR_NAME = "isaac_meshes"
MOLMOACT2_D405_RELATIVE_PATH = Path("assets/put_bottles/assets/i2rt_yam/assets/d405.stl")
MOLMOACT2_D405_LICENSE_RELATIVE_PATH = Path("assets/put_bottles/assets/i2rt_yam/LICENSE")
MOLMOACT2_D405_STL_NAME = "d405.stl"
MOLMOACT2_D405_OBJ_NAME = "d405.obj"
MOLMOACT2_D405_COLLISION_OBJ_NAME = "d405_collision.obj"
MOLMOACT2_WRIST_CAMERA_MOUNT_OBJ_NAME = "wrist_camera_mount.obj"
MOLMOACT2_WRIST_CAMERA_MOUNT_COLLISION_OBJ_NAME = "wrist_camera_mount_collision.obj"
MOLMOACT2_CAMERA_WIDTH = 640
MOLMOACT2_CAMERA_HEIGHT = 360
MOLMOACT2_TOP_CAMERA_HFOV_DEG = 69.4
MOLMOACT2_WRIST_CAMERA_HFOV_DEG = 87.0
MOLMOACT2_TOP_CAMERA_FOVY_DEG = 2.0 * math.degrees(
    math.atan((MOLMOACT2_CAMERA_HEIGHT / MOLMOACT2_CAMERA_WIDTH) * math.tan(math.radians(MOLMOACT2_TOP_CAMERA_HFOV_DEG) / 2.0))
)
MOLMOACT2_WRIST_CAMERA_FOVY_DEG = 2.0 * math.degrees(
    math.atan(
        (MOLMOACT2_CAMERA_HEIGHT / MOLMOACT2_CAMERA_WIDTH)
        * math.tan(math.radians(MOLMOACT2_WRIST_CAMERA_HFOV_DEG) / 2.0)
    )
)
MOLMOACT2_BIMANUAL_ARM_Y_OFFSET = 0.31
MOLMOACT2_TOP_CAMERA_BODY_POS = "0.15 0 0.8"
MOLMOACT2_TOP_CAMERA_BODY_QUAT = "0.7660444431189782 0 0.6427876096865391 0"
MOLMOACT2_WRIST_CAMERA_BODY_POS = "0 0.09 0.06"
MOLMOACT2_WRIST_CAMERA_BODY_QUAT = "0.612372429196013 -0.35355339154618404 -0.3535533966987049 -0.612372438120441"
MOLMOACT2_WRIST_CAMERA_BODY_MASS = "0.001"
MOLMOACT2_WRIST_CAMERA_BODY_INERTIA = "1e-6 1e-6 1e-6"
MOLMOACT2_WRIST_CAMERA_MOUNT_POS = "0 0.045 0.03"
MOLMOACT2_WRIST_CAMERA_MOUNT_QUAT = "1 0 0 0"
MOLMOACT2_TOP_CAMERA_BODY_NAME = "top_cam_mount"
YAM_FALLBACK_MASS_PROPS = {
    "bimanual_base": (1.0, (1.0e-2, 1.0e-2, 1.0e-2)),
    "left_arm": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "right_arm": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "left_link_6": (0.12, (1.0e-4, 1.0e-4, 1.0e-4)),
    "right_link_6": (0.12, (1.0e-4, 1.0e-4, 1.0e-4)),
    "top_cam_mount": (0.001, (1.0e-6, 1.0e-6, 1.0e-6)),
    "left_wrist_camera_mount": (0.001, (1.0e-6, 1.0e-6, 1.0e-6)),
    "right_wrist_camera_mount": (0.001, (1.0e-6, 1.0e-6, 1.0e-6)),
    "left_camera_d405": (0.001, (1.0e-6, 1.0e-6, 1.0e-6)),
    "right_camera_d405": (0.001, (1.0e-6, 1.0e-6, 1.0e-6)),
    "left_link_left_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "left_link_right_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "right_link_left_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "right_link_right_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
}
SINGLE_YAM_FALLBACK_MASS_PROPS = {
    "arm": (1.0, (1.0e-2, 1.0e-2, 1.0e-2)),
    "link_1": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "link_2": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "link_3": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "link_4": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "link_5": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "link_6": (0.12, (1.0e-4, 1.0e-4, 1.0e-4)),
    "link_left_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "link_right_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
}
YAM_ROBOT_SPECS = {
    "bimanual": {
        "mjcf_name": YAM_MJCF_NAME,
        "isaac_mjcf_name": YAM_ISAAC_MJCF_NAME,
        "usd_name": YAM_USD_NAME,
        "urdf_name": "bimanual_yam.urdf",
        "root_body": "bimanual_base",
        "fallback_mass_props": YAM_FALLBACK_MASS_PROPS,
    },
    "single": {
        "mjcf_name": SINGLE_YAM_MJCF_NAME,
        "isaac_mjcf_name": SINGLE_YAM_ISAAC_MJCF_NAME,
        "usd_name": SINGLE_YAM_USD_NAME,
        "urdf_name": "yam.urdf",
        "root_body": "arm",
        "fallback_mass_props": SINGLE_YAM_FALLBACK_MASS_PROPS,
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _assets_root() -> Path:
    return _repo_root() / "dextrah_lab" / "assets" / "yam"


def _download_assets(repo_id: str, force: bool) -> Path:
    assets_root = _assets_root()
    yam_mjcf_dir = assets_root / "yam_mujoco"
    source_xml = yam_mjcf_dir / YAM_MJCF_NAME
    if source_xml.is_file() and not force:
        print(f"YAM MJCF assets already present at {yam_mjcf_dir}")
        return yam_mjcf_dir

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is required to download MolmoAct2 YAM assets") from exc

    snapshot = Path(snapshot_download(repo_id=repo_id, repo_type="dataset"))
    source_assets = snapshot / "assets" / "yam"
    if not source_assets.is_dir():
        raise FileNotFoundError(f"Downloaded snapshot does not contain assets/yam: {snapshot}")

    if assets_root.exists() and force:
        for path in (
            assets_root / "yam_mujoco",
            assets_root / "yam_mjcf_usd",
            assets_root / "yam_urdf",
            assets_root / "yam_usd",
        ):
            if path.exists():
                shutil.rmtree(path)
    assets_root.mkdir(parents=True, exist_ok=True)
    # Several Slurm shards may reach first-time asset preparation together on a
    # shared NFS worktree.  Make the copy idempotent so a directory created by a
    # racing process does not fail the whole render.
    if yam_mjcf_dir.exists() and force:
        shutil.rmtree(yam_mjcf_dir)
    shutil.copytree(source_assets / "yam_mujoco", yam_mjcf_dir, dirs_exist_ok=True)
    if not source_xml.is_file():
        raise FileNotFoundError(f"Expected YAM MJCF after copy: {source_xml}")
    print(f"Installed YAM MJCF assets at {yam_mjcf_dir}")
    return yam_mjcf_dir


def _existing_env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_file() else None


def _candidate_d405_mesh_paths(mesh_dir: Path) -> list[Path]:
    candidates = [mesh_dir / "d405.stl"]
    env_path = _existing_env_path("MOLMOACT2_D405_MESH_PATH") or _existing_env_path("ABC_D405_MESH_PATH")
    if env_path is not None:
        candidates.append(env_path)
    candidates.extend(
        [
            _repo_root().parent / "abc" / MOLMOACT2_D405_RELATIVE_PATH,
            Path.home() / "code" / "abc" / MOLMOACT2_D405_RELATIVE_PATH,
        ]
    )
    return candidates


def _copy_d405_license(source_mesh_path: Path, target_license_path: Path) -> None:
    env_license_path = _existing_env_path("MOLMOACT2_D405_LICENSE_PATH") or _existing_env_path("ABC_D405_LICENSE_PATH")
    candidate_licenses = []
    if env_license_path is not None:
        candidate_licenses.append(env_license_path)
    candidate_licenses.extend(
        [
            source_mesh_path.parents[1] / "LICENSE" if len(source_mesh_path.parents) > 1 else source_mesh_path,
            _repo_root().parent / "abc" / MOLMOACT2_D405_LICENSE_RELATIVE_PATH,
            Path.home() / "code" / "abc" / MOLMOACT2_D405_LICENSE_RELATIVE_PATH,
        ]
    )
    for candidate in candidate_licenses:
        if candidate.is_file():
            shutil.copy2(candidate, target_license_path)
            return


def _export_d405_obj(stl_path: Path, obj_path: Path) -> None:
    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError("trimesh is required to convert the D405 STL to OBJ for Isaac MJCF import") from exc

    mesh = trimesh.load(str(stl_path), force="mesh")
    if mesh.is_empty:
        raise RuntimeError(f"D405 STL loaded as an empty mesh: {stl_path}")
    mesh.export(str(obj_path))


def _write_box_obj(path: Path, extents: tuple[float, float, float], center: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
    hx, hy, hz = (0.5 * float(value) for value in extents)
    cx, cy, cz = center
    vertices = (
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    )
    faces = ((1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 8, 4), (4, 8, 5, 1))
    lines = ["# Procedural collision mesh generated by prepare_yam_assets.py"]
    lines.extend(f"v {x:.9g} {y:.9g} {z:.9g}" for x, y, z in vertices)
    lines.extend(f"f {a} {b} {c} {d}" for a, b, c, d in faces)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _d405_collision_box_from_mesh(stl_path: Path) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    try:
        import trimesh
    except ImportError:
        return (0.044, 0.023, 0.042), (0.0, 0.0, 0.0)

    mesh = trimesh.load(str(stl_path), force="mesh")
    if mesh.is_empty:
        return (0.044, 0.023, 0.042), (0.0, 0.0, 0.0)
    extents = tuple(max(float(value), 1.0e-4) for value in mesh.bounding_box.extents)
    center = tuple(float(value) for value in mesh.bounding_box.centroid)
    return extents, center


def _ensure_d405_mesh(mesh_dir: Path) -> None:
    target_stl_path = mesh_dir / MOLMOACT2_D405_STL_NAME
    target_obj_path = mesh_dir / MOLMOACT2_D405_OBJ_NAME
    target_collision_path = mesh_dir / MOLMOACT2_D405_COLLISION_OBJ_NAME
    d405_obj_ready = target_obj_path.is_file()
    for candidate in _candidate_d405_mesh_paths(mesh_dir):
        if not candidate.is_file():
            continue
        if candidate.resolve() != target_stl_path.resolve():
            shutil.copy2(candidate, target_stl_path)
        _copy_d405_license(candidate, mesh_dir / "i2rt_yam_LICENSE")
        if not d405_obj_ready:
            _export_d405_obj(target_stl_path, target_obj_path)
            print(f"Copied D405 wrist camera mesh from {candidate} and exported {target_obj_path}")
        break
    if not target_obj_path.is_file():
        raise FileNotFoundError(
            "Missing D405 wrist camera mesh. Set MOLMOACT2_D405_MESH_PATH, ABC_D405_MESH_PATH, or place ABC at "
            f"{_repo_root().parent / 'abc'} so {MOLMOACT2_D405_RELATIVE_PATH} can be copied."
        )
    if not target_collision_path.is_file():
        extents, center = _d405_collision_box_from_mesh(target_stl_path)
        _write_box_obj(target_collision_path, extents, center)
        print(f"Generated D405 collision mesh at {target_collision_path}")


def _ensure_wrist_mount_meshes(mesh_dir: Path) -> None:
    mount_visual_path = mesh_dir / MOLMOACT2_WRIST_CAMERA_MOUNT_OBJ_NAME
    mount_collision_path = mesh_dir / MOLMOACT2_WRIST_CAMERA_MOUNT_COLLISION_OBJ_NAME
    if not mount_visual_path.is_file():
        _write_box_obj(mount_visual_path, (0.040, 0.085, 0.016))
        print(f"Generated wrist camera mount visual mesh at {mount_visual_path}")
    if not mount_collision_path.is_file():
        _write_box_obj(mount_collision_path, (0.038, 0.083, 0.014))
        print(f"Generated wrist camera mount collision mesh at {mount_collision_path}")


def _asset_child_with_name(asset: ET.Element, tag: str, name: str) -> ET.Element | None:
    for child in asset.findall(tag):
        if child.attrib.get("name") == name:
            return child
    return None


def _upsert_inertial(body: ET.Element) -> bool:
    inertial = body.find("inertial")
    expected = {
        "pos": "0 0 0",
        "mass": MOLMOACT2_WRIST_CAMERA_BODY_MASS,
        "diaginertia": MOLMOACT2_WRIST_CAMERA_BODY_INERTIA,
    }
    if inertial is None:
        body.insert(0, ET.Element("inertial", expected))
        return True

    changed = False
    for key, value in expected.items():
        if inertial.attrib.get(key) != value:
            inertial.attrib[key] = value
            changed = True
    return changed


def _upsert_named_child(parent: ET.Element, tag: str, attrib: dict[str, str]) -> tuple[ET.Element, bool]:
    name = attrib["name"]
    child = parent.find(f"./{tag}[@name='{name}']")
    if child is None:
        child = ET.SubElement(parent, tag, attrib)
        return child, True

    changed = False
    for key, value in attrib.items():
        if child.attrib.get(key) != value:
            child.attrib[key] = value
            changed = True
    return child, changed


def _remove_named_children(parent: ET.Element, tag: str, name: str) -> bool:
    changed = False
    for child in list(parent):
        if child.tag == tag and child.attrib.get("name") == name:
            parent.remove(child)
            changed = True
    return changed


def _upsert_mesh_asset(asset: ET.Element, name: str, file_name: str) -> bool:
    mesh = _asset_child_with_name(asset, "mesh", name)
    if mesh is None:
        ET.SubElement(asset, "mesh", {"name": name, "file": file_name})
        return True
    if mesh.attrib.get("file") != file_name:
        mesh.attrib["file"] = file_name
        return True
    return False


def _insert_wrist_mount_body(link_6: ET.Element, prefix: str) -> bool:
    mount_body, changed = _upsert_named_child(
        link_6,
        "body",
        {
            "name": f"{prefix}_wrist_camera_mount",
            "pos": MOLMOACT2_WRIST_CAMERA_MOUNT_POS,
            "quat": MOLMOACT2_WRIST_CAMERA_MOUNT_QUAT,
        },
    )
    changed = _upsert_inertial(mount_body) or changed
    for geom_attrib in (
        {
            "name": f"{prefix}_wrist_camera_mount_visual",
            "type": "mesh",
            "contype": "0",
            "conaffinity": "0",
            "group": "2",
            "density": "0",
            "material": "camera_black",
            "mesh": "wrist_camera_mount",
        },
        {
            "name": f"{prefix}_wrist_camera_mount_collision",
            "type": "mesh",
            "group": "4",
            "mesh": "wrist_camera_mount_collision",
        },
    ):
        _, geom_changed = _upsert_named_child(mount_body, "geom", geom_attrib)
        changed = geom_changed or changed
    return changed


def _insert_wrist_camera_body(link_6: ET.Element, prefix: str) -> bool:
    changed = False
    camera_body = link_6.find(f"./body[@name='{prefix}_camera_d405']")
    if camera_body is None:
        camera_body = ET.Element(
            "body",
            {
                "name": f"{prefix}_camera_d405",
                "pos": MOLMOACT2_WRIST_CAMERA_BODY_POS,
                "quat": MOLMOACT2_WRIST_CAMERA_BODY_QUAT,
            },
        )
        children = list(link_6)
        insert_index = len(children)
        for index, child in enumerate(children):
            if child.tag == "body" and "finger" in child.attrib.get("name", ""):
                insert_index = index
                break
        link_6.insert(insert_index, camera_body)
        changed = True
    for key, value in {
        "pos": MOLMOACT2_WRIST_CAMERA_BODY_POS,
        "quat": MOLMOACT2_WRIST_CAMERA_BODY_QUAT,
    }.items():
        if camera_body.attrib.get(key) != value:
            camera_body.attrib[key] = value
            changed = True

    changed = _upsert_inertial(camera_body) or changed
    changed = _remove_named_children(camera_body, "body", f"{prefix}_camera_frame") or changed
    for geom_attrib in (
        {
            "name": f"{prefix}_camera_d405_visual",
            "type": "mesh",
            "contype": "0",
            "conaffinity": "0",
            "group": "2",
            "density": "0.001",
            "mass": "0.001",
            "material": "camera_black",
            "mesh": "camera_d405",
        },
        {
            "name": f"{prefix}_camera_d405_collision",
            "type": "mesh",
            "group": "4",
            "mesh": "camera_d405_collision",
        },
    ):
        _, geom_changed = _upsert_named_child(camera_body, "geom", geom_attrib)
        changed = geom_changed or changed
    _, camera_changed = _upsert_named_child(
        camera_body,
        "camera",
        {
            "name": f"{prefix}_cam",
            "pos": "0 0 0",
            "quat": "1 0 0 0",
            "fovy": f"{MOLMOACT2_WRIST_CAMERA_FOVY_DEG:.9g}",
        },
    )
    return camera_changed or changed


def _insert_top_camera_body(base_body: ET.Element) -> bool:
    camera_body, changed = _upsert_named_child(
        base_body,
        "body",
        {
            "name": MOLMOACT2_TOP_CAMERA_BODY_NAME,
            "pos": MOLMOACT2_TOP_CAMERA_BODY_POS,
            "quat": MOLMOACT2_TOP_CAMERA_BODY_QUAT,
        },
    )
    changed = _upsert_inertial(camera_body) or changed
    _, camera_changed = _upsert_named_child(
        camera_body,
        "camera",
        {
            "name": "top_cam",
            "pos": "0 0 0",
            "quat": "1 0 0 0",
            "fovy": f"{MOLMOACT2_TOP_CAMERA_FOVY_DEG:.9g}",
        },
    )
    return camera_changed or changed


def _apply_molmoact2_bimanual_setup(source_xml: Path) -> None:
    mesh_dir = source_xml.parent / "assets"
    _ensure_d405_mesh(mesh_dir)
    _ensure_wrist_mount_meshes(mesh_dir)

    tree = ET.parse(source_xml)
    root = tree.getroot()
    asset = root.find("asset")
    if asset is None:
        raise ValueError(f"Missing asset block in {source_xml}")

    changed = False
    if _asset_child_with_name(asset, "material", "camera_black") is None:
        ET.SubElement(asset, "material", {"name": "camera_black", "rgba": "0.22 0.22 0.24 1"})
        changed = True
    for mesh_name, file_name in (
        ("camera_d405", MOLMOACT2_D405_OBJ_NAME),
        ("camera_d405_collision", MOLMOACT2_D405_COLLISION_OBJ_NAME),
        ("wrist_camera_mount", MOLMOACT2_WRIST_CAMERA_MOUNT_OBJ_NAME),
        ("wrist_camera_mount_collision", MOLMOACT2_WRIST_CAMERA_MOUNT_COLLISION_OBJ_NAME),
    ):
        changed = _upsert_mesh_asset(asset, mesh_name, file_name) or changed

    for arm_name, y_offset in (
        ("left_arm", MOLMOACT2_BIMANUAL_ARM_Y_OFFSET),
        ("right_arm", -MOLMOACT2_BIMANUAL_ARM_Y_OFFSET),
    ):
        arm = root.find(f".//body[@name='{arm_name}']")
        if arm is None:
            raise ValueError(f"Could not find {arm_name} in {source_xml}")
        desired_pos = f"0 {y_offset:.2f} 0"
        if arm.attrib.get("pos") != desired_pos:
            arm.attrib["pos"] = desired_pos
            changed = True

    base_body = root.find("./worldbody/body[@name='bimanual_base']")
    if base_body is None:
        raise ValueError(f"Could not find bimanual_base in {source_xml}")
    changed = _insert_top_camera_body(base_body) or changed

    for prefix in ("left", "right"):
        link_6 = root.find(f".//body[@name='{prefix}_link_6']")
        if link_6 is None:
            raise ValueError(f"Could not find {prefix}_link_6 in {source_xml}")
        changed = _insert_wrist_mount_body(link_6, prefix) or changed
        changed = _insert_wrist_camera_body(link_6, prefix) or changed

    if changed:
        ET.indent(tree, space="  ")
        tree.write(source_xml, encoding="utf-8", xml_declaration=False)
        print(f"Applied MolmoAct2 bimanual YAM camera/layout setup to {source_xml}")


def _write_isaac_compatible_mjcf(source_xml: Path, isaac_mjcf_name: str) -> Path:
    output_xml = source_xml.with_name(isaac_mjcf_name)
    source_mesh_dir = source_xml.parent / "assets"
    isaac_mesh_dir = source_mesh_dir / YAM_ISAAC_MESH_DIR_NAME
    isaac_mesh_dir.mkdir(parents=True, exist_ok=True)

    tree = ET.parse(source_xml)
    root = tree.getroot()
    compiler = root.find("compiler")
    if compiler is not None:
        compiler.attrib["meshdir"] = "assets/"

    for mesh in root.findall("./asset/mesh"):
        mesh_name = mesh.attrib["name"]
        source_file = mesh.attrib["file"]
        source_path = source_mesh_dir / source_file
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing MJCF mesh source for {mesh_name}: {source_path}")
        unique_file = f"{YAM_ISAAC_MESH_DIR_NAME}/{mesh_name}{source_path.suffix}"
        unique_path = source_mesh_dir / unique_file
        shutil.copy2(source_path, unique_path)
        mesh.attrib["file"] = unique_file

    for index, geom in enumerate(root.findall(".//geom")):
        geom_class = geom.attrib.get("class", "")
        if "name" not in geom.attrib:
            geom.attrib["name"] = f"yam_geom_{index:03d}"
        if "type" not in geom.attrib:
            if "mesh" in geom.attrib or geom_class.endswith("_visual"):
                geom.attrib["type"] = "mesh"
            elif geom_class.endswith("_collision"):
                geom.attrib["type"] = "capsule"
        if geom_class.endswith("_visual"):
            geom.attrib.setdefault("contype", "0")
            geom.attrib.setdefault("conaffinity", "0")
            geom.attrib.setdefault("density", "0")
    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=False)
    print(f"Wrote Isaac-compatible YAM MJCF at {output_xml}")
    return output_xml


def _split_floats(value: str | None, *, default: tuple[float, ...]) -> tuple[float, ...]:
    if value is None:
        return default
    return tuple(float(part) for part in value.split())


def _fmt(values: tuple[float, ...] | list[float]) -> str:
    return " ".join(f"{value:.9g}" for value in values)


def _quat_wxyz_to_rpy(quat_wxyz: tuple[float, float, float, float]) -> tuple[float, float, float]:
    w, x, y, z = quat_wxyz
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2.0 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2.0, sinp) if abs(sinp) >= 1.0 else math.asin(sinp)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def _add_origin(parent: ET.Element, attrs: dict[str, str]) -> None:
    xyz = _split_floats(attrs.get("pos"), default=(0.0, 0.0, 0.0))
    quat = _split_floats(attrs.get("quat"), default=(1.0, 0.0, 0.0, 0.0))
    origin_attrs = {"xyz": _fmt(xyz)}
    rpy = _quat_wxyz_to_rpy(quat)
    if any(abs(value) > 1.0e-10 for value in rpy):
        origin_attrs["rpy"] = _fmt(rpy)
    ET.SubElement(parent, "origin", origin_attrs)


def _add_inertial(link: ET.Element, body: ET.Element) -> None:
    inertial = body.find("inertial")
    inertial_el = ET.SubElement(link, "inertial")
    if inertial is None:
        ET.SubElement(inertial_el, "origin", {"xyz": "0 0 0"})
        ET.SubElement(inertial_el, "mass", {"value": "0.001"})
        ET.SubElement(
            inertial_el,
            "inertia",
            {"ixx": "1e-6", "ixy": "0", "ixz": "0", "iyy": "1e-6", "iyz": "0", "izz": "1e-6"},
        )
        return
    _add_origin(inertial_el, inertial.attrib)
    ET.SubElement(inertial_el, "mass", {"value": inertial.attrib.get("mass", "0.001")})
    diag = _split_floats(inertial.attrib.get("diaginertia"), default=(1.0e-6, 1.0e-6, 1.0e-6))
    ET.SubElement(
        inertial_el,
        "inertia",
        {"ixx": f"{diag[0]:.9g}", "ixy": "0", "ixz": "0", "iyy": f"{diag[1]:.9g}", "iyz": "0", "izz": f"{diag[2]:.9g}"},
    )


def _resolved_geom_type(geom: ET.Element) -> str:
    geom_type = geom.attrib.get("type")
    if geom_type is not None:
        return geom_type
    geom_class = geom.attrib.get("class", "")
    if "mesh" in geom.attrib or geom_class.endswith("_visual"):
        return "mesh"
    if geom_class.endswith("_collision"):
        return "capsule"
    return "sphere"


def _add_geometry(parent: ET.Element, geom: ET.Element, mesh_files: dict[str, str]) -> bool:
    geom_type = _resolved_geom_type(geom)
    geometry = ET.SubElement(parent, "geometry")
    if geom_type == "mesh":
        mesh_name = geom.attrib.get("mesh")
        mesh_file = mesh_files.get(mesh_name or "")
        if mesh_file is None:
            return False
        ET.SubElement(geometry, "mesh", {"filename": f"../yam_mujoco/assets/{mesh_file}"})
    elif geom_type == "box":
        size = _split_floats(geom.attrib.get("size"), default=(0.01, 0.01, 0.01))
        ET.SubElement(geometry, "box", {"size": _fmt([2.0 * value for value in size[:3]])})
    elif geom_type == "sphere":
        size = _split_floats(geom.attrib.get("size"), default=(0.005,))
        ET.SubElement(geometry, "sphere", {"radius": f"{size[0]:.9g}"})
    else:
        size = _split_floats(geom.attrib.get("size"), default=(0.01, 0.01))
        length = max(2.0 * size[1], 1.0e-4) if len(size) > 1 else 1.0e-4
        ET.SubElement(geometry, "cylinder", {"radius": f"{size[0]:.9g}", "length": f"{length:.9g}"})
    return True


def _add_visual_or_collision(link: ET.Element, geom: ET.Element, mesh_files: dict[str, str]) -> None:
    geom_class = geom.attrib.get("class", "")
    geom_type = _resolved_geom_type(geom)
    if geom_type == "mesh" or geom_class.endswith("_visual"):
        visual = ET.SubElement(link, "visual", {"name": geom.attrib.get("name", f"{link.attrib['name']}_visual")})
        _add_origin(visual, geom.attrib)
        if not _add_geometry(visual, geom, mesh_files):
            link.remove(visual)
            return
        material_name = geom.attrib.get("material")
        if material_name:
            ET.SubElement(visual, "material", {"name": material_name})
    if geom_class.endswith("_collision") or "collider" in geom.attrib.get("name", ""):
        collision = ET.SubElement(link, "collision", {"name": geom.attrib.get("name", f"{link.attrib['name']}_collision")})
        _add_origin(collision, geom.attrib)
        if not _add_geometry(collision, geom, mesh_files):
            link.remove(collision)


def _joint_effort(joint_name: str) -> float:
    if "finger" in joint_name:
        return 40.0
    if joint_name.endswith(("4", "5", "6")):
        return 10.0
    return 28.0


def _add_joint(urdf_root: ET.Element, parent_name: str, body: ET.Element) -> None:
    child_name = body.attrib["name"]
    mjcf_joint = body.find("joint")
    if mjcf_joint is None:
        joint = ET.SubElement(urdf_root, "joint", {"name": f"{child_name}_fixed", "type": "fixed"})
    else:
        joint_name = mjcf_joint.attrib["name"]
        joint_type = "prismatic" if mjcf_joint.attrib.get("type") == "slide" or "finger" in joint_name else "revolute"
        joint = ET.SubElement(urdf_root, "joint", {"name": joint_name, "type": joint_type})
    _add_origin(joint, body.attrib)
    ET.SubElement(joint, "parent", {"link": parent_name})
    ET.SubElement(joint, "child", {"link": child_name})
    if mjcf_joint is None:
        return
    ET.SubElement(joint, "axis", {"xyz": mjcf_joint.attrib.get("axis", "0 0 1")})
    lower, upper = _split_floats(mjcf_joint.attrib.get("range"), default=(-3.14159, 3.14159))
    ET.SubElement(
        joint,
        "limit",
        {"lower": f"{lower:.9g}", "upper": f"{upper:.9g}", "effort": f"{_joint_effort(mjcf_joint.attrib['name']):.9g}", "velocity": "5.0"},
    )
    ET.SubElement(joint, "dynamics", {"damping": "0.1", "friction": "0.1"})


def _add_body_tree(urdf_root: ET.Element, body: ET.Element, mesh_files: dict[str, str], parent_name: str | None = None) -> None:
    link_name = body.attrib["name"]
    link = ET.SubElement(urdf_root, "link", {"name": link_name})
    _add_inertial(link, body)
    for geom in body.findall("geom"):
        _add_visual_or_collision(link, geom, mesh_files)
    if parent_name is not None:
        _add_joint(urdf_root, parent_name, body)
    for child in body.findall("body"):
        _add_body_tree(urdf_root, child, mesh_files, link_name)


def _generate_urdf_from_mjcf(source_xml: Path, force: bool, *, urdf_name: str, root_body_name: str) -> Path:
    output_dir = _assets_root() / "yam_urdf"
    output_path = output_dir / urdf_name
    if output_path.is_file() and not force:
        print(f"YAM URDF already present at {output_path}")
        return output_path
    source_tree = ET.parse(source_xml)
    source_root = source_tree.getroot()
    mesh_files = {mesh.attrib["name"]: mesh.attrib["file"] for mesh in source_root.findall("./asset/mesh")}
    urdf_root = ET.Element("robot", {"name": Path(urdf_name).stem})
    for material in source_root.findall("./asset/material"):
        material_el = ET.SubElement(urdf_root, "material", {"name": material.attrib["name"]})
        ET.SubElement(material_el, "color", {"rgba": material.attrib.get("rgba", "0.5 0.5 0.5 1")})
    root_body = source_root.find(f"./worldbody/body[@name='{root_body_name}']")
    if root_body is None:
        raise ValueError(f"Could not find {root_body_name} in {source_xml}")
    _add_body_tree(urdf_root, root_body, mesh_files)
    ET.indent(ET.ElementTree(urdf_root), space="  ")
    output_dir.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(urdf_root).write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"Generated YAM URDF at {output_path}")
    return output_path


def _convert_urdf(urdf_path: Path, force: bool, *, usd_name: str, root_body_name: str) -> Path:
    from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg
    from isaaclab.utils.dict import print_dict

    output_dir = _assets_root() / "yam_usd"
    output_path = output_dir / usd_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = UrdfConverterCfg(
        asset_path=str(urdf_path),
        usd_dir=str(output_dir),
        usd_file_name=output_path.name,
        fix_base=True,
        root_link_name=root_body_name,
        merge_fixed_joints=False,
        force_usd_conversion=force,
        make_instanceable=False,
        self_collision=False,
        collision_from_visuals=False,
        replace_cylinders_with_capsules=True,
        joint_drive=None,
    )
    print("URDF converter config:")
    print_dict(cfg.to_dict(), nesting=0)
    converter = UrdfConverter(cfg)
    usd_path = Path(converter.usd_path)
    if not usd_path.is_file():
        raise FileNotFoundError(f"URDF converter did not create expected USD: {usd_path}")
    print(f"Generated YAM USD at {usd_path}")
    return usd_path


def _convert_mjcf(
    source_xml: Path,
    force: bool,
    *,
    isaac_mjcf_name: str,
    usd_name: str,
    fallback_mass_props: dict[str, tuple[float, tuple[float, float, float]]],
) -> Path:
    from isaacsim.core.utils.extensions import enable_extension
    import omni.kit.app

    from isaaclab.sim.converters import MjcfConverter, MjcfConverterCfg
    from isaaclab.utils.dict import print_dict

    enable_extension("isaacsim.asset.importer.mjcf")
    app = omni.kit.app.get_app()
    for _ in range(10):
        app.update()

    converter_xml = _write_isaac_compatible_mjcf(source_xml, isaac_mjcf_name)
    output_dir = _assets_root() / "yam_mjcf_usd"
    output_path = output_dir / usd_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = MjcfConverterCfg(
        asset_path=str(converter_xml),
        usd_dir=str(output_dir),
        usd_file_name=output_path.name,
        force_usd_conversion=force,
        make_instanceable=False,
        fix_base=True,
        import_sites=True,
        import_inertia_tensor=True,
        self_collision=False,
    )
    print("MJCF converter config:")
    print_dict(cfg.to_dict(), nesting=0)
    converter = MjcfConverter(cfg)
    usd_path = Path(converter.usd_path)
    if not usd_path.is_file():
        raise FileNotFoundError(f"MJCF converter did not create expected USD: {usd_path}")
    if usd_path.stat().st_size <= 1024:
        raise RuntimeError(f"MJCF converter produced an invalid stub USD: {usd_path} ({usd_path.stat().st_size} bytes)")
    _postprocess_mjcf_usd(usd_path, fallback_mass_props=fallback_mass_props)
    print(f"Generated YAM USD at {usd_path}")
    return usd_path


def _valid_positive_tuple(values: object) -> bool:
    if values is None:
        return False
    try:
        return all(math.isfinite(float(value)) and float(value) > 0.0 for value in values)
    except TypeError:
        return False


def _valid_finite_tuple(values: object) -> bool:
    if values is None:
        return False
    try:
        return all(math.isfinite(float(value)) for value in values)
    except TypeError:
        return False


def _postprocess_mjcf_usd(
    usd_path: Path,
    *,
    fallback_mass_props: dict[str, tuple[float, tuple[float, float, float]]],
) -> None:
    from pxr import Gf, PhysxSchema, Usd, UsdPhysics

    physics_path = usd_path.parent / "configuration" / f"{usd_path.stem}_physics.usd"
    if not physics_path.is_file():
        raise FileNotFoundError(f"MJCF converter did not create expected physics layer: {physics_path}")

    stage = Usd.Stage.Open(str(physics_path), Usd.Stage.LoadAll)
    if stage is None:
        raise RuntimeError(f"Could not open generated YAM physics layer: {physics_path}")
    default_prim = stage.GetDefaultPrim()
    if not default_prim:
        raise RuntimeError(f"Generated YAM physics layer has no default prim: {physics_path}")

    world_body = stage.GetPrimAtPath(f"{default_prim.GetPath()}/worldBody")
    if world_body.IsValid():
        # Isaac's MJCF importer adds a dummy worldBody articulation root. Isaac
        # Lab's fixed-base spawning expects the root API on a rigid body, so
        # keep the real robot base body as the single articulation root.
        world_body.RemoveAPI(UsdPhysics.ArticulationRootAPI)
        world_body.RemoveAPI(PhysxSchema.PhysxArticulationAPI)

    repaired_mass_bodies: list[str] = []
    for prim in stage.TraverseAll():
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            continue
        body_name = prim.GetName()
        fallback = fallback_mass_props.get(body_name)
        if fallback is None:
            continue
        mass_api = UsdPhysics.MassAPI.Apply(prim)
        mass = mass_api.GetMassAttr().Get()
        diag = mass_api.GetDiagonalInertiaAttr().Get()
        center = mass_api.GetCenterOfMassAttr().Get()
        if (
            mass is not None
            and math.isfinite(float(mass))
            and float(mass) > 0.0
            and _valid_positive_tuple(diag)
            and _valid_finite_tuple(center)
        ):
            continue
        fallback_mass, fallback_diag = fallback
        mass_api.GetMassAttr().Set(float(fallback_mass))
        mass_api.GetDiagonalInertiaAttr().Set(Gf.Vec3f(*fallback_diag))
        mass_api.GetCenterOfMassAttr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
        mass_api.GetPrincipalAxesAttr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        repaired_mass_bodies.append(body_name)

    stage.GetRootLayer().Save()
    print(
        "Post-processed YAM MJCF USD: "
        f"removed dummy worldBody articulation root; repaired mass bodies={repaired_mass_bodies}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=HF_REPO_ID)
    parser.add_argument("--force", action="store_true", help="Re-download and re-convert assets.")
    parser.add_argument("--force-conversion", action="store_true", help="Re-convert the existing MJCF without re-downloading.")
    parser.add_argument("--converter", choices=("mjcf", "urdf"), default="mjcf")
    parser.add_argument("--robot", choices=("bimanual", "single", "all"), default="bimanual")
    parser.add_argument("--download-only", action="store_true", help="Only download/copy MJCF assets.")
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()

    yam_mjcf_dir = _download_assets(args.repo_id, args.force)
    robot_names = ("bimanual", "single") if args.robot == "all" else (args.robot,)
    source_xml_by_robot = {
        robot_name: yam_mjcf_dir / str(YAM_ROBOT_SPECS[robot_name]["mjcf_name"])
        for robot_name in robot_names
    }
    for robot_name, source_xml in source_xml_by_robot.items():
        if not source_xml.is_file():
            raise FileNotFoundError(f"Expected {robot_name} YAM MJCF: {source_xml}")
        if robot_name == "bimanual":
            _apply_molmoact2_bimanual_setup(source_xml)
    if args.download_only:
        for source_xml in source_xml_by_robot.values():
            print(source_xml)
        return 0

    app_launcher = AppLauncher(args)
    simulation_app = app_launcher.app
    try:
        force_conversion = args.force or args.force_conversion
        for robot_name in robot_names:
            spec = YAM_ROBOT_SPECS[robot_name]
            source_xml = source_xml_by_robot[robot_name]
            if args.converter == "mjcf":
                output_path = _convert_mjcf(
                    source_xml,
                    force_conversion,
                    isaac_mjcf_name=str(spec["isaac_mjcf_name"]),
                    usd_name=str(spec["usd_name"]),
                    fallback_mass_props=spec["fallback_mass_props"],
                )
            else:
                urdf_path = _generate_urdf_from_mjcf(
                    source_xml,
                    force_conversion,
                    urdf_name=str(spec["urdf_name"]),
                    root_body_name=str(spec["root_body"]),
                )
                output_path = _convert_urdf(
                    urdf_path,
                    force_conversion,
                    usd_name=str(spec["usd_name"]),
                    root_body_name=str(spec["root_body"]),
                )
            print(output_path)
    finally:
        simulation_app.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
