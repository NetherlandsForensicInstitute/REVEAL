import random
import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from modifications import apply_modifications
from generate_messages import generate_messages
import os
import argparse

# Some parameters
HELPER_PARENTHESES = '"'
SUDO_PASSWORD = ""
WATERMARK = "Made@NFI!"

# Command strings for the command line based tools. For GUI tools Microsoft Power Automate was used. These scripts could
# not be included in this repository.
def write_tool_command(command_string, stego_image_name, modified_image_name,
                       tool, input_path, message_path, dest_path, key,
                       linux_tool_dir):
    command_string += f"if not os.path.exists('{dest_path}/{stego_image_name}'):"
    match tool:
        case 0:  # Works
            command_string += f"os.system(f{HELPER_PARENTHESES}echo {SUDO_PASSWORD} | sudo -S cp '{input_path}' '{dest_path}'{HELPER_PARENTHESES})"
        case 1:  # Check
            command_string += f"os.system({HELPER_PARENTHESES}python '{linux_tool_dir}/LSB/LSBRmain.py' --path='{input_path}' --dest_path='{dest_path}/' --encode --secret_path='{message_path}' --image_name='{stego_image_name.split('.')[0]}' {HELPER_PARENTHESES})"
        case 2:
            command_string += f"\n try: \n \t pvd_embed = processor.PVDProcessor('{input_path}'); \n \t pvd_embed.embed_payload('{message_path}', '{dest_path}/{stego_image_name}') \n except: \n \t pass"
        case 6:  # Works
            command_string += f"os.system({HELPER_PARENTHESES}steghide --embed -cf '{input_path}' -sf '{dest_path}/{stego_image_name}' -ef '{message_path}' -p {key}{HELPER_PARENTHESES})"
        case 8:  # Works
            command_string += f"os.system({HELPER_PARENTHESES}{linux_tool_dir}/stegify encode --carrier '{input_path}' --data '{message_path}' --result '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 12:  # Works
            command_string += f"os.system({HELPER_PARENTHESES} {linux_tool_dir}/jsteg hide '{input_path}' '{message_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 15:  # Check
            command_string += f"os.system({HELPER_PARENTHESES} stegano-lsb hide -i '{input_path}' -m '{message_path}' -o '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 19:  # Works
            command_string += f"os.system({HELPER_PARENTHESES}{linux_tool_dir}/stegolsb steglsb -h -i '{input_path}' -o '{dest_path}/{stego_image_name}' -s '{message_path}'{HELPER_PARENTHESES})"
        case 21:  # Works
            command_string += f"os.system({HELPER_PARENTHESES}'{linux_tool_dir}/stego' encode File --input '{input_path}' --output '{dest_path}/{stego_image_name}' --payload '{message_path}'{HELPER_PARENTHESES})"
        case 25:  # Works
            command_string += f"os.system({HELPER_PARENTHESES} cp '{input_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES});"
            if key != 'nan':
                command_string += f"os.system({HELPER_PARENTHESES}{linux_tool_dir}/stegman/./stegman encode {key} '{dest_path}/{stego_image_name}' '{message_path}'{HELPER_PARENTHESES})"
            else:
                command_string += f"os.system({HELPER_PARENTHESES}{linux_tool_dir}/stegman/./stegman encode '{dest_path}/{stego_image_name}' '{message_path}'{HELPER_PARENTHESES})"
        case 26:  # Works
            command_string += f"os.system({HELPER_PARENTHESES}python {linux_tool_dir}/tartarus.py -i '{input_path}' -o '{dest_path}/{stego_image_name}' -m '{message_path}'{HELPER_PARENTHESES})"
        case 42:  # Works
            command_string += f"\n try: \n \t os.system({HELPER_PARENTHESES} python '{linux_tool_dir}/DCT/run_stego_algorithm.py' -I '{input_path}' -M '{message_path}' -O '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES}) \n except: \n \t pass"
        case 43:  # Works
            command_string += f"os.system({HELPER_PARENTHESES} cp '{input_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES});"
            command_string += f"os.system({HELPER_PARENTHESES} python2 {linux_tool_dir}/Matroschka/matroschka.py -hide -k {key} -m {key} '{message_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 178:  # Works
            command_string += f"os.system({HELPER_PARENTHESES} {linux_tool_dir}/StegoLeggo/./a.out encode '{input_path}' '{message_path}'{HELPER_PARENTHESES});"
            command_string += f"os.system({HELPER_PARENTHESES}cp '{os.getcwd()}/encoded_image.{input_path.split('.')[-1]}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES});"
            command_string += f"os.system({HELPER_PARENTHESES}rm '{os.getcwd()}/encoded_image.{input_path.split('.')[-1]}' {HELPER_PARENTHESES})"
        case 49:
            command_string += f"os.system({HELPER_PARENTHESES}python {linux_tool_dir}/pvd_steganography/test_main.py E '{input_path}' '{message_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 45:
            command_string += f"os.system({HELPER_PARENTHESES} python2 {linux_tool_dir}/stepic-0.3/stepic --encode -i '{input_path}' -t '{message_path}' -o '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 54:
            command_string += f"os.system({HELPER_PARENTHESES}'{linux_tool_dir}/jphs/./jphide' '{input_path}' '{dest_path}/{stego_image_name}' '{message_path}'{HELPER_PARENTHESES})"
        case 67:
            command_string += f"os.system({HELPER_PARENTHESES} steganography-png -o hide -i '{input_path}' -sf '{message_path}' {HELPER_PARENTHESES});"
            command_string += f"os.system({HELPER_PARENTHESES} cp 'new-image.png' '{dest_path}/{stego_image_name}' {HELPER_PARENTHESES});"
            command_string += f"os.system({HELPER_PARENTHESES} rm 'new-image.png' {HELPER_PARENTHESES})"
        case 79:
            command_string += f"os.system({HELPER_PARENTHESES} cp '{input_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES});"
            command_string += f"os.system(f{HELPER_PARENTHESES}hide4pgp '{dest_path}/{stego_image_name}' '{message_path}'{HELPER_PARENTHESES})"
        case 104:
            command_string += f"os.system(f{HELPER_PARENTHESES}invisible-watermark -a encode -t bytes -m dwtDct -w {WATERMARK} -o '{dest_path}/{stego_image_name}' '{input_path}'{HELPER_PARENTHESES})"
        case 126:  # Check
            command_string += f"os.system({HELPER_PARENTHESES}python '{linux_tool_dir}/LSB/LSBMmain.py' --path='{input_path}' --dest_path='{dest_path}/' --encode --secret_path='{message_path}' --image_name='{stego_image_name.split('.')[0]}'{HELPER_PARENTHESES})"
        case 159:
            command_string += f"os.system(f{HELPER_PARENTHESES}stegosuite embed -k {key} -f '{message_path}' -o '{dest_path}/{stego_image_name}' '{input_path}'{HELPER_PARENTHESES})"
        case 169:
            command_string += f"\n\tos.chdir({HELPER_PARENTHESES}{linux_tool_dir}/F5-steganography{HELPER_PARENTHESES});\n"
            if key != 'nan':
                command_string += f"\tos.system({HELPER_PARENTHESES}java Embed '{input_path}' -p {key} -e '{message_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
            else:
                command_string += f"\tos.system({HELPER_PARENTHESES}java Embed '{input_path}' -e '{message_path}' '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case 172:  # Works
            command_string += f"\n try: \n \t lsb_embed = processor.LSBProcessor('{input_path}'); \n \t lsb_embed.embed_payload('{message_path}', '{dest_path}/{stego_image_name}') \n except: \n \t pass"
        case 190:
            command_string += f"os.system({HELPER_PARENTHESES} rsteg encode -i '{input_path}' -f '{message_path}' -o '{dest_path}/{stego_image_name}'{HELPER_PARENTHESES})"
        case _:
            command_string = command_string[:-len(
                f"if not os.path.exists('{dest_path}/{stego_image_name}'):")]
            command_string = write_run_manually_command(command_string,
                                                        input_path, dest_path,
                                                        modified_image_name,
                                                        stego_image_name, tool)
    return command_string, key


def write_run_manually_command(command_string, input_path, dest_path,
                               modified_image_name, stego_image_name,
                               tool_number):
    new_dir_name = f'Tool {str(tool_number)}'
    command_string += f"if not os.path.isdir('{dest_path}/{new_dir_name}') and not glob.glob('{dest_path}/{stego_image_name.split('.')[0]}.*'): os.mkdir('{dest_path}/{new_dir_name}'); \n"
    command_string += f"if not glob.glob('{dest_path}/{new_dir_name}/{modified_image_name.split('.')[0]}.*'): os.system({HELPER_PARENTHESES}cp '{input_path}' '{dest_path}/{new_dir_name}/{modified_image_name}'{HELPER_PARENTHESES})"
    return command_string


def main(dataset_master_file: str,
         tool_info: str,
         original_picture_dir: str,
         modified_picture_dir: str,
         stego_picture_dir: str,
         message_dir: str,
         linux_tool_dir: str,
         output_dir: str):
    # Tool Info
    tool_info_df = pd.read_excel(tool_info, index_col='ID', decimal=',')

    # Read dataset master file
    data = pd.read_csv(dataset_master_file, sep=';', decimal=',')

    # Apply modifications if necessary
    print(datetime.now().strftime(
        "%m/%d/%Y, %H:%M:%S") + f": Started applying modifications...")

    if "nrOfColourChannelsAfterModification" not in data.columns:
        data['nrOfColourChannelsAfterModification'] = ''

    if "stegoPictureName" not in data.columns:
        data['stegoPictureName'] = ""

    # If selection of tools made, only select these tools
    data_selected_tools = data.copy()

    # Create progress bar
    pbar = tqdm(total=len(data_selected_tools))

    # Loop over data
    for index, row in data_selected_tools.iterrows():
        input_path = f"{original_picture_dir}/{row['camera']}/{row['originalPictureName']}"
        tool = row['tool']
        accepted_file_types = tool_info_df.loc[
            tool, 'AcceptedFileTypes'].split('-')
        stego_setting = tool_info_df.loc[tool, 'Type/Setting']
        new_input_path, data, modifications = apply_modifications(input_path,
                                                                  index, row[
                                                                      'modifiedPictureName'],
                                                                  row[
                                                                      'modifications'],
                                                                  data,
                                                                  modified_picture_dir,
                                                                  accepted_file_types,
                                                                  stego_setting)
        pbar.update(1)

        # Pick random stegopicture output type from possibilities
        if tool in tool_info_df.loc[tool_info_df[
                                        'AcceptedFileTypeHasToEqualOutputFileType'] == True].index.tolist():
            data.loc[index, 'stegoPictureName'] = row['modifiedPictureName']
        if data.loc[index, 'stegoPictureName'] == "" or pd.isnull(
                data.loc[index, 'stegoPictureName']):
            stego_picture_type = random.choice(
                tool_info_df.loc[tool, 'OutputFileTypes'].split('-'))
            data.loc[index, 'stegoPictureName'] = \
            row['modifiedPictureName'].split('.')[0] + '.' + stego_picture_type

        # Write updated modified image paths to csv every 100 pictures
        if index % 100000 == 0:
            # Save dataset
            data.to_csv(dataset_master_file, index=False, sep=';', decimal=',')

            # Generate new messages if necessary
            generate_messages(data, message_dir)

        # Write updated modified image paths to csv
        data.to_csv(dataset_master_file, index=False, sep=';', decimal=',')

    # Generate commands in separate file for each OS
    for operating_system in tool_info_df['Run OS'].unique():
        print(datetime.now().strftime(
            "%m/%d/%Y, %H:%M:%S") + f": Started generating {operating_system} commands...")

        # Only write commands for current os tools
        current_os_tools = [int(x) for x in tool_info_df.loc[
            tool_info_df['Run OS'] == operating_system].index.to_list()]
        data_os = data[data['tool'].isin(current_os_tools)]
        data_os = data_os.sort_values('tool')
        data_os_selected_tools = data_os.copy()

        # Store commands as one string
        commands = []
        command_string = ''

        # For writing commands
        commands.append('import os; \n')
        commands.append('import glob; \n')

        # For printing updates
        commands.append('from datetime import datetime; \n')

        # For copying files
        commands.append('import shutil; \n')

        # Add info text
        commands.append(
            "print(datetime.now().strftime('%m/%d/%Y, %H:%M:%S') + ': Started generating stego images...'); \n")

        # Add progress bar
        commands.append('from tqdm import tqdm; \n')
        commands.append(
            'pbar = tqdm(total={0}); \n'.format(len(data_os_selected_tools)))

        # Necessary imports for tools
        commands.append('import sys; \n')
        commands.append(f"sys.path.append('{linux_tool_dir}/StegArmory'); \n")
        commands.append(f'import processor; \n')
        commands.append('from steganogan import SteganoGAN; \n')

        # Generate commands
        pbar = tqdm(total=len(data_os_selected_tools))
        for index, row in data_os_selected_tools.iterrows():
            stego_image_name = row['stegoPictureName']
            modified_image_name = row['modifiedPictureName']
            tool = row['tool']
            message_path = f"{message_dir}/{row['message']}"
            dest_path = f"{stego_picture_dir}"
            key = str(row['key'])
            modified_image_input_path = modified_picture_dir + '/' + row[
                'modifiedPictureName']

            # Write appropriate command given tool
            if operating_system == 'Linux':
                commands.append(
                    f"print('Currently generating stego image {stego_image_name} using tool {tool} with embedding rate {row['embeddingRate']}'); \n")
            command, key = write_tool_command("", stego_image_name,
                                              modified_image_name, tool,
                                              modified_image_input_path,
                                              message_path, dest_path, key,
                                              linux_tool_dir)
            if key == 'nan':
                data.loc[index, 'key'] = ''
            else:
                data.loc[index, 'key'] = key
            commands.append(command)
            commands.append("; \n")
            commands.append("pbar.update(1); \n")

            # Combine everything in one string
            command_string = ''.join(c for c in commands)

            # Update progress bar
            pbar.update(1)

        # Write string to text file
        print(datetime.now().strftime(
            "%m/%d/%Y, %H:%M:%S") + ": Applied modifications...")
        print(datetime.now().strftime(
            "%m/%d/%Y, %H:%M:%S") + ": Writing commands to text file...")

        text_file = open(os.path.join(output_dir, "commands" + '_' + str(
            operating_system) + '.py'), "w")
        text_file.write(command_string)
        text_file.close()

        print(datetime.now().strftime(
            "%m/%d/%Y, %H:%M:%S") + ': Generated commands in python script file.')

    # Save dataset master file
    data.to_csv(dataset_master_file, index=False, sep=';', decimal=',')
    print(datetime.now().strftime(
        "%m/%d/%Y, %H:%M:%S") + ': Saved comments to dataset master file.')
    data.to_excel(dataset_master_file.split('.')[0] + '.xlsx', index=False)


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
        '-t',
        '--tool-info',
        help='A path to a .csv file containing information on the stego tools'
             ' that will be used to generate the pictures.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-or',
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
        '-mes',
        '--message-dir',
        help='A path to the directory containing the messages to hide.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-l',
        '--linux-tool-dir',
        help='A path to the directory containing all Linux tools in a '
             'separate subfolder per tool.',
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
