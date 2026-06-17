"""Robot-independent configuration fields for GraspGen multi-object grasp tasks."""

from __future__ import annotations

from isaaclab.utils import configclass


MULTI_OBJECT_FEATURE_DIM = 8


@configclass
class MultiObjectGraspTaskCfg:
    """Shared object-manifest, spawn, and physics defaults for multi-object grasping."""

    # Asset manifest produced by dextrah_lab/assets/prepare_graspgen_assets.py.
    # If empty, object_assets_dir is scanned for a manifest.json or USD/*/*.usd.
    object_asset_manifest_path = ""
    object_assets_dir = "dextrah_lab/assets/graspgen_objects"
    max_objects = 0
    object_asset_assignment = "round_robin"
    require_graspgen_scale = True

    # Object placement and physical properties.
    object_spawn_center_offset_x = 0.05
    object_spawn_center_offset_y = 0.0
    object_spawn_xy_randomization = 0.10
    object_spawn_yaw_randomization_deg = 180.0
    object_spawn_z_clearance = 0.006
    object_stable_pose_enabled = False
    object_stable_pose_cache_dir = ""
    object_stable_pose_count = 1
    object_stable_pose_randomize = True
    object_stable_pose_allow_missing = False
    object_reset_settle_steps = 0
    object_reset_zero_velocity_after_settle = True
    object_reset_settle_full_reset_only = True
    object_default_half_extents = (0.03, 0.03, 0.03)
    object_default_grasp_size = 0.06
    object_default_scale = 1.0
    object_validate_usd_bounds = False
    object_usd_bounds_max_ratio = 4.0
    object_usd_bounds_max_dimension = 0.5
    object_density = 500.0
    object_kinematic_enabled = False
    object_disable_gravity = False
    object_static_friction = 1.5
    object_dynamic_friction = 1.2
    object_restitution = 0.0
    object_contact_offset = 0.004
    object_rest_offset = 0.0
    object_solver_position_iterations = 12
    object_solver_velocity_iterations = 4
    object_linear_damping = 0.08
    object_angular_damping = 0.25
    object_sleep_threshold = 0.02
    object_stabilization_threshold = 0.01
    object_max_linear_velocity = 1000.0
    object_max_angular_velocity = 1000.0
    object_max_depenetration_velocity = 3.0

    # Optional tabletop clutter group.  These objects are spawned and settled
    # with the scene, but the task objective and observations still track the
    # target object from the fields above.
    tabletop_clutter_enabled = False
    tabletop_clutter_object_count = 0
    # If empty, clutter reuses object_asset_manifest_path/object_assets_dir.
    tabletop_clutter_asset_manifest_path = ""
    tabletop_clutter_assets_dir = ""
    tabletop_clutter_max_objects = 0
    tabletop_clutter_asset_assignment = "random"
    tabletop_clutter_require_graspgen_scale = False
    tabletop_clutter_spawn_center_offset_x = 0.0
    tabletop_clutter_spawn_center_offset_y = 0.0
    tabletop_clutter_spawn_xy_randomization = 0.18
    tabletop_clutter_spawn_yaw_randomization_deg = 180.0
    tabletop_clutter_spawn_z_clearance = 0.006
    tabletop_clutter_spawn_z_jitter = 0.02
    tabletop_clutter_stable_pose_enabled = False
    tabletop_clutter_stable_pose_cache_dir = ""
    tabletop_clutter_stable_pose_count = 1
    tabletop_clutter_stable_pose_randomize = True
    tabletop_clutter_stable_pose_allow_missing = False
    tabletop_clutter_non_overlapping = True
    tabletop_clutter_placement_padding = 0.01
    tabletop_clutter_placement_attempts = 128
    tabletop_clutter_placement_grid_resolution = 21
    tabletop_clutter_include_target_object_in_placement = True
    tabletop_clutter_prioritize_common_objects = True
    tabletop_clutter_max_xy_radius = 0.14
    tabletop_clutter_validate_usd_bounds = False
    tabletop_clutter_usd_bounds_max_ratio = 4.0
    tabletop_clutter_usd_bounds_max_dimension = 0.5

    # Optional fixed tabletop bin used as a placement goal.  When enabled, the
    # target object and clutter placement keep at least tabletop_goal_bin_clearance
    # from the bin footprint.
    tabletop_goal_bin_enabled = False
    tabletop_goal_bin_center_offset_x = 0.0
    tabletop_goal_bin_center_offset_y = 0.0
    tabletop_goal_bin_inner_size_x = 0.22
    tabletop_goal_bin_inner_size_y = 0.22
    tabletop_goal_bin_wall_thickness = 0.02
    tabletop_goal_bin_bottom_thickness = 0.012
    tabletop_goal_bin_wall_height = 0.12
    tabletop_goal_bin_clearance = 0.10
    tabletop_goal_bin_placement_clearance = 0.0
    tabletop_goal_bin_goal_height = 0.06
    tabletop_goal_bin_success_xy_tol = 0.08
    tabletop_goal_bin_floor_color = (0.14, 0.16, 0.18)
    tabletop_goal_bin_x_wall_color = (0.18, 0.45, 0.60)
    tabletop_goal_bin_y_wall_color = (0.15, 0.38, 0.54)
    tabletop_goal_bin_visual_roughness = 0.68

    tabletop_clutter_density = 500.0
    tabletop_clutter_kinematic_enabled = False
    tabletop_clutter_disable_gravity = False
    tabletop_clutter_static_friction = 1.6
    tabletop_clutter_dynamic_friction = 1.2
    tabletop_clutter_restitution = 0.0
    tabletop_clutter_contact_offset = 0.004
    tabletop_clutter_rest_offset = 0.0
    tabletop_clutter_solver_position_iterations = 16
    tabletop_clutter_solver_velocity_iterations = 6
    tabletop_clutter_linear_damping = 0.25
    tabletop_clutter_angular_damping = 1.25
    tabletop_clutter_sleep_threshold = 0.06
    tabletop_clutter_stabilization_threshold = 0.03
    tabletop_clutter_max_linear_velocity = 1000.0
    tabletop_clutter_max_angular_velocity = 1000.0
    tabletop_clutter_max_depenetration_velocity = 2.0
    tabletop_clutter_common_object_keywords = (
        "apple",
        "bag",
        "bagel",
        "bar",
        "bottle",
        "bowl",
        "box",
        "can",
        "candy",
        "container",
        "cup",
        "dish",
        "food",
        "fork",
        "fruit",
        "jar",
        "knife",
        "marker",
        "mug",
        "pen",
        "pepper",
        "plate",
        "remote",
        "scissors",
        "snack",
        "soap",
        "spoon",
        "sponge",
        "teapot",
        "toothbrush",
        "vase",
    )
    tabletop_clutter_excluded_object_keywords = (
        "animal",
        "building",
        "car",
        "chair",
        "person",
        "plant",
        "room",
        "statue",
        "tree",
        "vehicle",
    )
