#!/usr/bin/env python3
import os
import subprocess
import sys
import yaml
import argparse
from pathlib import Path

# Define constants
BUILD_INFO_FILE = "build-info.yaml"
DEFAULT_WIX_BIN_PATH = r"C:\Program Files\WiX Toolset v5.0\bin"

# Function to check if WiX Toolset is installed
def check_wix_toolset(wix_path):
    candle_path = Path(wix_path) / "candle.exe"
    light_path = Path(wix_path) / "light.exe"
    
    if not candle_path.exists() or not light_path.exists():
        print("Error: WiX Toolset is not installed or not found in the expected location.")
        print("Please ensure that WiX Toolset is installed and the path is correctly set.")
        sys.exit(1)

# Function to run a subprocess and check for errors
def run_command(command, quiet=False):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    if not quiet:
        print(result.stdout)

# Function to read YAML configuration
def read_build_info(project_dir):
    build_info_path = Path(project_dir) / BUILD_INFO_FILE
    with open(build_info_path, 'r') as file:
        return yaml.safe_load(file)

# Function to populate the 'files[]' section with contents from the 'payload' folder
def populate_files_section(project_dir, config):
    payload_dir = Path(project_dir) / "payload"
    files_list = []
    
    if not payload_dir.exists():
        print(f"Error: Payload directory {payload_dir} does not exist.")
        sys.exit(1)

    for file_path in payload_dir.rglob('*'):
        if file_path.is_file():
            # Create a file entry
            file_entry = {
                "source": str(file_path).replace("\\", "/"),
                "destination": f"[INSTALLFOLDER]{file_path.relative_to(payload_dir)}",
                "component_id": f"Component_{file_path.stem}"
            }
            files_list.append(file_entry)
    
    # Update the config with the new files list
    config['files'] = files_list

    # Write the updated config back to the YAML file
    with open(Path(project_dir) / BUILD_INFO_FILE, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

# Function to generate WiX files
def generate_wix_files(project_dir, config):
    # Create the src directory if it doesn't exist
    src_dir = Path(project_dir) / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Generate Product.wxs
    product_wxs_content = f"""
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="{config['product']['name']}" Language="1033" Version="{config['product']['version']}" Manufacturer="{config['product']['manufacturer']}" UpgradeCode="{config['product']['upgrade_code']}">
    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine" />
    <Media Id="1" Cabinet="product.cab" EmbedCab="yes" />
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="{config['product']['name']}" />
      </Directory>
    </Directory>
    <Feature Id="MainFeature" Title="Main Feature" Level="1">
      {" ".join([f'<ComponentRef Id="{file["component_id"]}" />' for file in config['files']])}
    </Feature>
    <CustomActionRef Id="PreInstallAction" />
    <CustomActionRef Id="PostInstallAction" />
    <InstallExecuteSequence>
      <Custom Action="PreInstallAction" Before="InstallInitialize">NOT Installed</Custom>
      <Custom Action="PostInstallAction" After="InstallFinalize">Installed</Custom>
    </InstallExecuteSequence>
  </Product>
</Wix>
    """
    (src_dir / "Product.wxs").write_text(product_wxs_content.strip())

    # Generate DirectoryStructure.wxs
    directory_wxs_content = f"""
<Fragment>
  <DirectoryRef Id="INSTALLFOLDER">
    {" ".join([f'<Component Id="{file["component_id"]}" Guid="*"><File Id="{file["component_id"]}" Source="{file["source"]}" KeyPath="yes" /></Component>' for file in config['files']])}
  </DirectoryRef>
</Fragment>
    """
    (src_dir / "DirectoryStructure.wxs").write_text(directory_wxs_content.strip())

    # Generate CustomActions.wxs
    custom_actions_wxs_content = f"""
<Fragment>
  <CustomAction Id="PreInstallAction" FileKey="PreInstallScript" ExeCommand="" Return="ignore" />
  <CustomAction Id="PostInstallAction" FileKey="PostInstallScript" ExeCommand="" Return="ignore" />
  <Component Id="CustomActionsComponent" Guid="*">
    <File Id="PreInstallScript" Source="{config['actions']['preinstall']}" KeyPath="yes" />
    <File Id="PostInstallScript" Source="{config['actions']['postinstall']}" KeyPath="yes" />
  </Component>
</Fragment>
    """
    (src_dir / "CustomActions.wxs").write_text(custom_actions_wxs_content.strip())

    # Generate Components.wxs
    components_wxs_content = f"""
<Fragment>
  <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
    {" ".join([f'<ComponentRef Id="{file["component_id"]}" />' for file in config['files']])}
    <ComponentRef Id="CustomActionsComponent" />
  </ComponentGroup>
</Fragment>
    """
    (src_dir / "Components.wxs").write_text(components_wxs_content.strip())

# Function to compile and link WiX files into an MSI
def build_msi(project_dir, wix_path, output_dir, quiet):
    src_dir = Path(project_dir) / "src"
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    wixobj_files = []
    for wxs_file in src_dir.glob("*.wxs"):
        wixobj_file = output_dir / f"{wxs_file.stem}.wixobj"
        wixobj_files.append(str(wixobj_file))
        run_command(f'"{wix_path}\\candle.exe" -out {wixobj_file} {wxs_file}', quiet)
    
    msi_file = output_dir / "MyInstaller.msi"
    run_command(f'"{wix_path}\\light.exe" -out {msi_file} {" ".join(wixobj_files)}', quiet)

# Function to create a new project directory
def create_project_directory(project_dir):
    project_path = Path(project_dir)
    if project_path.exists():
        print(f"Error: Directory {project_dir} already exists.")
        return False
    project_path.mkdir()
    (project_path / "payload").mkdir()
    (project_path / "scripts").mkdir()
    default_build_info = {
        "product": {
            "name": "MyApp",
            "version": "1.0.0",
            "manufacturer": "MyCompany",
            "upgrade_code": "YOUR-GUID-HERE"
        },
        "files": [],
        "actions": {
            "preinstall": "scripts/preinstall.bat",
            "postinstall": "scripts/postinstall.bat"
        }
    }
    with open(project_path / BUILD_INFO_FILE, 'w') as file:
        yaml.dump(default_build_info, file, default_flow_style=False)
    print(f"Created new project directory at {project_dir}")
    return True

# Main function with command-line arguments
def main():
    parser = argparse.ArgumentParser(description="gorilla-pkg: A tool for building MSI packages on Windows")
    parser.add_argument('project_dir', help="The project directory to build or operate on.")
    parser.add_argument('--create', action='store_true', help="Create a new project directory with default settings.")
    parser.add_argument('--import_msi', metavar='MSI_FILE', help="Import an existing MSI package as a project.")
    parser.add_argument('--output', metavar='DIRECTORY', help="Specify a different output directory for the built MSI package.", default='output')
    parser.add_argument('--quiet', action='store_true', help="Suppress output messages except for errors.")
    parser.add_argument('--wix-path', metavar='WIX_DIRECTORY', help="Specify the path to the WiX Toolset installation.", default=DEFAULT_WIX_BIN_PATH)
    
    args = parser.parse_args()

    if args.create:
        if not create_project_directory(args.project_dir):
            sys.exit(1)
    elif args.import_msi:
        print("Importing existing MSI is not implemented yet.", file=sys.stderr)
        sys.exit(1)
    else:
        # Check if WiX Toolset is installed
        check_wix_toolset(args.wix_path)

        # Read build-info.yaml
        config = read_build_info(args.project_dir)

        # Populate 'files[]' with the contents of the 'payload' folder
        populate_files_section(args.project_dir, config)

        # Generate WiX source files
        generate_wix_files(args.project_dir, config)

        # Build the MSI package
        build_msi(args.project_dir, args.wix_path, args.output, args.quiet)

        print("MSI package created successfully.")

if __name__ == '__main__':
    main()
