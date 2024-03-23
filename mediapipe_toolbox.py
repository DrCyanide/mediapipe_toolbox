import bpy
import bmesh
import json
import os
import addon_utils

missing_modules = False
try:
    # These modules aren't standard to Blender/Python, so they'll need to be installed. Opening the add-on with Blender in admin mode should trigger the installer.
    import mediapipe
    import cv2
    import numpy
    import skimage
except:
    missing_modules = True

def install_missing_modules():
    print('Missing Modules, trying to install them now...')
    import sys
    import pip
    # https://stackoverflow.com/questions/11161901/how-to-install-python-modules-in-blender
    required_modules = [
        'mediapipe',
        'cv2',
        'numpy',
        'skimage'
    ]

    try:
        for module in required_modules:
            pip.main(['install', module, '--target', (sys.exec_prefix) + r'\lib\site-packages'])
    except Exception as e:
        print(e)


bl_info = {
    "name": "MediaPipe Toolbox",
    "author": "DrCyanide",
    "version": (1,0),
    "description": "Adds MediaPipe functionality for Blender in ways that speed up modeling, rigging, and animation."
}

hand_mapping_file = 'data/hand_rigify_mapping.json'
hand_config_data = {}
facemesh_mapping_file = 'data/facemesh_rigify_mapping.json'
facemesh_config_data = {}

def load_configs():
    global facemesh_config_data, hand_config_data
    matching_addons = list(filter(lambda x: x.bl_info['name'] == bl_info['name'], addon_utils.modules()))
    root_url = ''
    if len(matching_addons) > 0:
        # Production/installed environment path
        root_url = os.path.dirname(matching_addons[0].__file__)
    else:
        # Dev environment path, user agnostic
        script_dirs = bpy.utils.user_resource('SCRIPTS')
        split_drive = os.path.splitdrive(script_dirs)
        user_dir = os.path.join(split_drive[0], os.sep, *split_drive[1].split(os.sep)[0:3]) # user/username is common on Windows and Linux
        docs_dir = ['Documents','Blender','Add Ons','mediapipe_toolbox']
        root_url = os.path.join(user_dir, *docs_dir)
    with open(os.path.join(root_url, facemesh_mapping_file), 'r') as input_file:
        string_format = input_file.read()
        facemesh_config_data = json.loads(string_format)
    with open(os.path.join(root_url, hand_mapping_file), 'r') as input_file:
        string_format = input_file.read()
        hand_config_data = json.loads(string_format)


def armature_bone_count_match(_, obj):
    rigify_bone_count = 159 # How many bones a rigify rig has.
    # return len(obj.bones) == rigify_bone_count
    return obj.users > 0 and len(obj.bones) == rigify_bone_count


def facemesh_vertex_count_match(_, obj):
    facemesh_vertices_count = 468 # How many verticies a facemesh should have
    # return len(obj.vertices) == facemesh_vertices_count
    return obj.users > 0 and len(obj.vertices) == facemesh_vertices_count


def realistic_hand_match(_, obj):
    hand_vertices_count = 831
    return obj.users > 0 and len(obj.vertices) == hand_vertices_count

def findObjectByNameAndType(name, obj_type):
    objects = [obj for obj in bpy.context.scene.objects if obj.type == obj_type and obj.data.name == name]
    if len(objects) == 1:
        return objects[0]
    print('Found %s objects for %s, %s' % (len(objects), name, obj_type))
    print(objects)
    return objects[-1]

def selectObject(name, obj_type):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj = findObjectByNameAndType(name, obj_type)
    bpy.context.view_layer.objects.active = obj # Active object is what transform_apply is interacting with
    bpy.data.objects[obj.name].select_set(True)
    return obj

class AddRigOperator(bpy.types.Operator):
    """Add a rigify rig to the scene and select it"""
    bl_idname = 'mp_tools.add_rig_to_scene'
    bl_label = 'Add Rigify Rig'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations?

    def execute(self, context):
        # Add Rig
        bpy.ops.object.armature_human_metarig_add()
        armatures = bpy.data.armatures
        context.scene.mp_edit_rig = armatures[-1]
        return {'FINISHED'}
    
class MetarigToFacemeshOperator(bpy.types.Operator):
    """Positions the face and eye bones of the metarig"""
    bl_idname = 'mp_tools.metarig_to_facemesh'
    bl_label = 'Align to Facemesh'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations

    def execute(self, context):
        armature = context.scene.mp_edit_rig
        facemesh = context.scene.mp_facemesh
        # bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.ops.object.select_all(action='DESELECT')
        # armature_obj = findObjectByNameAndType(armature.name, 'ARMATURE')
        # bpy.context.view_layer.objects.active = armature_obj
        # bpy.data.objects[armature_obj.name].select_set(True)

        starting_mode = bpy.context.object.mode

        armature_obj = selectObject(armature.name, 'ARMATURE')
        armature_world_matrix_inverted = armature_obj.matrix_world.inverted()
        bpy.ops.object.mode_set(mode='EDIT')

        facemesh_obj = findObjectByNameAndType(facemesh.name, 'MESH')
        facemesh_world_matrix = facemesh_obj.matrix_world
        for bone_name in facemesh_config_data['bone_positions'].keys():
            bone_id = armature.bones.find(bone_name)
            # print('%s = %s' % (bone_name, bone_id))
            head = facemesh_config_data['bone_positions'][bone_name]['head']
            if head is not None:
                facemesh_co = facemesh.vertices[head].co
                world_co = facemesh_world_matrix @ facemesh_co
                # bpy.data.objects[armature.name].data.edit_bones[bone_id].head = facemesh_co
                armature_obj.data.edit_bones[bone_id].head = armature_world_matrix_inverted @ world_co
            
            tail = facemesh_config_data['bone_positions'][bone_name]['tail']
            if tail is not None:
                facemesh_co = facemesh.vertices[tail].co
                world_co = facemesh_world_matrix @ facemesh_co
                # bpy.data.objects[armature.name].data.edit_bones[bone_id].tail = facemesh_co
                armature_obj.data.edit_bones[bone_id].tail = armature_world_matrix_inverted @ world_co

        if context.scene.mp_eye_left is not None and context.scene.mp_eye_right is not None:
            # Position the eyes
            eye_bone_names = ['eye.L', 'eye.R']
            eye_objs = [findObjectByNameAndType(context.scene.mp_eye_left.name, 'MESH'), findObjectByNameAndType(context.scene.mp_eye_right.name, 'MESH')]
            for index in range(2):
                bone_id = armature.bones.find(eye_bone_names[index])
                bone_head_location = armature_obj.data.edit_bones[bone_id].head
                bone_head_new_location = armature_world_matrix_inverted @ eye_objs[index].location # World location of origin
                bone_translation = bone_head_location - bone_head_new_location
                bone_tail_new_location = armature_obj.data.edit_bones[bone_id].tail - bone_translation
                armature_obj.data.edit_bones[bone_id].head = bone_head_new_location
                armature_obj.data.edit_bones[bone_id].tail = bone_tail_new_location

        # bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode=starting_mode)

        return {'FINISHED'}

class CutoutFacemeshEyesOperator(bpy.types.Operator):
    """Cutout the eye holes from the facemesh"""
    bl_idname = 'mp_tools.cutout_facemesh_eyes'
    bl_label = 'Cutout Eyes'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations

    def execute(self, context):
        facemesh = context.scene.mp_facemesh

        starting_mode = bpy.context.object.mode
        selectObject(facemesh.name, 'MESH')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Counter-intuitively, you select the vertexes in Object mode, then switch to Edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for edge in facemesh.edges:
            edge.select = False
        print('Selected Edges: %s' % len([edge for edge in facemesh.edges if edge.select]))
        for index in facemesh_config_data['eye_edges']['eye.L']:
            facemesh.edges[index].select = True
        for index in facemesh_config_data['eye_edges']['eye.R']:
            facemesh.edges[index].select = True
        print('Selected Edges: %s' % len([edge for edge in facemesh.edges if edge.select]))
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete(type='EDGE')

        bpy.ops.object.mode_set(mode=starting_mode)
        return {'FINISHED'}

class RipFacemeshMouthOperator(bpy.types.Operator):
    """Cut the mouth out of the mesh, so the lips aren't glued together"""
    bl_idname = 'mp_tools.rip_facemesh_mouth'
    bl_label = 'Rip mouth open'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations?

    def selectVertices(self, facemesh):
        # for vert in facemesh.vertices:
        #     vert.select = False
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Counter-intuitively, you select the vertexes in Object mode, then switch to Edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for index in facemesh_config_data['rip_verts']['mouth']:
            facemesh.vertices[index].select = True

    def execute(self, context):
        facemesh = context.scene.mp_facemesh

        selectObject(facemesh.name, 'MESH')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        # TODO: See if I can avoid this separate meshes step now
        self.selectVertices(facemesh)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED') # Equivalent of P (separate menu) and "Separate Selection". Creates another object in the scene collection that should get cleaned up. Was encountering a "cannot rip selected faces" error without this step

        # Both the facemesh and the separate are selected. Reset the selection to just the facemesh. 
        selectObject(facemesh.name, 'MESH')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        self.selectVertices(facemesh) # Reselect the vertices

        bpy.ops.object.mode_set(mode='EDIT')
        # Operator bpy.ops.mesh.rip.poll() failed, context is incorrect
        # bpy.ops.mesh.rip() # V to rip 
        # bpy.ops.mesh.rip('INVOKE_DEFAULT') # V to rip 
        bpy.ops.mesh.rip_move('INVOKE_DEFAULT', MESH_OT_rip={"mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "release_confirm":False, "use_accurate":False, "use_fill":False}, TRANSFORM_OT_translate={"value":(0, 0, 0.000381055), "orient_axis_ortho":'X', "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, True), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_elements":{'INCREMENT'}, "use_snap_project":False, "snap_target":'CLOSEST', "use_snap_self":False, "use_snap_edit":False, "use_snap_nonedit":False, "use_snap_selectable":False, "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "view2d_edge_pan":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})

        return {'FINISHED'}

# DEPRICATED!
class AlignEyeBonesOperator(bpy.types.Operator):
    """Position the eye bones at the center of the eye"""
    bl_idname = 'mp_tools.align_eye_bones'
    bl_label = 'Align eye bones'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations

    def execute(self, context):
        eye_l_bone_name = 'eye.L'
        eye_r_bone_name = 'eye.R'
        eye_l_obj = findObjectByNameAndType(context.scene.mp_eye_left.name, 'MESH')
        eye_r_obj = findObjectByNameAndType(context.scene.mp_eye_right.name, 'MESH')
        armature = context.scene.mp_edit_rig
        armature_obj = selectObject(armature.name, 'ARMATURE')
        bpy.ops.object.mode_set(mode='EDIT')

        armature_world_matrix_inverted = armature_obj.matrix_world.inverted()

        bone_id = armature.bones.find(eye_l_bone_name)
        bone_head_location = armature_obj.data.edit_bones[bone_id].head
        bone_head_new_location = armature_world_matrix_inverted @ eye_l_obj.location # World location of origin
        bone_translation = bone_head_location - bone_head_new_location
        bone_tail_new_location = armature_obj.data.edit_bones[bone_id].tail - bone_translation
        armature_obj.data.edit_bones[bone_id].head = bone_head_new_location
        armature_obj.data.edit_bones[bone_id].tail = bone_tail_new_location

        bone_id = armature.bones.find(eye_r_bone_name)
        bone_head_location = armature_obj.data.edit_bones[bone_id].head
        bone_head_new_location = armature_world_matrix_inverted @ eye_r_obj.location # World location of origin
        bone_translation = bone_head_location - bone_head_new_location
        bone_tail_new_location = armature_obj.data.edit_bones[bone_id].tail - bone_translation
        armature_obj.data.edit_bones[bone_id].head = bone_head_new_location
        armature_obj.data.edit_bones[bone_id].tail = bone_tail_new_location

        return {'FINISHED'}

class AlignHandsOperator(bpy.types.Operator):
    """Position the hand bones - ONLY works with Blender's 'Hand - Realistic' preset"""
    bl_idname = 'mp_tools.align_hands_bones'
    bl_label = 'Align hand bones'
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for operations

    def execute(self, context):
        starting_mode = bpy.context.object.mode

        left_hand = context.scene.mp_hand_left
        right_hand = context.scene.mp_hand_right
        left_hand_obj = findObjectByNameAndType(context.scene.mp_hand_left.name, 'MESH')
        right_hand_obj = findObjectByNameAndType(context.scene.mp_hand_right.name, 'MESH')

        armature = context.scene.mp_edit_rig
        armature_obj = selectObject(armature.name, 'ARMATURE')
        armature_world_matrix_inverted = armature_obj.matrix_world.inverted()
        bpy.ops.object.mode_set(mode='EDIT')

        for side in ['L', 'R']:
            hand = left_hand
            hand_obj = left_hand_obj
            if side == 'R':
                hand = right_hand
                hand_obj = right_hand_obj
            
            hand_world_matrix = hand_obj.matrix_world
            for bone_name in hand_config_data['bone_positions'].keys():
                sided_bone_name = '%s.%s' % (bone_name, side)
                bone_id = armature.bones.find(sided_bone_name)
                # Head
                head_verts = hand_config_data['bone_positions'][bone_name]['head']
                head_verts_cos_world = [hand_world_matrix @ hand.vertices[head].co for head in head_verts]
                vert_co_world_sum = head_verts_cos_world[0]
                for i in range(1, len(head_verts_cos_world)):
                    vert_co_world_sum += head_verts_cos_world[i]
                head_vert_co_world_avg = vert_co_world_sum / len(head_verts_cos_world)
                armature_obj.data.edit_bones[bone_id].head = armature_world_matrix_inverted @ head_vert_co_world_avg
                # Tail
                tail_verts = hand_config_data['bone_positions'][bone_name]['tail']
                tail_verts_cos_world = [hand_world_matrix @ hand.vertices[tail].co for tail in tail_verts]
                vert_co_world_sum = tail_verts_cos_world[0]
                for i in range(1, len(tail_verts_cos_world)):
                    vert_co_world_sum += tail_verts_cos_world[i]
                tail_vert_co_world_avg = vert_co_world_sum / len(tail_verts_cos_world)
                armature_obj.data.edit_bones[bone_id].tail = armature_world_matrix_inverted @ tail_vert_co_world_avg

        bpy.ops.object.mode_set(mode=starting_mode)
        return {'FINISHED'}


class MEDIAPIPE_TOOLBOX_PT_Panel(bpy.types.Panel):
    bl_label = "MediaPipe Toolbox"
    bl_idname = "MEDIAPIPE_TOOLBOX_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = 'object'
    bl_category = 'MP Tools'

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        # view = context.space_data
        view = context.scene

        col = layout.column(align=True)
        sub = col.column()
        
        sub.prop(view, "mp_edit_rig")
        rig = view.mp_edit_rig
        if not rig:
            col.operator(AddRigOperator.bl_idname, text="Add Rig to scene")

        # Great, the user can select a rig now!
        sub.prop(view, "mp_facemesh")

        sub.prop(view, "mp_eye_left")
        sub.prop(view, "mp_eye_right")
        sub.prop(view, "mp_hand_left")
        sub.prop(view, "mp_hand_right")
        # Fit rig to mesh button
        col.operator(CutoutFacemeshEyesOperator.bl_idname, text="Cutout Eye Sockets")
        # col.operator(AlignEyeBonesOperator.bl_idname, text="Rig Eyes")
        col.operator(MetarigToFacemeshOperator.bl_idname, text="Metarig to Facemesh and Eyes")
        col.operator(AlignHandsOperator.bl_idname, text="Metarig to Hands")
        col.operator(RipFacemeshMouthOperator.bl_idname, text="Rip Mouth")

class TESTING_PT_Panel(bpy.types.Panel):
    bl_label = "Testing Tab"
    bl_idname = "TESTING_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = 'object'
    bl_category = 'MP Tools'

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        # view = context.space_data
        view = context.scene

        col = layout.column(align=True)
        sub = col.column()
        
        sub.prop(view, "mp_edit_rig")

classes = (
    AddRigOperator,
    MetarigToFacemeshOperator,
    CutoutFacemeshEyesOperator,
    RipFacemeshMouthOperator,
    # AlignEyeBonesOperator,
    AlignHandsOperator,
    MEDIAPIPE_TOOLBOX_PT_Panel,
    TESTING_PT_Panel,
)

def register():
    bpy.types.Scene.mp_edit_rig = bpy.props.PointerProperty(
        name="Metarig",
        description="Rigify rig",
        type=bpy.types.Armature,
        poll=armature_bone_count_match
    )

    bpy.types.Scene.mp_facemesh = bpy.props.PointerProperty(
        name="FaceMesh",
        description="FaceMesh generated from Mediapipe",
        type=bpy.types.Mesh,
        poll=facemesh_vertex_count_match
    )

    bpy.types.Scene.mp_eye_left = bpy.props.PointerProperty(
        name="Left Eye",
        description="The character's left eye",
        type=bpy.types.Mesh,
    )

    bpy.types.Scene.mp_eye_right = bpy.props.PointerProperty(
        name="Right Eye",
        description="The character's right eye",
        type=bpy.types.Mesh,
    )

    bpy.types.Scene.mp_hand_left = bpy.props.PointerProperty(
        name="Left Hand",
        description="The character's left hand",
        type=bpy.types.Mesh,
        poll=realistic_hand_match
    )

    bpy.types.Scene.mp_hand_right = bpy.props.PointerProperty(
        name="Right Hand",
        description="The character's right hand",
        type=bpy.types.Mesh,
        poll=realistic_hand_match
    )

    if missing_modules:
        install_missing_modules()

    load_configs()

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Scene.mp_edit_rig
    del bpy.types.Scene.mp_facemesh
    del bpy.types.Scene.mp_eye_left
    del bpy.types.Scene.mp_eye_right
    del bpy.types.Scene.mp_hand_left
    del bpy.types.Scene.mp_hand_right

    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()