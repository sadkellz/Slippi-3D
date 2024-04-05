import bpy
import json
from mathutils import Quaternion, Vector, Euler
import math

# Id map
character_ids = {
    int('0x00', 16): 'PlMr',
    int('0x01', 16): 'PlFx',
    int('0x02', 16): 'PlCa',
    int('0x03', 16): 'PlDk',
    int('0x04', 16): 'PlKb',
    int('0x05', 16): 'PlKp',
    int('0x06', 16): 'PlLk',
    int('0x07', 16): 'PlSk',
    int('0x08', 16): 'PlNs',
    int('0x09', 16): 'PlPe',
    int('0x0A', 16): 'PlPp',
    int('0x0B', 16): 'PlNn',
    int('0x0C', 16): 'PlPk',
    int('0x0D', 16): 'PlSs',
    int('0x0E', 16): 'PlYs',
    int('0x0F', 16): 'PlPr',
    int('0x10', 16): 'PlMt',
    int('0x11', 16): 'PlLg',
    int('0x12', 16): 'PlMs',
    int('0x13', 16): 'PlZd',
    int('0x14', 16): 'PlCl',
    int('0x15', 16): 'PlDr',
    int('0x16', 16): 'PlFc',
    int('0x17', 16): 'PlPc',
    int('0x18', 16): 'PlGw',
    int('0x19', 16): 'PlGn',
    int('0x1A', 16): 'PlFe',
    int('0x1B', 16): 'Master Hand',
    int('0x1C', 16): 'Crazy Hand',
    int('0x1D', 16): 'Wireframe Male (Boy)',
    int('0x1E', 16): 'Wireframe Female (Girl)',
    int('0x1F', 16): 'Giga Bowser',
    int('0x20', 16): 'Sandbag'
}

# Set frame to 0
bpy.context.scene.frame_set(0)

# Set camera
cam = bpy.data.objects['Camera']
interest = bpy.data.objects['Origin']
item_file = 'C:/Users/fores/source/repos/slippi-js/frame_items.json'
replay_file = 'C:/Users/fores/source/repos/slippi-js/data.json'
# Load JSON data from the file
with open(replay_file, 'r') as json_file:
    replay_data = json.load(json_file)
 
with open(item_file, 'r') as json_file:
    item_frames = json.load(json_file)

current_frame = -123
match = 0
# Start of keyframing
for frame in replay_data[177:178]:
    # In-game frame counter
    replay_frame = frame['frame']

    # Cam
    cam_data = frame['camData']
    cam_eye_pos = Vector((cam_data['eyeX'], cam_data['eyeY'], cam_data['eyeZ']))
    cam_interest_pos = Vector((cam_data['interestX'], cam_data['interestY'], cam_data['interestZ']))

    # Set camera to data
    cam_eye_pos.z = (cam_eye_pos.z * -1)
    cam_interest_pos.z = (cam_interest_pos.z * -1)

    cam.matrix_world.translation.xzy = cam_eye_pos
    interest.matrix_world.translation.xzy = cam_interest_pos
    cam.data.angle = (math.radians(cam_data['fov']))

    for prop in ['location', 'rotation_euler', 'scale']:
        cam.keyframe_insert(data_path=prop)
        interest.keyframe_insert(data_path=prop)

    # Characters
    replay_char_id = frame.get('charId')
    if replay_char_id in character_ids:
        Pl = character_ids[replay_char_id]
        print(Pl)
    else:
        print('non-match')

    # Our character rig
    skeleton = bpy.data.objects.get(f'{Pl}_skeleton')
    default_transform_file = f'C:/Users/fores/Documents/Slippi 3D/Default Transforms/{Pl}_t.json'
    bpy.context.view_layer.objects.active = skeleton
    bpy.ops.object.mode_set(mode='POSE')

    with open(default_transform_file, 'r') as json_file:
        default_transform_data = json.load(json_file)

    default_transforms = default_transform_data['nodes'][0]['data']['JOBJ']
    bones_data = frame.get('bones', [])

    # Items
    # for item_frame in item_frames:
    #     item_data = None
    #     items = item_frame.get('items', [])
    #     for item in items:
    #         if item['frame'] == replay_frame:
    #             item_data = item
    #             item_type = item_data['typeId']
    #             item_owner_id = item_data['ownerId']
    #             item_bone_parent = item_data['boneParent']
    #             if item_type == 99:
    #                 if item_bone_parent != 0:
    #                     item_obj = bpy.data.objects.get('turnip_skeleton')

    #                     item_pos = Vector((item_data['positionX'], item_data['positionY'], item_data['positionZ']))
    #                     item_rot = Euler((item_data['rotationZ'], item_data['rotationX'], item_data['rotationY']))
    #                     item_scale = Vector((item_data['scaleX'], item_data['scaleY'], item_data['scaleZ']))
    # #                     item_obj.matrix_world.translation.xzy = item_pos

    #                     pose_bone = skeleton.pose.bones.get(f'JOBJ_{item_bone_parent}')
    #                         # Add a Child Of constraint to the object
    #                     child_of_constraint = skeleton.constraints.new(type='CHILD_OF')
    #                     child_of_constraint.target = item_obj
    #                     child_of_constraint.subtarget = f'JOBJ_{item_bone_parent}'
                        
                        # # Set the constraint's inverse_matrix to the identity matrix to maintain the relative position
                        # child_of_constraint.inverse_matrix = item_obj.matrix_world.inverted()

                    # item_obj.matrix_world.translation.xzy = item_pos
                    # item_obj.rotation_mode = 'XYZ'
                    # item_obj.rotation_euler = item_rot
                    # item_obj.scale.xzy = item_scale
                    # for prop in ['location', 'rotation_euler', 'scale']:
                    #     item_obj.keyframe_insert(data_path=prop)

        
    # Iterate through the pose bones and apply transformations to the main tree
    # print(f'applying transforms to {Pl}')

    for index, bone_data in enumerate(bones_data):
        bone_name = f'JOBJ_{index}'
        pose_bone = skeleton.pose.bones.get(bone_name)
        bone_data = bones_data[index]
        transform_data = default_transforms[index]

        # Setup data
        def_position_data = Vector((transform_data['translation_x'], transform_data['translation_y'], transform_data['translation_z']))
        replay_position_data = Vector((bone_data['posX'], bone_data['posY'], bone_data['posZ']))

        def_rotation_data = Euler((transform_data['rotation_x'], transform_data['rotation_y'], transform_data['rotation_z']))
        replay_rotation_data = Quaternion((bone_data['rotW'], bone_data['rotX'], bone_data['rotY'], bone_data['rotZ']))
        def_rotation_data_quat = def_rotation_data.to_quaternion()

        def_scale_data = Vector((transform_data['scale_x'], transform_data['scale_y'], transform_data['scale_z']))
        replay_scale_data = Vector((bone_data['scaleX'], bone_data['scaleY'], bone_data['scaleZ']))

        local_transform = replay_position_data - def_position_data
        local_scale = replay_scale_data

        rotation_mode = 'QUATERNION'
        local_rotation = Quaternion()
        local_rotation = def_rotation_data_quat.rotation_difference(replay_rotation_data)

        # Set and keyframe bone props
        if pose_bone:
            pose_bone.rotation_mode = rotation_mode
            pose_bone.location = local_transform
            pose_bone.scale = local_scale
            pose_bone.rotation_quaternion = local_rotation
            for prop in ['location', 'rotation_quaternion', 'scale']:
                pose_bone.keyframe_insert(data_path=prop)

        else:
            print(f'Pose bone {bone_name} not found in the armature.')

    if current_frame != replay_frame:
        # Advance to the next frame
        current_frame += 1
        bpy.ops.screen.frame_offset(delta=1)
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

else:
    print('Armature object not found or is not an armature.')
