import bpy
import json
from mathutils import Quaternion, Vector

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

    for frame in replay_data:
        #char_id = replay_data.get("charID")
        bones_data = replay_data.get("bones", [])
        # Iterate through the pose bones and apply transformations to the main tree
        for index, bone_data in enumerate(bones_data):
            #for index in range(5):
                bone_name = f'JOBJ_{index}'
                pose_bone = skeleton.pose.bones.get(bone_name)
                bone_data = bones_data[index]
                transform_data = default_transforms[index]

                local_transform = Vector()
                local_transform.x = (bone_data["posX"] - transform_data["translation_x"])
                local_transform.y = (bone_data["posY"] - transform_data["translation_y"])
                local_transform.z = (bone_data["posZ"] - transform_data["translation_z"])

                local_scale = Vector()
                local_scale.x = (bone_data["scaleX"] - transform_data["scale_x"])
                local_scale.y = (bone_data["scaleY"] - transform_data["scale_y"])
                local_scale.z = (bone_data["scaleZ"] - transform_data["scale_z"])

                if bone_data["useQuat"] == 0:
                    local_rotation = Vector()
                    local_rotation.x = (bone_data["rotX"] - transform_data["rotation_x"])
                    local_rotation.y = (bone_data["rotY"] - transform_data["rotation_y"])
                    local_rotation.z = (bone_data["rotZ"] - transform_data["rotation_z"])
                else:
                    local_rotation = Quaternion()
                    local_rotation.x = (bone_data["rotX"] - transform_data["rotation_x"])
                    local_rotation.y = (bone_data["rotY"] - transform_data["rotation_y"])
                    local_rotation.z = (bone_data["rotZ"] - transform_data["rotation_z"])
                    local_rotation.w = bone_data["rotW"]


                if pose_bone:
                    pose_bone.location = (local_transform.x, local_transform.y, local_transform.z)
                    if bone_data["useQuat"] == 0:
                        print("euler:", bone_name, local_rotation)
                        pose_bone.rotation_euler = (local_rotation.x, local_rotation.y, local_rotation.z)
                    else:
                        print("quat:", bone_name, local_rotation)
                        pose_bone.rotation_quaternion = (local_rotation.w, local_rotation.x, local_rotation.y, local_rotation.z)
                        pose_bone.rotation_euler = local_rotation.to_euler()

                # print(f"Applied transformations to bone {bone_name}")
                else:
                    print(f"Pose bone {bone_name} not found in the armature.")

        # Switch back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

    else:
        print("Armature object not found or is not an armature.")
