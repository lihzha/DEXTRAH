#!/usr/bin/env python3
"""Download and convert MolmoAct2 bimanual YAM assets for DEXTRAH."""

from __future__ import annotations

import argparse
import math
import shutil
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

from isaaclab.app import AppLauncher


HF_REPO_ID = "TreeePlanter/molmoact2-sim-eval-assets"
YAM_MJCF_NAME = "bimanual_yam_linear_flattened.xml"
YAM_ISAAC_MJCF_NAME = "bimanual_yam_linear_flattened_isaac.xml"
YAM_USD_NAME = "bimanual_yam_linear_flattened.usd"
YAM_ISAAC_MESH_DIR_NAME = "isaac_meshes"
YAM_FALLBACK_MASS_PROPS = {
    "bimanual_base": (1.0, (1.0e-2, 1.0e-2, 1.0e-2)),
    "left_arm": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "right_arm": (0.2, (2.0e-4, 2.0e-4, 2.0e-4)),
    "left_link_6": (0.12, (1.0e-4, 1.0e-4, 1.0e-4)),
    "right_link_6": (0.12, (1.0e-4, 1.0e-4, 1.0e-4)),
    "left_link_left_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "left_link_right_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "right_link_left_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
    "right_link_right_finger": (0.03, (2.0e-5, 2.0e-5, 2.0e-5)),
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
        return source_xml

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
    if yam_mjcf_dir.exists():
        shutil.rmtree(yam_mjcf_dir)
    shutil.copytree(source_assets / "yam_mujoco", yam_mjcf_dir)
    if not source_xml.is_file():
        raise FileNotFoundError(f"Expected YAM MJCF after copy: {source_xml}")
    print(f"Installed YAM MJCF assets at {yam_mjcf_dir}")
    return source_xml


def _write_isaac_compatible_mjcf(source_xml: Path) -> Path:
    output_xml = source_xml.with_name(YAM_ISAAC_MJCF_NAME)
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


def _generate_urdf_from_mjcf(source_xml: Path, force: bool) -> Path:
    output_dir = _assets_root() / "yam_urdf"
    output_path = output_dir / "bimanual_yam.urdf"
    if output_path.is_file() and not force:
        print(f"YAM URDF already present at {output_path}")
        return output_path
    source_tree = ET.parse(source_xml)
    source_root = source_tree.getroot()
    mesh_files = {mesh.attrib["name"]: mesh.attrib["file"] for mesh in source_root.findall("./asset/mesh")}
    urdf_root = ET.Element("robot", {"name": "bimanual_yam"})
    for material in source_root.findall("./asset/material"):
        material_el = ET.SubElement(urdf_root, "material", {"name": material.attrib["name"]})
        ET.SubElement(material_el, "color", {"rgba": material.attrib.get("rgba", "0.5 0.5 0.5 1")})
    root_body = source_root.find("./worldbody/body[@name='bimanual_base']")
    if root_body is None:
        raise ValueError(f"Could not find bimanual_base in {source_xml}")
    _add_body_tree(urdf_root, root_body, mesh_files)
    ET.indent(ET.ElementTree(urdf_root), space="  ")
    output_dir.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(urdf_root).write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"Generated YAM URDF at {output_path}")
    return output_path


def _convert_urdf(urdf_path: Path, force: bool) -> Path:
    from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg
    from isaaclab.utils.dict import print_dict

    output_dir = _assets_root() / "yam_usd"
    output_path = output_dir / "bimanual_yam.usd"
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = UrdfConverterCfg(
        asset_path=str(urdf_path),
        usd_dir=str(output_dir),
        usd_file_name=output_path.name,
        fix_base=True,
        root_link_name="bimanual_base",
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


def _convert_mjcf(source_xml: Path, force: bool) -> Path:
    from isaacsim.core.utils.extensions import enable_extension
    import omni.kit.app

    from isaaclab.sim.converters import MjcfConverter, MjcfConverterCfg
    from isaaclab.utils.dict import print_dict

    enable_extension("isaacsim.asset.importer.mjcf")
    app = omni.kit.app.get_app()
    for _ in range(10):
        app.update()

    converter_xml = _write_isaac_compatible_mjcf(source_xml)
    output_dir = _assets_root() / "yam_mjcf_usd"
    output_path = output_dir / YAM_USD_NAME
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
    _postprocess_mjcf_usd(usd_path)
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


def _postprocess_mjcf_usd(usd_path: Path) -> None:
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
        # keep the real bimanual_base body as the single articulation root.
        world_body.RemoveAPI(UsdPhysics.ArticulationRootAPI)
        world_body.RemoveAPI(PhysxSchema.PhysxArticulationAPI)

    repaired_mass_bodies: list[str] = []
    for prim in stage.TraverseAll():
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            continue
        body_name = prim.GetName()
        fallback = YAM_FALLBACK_MASS_PROPS.get(body_name)
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
    parser.add_argument("--download-only", action="store_true", help="Only download/copy MJCF assets.")
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()

    source_xml = _download_assets(args.repo_id, args.force)
    if args.download_only:
        print(source_xml)
        return 0

    app_launcher = AppLauncher(args)
    simulation_app = app_launcher.app
    try:
        force_conversion = args.force or args.force_conversion
        if args.converter == "mjcf":
            output_path = _convert_mjcf(source_xml, force_conversion)
        else:
            urdf_path = _generate_urdf_from_mjcf(source_xml, force_conversion)
            output_path = _convert_urdf(urdf_path, force_conversion)
        print(output_path)
    finally:
        simulation_app.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
