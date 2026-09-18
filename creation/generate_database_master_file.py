import multiprocessing
import os
import pandas as pd
import numpy as np
import cv2
import random
from datetime import datetime
from atpbar import atpbar
import modifications
from utils import average_hue, complexity, motion_blur
import math
import argparse

# Define important parameters
NUMBER_OF_STEGO_TOOLS = 50 + 1 # (50 stego tools + 1 control condition)
EMBEDDING_RATES = [0.00001, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]
PASSWORD = "Test@1234567890!"
MAX_MODIFICATION_CHAIN_LENGTH = 4

"""Function in parallel reads images from original picture directory in dataframe."""
def read_images_in_dataframe_multiprocessing(image_folder):
    # Initialize threadpool with available number of threads
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    cameras = os.listdir(image_folder)
    cameras = [image_folder + "/" + camera for camera in cameras]
    results = [j for i in pool.map(read_images_from_camera, cameras) for j in i]

    # Creating a pandas DataFrame
    df = pd.DataFrame(results, columns=['originalPictureName', 'originalPictureHash', 'camera', 'cameraYear', 'originalCameraResolution (MP)', 'originalPictureNrOfPixels', 'originalPictureNrOfColorChannels', 'originalPictureComplexity', 'originalPictureAvgHue', 'originalPictureFilesize', 'originalPictureMotionBlur'])
    return df

"""Function sequentially reads images from original picture directory in dataframe."""
def read_images_in_dataframe(image_folder):
    cameras = os.listdir(image_folder)
    cameras = [image_folder + "/" + camera for camera in cameras]
    results = []
    for camera in cameras:
        results.extend(read_images_from_camera(image_folder, camera))

    # Creating a pandas DataFrame
    df = pd.DataFrame(results, columns=['originalPictureName', 'originalPictureHash', 'camera', 'cameraYear', 'originalCameraResolution (MP)', 'originalPictureNrOfPixels', 'originalPictureNrOfColorChannels', 'originalPictureComplexity', 'originalPictureAvgHue', 'originalPictureFilesize', 'originalPictureMotionBlur'])
    return df

"""Function reads image attributes for images in camera folder and adds result to dataframe."""
def read_images_from_camera(picture_dir, camera_folder):
    images_list = []
    images = [x for x in os.listdir(os.path.join(picture_dir, camera_folder))]
    for image in atpbar(images, name=camera_folder):
        try:
            # Default values to change later
            year = 0
            resolution = 0

            # Read image
            img = cv2.imread(os.path.join(picture_dir, camera_folder, image))

            # Calculate complexity
            compl = complexity(img)

            # Determine average hue
            avg_hue = average_hue(img)

            # Calculate number of pixels
            height, width, channels = img.shape
            nr_of_pixels = height * width

            # Get camera from camera folder string
            camera = camera_folder.split('/')[-1]

            # Calculate original image hash
            img_hash = modifications.sha256_file(os.path.join(picture_dir, camera_folder, image))

            # Filesize
            fs = os.path.getsize(os.path.join(picture_dir, camera_folder, image))

            # Motionblur
            mb = motion_blur(img)

            # Add entry to list
            images_list.append([image, img_hash, camera, year, resolution, nr_of_pixels, channels, compl, avg_hue, fs, mb])

        except Exception as e:
            print(f"{camera_folder}/{image}" + f': Something went wrong with this image...: {e}')

    return images_list

""""Function divides the images over tools."""
def assign_stego_tools_to_images(dataframe, tools):
    # Group images by camera
    grouped = dataframe.groupby("camera")

    # For every camera, divide available images over tools
    tool_assignments = []
    for name, camera in grouped:

        # Sort images by complexity
        sorted = camera.sort_values(by="originalPictureComplexity", ascending=True)

        # If not enough images raise exception
        if len(sorted) < NUMBER_OF_STEGO_TOOLS:
            raise Exception('The number of stego tools is larger than the number of available images. Please ensure enough images are available so that every tool has at least one image available.')

        # Create tool division for available images
        split = np.array_split(sorted, len(sorted) // NUMBER_OF_STEGO_TOOLS)

        for current_complexity_level in split:
            # Shuffle tool order
            tool_order = np.arange(NUMBER_OF_STEGO_TOOLS)
            np.random.shuffle(tools)

            # Get a shuffled sample
            shuffled = current_complexity_level.sample(frac=1)

            # Loop over shuffled sample and assign tools randomly in order until all samples have a tool assigned
            current_tool = 0
            for (index, row) in shuffled.iterrows():
                row['tool'] = tool_order[current_tool]
                tool_assignments.append(row[['originalPictureName', 'originalPictureHash', 'camera', 'cameraYear', 'originalCameraResolution (MP)', 'originalPictureNrOfPixels', 'originalPictureNrOfColorChannels', 'originalPictureComplexity', 'originalPictureAvgHue', 'originalPictureFilesize', 'originalPictureMotionBlur', 'tool']].values)
                current_tool += 1
                if current_tool == len(tool_order):
                    current_tool = 0

    df = pd.DataFrame(tool_assignments, columns=['originalPictureName', 'originalPictureHash', 'camera', 'cameraYear', 'originalCameraResolution (MP)', 'originalPictureNrOfPixels', 'originalPictureNrOfColorChannels', 'originalPictureComplexity', 'originalPictureAvgHue', 'originalPictureFilesize', 'originalPictureMotionBlur', 'tool'])
    return df

"""Function adds camera year and resolution to dataframe based on data stored in camera_specs.py."""
def add_camera_specs(dataframe, camera_specs):
    # Loop over images and assign correct camera specs
    for camera in dataframe['camera'].unique():
        dataframe.loc[dataframe['camera'] == camera, 'cameraYear'] = camera_specs.loc[camera_specs['Camera'] == camera, 'Year'].tolist()[0]
        dataframe.loc[dataframe['camera'] == camera, 'originalCameraResolution (MP)'] = camera_specs.loc[camera_specs['Camera'] == camera, 'Resolution (MP)'].tolist()[0]

    return dataframe

""""Function distributes embedding rates in EMBEDDING_RATES randomly over images."""
def distribute_embedding_rates(dataframe, tool_run_info_df):
    watermarking_tools = tool_run_info_df[tool_run_info_df['Type/Setting'] == "Watermarking"].index.tolist()

    # Loop over tools and divide embedding rates
    for group_name, group_df in dataframe.groupby('tool'):
        # generate equal number of embedding rates and assign randomly to images in group
        embedding_rates_to_distribute = np.tile(EMBEDDING_RATES, math.floor(len(group_df)/len(EMBEDDING_RATES)))
        embedding_rates_to_distribute = np.append(embedding_rates_to_distribute, random.choices(EMBEDDING_RATES, k=len(group_df) % len(EMBEDDING_RATES)))
        np.random.shuffle(embedding_rates_to_distribute)
        dataframe.loc[group_df.index, "embeddingRate"] = embedding_rates_to_distribute

    # Set embedding rate to 0 for non-stego tools
    dataframe.loc[dataframe['tool'] == 0, "embeddingRate"] = 0
    dataframe.loc[dataframe['tool'].isin(watermarking_tools), "embeddingRate"] = 0

    return dataframe

def distribute_modifications(dataframe):
    # Add random modification chain for every picture
    dataframe['modifications'] = dataframe.apply(lambda x: modifications.generate_possible_modification_chain(MAX_MODIFICATION_CHAIN_LENGTH, x['originalPictureNrOfPixels']), axis=1)
    return dataframe

""""Function assigns correct stego messages to every image depending on its resolution and embedding rate."""
def assign_stego_messages(dataframe, tool_run_info_df):
    text = []
    steg = []
    watermarking_tools = tool_run_info_df[tool_run_info_df['Type/Setting'] == "Watermarking"].index.tolist()

    for name, row in dataframe.iterrows():
        # If no stego no message is needed
        if row["tool"] == 0:
            text.append("-")
            steg.append("No Stego")
        # If tool is watermarking tool
        elif row["tool"] in watermarking_tools:
            text.append("Watermark.txt")
            steg.append("Watermark")
        # Otherwise add name of corresponding file
        else:
            text.append(f"{str(row['embeddingRate']).replace('.', '')}_{str(row['originalPictureNrOfPixels'])}_{row['originalPictureNrOfColourChannels']}.txt")
            steg.append("Stego")

    dataframe["message"] = text
    dataframe["stego"] = steg
    dataframe.reset_index()

    return dataframe

""""Function adds keys to be used in algorithm (if necessary) to dataframe."""
def add_keys(dataframe, tool_run_info_df):
    watermarking_tools = tool_run_info_df[tool_run_info_df['Type/Setting'] == "Watermarking"].index.tolist()
    # Iterate over dataframe rows
    for index, row in dataframe.iterrows():
        # Skip control condition
        if row['tool'] != 0 and not row['tool'] in watermarking_tools:
            # Check if tool must have key
            if bool((tool_run_info_df.loc[tool_run_info_df.index == row['tool']]['Must Have Key']).values[0]):
                dataframe.loc[index, "key"] = PASSWORD
            else:
                # For each row add password with probability 0.5
                try:
                    password_possible = bool((tool_run_info_df.loc[tool_run_info_df.index == row['tool']]['Can Have Key']).values[0])
                except:
                    password_possible = False
                if password_possible and bool(random.getrandbits(1)):
                    dataframe.loc[index, "key"] = PASSWORD
                else:
                    dataframe.loc[index, "key"] = ''
        else:
            dataframe.loc[index, "key"] = ''
    return dataframe


def main(picture_dir: str,
         camera_info_file: str,
         tool_info_file: str,
         output_dir: str):
    # Check if all folders have a camera in CameraInfo
    camera_specs = pd.read_csv(camera_info_file, sep=';')
    tool_run_info_df = pd.read_excel(tool_info_file, index_col='ID')
    stego_tools = tool_run_info_df[tool_run_info_df['Type/Setting'] == "Stego"].index.tolist()

    if len(set(camera_specs['Camera'].tolist()).symmetric_difference(set(os.listdir(picture_dir)))) == 0:
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Found all camera specs!")
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ': Started reading images...')

        # Read all images into dataframe
        data = read_images_in_dataframe(picture_dir)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Created dataframe")

        # Add camera year and resolution data
        data = add_camera_specs(data, camera_specs)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Added camera specs")

        # Assign tools to images
        data = assign_stego_tools_to_images(data, stego_tools)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Assigned stego tools")

        # Distribute embedding rates randomly over images
        data = distribute_embedding_rates(data, tool_run_info_df)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Assigned embedding rates")

        # Add modifications
        data = distribute_modifications(data)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Assigned modifications")

        # Add corresponding labels for steganography and secret messages
        data = assign_stego_messages(data, tool_run_info_df)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Assigned messages")

        # Add keys
        data = add_keys(data, tool_run_info_df)
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Assigned keys")

        # Assign images names for stego image directory (prevent overlap)
        data['modifiedPictureName'] = [f"{str(int(index))}.{row['originalPictureName'].split('.')[-1].lower()}" for (index, row) in data.iterrows()]

        data.to_csv(output_dir + '/dataset_master.csv', index=False, sep=';', decimal=',')
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": Saved Dataset master file!")
    else:
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": There is a mismatch between the CameraInfo.csv file and the cameras in the images folder...please ensure the image folder names are equal to the camera names in the csv file and both locations contain the same cameras")
        print(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ": The following cameras are not present on both locations: " + str(set(camera_specs['Camera'].tolist()).symmetric_difference(set(os.listdir(PICTURE_FOLDER_NAME)))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p',
        '--picture-dir',
        help='A path to a directory containing all input pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-c',
        '--camera-info',
        help='A path to a .csv file containing information on the cameras that'
             ' were used to take the pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-t',
        '--tool-info',
        help='A path to a .csv file containing information on the stego tools'
             ' that will be used to generate the pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-o',
        '--output-dir',
        help='The output directory to export the database master file to.',
        required=True,
        type=str
    )
    args = parser.parse_args()
    main(**vars(args))