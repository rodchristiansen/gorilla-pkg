#!/usr/bin/env python3
import os
import subprocess
import sys
import yaml
import base64
import argparse
import uuid
import shutil
from lxml import etree
from pathlib import Path

# Define constants
BUILD_INFO_FILE = "build-info.yaml"
DEFAULT_WIX_BIN_PATH = r"C:\Program Files\WiX Toolset v5.0\bin"

import logging

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

def log(message, level=logging.INFO, error=False):
    if error:
        logging.error(message)
    else:
        logging.log(level, message)

def check_wix_toolset(wix_path):
    wix_exe_path = Path(wix_path) / "wix.exe"
    log(f"Checking for WiX Toolset at {wix_exe_path}")
    
    if not wix_exe_path.exists():
        log("WiX Toolset is not installed or not found in the expected location.", error=True)
        sys.exit(1)

def read_build_info(project_dir):
    build_info_path = Path(project_dir) / BUILD_INFO_FILE
    log(f"Reading build info from {build_info_path}")
    with open(build_info_path, 'r') as file:
        return yaml.safe_load(file)

def generate_guids(identifier):
    upgrade_code = uuid.uuid5(uuid.NAMESPACE_DNS, identifier)
    product_code = uuid.uuid4()
    return str(product_code), str(upgrade_code)

def create_project_directory(project_dir):
    project_path = Path(project_dir)
    if project_path.exists():
        print(f"Error: Directory {project_dir} already exists.")
        return False

    os.makedirs(project_path / "payload", exist_ok=True)
    os.makedirs(project_path / "scripts", exist_ok=True)
    
    default_build_info = {
        "product": {
            "name": "PkgName",
            "version": "1.0.0",
            "manufacturer": "MyCompany",
            "identifier": "com.domain.winadmins.package_name"
        },
        "install_path": "C:\\Program Files\\PkgName",
        "postinstall_action": "none"
    }
    with open(project_path / BUILD_INFO_FILE, 'w') as file:
        yaml.dump(default_build_info, file, default_flow_style=False)
    print(f"Created new project directory at {project_dir}")
    return True

def parse_version(version_str):
    try:
        parts = version_str.split('.')
        if len(parts) == 3 and len(parts[0]) == 4:  # Date-based version
            major = int(parts[0][-2:])  # Last two digits of the year
            minor = int(parts[1]) % 256
            build = int(parts[2]) % 65536
        elif len(parts) in [3, 4]:  # Semantic version or version with build number
            major = int(parts[0]) % 256
            minor = int(parts[1]) % 256
            build = int(parts[2]) % 65536
            if len(parts) == 4:
                build = (build * 1000 + int(parts[3])) % 65536
        else:
            raise ValueError(f"Invalid version format: {version_str}")
        
        return f"{major}.{minor}.{build}"
    except ValueError as e:
        log(f"Error parsing version: {e}", error=True)
        log(f"Expected format: 'YYYY.MM.DD', 'X.Y.Z', or 'X.Y.Z.B'", error=True)
        sys.exit(1)

def get_standard_directories():
    username = os.getlogin()
    return {
        "C:\\Program Files": "ProgramFilesFolder",
        "C:\\Program Files (x86)": "ProgramFiles6432Folder",
        "C:\\Program Files\\Common Files": "CommonFilesFolder",
        "C:\\Program Files\\Common Files (x86)": "CommonFiles6432Folder",
        "C:\\ProgramData": "CommonAppDataFolder",
        "C:\\Windows": "WindowsFolder",
        "C:\\Windows\\System32": "SystemFolder",
        "C:\\Windows\\SysWOW64": "System64Folder",
        "C:\\Windows\\Fonts": "FontsFolder",
        f"C:\\Users\\{username}\\AppData\\Local": "LocalAppDataFolder",
        f"C:\\Users\\{username}\\AppData\\Roaming": "AppDataFolder",
        f"C:\\Users\\{username}\\Desktop": "DesktopFolder",
        f"C:\\Users\\{username}\\Documents": "PersonalFolder",
        f"C:\\Users\\{username}\\Favorites": "FavoritesFolder",
        f"C:\\Users\\{username}\\My Pictures": "MyPicturesFolder",
        f"C:\\Users\\{username}\\NetHood": "NetHoodFolder",
        f"C:\\Users\\{username}\\PrintHood": "PrintHoodFolder",
        f"C:\\Users\\{username}\\Recent": "RecentFolder",
        f"C:\\Users\\{username}\\SendTo": "SendToFolder",
        f"C:\\Users\\{username}\\Start Menu": "StartMenuFolder",
        f"C:\\Users\\{username}\\Startup": "StartupFolder",
        "C:\\Windows\\System": "System16Folder",
        "C:\\Windows\\Temp": "TempFolder",
        "C:\\Windows\\System32\\config\\systemprofile\\AppData\\Local": "LocalAppDataFolder",
    }

def create_directory_structure(parent, path):
    current_dir = parent
    for part in Path(path).parts:
        dir_id, dir_name = generate_directory_id_name(part)
        current_dir = etree.SubElement(current_dir, "Directory", Id=dir_id, Name=dir_name)
    return current_dir

def generate_directory_id_name(part):
    sanitized_part = part.replace(' ', '_').replace(':', '').replace('\\', '').replace('/', '')
    dir_id = f"dir_{sanitized_part}"
    dir_name = part.replace(":", "").replace("\\", "").replace("/", "")
    
    if not dir_name:
        dir_name = "ROOT"
        
    return dir_id, dir_name

def find_standard_directory(install_path, standard_directories):
    normalized_install_path = os.path.normpath(install_path).lower()
    
    sorted_directories = sorted(standard_directories.items(), key=lambda x: -len(x[0]))
    
    for standard_path, directory_id in sorted_directories:
        normalized_standard_path = os.path.normpath(standard_path).lower()
        if normalized_install_path == normalized_standard_path:
            return directory_id, ""
        elif normalized_install_path.startswith(normalized_standard_path):
            remaining_path = normalized_install_path[len(normalized_standard_path):].lstrip(os.sep)
            return directory_id, remaining_path

    return None, install_path

import platform

def get_arch_short():
    """Determine the architecture suffix for Wix4UtilCA."""
    arch = platform.machine().lower()
    if arch in ['x86_64', 'amd64']:
        return 'x64'
    elif arch in ['x86', 'i386', 'i686']:
        return 'x86'
    elif 'arm' in arch:
        return 'arm64'
    else:
        raise ValueError(f"Unsupported architecture: {arch}")

def add_custom_actions(package, project_dir):
    scripts_dir = Path(project_dir) / "scripts"
    if scripts_dir.exists():
        # Ensure the InstallExecuteSequence element is present
        install_execute_sequence = package.find("./InstallExecuteSequence")
        if install_execute_sequence is None:
            install_execute_sequence = etree.SubElement(package, "InstallExecuteSequence")

        script_count = 0  # Counter for the number of scripts processed

        # Namespace for util elements
        NS_UTIL = "http://wixtoolset.org/schemas/v4/wxs/util"

        # Determine the architecture-specific suffix for Wix4UtilCA
        arch_suffix = get_arch_short()

        for script_file in scripts_dir.iterdir():
            if script_file.suffix.lower() == '.js':
                script_name = script_file.stem.lower()

                if "preinstall" in script_name:
                    action_id = f"PreInstall_{uuid.uuid4().hex}"
                    sequence_ref = "InstallInitialize"
                    sequence_position = "After"
                elif "postinstall" in script_name:
                    action_id = f"PostInstall_{uuid.uuid4().hex}"
                    sequence_ref = "InstallFinalize"
                    sequence_position = "Before"
                else:
                    continue

                # Command line to execute the .js script using cscript.exe
                cmd_value = f'"[SystemFolder]cscript.exe" //NoLogo "[#File_{script_file.name}]"'

                # Create a SetProperty element to set the command line for WixQuietExec
                set_property = etree.SubElement(
                    package,
                    "SetProperty",
                    Id=action_id,
                    Value=cmd_value,
                    Before=action_id,
                    Sequence="execute"
                )

                # Create the CustomAction element referencing WixQuietExec
                custom_action = etree.SubElement(
                    package,
                    "CustomAction",
                    Id=action_id,
                    BinaryRef=f"Wix4UtilCA_{arch_suffix}",
                    DllEntry="WixQuietExec",
                    Execute="deferred",
                    Impersonate="no",
                    Return="check"
                )

                # Schedule the custom action in the InstallExecuteSequence
                custom_element = etree.SubElement(
                    install_execute_sequence,
                    "Custom",
                    Action=action_id,
                    **{sequence_position: sequence_ref},
                    Condition="NOT Installed"
                )

                script_count += 1  # Increment the script counter
            else:
                log(f"File {script_file.name} is not a supported script type. Skipping.")

        if script_count > 0:
            log(f"Added custom actions for {script_count} scripts using WixQuietExec")
        else:
            log("No valid scripts found in the scripts directory.")
    else:
        log("No scripts directory found. Skipping custom actions.")

import os

def find_wix_util_dll():
    """Locate the WixToolset.Util.wixext DLL for the appropriate architecture."""
    arch_suffix = get_arch_short()  # Get architecture suffix (x64, x86, arm64)
    
    possible_base_paths = [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Common Files", "WixToolset", "extensions"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Common Files", "WixToolset", "extensions"),
    ]
    
    for base_path in possible_base_paths:
        extension_path = os.path.join(base_path, "WixToolset.Util.wixext", "5.0.2", "wixext5", "WixToolset.Util.wixext.dll")
        if os.path.isfile(extension_path):
            return extension_path
    
    log("Could not find WixToolset.Util.wixext.dll. Ensure the file is installed correctly.", error=True)
    sys.exit(1)

def add_binary_reference(package):
    """Add the Binary reference for the appropriate architecture."""
    arch_suffix = get_arch_short()  # Get architecture suffix (x64, x86, arm64)
    binary_id = f"Wix4UtilCA_{arch_suffix}"
    
    # Find the path to the DLL
    source_file_path = find_wix_util_dll()

    # Create the Binary element
    etree.SubElement(
        package,
        "Binary",
        Id=binary_id,
        SourceFile=source_file_path
    )

def generate_wix_files(project_dir, config):
    NS_WIX = "http://wixtoolset.org/schemas/v4/wxs"
    NS_UTIL = "http://wixtoolset.org/schemas/v4/wxs/util"

    nsmap = {None: NS_WIX, 'util': NS_UTIL}

    install_path = config['install_path'].replace("[username]", os.getlogin())
    standard_directories = get_standard_directories()
    directory_id, remaining_path = find_standard_directory(install_path, standard_directories)

    wix = etree.Element("Wix", nsmap=nsmap)
    package = etree.SubElement(wix, "Package",
                               Name=config['product']['name'],
                               Version=parse_version(config['product']['version']),
                               Manufacturer=config['product']['manufacturer'],
                               UpgradeCode=generate_guids(config['product']['identifier'])[1],
                               InstallerVersion="500",
                               Compressed="yes")

    # Ensure the InstallExecuteSequence element is present
    if package.find("./InstallExecuteSequence") is None:
        etree.SubElement(package, "InstallExecuteSequence")

    # Add MajorUpgrade element
    etree.SubElement(package, "MajorUpgrade",
                     DowngradeErrorMessage="A newer version of [ProductName] is already installed.")

    # Add Media element
    etree.SubElement(package, "Media", Id="1", Cabinet="product.cab", EmbedCab="yes")

    # Use INSTALLFOLDER as the main installation directory
    if directory_id:
        install_folder = etree.SubElement(package, "StandardDirectory", Id=directory_id)
        current_dir = create_directory_structure(install_folder, remaining_path)
    else:
        install_folder = etree.SubElement(package, "StandardDirectory", Id="INSTALLFOLDER")
        current_dir = create_directory_structure(install_folder, install_path)

    # Always create a Feature element
    feature = etree.SubElement(package, "Feature", Id="MainFeature", Title="Main Feature", Level="1")

    # Adding payload handling
    add_payload_files(current_dir, project_dir, feature)

    # Add custom actions and binary reference
    add_custom_actions(package, project_dir)
    add_binary_reference(package)

    return wix

def add_payload_files(current_dir, project_dir, feature):
    payload_dir = Path(project_dir) / "payload"
    scripts_dir = Path(project_dir) / "scripts"
    all_files_dir = [payload_dir, scripts_dir]

    for directory in all_files_dir:
        if directory.exists():
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(directory)
                    dir_element = get_or_create_directory(current_dir, relative_path.parent)

                    component_id = f"Component_{uuid.uuid4().hex}"
                    component = etree.SubElement(dir_element, "Component", Id=component_id, Guid=str(uuid.uuid4()))
                    file_id = f"File_{file_path.name}"
                    etree.SubElement(component, "File", Id=file_id, Source=str(file_path), KeyPath="yes")

                    etree.SubElement(feature, "ComponentRef", Id=component_id)

def get_or_create_directory(parent, path):
    current = parent
    for part in path.parts:
        dir_id, dir_name = generate_directory_id_name(part)
        existing = current.find(f"./Directory[@Id='{dir_id}']")
        if existing is None:
            current = etree.SubElement(current, "Directory", Id=dir_id, Name=dir_name)
        else:
            current = existing
    return current

def print_wxs_content(package_wxs_path):
    log("Contents of the generated WXS file:")
    with open(package_wxs_path, 'r') as file:
        log(file.read())

def run_command(command, quiet=False, verbose=False):
    try:
        if verbose:
            command += " -v"
        log(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        result.check_returncode()
        if not quiet:
            log(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        log(f"Command failed with return code {e.returncode}. Error output: {e.stderr}", error=True)
        if not quiet:
            log(f"Standard Output: {e.stdout}", error=True)
            log(f"Standard Error: {e.stderr}", error=True)
        return False, e.stderr
    except Exception as e:
        log(f"An unexpected error occurred: {str(e)}", error=True)
        return False, str(e)

def verify_wxs_files(project_dir, has_scripts):
    src_dir = Path(project_dir) / "src"
    package_wxs_path = src_dir / "Package.wxs"
    
    try:
        with open(package_wxs_path, 'rb') as file:
            content = file.read()

        tree = etree.fromstring(content)
        NS_WIX = "http://wixtoolset.org/schemas/v4/wxs"
        
        required_tags = [
            f"{{{NS_WIX}}}Package",
            f"{{{NS_WIX}}}Directory",
            f"{{{NS_WIX}}}Component",
            f"{{{NS_WIX}}}ComponentRef",
        ]

        if has_scripts:
            required_tags += [
                f"{{{NS_WIX}}}CustomAction",
                f"{{{NS_WIX}}}InstallExecuteSequence"
            ]

        missing_tags = []
        for tag in required_tags:
            if not tree.findall(f".//{tag}"):
                missing_tags.append(tag)

        if missing_tags:
            log(f"Package.wxs is missing necessary tags: {missing_tags}", error=True)
            return False

    except Exception as e:
        log(f"Error reading or parsing {package_wxs_path}: {str(e)}", error=True)
        return False

    log("WXS files verification passed.")
    return True

def sign_msi(msi_file, identity):
    log(f"Signing MSI package {msi_file} with identity {identity}")
    sign_command = f'signtool sign /n "{identity}" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "{msi_file}"'
    success, output = run_command(sign_command)
    if not success:
        log("Failed to sign MSI package.", error=True)
        return False
    log("MSI package signed successfully.")
    return True

def find_wix_extension_package(extension_name):
    possible_base_paths = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WiX Toolset v5.0" / "extensions",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "WiX Toolset v5.0" / "extensions",
    ]

    for base_path in possible_base_paths:
        if not base_path.exists():
            continue
        extension_path = base_path / extension_name
        if extension_path.exists():
            return str(extension_path)
    return None

def find_wix_extension_dll(extension_name):
    import glob
    from pathlib import Path

    possible_base_paths = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Common Files" / "WixToolset" / "extensions",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Common Files" / "WixToolset" / "extensions"
    ]

    extension_dlls = []

    for base_path in possible_base_paths:
        if not base_path.exists():
            continue
        # Construct the search pattern for the extension DLL
        search_pattern = f"{extension_name}/*/*/{extension_name}.dll"
        found_dlls = list(base_path.glob(search_pattern))
        extension_dlls.extend(found_dlls)

    if not extension_dlls:
        log(f"Extension DLL for {extension_name} not found in known locations.", error=True)
        return None

    # Sort the list to pick the latest version
    extension_dlls.sort()
    latest_extension_dll = extension_dlls[-1]
    log(f"Found extension DLL for {extension_name} at {latest_extension_dll}")
    return str(latest_extension_dll)

def is_wix_extension_installed(wix_path, extension_name):
    command = f'"{wix_path}\\wix.exe" extension list'
    success, output = run_command(command, quiet=True)
    if not success:
        log("Failed to list WiX extensions.", error=True)
        return False
    return extension_name in output

def add_wix_extension(wix_path, extension_name):
    # Attempt to add the extension by name
    command = f'"{wix_path}\\wix.exe" extension add {extension_name}'
    success, output = run_command(command)
    if success:
        log(f"WiX extension {extension_name} added successfully by name.")
        return True

    # If adding by name fails, try adding by path
    extension_path = find_wix_extension_package(extension_name)
    if extension_path:
        command = f'"{wix_path}\\wix.exe" extension add "{extension_path}"'
        success, output = run_command(command)
        if success:
            log(f"WiX extension {extension_name} added successfully from path.")
            return True
        else:
            log(f"Failed to add WiX extension {extension_name} from path.", error=True)
            return False
    else:
        log(f"Could not find the extension package for {extension_name}.", error=True)
        return False


def build_msi(project_dir, wix_path, output_dir=None):
    src_dir = Path(project_dir) / "src"

    if output_dir is None:
        output_dir = Path(project_dir) / "build"
    else:
        output_dir = Path(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    wix_exe = Path(wix_path) / "wix.exe"
    package_wix_file = src_dir / "Package.wxs"
    msi_file_name = f"{read_build_info(project_dir)['product']['name']}.msi"
    msi_file = output_dir / msi_file_name

    extension_name = "WixToolset.Util.wixext"

    # Check if the extension is installed
    if not is_wix_extension_installed(wix_path, extension_name):
        log(f"WiX extension {extension_name} is not installed. Attempting to add it.")
        if not add_wix_extension(wix_path, extension_name):
            log(f"Failed to add WiX extension {extension_name}.", error=True)
            return None

    # Use the extension by name in the build command
    command = f'"{wix_exe}" build -ext {extension_name} -out "{msi_file}" "{package_wix_file}"'
    success, output = run_command(command)
    if not success:
        log("Failed to create MSI package.", error=True)
        return None

    log(f"MSI package created successfully at {msi_file}.")
    
    config = read_build_info(project_dir)
    if 'identity' in config:
        if not sign_msi(msi_file, config['identity']):
            log("MSI signing process failed.", error=True)
            return None

    try:
        log(f"Cleaning up the src directory: {src_dir}")
        shutil.rmtree(src_dir)
        log("src directory and Package.wxs file have been removed.")
    except Exception as e:
        log(f"Failed to clean up src directory: {str(e)}", error=True)

    wixpdb_file = output_dir / f"{msi_file_name.replace('.msi', '')}.wixpdb"
    if wixpdb_file.exists():
        try:
            wixpdb_file.unlink()
            log(f"{wixpdb_file} file has been removed.")
        except Exception as e:
            log(f"Failed to remove {wixpdb_file}: {str(e)}", error=True)

    return msi_file

def generate_and_save_wix_files(project_dir, config):
    wix_element = generate_wix_files(project_dir, config)
    
    src_dir = Path(project_dir) / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    package_wxs_path = src_dir / "Package.wxs"
    
    xml_str = etree.tostring(wix_element, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    with open(package_wxs_path, 'wb') as file:
        file.write(xml_str)
    
    log(f"Generated and saved WXS file to {package_wxs_path}")
    return package_wxs_path

def main():
    parser = argparse.ArgumentParser(description="gorilla-pkg: A tool for building MSI packages on Windows")
    parser.add_argument('project_dir', nargs='?', help="The project directory to build or operate on.")
    parser.add_argument('--create', action='store_true', help="Create a new project directory with default settings.")
    parser.add_argument('--output', metavar='DIRECTORY', help="Specify a different output directory for the built MSI package.")
    parser.add_argument('--wix-path', metavar='WIX_DIRECTORY', help="Specify the path to the WiX Toolset installation.", default=DEFAULT_WIX_BIN_PATH)
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging.")
    parser.add_argument('--no-sign', action='store_true', help="Skip MSI signing even if identity is provided.")
    parser.add_argument('--force', '-f', action='store_true', help="Force overwrite of existing files.")
    
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.create:
        if not create_project_directory(args.project_dir):
            log("Failed to create a new project directory.", error=True)
            sys.exit(1)
        log(f"Project directory created at {args.project_dir}")
    else:
        try:
            check_wix_toolset(args.wix_path)

            config = read_build_info(args.project_dir)

            package_wxs_path = generate_and_save_wix_files(args.project_dir, config)
            print_wxs_content(package_wxs_path)

            scripts_dir = Path(args.project_dir) / "scripts"
            has_scripts = scripts_dir.exists() and (any(scripts_dir.glob('*.vbs')) or any(scripts_dir.glob('*.js')))

            if not verify_wxs_files(args.project_dir, has_scripts):
                log("Verification of WiX source files failed, aborting MSI creation.", error=True)
                sys.exit(1)

            msi_file = build_msi(args.project_dir, args.wix_path, args.output)
            
            if msi_file:
                log(f"MSI package created successfully: {msi_file}")
                
                if 'identity' in config and not args.no_sign:
                    if sign_msi(msi_file, config['identity']):
                        log("MSI package signed successfully.")
                    else:
                        log("Failed to sign MSI package.", error=True)
                
                log("MSI package creation process completed successfully.")
            else:
                log("Failed to create MSI package.", error=True)
                sys.exit(1)

        except Exception as e:
            log(f"An error occurred during the MSI creation process: {str(e)}", error=True)
            if args.verbose:
                import traceback
                log(f"Traceback:\n{traceback.format_exc()}", error=True)
            sys.exit(1)

if __name__ == '__main__':
    main()
