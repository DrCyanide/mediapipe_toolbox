# MediaPipe Toolbox
 Blender Addon automating some human model creation/posing processes with MediaPipe AI

**Note:** This version is **PRE-ALPHA**. It probably won't work on your machine without you doing some coding yourself. I'm mostly uploading it here to avoid loosing my work and share it between my other computer.

The goal is to use [MediaPipe](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker)'s 3D Pose Estimation to assist in the creation of human characters in Blender. This includes face, hand, and body rigging, as well as posing characters from images, webcam, or video. The supported rig is the Rigify rig, because that addon is included with Blender by default and it seems good enough for this.

The project currently rigs faces that match the template created by [mediapipe-facemesh-to-obj](https://github.com/DrCyanide/mediapipe-facemesh-to-obj). I will probably include that project inside this addon eventually.

# Current Status: PRE-ALPHA

* Face
    * Only supports [mediapipe-facemesh-to-obj](https://github.com/DrCyanide/mediapipe-facemesh-to-obj) face meshes
    * Can position face rig to match the face mesh
    * Can automatically cutout eye holes
* Eyes
    * Supports spheres as well as [TinyEye](https://tinynocky.gumroad.com/l/tinyeye?a=299264723). Other eyes should work as long as the origin of the object is in the center of the eye
    * Positions the eye bone on the appropriate eye
* Hands
    * Only supports [Blender's Human Base Meshes Realistic Hands](https://www.blender.org/download/demo-files/) at this time (no MediaPipe integration yet)
    * Can position the rig to fit the hands
* Body
    * Not yet implemented
* Posing
    * Not yet implemented