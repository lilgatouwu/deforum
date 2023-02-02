import os
from rife.inference_video import run_rife_new_video_infer
from .video_audio_utilities import get_quick_vid_info, vid2frames

# e.g gets 'x2' returns just 2 as int
def extract_number(string):
    return int(string[1:]) if len(string) > 1 and string[1:].isdigit() else -1
   
# gets 'RIFE v4.3', returns: 'RIFE43'   
def extract_rife_name(string):
    parts = string.split()
    if len(parts) != 2 or parts[0] != "RIFE" or (parts[1][0] != "v" or not parts[1][1:].replace('.','').isdigit()):
        raise ValueError("Input string should contain exactly 2 words, first word should be 'RIFE' and second word should start with 'v' followed by 2 numbers")
    return "RIFE"+parts[1][1:].replace('.','')

# This function usually gets a filename, and converts it to a legal linux/windows *folder* name
def clean_folder_name(string):
    illegal_chars = ["/", "\\", "<", ">", ":", "\"", "|", "?", "*", "."]
    for char in illegal_chars:
        string = string.replace(char, "_")
    return string

def set_interp_out_fps(interp_x, slom_x, in_vid_fps):
    if interp_x == 'Disabled' or in_vid_fps in ('---', None, '', 'None'):
        return '---'

    clean_interp_x = extract_number(interp_x)
    clean_slom_x = extract_number(slom_x)
    fps = float(in_vid_fps) * int(clean_interp_x)
    if clean_slom_x != -1:
        fps /= int(clean_slom_x)
    return int(fps) if fps.is_integer() else fps
    
# get uploaded video frame count, fps, and return 3 valuees for the gradio UI: in fcount, in fps, out fps (using the set_interp_out_fps function above)
def gradio_f_interp_get_fps_and_fcount(vid_path, interp_x, slom_x):
    if vid_path is None:
        return '---', '---', '---'
    fps, fcount, resolution = get_quick_vid_info(vid_path.name)
    expected_out_fps = set_interp_out_fps(interp_x, slom_x, fps)
    return (fps if fps is not None else '---', fcount if fcount is not None else '---', expected_out_fps)

# handle call to interpolate an uploaded video from gradio button in args.py (the function that calls this func is named 'upload_vid_to_rife')
def process_rife_vid_upload_logic(file, engine, x_am, sl_am, keep_imgs, f_location, f_crf, f_preset, in_vid_fps, f_models_path, folder_name):
    print("got a request to *frame interpolate* an existing video.")
    outdir_no_tmp = os.path.join(os.getcwd(), 'outputs', 'frame-interpolation', folder_name)
    i = 1
    while os.path.exists(outdir_no_tmp):
        outdir_no_tmp = os.path.join(os.getcwd(), 'outputs', 'frame-interpolation', folder_name + '_' + str(i))
        i += 1

    outdir = os.path.join(outdir_no_tmp, 'tmp_input_frames')
    os.makedirs(outdir, exist_ok=True)
    
    vid2frames(video_path=file.name, video_in_frame_path=outdir, overwrite=True, extract_from_frame=0, extract_to_frame=-1, numeric_files_output=True, out_img_format='png')
    
    process_video_interpolation(frame_interpolation_engine=engine, frame_interpolation_x_amount=x_am, frame_interpolation_slow_mo_amount=sl_am, orig_vid_fps=in_vid_fps, deforum_models_path=f_models_path, real_audio_track=file.name, raw_output_imgs_path=outdir, ffmpeg_location=f_location, ffmpeg_crf=f_crf, ffmpeg_preset=f_preset, keep_interp_imgs=keep_imgs, orig_vid_name=folder_name)

# handle actual frame interoplation call to the rife module
def process_video_interpolation(frame_interpolation_engine=None, frame_interpolation_x_amount="Disabled", frame_interpolation_slow_mo_amount="Disabled", orig_vid_fps=None, deforum_models_path=None, real_audio_track=None, raw_output_imgs_path=None, img_batch_id=None, ffmpeg_location=None, ffmpeg_crf=None, ffmpeg_preset=None, keep_interp_imgs=False, orig_vid_name=None, resolution = (512,512)):

    if frame_interpolation_x_amount != "Disabled":

        UHD = False
        if resolution[0] >= 2048 and resolution[1] >= 2048:
            UHD = True
        
        # extract clean numbers from values of 'x2' etc'
        interp_amount_clean_num = extract_number(frame_interpolation_x_amount)
        interp_slow_mo_clean_num = extract_number(frame_interpolation_slow_mo_amount)
        
        # Don't try to merge audio in the end if slow-mo is enabled
        # Todo: slow-down the music to fit the new video duraion wihout changing audio's pitch
        if real_audio_track is not None and (interp_slow_mo_clean_num != -1):
            real_audio_track = None

        # **HANDLE RIFE INTERPOLATIONS** Other models might come in the future
        if frame_interpolation_engine.startswith("RIFE"):
            # change rife model name. e.g: 'RIFE v4.3' becomes 'RIFE43' 
            actual_model_folder_name = extract_rife_name(frame_interpolation_engine)
            
            # make sure interp_amount is in its valid range
            if interp_amount_clean_num not in range(2, 11):
                raise Error("frame_interpolation_x_amount must be between 2x and 10x")
            
            # set initial output vid fps
            fps = float(orig_vid_fps) * interp_amount_clean_num
            # re-calculate fps param to pass if slow_mo mode is enabled
            if interp_slow_mo_clean_num != -1:
                if int(interp_slow_mo_clean_num) not in [2,4,8]:
                    raise Error("frame_interpolation_slow_mo_amount must be 2x, 4x or 8x")
                fps = float(orig_vid_fps) * int(interp_amount_clean_num) / int(interp_slow_mo_clean_num)
                
            # run actual interpolation and video stitching etc - the whole suite
            if actual_model_folder_name:
                run_rife_new_video_infer(interp_x_amount=interp_amount_clean_num, slow_mo_x_amount=interp_slow_mo_clean_num, output=None, model=actual_model_folder_name, fps=fps, deforum_models_path=deforum_models_path, audio_track=real_audio_track, raw_output_imgs_path=raw_output_imgs_path, img_batch_id=img_batch_id, ffmpeg_location=ffmpeg_location, ffmpeg_crf=ffmpeg_crf, ffmpeg_preset=ffmpeg_preset, keep_imgs=keep_interp_imgs, orig_vid_name=orig_vid_name, UHD=UHD)          
