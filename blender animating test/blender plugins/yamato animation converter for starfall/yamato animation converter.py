bl_info = {
    "name": "Slashblade Animation Exporter",
    "author": "Generated for you",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "3D View > Object > Export Slashblade Anim / Armature Properties",
    "description": "Export animation keyframes to slashblade_project/anim/*.txt in your specified format",
    "category": "Export",
}

import bpy
import os
import math
from mathutils import Matrix

# --- Configuration ---
# Bone order (Torso + Right side first, then Left side)
BONE_ORDER = [
    "Torso",
    "UpperArm_Left",
    "ForeArm_Left",
    "Hand_Left",
    "Hand_Flipped_Left",
    "UpperArm_Right",
    "ForeArm_Right",
    "Hand_Right",
    "Sword",
]

# --- Utilities ---
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def vec_to_angle_str(deg_tuple):
    return "Angle({:.6f},{:.6f},{:.6f})".format(deg_tuple[0], deg_tuple[1], deg_tuple[2])

def gather_action_keyframes(action):
    """Return sorted list of unique keyframe frame numbers (int)."""
    frames = set()
    for fcu in action.fcurves:
        for kp in fcu.keyframe_points:
            frames.add(int(round(kp.co.x)))
    return sorted(frames)

def pose_bone_relative_euler_degrees(arm_obj, pb):
    """Euler XYZ in degrees, relative to parent; torso = world angles (with -90° X offset)."""
    if pb.parent:
        rel_mat = pb.parent.matrix.inverted() @ pb.matrix
        e = rel_mat.to_euler('XYZ')
    else:
        world_mat = arm_obj.matrix_world @ pb.matrix
        e = world_mat.to_euler('XYZ')
        # Apply offset correction to neutralize Blender's default 90° pitch
        e.x -= math.radians(90.0)
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))

# --- Export core ---
def export_action_to_slashblade_text(context, arm_obj, action, out_path):
    scene = context.scene
    keyframes = gather_action_keyframes(action)
    if not keyframes:
        raise RuntimeError("No keyframes found in action!")

    anim_name = action.name
    anim_name_lower = anim_name.lower().replace(" ", "_")
    anim_name_upper = anim_name.upper().replace(" ", "_")

    header = f"--@name slashblade_project/anim/{anim_name_lower}\n{anim_name_upper}={{\n"
    lines = [header]

    orig_frame = scene.frame_current

    for i, f in enumerate(keyframes):
        scene.frame_set(f)
        bpy.context.view_layer.update()

        # Determine frame length based on next keyframe
        if i < len(keyframes) - 1:
            frame_length = keyframes[i + 1] - f
        else:
            frame_length = 1  # fallback for last key

        # Collect angles in new bone order
        angle_lines = []
        for bone_name in BONE_ORDER:
            try:
                pb = arm_obj.pose.bones[bone_name]
                degs = pose_bone_relative_euler_degrees(arm_obj, pb)
                angle_lines.append(vec_to_angle_str(degs))
            except KeyError:
                angle_lines.append("Angle(0,0,0)")

        # Write frame block
        lines.append("{\n")
        for ang in angle_lines:
            lines.append(ang + ",\n")
        lines.append(str(frame_length) + ",\n")
        lines.append("true\n")  # sword out
        if i < len(keyframes) - 1:
            lines.append("},\n")
        else:
            lines.append("}\n")

    lines.append("}\n")

    ensure_dir(os.path.dirname(out_path))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)

    scene.frame_set(orig_frame)
    bpy.context.view_layer.update()

    return out_path

# --- Operator & Panel ---
class SLASHBLADE_OT_export_anim(bpy.types.Operator):
    bl_idname = "export.slashblade_anim"
    bl_label = "Export Slashblade Anim (.txt)"
    bl_description = "Export keyframes of the active Action for Slashblade"
    bl_options = {'REGISTER'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an Armature object.")
            return {'CANCELLED'}

        arm = obj
        action = arm.animation_data.action if arm.animation_data else None
        if not action:
            self.report({'ERROR'}, "No Action found on the active Armature.")
            return {'CANCELLED'}

        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Please save your .blend file first.")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(bpy.data.filepath)
        folder = os.path.join(blend_dir, "slashblade_project", "anim")
        filename = action.name.lower().replace(" ", "_") + ".txt"
        out_path = os.path.join(folder, filename)

        try:
            written = export_action_to_slashblade_text(context, arm, action, out_path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported '{action.name}' to: {written}")
        return {'FINISHED'}

class SLASHBLADE_PT_panel(bpy.types.Panel):
    bl_label = "Slashblade Export"
    bl_idname = "SLASHBLADE_PT_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob is not None and ob.type == 'ARMATURE'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export current Action for Slashblade:")
        layout.operator("export.slashblade_anim", icon='EXPORT')

def menu_func(self, context):
    self.layout.operator(SLASHBLADE_OT_export_anim.bl_idname, icon='EXPORT')

classes = (
    SLASHBLADE_OT_export_anim,
    SLASHBLADE_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
