import bpy
import json
from mathutils import Quaternion, Vector, Euler
import math

# Id map
character_ids = {
    '0x00': 'PlMr',
    '0x01': 'PlFx',
    '0x02': 'PlCa',
    '0x03': 'PlDk',
    '0x04': 'PlKb',
    '0x05': 'PlKp',
    '0x06': 'PlLk',
    '0x07': 'PlSk',
    '0x08': 'PlNs',
    '0x09': 'PlPe',
    '0x0A': 'PlPp',
    '0x0B': 'PlNn',
    '0x0C': 'PlPk',
    '0x0D': 'PlSs',
    '0x0E': 'PlYs',
    '0x0F': 'PlPr',
    '0x10': 'PlMt',
    '0x11': 'PlLg',
    '0x12': 'PlMs',
    '0x13': 'PlZd',
    '0x14': 'PlCl',
    '0x15': 'PlDr',
    '0x16': 'PlFc',
    '0x17': 'PlPc',
    '0x18': 'PlGw',
    '0x19': 'PlGn',
    '0x1A': 'PlFe',
    '0x1B': 'Master Hand',
    '0x1C': 'Crazy Hand',
    '0x1D': 'Wireframe Male (Boy)',
    '0x1E': 'Wireframe Female (Girl)',
    '0x1F': 'Giga Bowser',
    '0x20': 'Sandbag'
}

# Set frame to 0
bpy.context.scene.frame_set(0)

# Set camera
cam = bpy.data.objects['Camera']
interest = bpy.data.objects['Origin']

replay_file = 'C:/Users/fores/source/repos/slippi-js/data.json'
# Load JSON data from the file
with open(replay_file, 'r') as json_file:
    replay_data = json.load(json_file)
 
current_frame = -123

# Start of keyframing
for frame in replay_data:
    # In-game frame counter
    replay_frame = frame["frame"]
    print(replay_frame)
    cam_data = frame["camData"]
    cam_eye_pos = Vector((cam_data["eyeX"], cam_data["eyeY"], cam_data["eyeZ"]))
    cam_interest_pos = Vector((cam_data["interestX"], cam_data["interestY"], cam_data["interestZ"]))
    #print(cam_eye_pos)
    #print(cam_interest_pos)
    
    # Set camera to data
    cam_eye_pos.z = (cam_eye_pos.z * -1)
    # cam_eye_pos.x = cam_eye_pos.x / 10
    # cam_eye_pos.y = cam_eye_pos.y / 10

    cam_interest_pos.z = (cam_interest_pos.z * -1)
    # cam_interest_pos.x = cam_interest_pos.x / 10
    # cam_interest_pos.y = cam_interest_pos.y / 10

    cam.matrix_world.translation.xzy = cam_eye_pos
    interest.matrix_world.translation.xzy = cam_interest_pos
    cam.data.angle = (math.radians(cam_data["fov"]))

    for prop in ['location', 'rotation_euler', 'scale']:
        cam.keyframe_insert(data_path=prop)
        interest.keyframe_insert(data_path=prop)



    replay_char_id = frame.get("charId")
    replay_char_id = '0x{:02X}'.format(replay_char_id)
    if replay_char_id in character_ids:
        Pl = character_ids[replay_char_id]
    else:
        print('non-match')
        
    # Our character rig
    skeleton = bpy.data.objects.get(f'{Pl}_skeleton')
    default_transform_file = f'C:/Users/fores/Documents/Slippi 3D/Default Transforms/{Pl}_t.json'
    bpy.context.view_layer.objects.active = skeleton
    bpy.ops.object.mode_set(mode='POSE')

    with open(default_transform_file, 'r') as json_file:
        default_transform_data = json.load(json_file)

    default_transforms = default_transform_data["nodes"][0]["data"]["JOBJ"]
    bones_data = frame.get("bones", [])
    # Iterate through the pose bones and apply transformations to the main tree
    print(f'applying transforms to {Pl}')

    for index, bone_data in enumerate(bones_data):
        bone_name = f'JOBJ_{index}'
        pose_bone = skeleton.pose.bones.get(bone_name)
        bone_data = bones_data[index]
        transform_data = default_transforms[index]

        # Setup data
        def_position_data = Vector((transform_data["translation_x"], transform_data["translation_y"], transform_data["translation_z"]))
        replay_position_data = Vector((bone_data["posX"], bone_data["posY"], bone_data["posZ"]))

        def_rotation_data = Euler((transform_data["rotation_x"], transform_data["rotation_y"], transform_data["rotation_z"]))
        replay_rotation_data = Quaternion((bone_data["rotW"], bone_data["rotX"], bone_data["rotY"], bone_data["rotZ"]))
        def_rotation_data_quat = def_rotation_data.to_quaternion()

        def_scale_data = Vector((transform_data["scale_x"], transform_data["scale_y"], transform_data["scale_z"]))
        replay_scale_data = Vector((bone_data["scaleX"], bone_data["scaleY"], bone_data["scaleZ"]))

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
            print(f"Pose bone {bone_name} not found in the armature.")

    if current_frame != replay_frame:
        # Advance to the next frame
        current_frame += 1
        bpy.ops.screen.frame_offset(delta=1)
    
    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

else:
    print("Armature object not found or is not an armature.")
