import bpy
import json
from mathutils import Quaternion, Vector

bpy.context.scene.frame_set(0)
# Get the current frame number
#current_frame = bpy.context.scene.frame_current


# Replace 'PlFxNr_skeleton' with the actual name of your armature object
skeleton = bpy.data.objects.get('PlFxNr_skeleton')

#replay_file = 'C:/Users/fores/Documents/Slippi 3D/test_anim_data.json'
replay_file = 'C:/Users/fores/Documents/Slippi 3D/full_replay.json'
default_transform_file = 'C:/Users/fores/Documents/Slippi 3D/PlFx_transforms.json'

# Check if the object is an armature
if skeleton and skeleton.type == 'ARMATURE':
    # Access the pose mode of the armature
    bpy.context.view_layer.objects.active = skeleton
    bpy.ops.object.mode_set(mode='POSE')

    # Load JSON data from the file
    with open(replay_file, 'r') as json_file:
        replay_data = json.load(json_file)

    with open(default_transform_file, 'r') as json_file:
        default_transform_data = json.load(json_file)

    default_transforms = default_transform_data["nodes"][0]["data"]["JOBJ"]

    for frame in replay_data[:500]:
        bones_data = frame.get("bones", [])
        # Iterate through the pose bones and apply transformations to the main tree
        for index, bone_data in enumerate(bones_data):
            bone_name = f'JOBJ_{index}'
            pose_bone = skeleton.pose.bones.get(bone_name)
            bone_data = bones_data[index]
            transform_data = default_transforms[index]

            local_transform = Vector()
            local_transform.x = (bone_data["posX"] - transform_data["translation_x"])
            local_transform.y = (bone_data["posY"] - transform_data["translation_y"])
            local_transform.z = (bone_data["posZ"] - transform_data["translation_z"])

            local_scale = Vector()
            local_scale.x = bone_data["scaleX"]
            local_scale.y = bone_data["scaleY"]
            local_scale.z = bone_data["scaleZ"]

            if bone_data["useQuat"] == 0:
                rotation_mode = 'XYZ'
                local_rotation = Vector()
                local_rotation.x = (bone_data["rotX"] - transform_data["rotation_x"])
                local_rotation.y = (bone_data["rotY"] - transform_data["rotation_y"])
                local_rotation.z = (bone_data["rotZ"] - transform_data["rotation_z"])
            else:
                rotation_mode = 'QUATERNION'
                local_rotation = Quaternion()
                local_rotation.x = (bone_data["rotX"] - transform_data["rotation_x"])
                local_rotation.y = (bone_data["rotY"] - transform_data["rotation_y"])
                local_rotation.z = (bone_data["rotZ"] - transform_data["rotation_z"])
                local_rotation.w = bone_data["rotW"]


            if pose_bone:
                pose_bone.rotation_mode = rotation_mode
                pose_bone.location = (local_transform.x, local_transform.y, local_transform.z)
                pose_bone.scale = (local_scale.x, local_scale.y, local_scale.z)

                if bone_data["useQuat"] == 0:
                    print("euler:", bone_name, local_rotation)
                    pose_bone.rotation_euler = (local_rotation.x, local_rotation.y, local_rotation.z)
                    for prop in ['location', 'rotation_euler', 'scale']:
                        pose_bone.keyframe_insert(data_path=prop)
                else:
                    print("quat:", bone_name, local_rotation)
                    pose_bone.rotation_quaternion = (local_rotation.w, local_rotation.x, local_rotation.y, local_rotation.z)
                    for prop in ['location', 'rotation_quaternion', 'scale']:
                        pose_bone.keyframe_insert(data_path=prop)

            else:
                print(f"Pose bone {bone_name} not found in the armature.")

            # Advance to the next frame
        bpy.ops.screen.frame_offset(delta=1)
        
        # Switch back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

    else:
        print("Armature object not found or is not an armature.")
