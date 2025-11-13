import os
import numpy as np
import pandas as pd
from PIL import ImageOps, ImageFile
import torch
from torchvision import transforms
import subprocess
import time
import random
from PIL import Image
from filehash import FileHash
from utils import average_hue, complexity, PIL_to_opencv, motion_blur

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None
SECOND_MONITOR_WIDTH = 3840
SUDO_PASSWORD = "123stagiair!"
MD5HASHER = FileHash('md5')

modifications = {
    "no modifications" : ["no modifications", 0.35],
    "to JPEG (conversion) PIL DCT quality preset maximum" : ["file conversion", 0.05],
    "to JPEG (conversion) PIL DCT quality preset medium" : ["file conversion", 0.05],
    "to JPEG (conversion) PIL DCT quality preset low": ["file conversion", 0.05],
    "to JPEG (conversion) PIL DCT quality preset web_high": ["file conversion", 0.05],
    "to JPEG (conversion) PIL DCT quality preset web_low": ["file conversion", 0.05],
    "to PNG" : ["file conversion", 0.25],
    "to GIF" : ["file conversion", 0.05],
    "to BMP" : ["file conversion", 0.03],
    "upsampling to 1920x1080": ["resolution modification", 0.015],
    "downsampling to 1920x1080" : ["resolution modification", 0.005],
    "downsampling to 512x512": ["resolution modification", 0.003],
    "downsampling to 256x256": ["resolution modification", 0.003],
    "upsampling to 1280x720" : ["resolution modification", 0.008],
    "downsampling to 1280x720": ["resolution modification", 0.008],
    "upsampling to 1080x1080" : ["resolution modification", 0.008],
    "downsampling to 1080x1080": ["resolution modification", 0.003],
    "upsampling to 3840x2160" : ["resolution modification", 0.005],
    "downsampling to 3840x2160" : ["resolution modification", 0.0005],
    "upsampling to 4096x2160" : ["resolution modification", 0.02],
    "downsampling to 4096x2160" : ["resolution modification", 0.001],
    "upsampling to 500x500" : ["resolution modification", 0.0001],
    "downsampling to 500x500" : ["resolution modification", 0.002],
    "upsampling to 7680x4320" : ["resolution modification", 0.003],
    "crop to 1:1" : ["image boundary modification", 0.015],
    "crop to 3:2" : ["image boundary modification", 0.015],
    "crop to 5:4" : ["image boundary modification", 0.015],
    "crop to 16:9" : ["image boundary modification", 0.015],
    "crop to 9:16" : ["image boundary modification", 0.015],
    "log" : ["compression", 0.008],
    "to JPEG (compression) PIL DCT quality preset maximum" : ["compression", 0.07],
    "to JPEG (compression) PIL DCT quality preset medium" : ["compression", 0.07],
    "to JPEG (compression) PIL DCT quality preset low": ["compression", 0.07],
    "to JPEG (compression) PIL DCT quality preset web_high": ["compression", 0.07],
    "to JPEG (compression) PIL DCT quality preset web_low": ["compression", 0.07],
    "to RGB": ["colour modification", 0.01],
    "to CMYK and back to RGB": ["colour modification", 0.0001],
    "to RGBA (and PNG)": ["colour modification", 0.03],
    "to L": ["colour modification", 0.002],
    "to HSV and back to RGB": ["colour modification", 0.0025],
    "zip and unzip" : ["compression", 0.05],
    "EXIF wipe" : ["other", 0.008],
    "mirror" : ["other", 0.01],
    "rotate 90" : ["rotations", 0.02],
    "rotate -90" : ["rotations", 0.02],
    "rotate 180" : ["rotations", 0.01],
    "screenshot and crop" : ["other", 0.003]
}

# Create helper lists of modification categories
mod_categories = sorted(list(set(np.array(list(modifications.values()))[:, 0])))

def generate_possible_modification_chain(max_modification_chain_length, nr_of_pixels_in_picture):
    # Choose random chain length
    modifications_present = random.choices([False, True], weights=(modifications['no modifications'][1], 1 - modifications['no modifications'][1]), k=1)[0]

    # If modifications present, generate modification chain
    if modifications_present:

        # Initialize empty chain
        chain_list = []

        # As long as chain length is less than max chain length, add modifications
        while len(chain_list) < max_modification_chain_length:
            # Choose modification taking into account probabilities
            chain_list = get_next_modification(chain_list, nr_of_pixels_in_picture)

            # If resolution modified then change number of pixels after modification
            if chain_list[-1].split(' ') == "upsampling" or chain_list[-1].split(' ') == "downsampling":
                resolution = chain_list[-1].split(" ")[2]
                nr_of_pixels_in_picture = int(resolution.split('x')[0]) * int(resolution.split('x')[1])

            # If last modification is no modifications (stop signal), remove it
            if chain_list[-1] == 'no modifications' and len(chain_list) > 1:
                chain_list.remove(chain_list[-1])
                break

        # Turn list into string
        chain = ''
        for i, m in enumerate(chain_list):
            # Add modification
            chain += m

            # Add delimiter
            if i != len(chain_list) - 1:
                chain += ' - '

    # Otherwise return 0 (no modifications)
    else:
        chain = 'no modifications'

    return chain

def get_next_modification(chain, nr_of_pixels_in_picture):
    # If chain is empty, choose random modification to start
    if len(chain) == 0:
        keys_no_mods_removed = list(modifications.keys())
        keys_no_mods_removed.remove('no modifications')
        mod = random.choices(keys_no_mods_removed, weights=list(np.array([modifications[x] for x in modifications if x in keys_no_mods_removed])[:, 1].astype('float')), k=1)[0]

    # Otherwise choose modification category based on last modification
    else:
        possible_mod_categories = []
        # Match with modification type
        match modifications.get(chain[-1])[0]:
            case "file conversion":
                possible_mod_categories = ["resolution modification", "image boundary modification", "rotations", "compression", "colour modification", "other", "no modifications"]
            case "resolution modification":
                possible_mod_categories = ["file conversion", "image boundary modification", "rotations", "compression", "colour modification", "other", "no modifications"]
            case "rotations":
                possible_mod_categories = ["resolution modification", "file conversion", "image boundary modification", "compression", "other", "colour modification", "no modifications"]
            case "image boundary modification":
                possible_mod_categories = ["resolution modification", "file conversion", "rotations", "compression", "other", "colour modification", "no modifications"]
            case "colour modification":
                possible_mod_categories = ["file conversion", "resolution modification", "rotations", "compression", "image boundary modification", "other", "colour modification", "no modifications"]
            case "compression":
                possible_mod_categories = ["file conversion", "resolution modification", "rotations", "compression", "image boundary modification", "colour modification", "other", "no modifications"]
            case "other":
                possible_mod_categories = ["file conversion", "resolution modification", "rotations", "image boundary modification", "compression", "colour modification", "other", "no modifications"]
            case "no modifications":
                return chain

        # Remove possible modifications from excluded categories and pick a new modification taking into account probabilities
        possible_modifications = filter_possible_resolution_modifications(nr_of_pixels_in_picture)
        possible_mods = [x for x in possible_modifications if possible_modifications[x][0] in possible_mod_categories]
        possible_mods_probs = [possible_modifications[x][1] for x in possible_modifications if possible_modifications[x][0] in possible_mod_categories]
        mod = random.choices(possible_mods, weights=possible_mods_probs, k=1)[0]

    # Add to chain
    chain.append(mod)

    return chain

def filter_possible_resolution_modifications(nr_of_pixels_in_picture):
    possible_modifications = modifications.copy()
    for resolution in ["1920x1080", "1280x720", "1080x1080", "3840x2160", "4096x2160", "500x500", "7680x4320"]:
        nr_of_pixels_in_resolution = int(resolution.split("x")[0]) * int(resolution.split("x")[1])
        if nr_of_pixels_in_resolution < nr_of_pixels_in_picture:
            possible_modifications.pop("upsampling to " + resolution, None)
        elif nr_of_pixels_in_resolution > nr_of_pixels_in_picture:
            possible_modifications.pop("downsampling to " + resolution, None)
    return possible_modifications

def convert_image(input_image_path, output_image_path, file_type, dct_quality_preset="maximum"):
    img = Image.open(input_image_path)
    exif_data_present = 'exif' in img.info.keys()
    new_output_image_path = output_image_path.split('.')[0] + '.' + file_type

    # Change to jpeg for encoding if jpg in filename
    if file_type == 'jpg':
        file_type = 'jpeg'

    # If file type is jpeg, change colour mode to RGB
    if (file_type == 'jpeg' and img.mode == 'L') or (file_type == 'jpeg' and img.mode == 'P') or (file_type == 'jpeg' and img.mode == 'RGBA'):
        img = img.convert('RGB')

    # Create EXIF data variable
    if exif_data_present:
        # Save image (for jpeg with given quality preset)
        if file_type == 'jpeg':
            img.save(new_output_image_path, format=file_type, exif=img.info['exif'], quality=dct_quality_preset)
        else:
            img.save(new_output_image_path, format=file_type, exif=img.info['exif'])
    else:
        # Save image (for jpeg with given quality preset)
        if file_type == 'jpeg':
            img.save(new_output_image_path, format=file_type, quality=dct_quality_preset)
        else:
            img.save(new_output_image_path, format=file_type)

    # Remove input image if not equal to output image path
    if input_image_path != new_output_image_path:
        os.system(f"rm '{input_image_path}'")

    return new_output_image_path

def resample_image(input_image_path, output_image_path, image_name, target_resolution):
    # Open image
    img = Image.open(input_image_path)

    # If image height is greater than width, switch target resolution elements (keep original aspect ratio)
    if img.width > img.height:
        target_resolution = (target_resolution[1], target_resolution[0])

    # Resample image
    img_tensor = transforms.ToTensor()(img)
    resampled_tensor = torch.nn.functional.interpolate(input=img_tensor.unsqueeze(0).float(), size=target_resolution, mode='nearest-exact').squeeze()
    resampled_img = transforms.ToPILImage()(resampled_tensor)

    exif_data_present = 'exif' in img.info.keys()
    if exif_data_present:
        resampled_img.save(output_image_path, format=img.format, exif=img.info['exif'])
    else:
        resampled_img.save(output_image_path, format=img.format)

def apply_modifications(original_picture_path, index, picture_name, modifications, dataset_master_file, MODIFIED_PICTURE_DIRECTORY, accepted_file_types, stego_setting):
    # Set modified image path
    modified_picture_path = os.path.join(MODIFIED_PICTURE_DIRECTORY, picture_name)
    applied_modifications = False

    # Only run if image not yet present
    print(modified_picture_path)
    if not os.path.exists(modified_picture_path):
        # Reset modified picture path
        modified_picture_path = f"{modified_picture_path.split('.')[0]}.{original_picture_path.split('.')[-1]}"

        # Copy image to modified image path
        os.system(f"cp '{original_picture_path}' '{modified_picture_path}'")

        # Modify image for every modification in modifications
        if modifications != 'no modifications':
            for m in modifications.split(' - '):
                modified_picture_path = apply_modification(modified_picture_path, picture_name, m)

        # If original image was photoshopped (man_modified), add this as a first modification to the modification chain
        if original_picture_path.split('/')[-1].split('_')[0] == 'MOD':
            if modifications == 'no modifications' or modifications == 'manually photoshopped':
                modifications = 'manually photoshopped'
            else:
                modifications = 'manually photoshopped - ' + modifications

        # Update parameters
        dataset_master_file.loc[index, 'modifiedPictureNrOfPixels'] = get_nr_of_pixels(Image.open(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureWidth'] = Image.open(modified_picture_path).size[0]
        dataset_master_file.loc[index, 'modifiedPictureHeight'] = Image.open(modified_picture_path).size[1]
        dataset_master_file.loc[index, 'modifiedPictureComplexity'] = complexity(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureAvgHue'] = average_hue(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureMotionBlur'] = motion_blur(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureFilesize'] = os.path.getsize(modified_picture_path)
        applied_modifications = True

    # Check input file compatability
    modified_picture_path, modifications, changed_file_type = check_input_file_compatability(modified_picture_path, accepted_file_types, modifications)

    # Check colour mode compatability
    # modified_picture_path, modifications, changed_input_mode = check_colour_mode_compatability(modified_picture_path, index, accepted_colour_modes, modifications, picture_name)

    # If any of the two is missing also recalculate
    if pd.isnull(dataset_master_file.loc[index, 'modifiedPictureComplexity']) or pd.isnull(dataset_master_file.loc[index, 'modifiedPictureAvgHue']):
        changed_file_type = True

    # Update parameters if something changed about the file
    if applied_modifications or changed_file_type:
        dataset_master_file.loc[index, 'modifications'] = modifications
        dataset_master_file.loc[index, 'modifiedPictureComplexity'] = complexity(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureAvgHue'] = average_hue(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureHash'] = MD5HASHER.hash_file(modified_picture_path)
        dataset_master_file.loc[index, 'modifiedPictureNrOfColourChannels'] = get_nr_of_colour_channels(Image.open(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureWidth'] = Image.open(modified_picture_path).size[0]
        dataset_master_file.loc[index, 'modifiedPictureHeight'] =  Image.open(modified_picture_path).size[1]
        dataset_master_file.loc[index, 'modifiedPictureNrOfPixels'] = get_nr_of_pixels(Image.open(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureMotionBlur'] = motion_blur(PIL_to_opencv(modified_picture_path))
        dataset_master_file.loc[index, 'modifiedPictureFilesize'] = os.path.getsize(modified_picture_path)
        if stego_setting == "Stego":
            dataset_master_file.loc[index, 'message'] = f"{str(dataset_master_file.loc[index, 'embeddingRate']).replace('.', '')}_{get_nr_of_pixels(Image.open(modified_picture_path))}_{get_nr_of_colour_channels(Image.open(modified_picture_path))}.txt"
            print("changed message")
        dataset_master_file.loc[index, 'modifiedPictureName'] = modified_picture_path.split('/')[-1]

    return modified_picture_path, dataset_master_file, modifications

def get_nr_of_pixels(image):
    return image.width * image.height

def get_nr_of_colour_channels(image):
    return len(image.getbands())

def check_input_file_compatability(image_path, accepted_file_types, modifications):
    # If current file type is not in accepted file types
    if (image_path.split('.')[-1]).lower() not in accepted_file_types:
        # Change to a random accepted file type
        new_file_type = random.choice(accepted_file_types)

        # Convert file
        new_output_path = convert_image(image_path, image_path, new_file_type)

        # Add modification to end of modification chain
        if modifications == 'no modifications' or modifications[:6] == 'make f':
            modifications = f'make file type compatible (to {new_file_type})'
        elif len(modifications.split(' - ')) > 1 and modifications.split(' - ')[-1][:6] == 'make f':
            old_modifications = modifications.split(' - ')
            old_modifications = old_modifications[:-1]
            old_modifications.append(f'make file type compatible (to {new_file_type})')
            mod_string = ''
            for mod in old_modifications:
                mod_string += mod + ' - '
            modifications = mod_string[:-3]
        else:
            modifications += f' - make file type compatible (to {new_file_type})'

        return new_output_path, modifications, True

    return image_path, modifications, False

def check_colour_mode_compatability(image_path, index, accepted_colour_modes, modifications, picture_name):
    # By default return unchanged
    changed = False

    # If current file type is not in accepted file types
    if Image.open(image_path).mode not in accepted_colour_modes:
        # Change to a random accepted file type
        new_colour_mode = random.choice(accepted_colour_modes)

        # Convert file
        image_path = change_image_mode(image_path, image_path, new_colour_mode, picture_name)

        # Add modification to end of modification chain
        if modifications == 'no modifications' or modifications[:6] == 'make c':
            modifications = f'make colour mode compatible (to {new_colour_mode})'
        else:
            modifications += f' - make colour mode compatible (to {new_colour_mode})'

        # Set changed to true
        changed = True

    return image_path, modifications, changed

# Code based on https://stackoverflow.com/questions/273946/how-do-i-resize-an-image-using-pil-and-maintain-its-aspect-ratio
def crop_image(input_image_path, output_image_path, image_name, target_aspect_ratio):
    # Open image and determine current aspect ratio
    img = Image.open(input_image_path)
    width, height = img.size
    current_aspect_ratio = width / float(height)

    target_width = int(target_aspect_ratio * height)
    target_height = int(width / target_aspect_ratio)

    # If current aspect ratio is bigger than target aspect ratio crop sides, otherwise crop top and bottom
    if current_aspect_ratio > target_aspect_ratio:
        offset = (width - target_width) / 2
        resize_area = (offset, 0, width - offset, height)
    else:
        offset = (height - target_height) / 2
        resize_area = (0, offset, width, height - offset)

    # Crop Image
    image_cropped = img.crop(resize_area)
    # image_cropped.show()

    exif_data_present = 'exif' in img.info.keys()
    if exif_data_present:
        image_cropped.save(output_image_path, format=img.format, exif=img.info['exif'])
    else:
        image_cropped.save(output_image_path, format=img.format)

def mirror_image(input_image_path, output_image_path):
    img = Image.open(input_image_path)
    img_mirrored = ImageOps.mirror(img)
    exif_data_present = 'exif' in img.info.keys()
    if exif_data_present:
        img_mirrored.save(output_image_path, format=img.format, exif=img.info['exif'])
    else:
        img_mirrored.save(output_image_path, format=img.format)

def remove_exif_data(input_image_path, output_image_path):
    img = Image.open(input_image_path)
    img_stripped = Image.new(img.mode, img.size)
    img_stripped.putdata(list(img.getdata()))
    img_stripped.save(output_image_path, format=img.format)

def screenshot_and_crop(input_image_path, output_image_path, image_name):
    # Open image file on screen
    process = subprocess.Popen(["eog", f"{input_image_path}"], shell=False, stdout=subprocess.PIPE)

    # Wait a second
    time.sleep(10)

    # Update image path
    if output_image_path.split('.') == "gif":
        new_file_type = random.choice(['.jpeg', '.png'])
        output_image_path = input_image_path.split('.')[0] + new_file_type
    elif output_image_path.split('.') == '.jpeg':
        output_image_path = input_image_path.split('.')[0] + '.jpg'

    # Crop screenshot using window dimensions (and slight offset to account for inaccuracies in cropping and window dimensions)
    os.system(f'sleep 2s && import -window $(xdotool getactivewindow) {output_image_path}')

    # Wait a second
    time.sleep(10)

    # Close image window
    subprocess.Popen(["wmctrl", "-ic", "$(xdotool getactivewindow)"], shell=False)
    
    # Wait a second
    time.sleep(10)

    # Remove original image if different file type
    if input_image_path != output_image_path:
        os.system(f"rm '{input_image_path}'")

    return output_image_path

# Log transform code adapted from https://www.geeksforgeeks.org/log-transformation-of-an-image-using-python-and-opencv/
def log_compression(input_image_path, output_image_path):
    # Read Image
    img = Image.open(input_image_path)
    img_array = np.array(img)

    # Apply log transform
    c = 255 / np.log1p(np.max(img_array))
    log_image = c * (np.log1p(img_array))
    log_image = np.array(log_image, dtype=np.uint8)

    # Save image
    log_img = Image.fromarray(log_image)
    exif_data_present = 'exif' in img.info.keys()
    if exif_data_present:
        log_img.save(output_image_path, format=img.format, exif=img.info['exif'])
    else:
        log_img.save(output_image_path, format=img.format)

def change_image_mode(input_image_path, output_image_path, image_mode, image_name):
    # Read and convert image
    img = Image.open(input_image_path)
    img_converted = img.convert(image_mode)
    exif_data_present = 'exif' in img.info.keys()
    format = img.format

    # Convert back to RGB in case this colour mode cannot be saved in file
    if img_converted.mode == "HSV" or img_converted.mode == "CMYK":
        img_converted = img_converted.convert('RGB')

    # Convert to png if image mode is RGBA
    if img_converted.mode == "RGBA":
        format = 'png'
        output_image_path = output_image_path.split('.')[0] + '.png'
    if exif_data_present:
        img_converted.save(output_image_path, format=format, exif=img.info['exif'])
    else:
        img_converted.save(output_image_path, format=format)

    # Remove input image if not equal to output image path
    if input_image_path != output_image_path:
        try:
            os.system(f"rm '{input_image_path}'")
        except:
            pass

    return output_image_path

def zip_compression_and_unzip(input_image_path, output_image_path):
    # Create zip file
    os.system(f"zip -j '{output_image_path.split('.')[0]}.zip' '{input_image_path}'")

    # Remove original image
    os.system(f"rm '{input_image_path}'")

    # Unzip zip file
    os.system(f"unzip '{output_image_path.split('.')[0]}.zip' -d '{os.path.dirname(output_image_path)}'")

    # Delete zip archive
    os.system(f"rm '{output_image_path.split('.')[0]}.zip'")

def rotate(input_image_path, output_image_path, angle):
    # Rotate image itself
    img = Image.open(input_image_path)
    img_rot = img.rotate(angle, expand=True)

    exif_data_present = 'exif' in img.info.keys()
    if exif_data_present:
        img_rot.save(output_image_path, format=img.format, exif=img.info['exif'])
    else:
        img_rot.save(output_image_path, format=img.format)

def apply_modification(image_path, image_name, modification):
    match modification:
        case "to JPEG (conversion) PIL DCT quality preset maximum":
            image_path = convert_image(image_path, image_path, 'jpeg', "maximum")
        case "to JPEG (conversion) PIL DCT quality preset medium":
            image_path = convert_image(image_path, image_path, 'jpeg', "medium")
        case "to JPEG (conversion) PIL DCT quality preset low":
            image_path = convert_image(image_path, image_path, 'jpeg', "low")
        case "to JPEG (conversion) PIL DCT quality preset web_high":
            image_path = convert_image(image_path, image_path, 'jpeg', "web_high")
        case "to JPEG (conversion) PIL DCT quality preset web_low":
            image_path = convert_image(image_path, image_path, 'jpeg', "web_low")
        case "to PNG":
            image_path = convert_image(image_path, image_path, 'png')
        case "to GIF":
            image_path = convert_image(image_path, image_path, 'gif')
        case "to BMP":
            image_path = convert_image(image_path, image_path, 'bmp')
        case "upsampling to 1920x1080":
            resample_image(image_path, image_path, image_name, (1080, 1920))
        case "downsampling to 1920x1080":
            resample_image(image_path, image_path, image_name, (1080, 1920))
        case "upsampling to 1280x720":
            resample_image(image_path, image_path, image_name, (720, 1280))
        case "downsampling to 1280x720":
            resample_image(image_path, image_path, image_name, (720, 1280))
        case "upsampling to 1080x1080":
            resample_image(image_path, image_path, image_name, (1080, 1080))
        case "downsampling to 1080x1080":
            resample_image(image_path, image_path, image_name, (1080, 1080))
        case "upsampling to 3840x2160":
            resample_image(image_path, image_path, image_name, (2160, 3840))
        case "downsampling to 3840x2160":
            resample_image(image_path, image_path, image_name, (2160, 3840))
        case "upsampling to 4096x2160":
            resample_image(image_path, image_path, image_name, (2160, 4096))
        case "downsampling to 4096x2160":
            resample_image(image_path, image_path, image_name, (2160, 4096))
        case "upsampling to 500x500":
            resample_image(image_path, image_path, image_name, (500, 500))
        case "upsampling to 7680x4320":
            resample_image(image_path, image_path, image_name, (7680, 4320))
        case "downsampling to 500x500":
            resample_image(image_path, image_path, image_name, (500, 500))
        case "downsampling to 512x512":
            resample_image(image_path, image_path, image_name, (512, 512))
        case "downsampling to 256x256":
            resample_image(image_path, image_path, image_name, (256, 256))
        case "crop to 1:1":
            crop_image(image_path, image_path, image_name, 1 / 1)
        case "crop to 3:2":
            crop_image(image_path, image_path, image_name, 3 / 2)
        case "crop to 5:4":
            crop_image(image_path, image_path, image_name, 5 / 4)
        case "crop to 16:9":
            crop_image(image_path, image_path, image_name, 16 / 9)
        case "crop to 9:16":
            crop_image(image_path, image_path, image_name, 9 / 16)
        case "mirror":
            mirror_image(image_path, image_path)
        case "EXIF wipe":
            remove_exif_data(image_path, image_path)
        case "log":
            log_compression(image_path, image_path)
        case "to JPEG (compression) PIL DCT quality preset maximum":
            image_path = convert_image(image_path, image_path, 'jpeg', "maximum")
        case "to JPEG (compression) PIL DCT quality preset medium":
            image_path = convert_image(image_path, image_path, 'jpeg', "medium")
        case "to JPEG (compression) PIL DCT quality preset low":
            image_path = convert_image(image_path, image_path, 'jpeg', "low")
        case "to JPEG (compression) PIL DCT quality preset web_high":
            image_path = convert_image(image_path, image_path, 'jpeg', "web_high")
        case "to JPEG (compression) PIL DCT quality preset web_low":
            image_path = convert_image(image_path, image_path, 'jpeg', "web_low")
        case "to RGB":
            image_path = change_image_mode(image_path, image_path, 'RGB', image_name)
        case "to RGBA (and PNG)":
            image_path = change_image_mode(image_path, image_path, 'RGBA', image_name)
        case "to L":
            image_path = change_image_mode(image_path, image_path, 'L', image_name)
        case "to CMYK and back to RGB":
            image_path = change_image_mode(image_path, image_path, 'CMYK', image_name)
        case "to HSV and back to RGB":
            image_path = change_image_mode(image_path, image_path, 'HSV', image_name)
        case "zip and unzip":
            zip_compression_and_unzip(image_path, image_path)
        case "screenshot and crop":
            image_path = screenshot_and_crop(image_path, image_path, image_name)
        case "rotate 90":
            rotate(image_path, image_path, 90)
        case "rotate -90":
            rotate(image_path, image_path, -90)
        case "rotate 180":
            rotate(image_path, image_path, 180)
        case _:
            return image_path
    return image_path
