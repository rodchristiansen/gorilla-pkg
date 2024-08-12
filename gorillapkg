#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import yaml
import argparse
import uuid
import shutil
import shlex
from pathlib import Path

# Define constants
BUILD_INFO_FILE = "build-info.yaml"
DEFAULT_WIX_BIN_PATH = r"C:\Program Files\WiX Toolset v5.0\bin"

# Enhanced logging function for debugging
def log(message, error=False):
    if error:
        print(f"ERROR: {message}", file=sys.stderr)
    else:
        print(f"DEBUG: {message}")

# Function to check if WiX Toolset is installed
def check_wix_toolset(wix_path):
    wix_exe_path = Path(wix_path) / "wix.exe"
    log(f"Checking for WiX Toolset at {wix_exe_path}")
    
    if not wix_exe_path.exists():
        log("WiX Toolset is not installed or not found in the expected location.", error=True)
        sys.exit(1)

# Function to read YAML configuration
def read_build_info(project_dir):
    build_info_path = Path(project_dir) / BUILD_INFO_FILE
    log(f"Reading build info from {build_info_path}")
    with open(build_info_path, 'r') as file:
        return yaml.safe_load(file)

def clean_src_folder(src_dir):
    if src_dir.exists():
        try:
            shutil.rmtree(src_dir)
            log(f"Cleaned up existing src directory: {src_dir}")
        except Exception as e:
            log(f"Failed to clean up src directory: {str(e)}", error=True)
            sys.exit(1)
    src_dir.mkdir(exist_ok=True)  # Recreate the src directory after cleanup

# Function to dynamically populate files section based on payload directory contents
def get_files_from_payload(project_dir):
    payload_dir = Path(project_dir) / "payload"
    log(f"Getting files from payload directory {payload_dir}")
    files_list = []
    
    if not payload_dir.exists():
        log(f"Warning: Payload directory {payload_dir} does not exist. Building a payload-free package.", error=True)

    for file_path in payload_dir.rglob('*'):
        if file_path.is_file():
            file_entry = {
                "source": str(file_path).replace("\\", "/"),
                "destination": f"[INSTALLFOLDER]{file_path.relative_to(payload_dir)}",
                "component_id": f"Component_{file_path.stem}"
            }
            files_list.append(file_entry)
            log(f"Added file: {file_entry['source']} to installation package")
    
    return files_list

# Function to dynamically detect and include preinstall and postinstall scripts
def get_scripts(project_dir):
    scripts_dir = Path(project_dir) / "scripts"
    actions = {}
    log(f"Checking for scripts in {scripts_dir}")

    for script_type in ['preinstall', 'postinstall']:
        for ext in ['.bat', '.ps1']:
            script_path = scripts_dir / f"{script_type}{ext}"
            if script_path.exists():
                actions[script_type] = str(script_path)
                log(f"Found {script_type} script: {script_path}")

    return actions

# Function to generate UpgradeCodes
def generate_guids(identifier):
    # Generate a consistent UpgradeCode using the identifier
    upgrade_code = uuid.uuid5(uuid.NAMESPACE_DNS, identifier)
    
    # Generate a new ProductCode for each version (can be changed per run)
    product_code = uuid.uuid4()
    
    return str(product_code), str(upgrade_code)
    
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
            "identifier": "com.domain.winadmins.package_name"
        },
        "install_path": "C:\\Program Files\\MyApp",
        "postinstall_action": "none"
    }
    with open(project_path / BUILD_INFO_FILE, 'w') as file:
        yaml.dump(default_build_info, file, default_flow_style=False)
    print(f"Created new project directory at {project_dir}")
    return True

# Function to parse version number in build-info.yaml
def parse_version(version_str):
    """
    Parses a version string and converts it to a Windows Installer compatible version.
    If the version is date-based (e.g., '2024.08.09'), it converts it to 'YY.MM.DD'.
    If the version is semantic (e.g., '1.2.3'), it is returned as is.
    """
    try:
        parts = version_str.split('.')
        if len(parts) == 3 and len(parts[0]) == 4:  # Date-based version
            major = int(parts[0][-2:])  # Last two digits of the year
            minor = int(parts[1]) % 256
            build = int(parts[2]) % 65536
            return f"{major}.{minor}.{build}"
        elif len(parts) == 3:  # Semantic version
            major = int(parts[0]) % 256
            minor = int(parts[1]) % 256
            build = int(parts[2]) % 65536
            return f"{major}.{minor}.{build}"
        else:
            log(f"Invalid version format '{version_str}'. Expected format: 'YYYY.MM.DD' or 'X.Y.Z'.", error=True)
            sys.exit(1)
    except ValueError:
        log(f"Invalid version format '{version_str}'. Expected format: 'YYYY.MM.DD' or 'X.Y.Z'.", error=True)
        sys.exit(1)

def generate_wix_files(project_dir, config):
    log("Generating WiX source files...")
    src_dir = Path(project_dir) / "src"
    
    # Clean up the src directory before generating new files
    clean_src_folder(src_dir)
    
    files = get_files_from_payload(project_dir)
    actions = get_scripts(project_dir)
    postinstall_action = config.get("postinstall_action", "none")
    
    namespace = "http://wixtoolset.org/schemas/v4/wxs"
    
    # Generate ProductCode and UpgradeCode based on the identifier
    product_code, upgrade_code = generate_guids(config['product']['identifier'])
    
    # Parse the version using the new function
    parsed_version = parse_version(config['product']['version'])
    
    # Ensure we have components to reference
    if not files:
        log("No files found in the payload. Aborting generation.", error=True)
        return
    
    # Generate Package.wxs content for WiX v5, defaulting to x64
    package_wxs_content = f"""
<Wix xmlns="{namespace}">
    <Package Name="{config['product']['name']}" Language="1033" Version="{parsed_version}" Manufacturer="{config['product']['manufacturer']}" UpgradeCode="{upgrade_code}" InstallerVersion="500">
        <Media Id="1" Cabinet="product.cab" EmbedCab="yes" />
        <StandardDirectory Id="ProgramFiles64Folder">
            <Directory Id="INSTALLFOLDER" Name="{config['install_path'].split(os.sep)[-1]}">
                {"".join([f'<Component Id="{file["component_id"]}" Guid="*"><File Id="{file["component_id"]}" Source="{file["source"]}" KeyPath="yes" /></Component>' for file in files])}
            </Directory>
        </StandardDirectory>
        <Feature Id="MainFeature" Title="Main Feature" Level="1">
            {"".join([f'<ComponentRef Id="{file["component_id"]}" />' for file in files])}
        </Feature>
        {generate_install_execute_sequence(actions, postinstall_action)}
    </Package>
</Wix>
    """
    (src_dir / "Package.wxs").write_text(package_wxs_content.strip())
    log("WiX source files generated successfully.")

def generate_install_execute_sequence(actions, postinstall_action):
    sequence_parts = []
    if 'preinstall' in actions:
        sequence_parts.append('<Custom Action="PreInstallAction" Before="InstallInitialize">NOT Installed</Custom>')
    if 'postinstall' in actions:
        sequence_parts.append('<Custom Action="PostInstallAction" After="InstallFinalize">Installed</Custom>')
    if postinstall_action == 'logout':
        sequence_parts.append('<Custom Action="ForceLogout" After="InstallFinalize">Installed</Custom>')
    if postinstall_action == 'restart':
        sequence_parts.append('<Custom Action="ForceRestart" After="InstallFinalize">Installed</Custom>')
    
    return "\n      ".join(sequence_parts)

def generate_custom_actions_wxs(actions, postinstall_action, namespace):
    custom_actions = ""
    if 'preinstall' in actions:
        custom_actions += f'<CustomAction Id="PreInstallAction" FileKey="PreInstallScript" ExeCommand="" Return="ignore" />'
    if 'postinstall' in actions:
        custom_actions += f'<CustomAction Id="PostInstallAction" FileKey="PostInstallScript" ExeCommand="" Return="ignore" />'
    if postinstall_action == 'logout':
        custom_actions += '<CustomAction Id="ForceLogout" ExeCommand="shutdown.exe /l /f" Return="ignore" Directory="SystemFolder" />'
    if postinstall_action == 'restart':
        custom_actions += '<CustomAction Id="ForceRestart" ExeCommand="shutdown.exe /r /f /t 00" Return="ignore" Directory="SystemFolder" />'
    return f"""
<Wix xmlns="{namespace}">
    <Fragment>
        <Component Id="CustomActionsComponent" Guid="*">
            {custom_actions}
            <File Id="PreInstallScript" Source="{actions.get('preinstall', '')}" KeyPath="yes" />
            <File Id="PostInstallScript" Source="{actions.get('postinstall', '')}" KeyPath="yes" />
        </Component>
    </Fragment>
</Wix>
    """
        
# Function to run a subprocess and check for errors
def run_command(command, quiet=False, verbose=False):
    if verbose:
        command += " -v"
    log(f"Executing command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Command failed with return code {result.returncode}: {result.stderr}", error=True)
        if not quiet:
            log(f"Output: {result.stdout}", error=True)
        return False, result.stderr
    if not quiet:
        log(result.stdout)
    return True, result.stdout

def verify_wxs_files(project_dir):
    src_dir = Path(project_dir) / "src"
    package_wxs_path = src_dir / "Package.wxs"
    
    try:
        with open(package_wxs_path, 'r') as file:
            content = file.read()

        # Regex patterns to find tags, accounting for possible newlines and spaces
        patterns = {
            "Package": r"<Package[^>]*>",
            "Directory": r"<Directory[^>]*>",
            "Component": r"<Component[^>]*>",
            "ComponentRef": r"<ComponentRef[^>]*>"
        }

        missing_tags = [tag for tag, pattern in patterns.items() if not re.search(pattern, content)]
        if missing_tags:
            log(f"Package.wxs is missing necessary tags: {missing_tags}", error=True)
            return False

    except Exception as e:
        log(f"Error reading {package_wxs_path}: {str(e)}", error=True)
        return False

    log("WXS files verification passed.")
    return True
    
# Function to run SignTool if 'identity' key is present
def sign_msi(msi_file, identity):
    log(f"Signing MSI package {msi_file} with identity {identity}")
    sign_command = f'signtool sign /n "{identity}" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "{msi_file}"'
    success, output = run_command(shlex.quote(sign_command))
    if not success:
        log("Failed to sign MSI package.", error=True)
        return False
    log("MSI package signed successfully.")
    return True

# Update the build_msi function to include signing
def build_msi(project_dir, wix_path, output_dir=None):
    src_dir = Path(project_dir) / "src"
    
    # Use 'build' folder as default output directory unless specified
    if output_dir is None:
        output_dir = Path(project_dir) / "build"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    wix_exe = Path(wix_path) / "wix.exe"
    package_wix_file = src_dir / "Package.wxs"
    msi_file_name = f"{read_build_info(project_dir)['product']['name']}.msi"
    msi_file = output_dir / msi_file_name
    
    # Command to use Package.wxs for building MSI with default x64 architecture
    command = f'"{wix_exe}" build -dBUILDARCH=x64 -out "{msi_file}" "{package_wix_file}"'
    success, output = run_command(command)
    if not success:
        log("Failed to create MSI package.", error=True)
        return
    
    log(f"MSI package created successfully at {msi_file}.")
    
    # Check if 'identity' key is present in build-info.yaml for signing
    config = read_build_info(project_dir)
    if 'identity' in config:
        if not sign_msi(msi_file, config['identity']):
            log("MSI signing process failed.", error=True)
            return
    
    # Clean up the src directory and Package.wxs file after the build
    log(f"Cleaning up the src directory: {src_dir}")
    try:
        shutil.rmtree(src_dir)
        log("src directory and Package.wxs file have been removed.")
    except Exception as e:
        log(f"Failed to clean up src directory: {str(e)}", error=True)

    # Clean up the .wixpdb file
    wixpdb_file = output_dir / f"{msi_file_name.replace('.msi', '')}.wixpdb"
    if wixpdb_file.exists():
        try:
            wixpdb_file.unlink()
            log(f"{wixpdb_file} file has been removed.")
        except Exception as e:
            log(f"Failed to remove {wixpdb_file}: {str(e)}", error=True)

# Main function with command-line arguments
def main():
    parser = argparse.ArgumentParser(description="gorilla-pkg: A tool for building MSI packages on Windows")
    parser.add_argument('project_dir', help="The project directory to build or operate on.")
    parser.add_argument('--create', action='store_true', help="Create a new project directory with default settings.")
    parser.add_argument('--output', metavar='DIRECTORY', help="Specify a different output directory for the built MSI package.")
    parser.add_argument('--wix-path', metavar='WIX_DIRECTORY', help="Specify the path to the WiX Toolset installation.", default=DEFAULT_WIX_BIN_PATH)
    
    args = parser.parse_args()

    if args.create:
        if not create_project_directory(args.project_dir):
            log("Failed to create a new project directory.", error=True)
            sys.exit(1)
        log(f"Project directory created at {args.project_dir}")
    else:
        # Check if WiX Toolset is installed
        check_wix_toolset(args.wix_path)

        # Read build-info.yaml
        config = read_build_info(args.project_dir)

        # Generate WiX source files based on payload and scripts
        generate_wix_files(args.project_dir, config)

        # Verify the generated WiX source files before building the MSI
        if not verify_wxs_files(args.project_dir):
            log("Verification of WiX source files failed, aborting MSI creation.", error=True)
            sys.exit(1)

        # Build the MSI package with an optional output directory
        build_msi(args.project_dir, args.wix_path, args.output)
        log("MSI package creation process completed.")

if __name__ == '__main__':
    main()
