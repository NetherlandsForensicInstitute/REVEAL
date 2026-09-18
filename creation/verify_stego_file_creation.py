import os.path
import pandas as pd
from tqdm import tqdm
from utils import *
from modifications import get_nr_of_colour_channels, sha256_file
import argparse


def main(dataset_master_file: str,
         original_picture_dir: str,
         modified_picture_dir: str,
         stego_picture_dir: str,
         check_for_missed_files: bool = False,
         reread_original_pictures: bool = False,
         reread_modified_pictures: bool = False,
         reread_stego_pictures: bool = False):

    # Read dataset master file into dataframe
    dataset = pd.read_csv(dataset_master_file)

    # Calculate hashes of stego pictures if not yet filled in

    # Temporarily add helper column
    dataset['modifiedPictureInteger'] = (
        dataset['modifiedPictureName'].apply(lambda x: x.split('.')[0]))

    # Check for missed files
    if check_for_missed_files:
        for file in os.listdir(stego_picture_dir):
            if not os.path.isdir(file):
                filepath = os.path.join(stego_picture_dir, file)
                pictureInteger = file.split('.')[0]
                if len(dataset.loc[dataset['modifiedPictureInteger'] == pictureInteger, 'stegoPictureName'].tolist()) > 0 and pd.isnull(dataset.loc[dataset['modifiedPictureInteger'] == pictureInteger, 'stegoPictureName'].tolist()[0]):
                    print(pictureInteger, file)
                    dataset.loc[dataset['modifiedPictureInteger'] == pictureInteger, 'stegoPictureName'] = file

    # Only look at pictures that do already have a modified picture
    dataset_modified_pictures = dataset.dropna(subset=['stegoPictureName'])

    # Loop over stego pictures and fill in dataframe for existing pictures
    pbar = tqdm(total=len(dataset_modified_pictures))
    for index, row in dataset_modified_pictures.iterrows():
        # Check stego picture hash
        if row['stegoPictureHash'] == '' or pd.isna(row['stegoPictureHash']) or row['stegoPictureHash'] == "Stego picture was not found" or reread_stego_pictures:
            pic = os.path.join(stego_picture_dir, row['stegoPictureName'])
            try:
                picture = Image.open(pic)
                opencv_pic = PIL_to_opencv(pic)
                dataset.loc[index, 'stegoPictureHash'] = sha256_file(pic)
                dataset.loc[index, 'stegoPictureNrOfColourChannels'] = get_nr_of_colour_channels(picture)
                dataset.loc[index, 'stegoPictureComplexity'] = complexity(opencv_pic)
                width, height = picture.size
                dataset.loc[index, 'stegoPictureWidth'] = width
                dataset.loc[index, 'stegoPictureHeight'] = height
            except:
                dataset.loc[index, 'stegoPictureHash'] = np.nan
                dataset.loc[index, 'stegoPictureNrOfColourChannels'] = np.nan
                dataset.loc[index, 'stegoPictureComplexity'] = np.nan
                dataset.loc[index, 'stegoPictureWidth'] = np.nan
                dataset.loc[index, 'stegoPictureHeight'] = np.nan
        pbar.update(1)

    # Check if modified picture exists and adjust dataset master accordingly
    pbar = tqdm(total=len(dataset))
    for index, row in dataset.iterrows():
        if not os.path.exists(os.path.join(modified_picture_dir, row['modifiedPictureName'])):
            dataset.loc[index, 'modifiedPictureHash'] = np.nan
            dataset.loc[index, 'modifiedPictureComplexity'] = np.nan
            dataset.loc[index, 'modifiedPictureNrOfColourChannels'] = np.nan
            dataset.loc[index, 'modifiedPictureWidth'] = np.nan
            dataset.loc[index, 'modifiedPictureHeight'] = np.nan
        elif pd.isna(dataset.loc[index, 'modifiedPictureHash']) or reread_modified_pictures:
            try:
                pic_path = os.path.join(modified_picture_dir, row['modifiedPictureName'])
                picture = Image.open(pic_path)
                opencv_pic = PIL_to_opencv(pic_path)
                dataset.loc[index, 'modifiedPictureHash'] = sha256_file(pic_path)
                dataset.loc[index, 'modifiedPictureComplexity'] = complexity(opencv_pic)
                dataset.loc[index, 'modifiedPictureNrOfColourChannels'] = get_nr_of_colour_channels(picture)
                width, height = picture.size
                dataset.loc[index, 'modifiedPictureWidth'] = width
                dataset.loc[index, 'modifiedPictureHeight'] = height
            except:
                pass
        pbar.update(1)

    # Recalculate empty original picture hashes
    pbar = tqdm(total=len(dataset))
    for index, row in dataset.iterrows():
        if pd.isna(dataset.loc[index, 'originalPictureHash']):
            pic_path = os.path.join(original_picture_dir, row['camera'], row['originalPictureName'])
            dataset.loc[index, 'originalPictureHash'] = sha256_file(pic_path)
        pbar.update(1)

    # Recalculate original picture complexities and avg hues
    if reread_original_pictures:
        pbar = tqdm(total=len(dataset))
        for index, row in dataset.iterrows():
            pic_path = os.path.join(original_picture_dir, row['camera'], row['originalPictureName'])
            picture = Image.open(pic_path)
            opencv_pic = PIL_to_opencv(pic_path)
            dataset.loc[index, 'originalPictureComplexity'] = complexity(opencv_pic)
            dataset.loc[index, 'originalPictureNrOfColourChannels'] = get_nr_of_colour_channels(picture)
            width, height = picture.size
            dataset.loc[index, 'originalPictureWidth'] = width
            dataset.loc[index, 'originalPictureHeight'] = height
            pbar.update(1)

    # Remove helper column
    dataset = dataset.drop('modifiedPictureInteger', axis=1)

    # Update dataset
    if reread_original_pictures or reread_modified_pictures or reread_stego_pictures or check_for_missed_files:
        dataset.to_csv(dataset_master_file, index=False, decimal='.')

    # Drop part of dataset for which stego did not work
    dataset_successfully_created_pictures = dataset.dropna(subset=['stegoPictureHash'])
    dataset_successfully_modified_pictures = dataset.dropna(subset=['modifiedPictureHash'])
    print(f'Proportion successfully generated pictures: {round(len(dataset_successfully_created_pictures)/len(dataset) * 100, 2)}%')
    print(f'Proportion successfully modified pictures: {round(len(dataset_successfully_modified_pictures)/len(dataset) * 100, 2)}%')
    print()

    # Perform checks
    if not len(dataset_successfully_modified_pictures)==len(dataset):
        print("Not all pictures have been modified yet...")
    else:
        # Stego Picture Hashes are Unique
        stego_pictures_are_unique = dataset_successfully_created_pictures['stegoPictureHash'].duplicated() == 0
        print("Stego picture hashes are unique:", stego_pictures_are_unique.all())
        if not stego_pictures_are_unique.all():
            print(dataset_successfully_created_pictures[
                      dataset_successfully_created_pictures['stegoPictureHash'].duplicated() == True][
                      'modifiedPictureName'])

        # Modified Picture Hashes are Unique
        modified_pictures_are_unique = dataset_successfully_created_pictures['modifiedPictureHash'].duplicated() == 0
        print("Modified picture hashes are unique:", modified_pictures_are_unique.all())
        if not modified_pictures_are_unique.all():
            print(dataset_successfully_modified_pictures[
                      dataset_successfully_modified_pictures['modifiedPictureHash'].duplicated() == True][
                      'modifiedPictureName'])

        # Original Picture Hashes are Unique
        original_pictures_are_unique = dataset_successfully_created_pictures['originalPictureHash'].duplicated() == 0
        print("Original picture hashes are unique:", original_pictures_are_unique.all())
        if not original_pictures_are_unique.all():
            print(dataset_successfully_modified_pictures[dataset_successfully_modified_pictures['originalPictureHash'].duplicated() == True]['originalPictureName'])

        # Control condition hashes of modified pictures and stego pictures are the same
        control_condition_pictures = dataset_successfully_created_pictures[dataset_successfully_created_pictures['toolName'] == 'Control Condition']
        control_modified_same_as_stego = control_condition_pictures['modifiedPictureHash'] == control_condition_pictures['stegoPictureHash']
        print("Modified pictures are the same as stego pictures for control condition:", control_modified_same_as_stego.all())
        if not control_modified_same_as_stego.all():
            print(control_condition_pictures[control_modified_same_as_stego == False]['modifiedPictureName'])

        # Stego condition hashes of modified pictures and stego pictures are different
        stego_condition_pictures = dataset_successfully_created_pictures[dataset_successfully_created_pictures['toolName'] != 'Control Condition']
        stego_modified_different_from_stego = (stego_condition_pictures['modifiedPictureHash'] != stego_condition_pictures['stegoPictureHash'])
        print("Modified pictures are different from stego pictures for stego/watermarking condition:", stego_modified_different_from_stego.all())
        if not stego_modified_different_from_stego.all():
            print(stego_condition_pictures[stego_modified_different_from_stego == False]['modifiedPictureName'].tolist())

        # Original picture hashes and modified picture hashes for pictures with no modifications are the same
        pictures_without_modifications = dataset[dataset['modifications'] == 'no modifications']
        no_modification_original_pictures_same_as_modified = (pictures_without_modifications['modifiedPictureHash'] == pictures_without_modifications['originalPictureHash'])
        print("Original pictures are the same as modified pictures for pictures without modifications:", no_modification_original_pictures_same_as_modified.all())
        if not no_modification_original_pictures_same_as_modified.all():
            print(pictures_without_modifications[no_modification_original_pictures_same_as_modified == False]['modifiedPictureName'].tolist())

        # Messages have the properties of modified picture
        dataset_stego = dataset[dataset['message'] != '-']
        dataset_stego = dataset_stego[dataset_stego['message'] != 'Watermark.txt']

        embedding_rate_in_message = dataset_stego['message'].apply(lambda x: float(x.split("_")[0][:1] + '.' + x.split("_")[0][1:]))
        embedding_rate_modified_picture = dataset_stego['embeddingRate'].apply(lambda x: str(x).replace(',', '.')).astype(float)

        nr_of_pixels_in_message = dataset_stego['message'].apply(lambda x: int(x.split("_")[1]))
        nr_of_pixels_modified_picture = dataset_stego['modifiedPictureWidth'].astype(int) * dataset_stego['modifiedPictureHeight'].astype(int)

        nr_of_colour_channels_in_message = dataset_stego['message'].apply(lambda x: int(x.split("_")[2].split('.')[0]))
        nr_of_colour_channels_modified_picture = dataset_stego['modifiedPictureNrOfColourChannels'].astype(int)

        dataset_stego['seemsWrongMessage'] = (nr_of_pixels_in_message != nr_of_pixels_modified_picture) | (embedding_rate_in_message != embedding_rate_modified_picture) | (nr_of_colour_channels_modified_picture != nr_of_colour_channels_in_message)
        print("Correct messages corresponding with modified pictures:", dataset_stego['seemsWrongMessage'].sum() == 0)
        if dataset_stego['seemsWrongMessage'].sum() != 0:
            print(dataset_stego[dataset_stego['seemsWrongMessage'] == True]['modifiedPictureName'].tolist())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d',
        '--dataset-master-file',
        help='The dataset master file to verify.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-o',
        '--original-picture-dir',
        help='A path to the directory containing the original pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-m',
        '--modified-picture-dir',
        help='A path to the directory containing the modified pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-s',
        '--stego-picture-dir',
        help='A path to the directory containing the stego pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-c',
        '--check-for-missed-files',
        help='Whether to check for missed files.',
        required=False,
        default=False,
        type=bool
    )
    parser.add_argument(
        '-ro',
        '--reread-original-pictures',
        help='Whether to recalculate all data for the original pictures.',
        required=False,
        default=False,
        type=bool
    )
    parser.add_argument(
        '-rm',
        '--reread-modified-pictures',
        help='Whether to recalculate all data for the modified pictures.',
        required=False,
        default=False,
        type=bool
    )
    parser.add_argument(
        '-so',
        '--reread-stego-pictures',
        help='Whether to recalculate all data for the stego pictures.',
        required=False,
        default=False,
        type=bool
    )
    args = parser.parse_args()
    main(**vars(args))