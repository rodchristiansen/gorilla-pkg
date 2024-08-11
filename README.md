# gorillapkg

## Introduction

`gorillapkg` is a tool for building MSI packages in a consistent, repeatable manner from source files, scripts, and a YAML configuration file in a project directory.

This tool leverages the [WiX Toolset](https://wixtoolset.org/) to compile and build MSI packages. It has heavily borrowed ideas and structure from [munki-pkg](https://github.com/munki/munki-pkg), adapting them to suit the needs of Windows environments.

While you can use `gorillapkg` to generate packages for various Windows environments, the packages `gorillapkg` builds are standard MSI installer packages usable wherever Windows MSI packages are supported.

Files, scripts, and metadata are stored in a way that is easy to track and manage using a version control system like git.

### Features

- **Dynamic File Inclusion**: Automatically includes all files from a specified payload directory into the MSI package.
- **Script Support**: Allows for optional pre-installation and post-installation scripts to be executed.
- **Custom Installation Paths**: Specify a custom installation path for the payload.
- **Dynamic GUID Management**: Automatically handles the generation of `ProductCode` GUIDs for new versions, while using a consistent `UpgradeCode` derived from an identifier provided in the build-info YAML.
- **Post-Install Actions**: Specify actions like system restart or logout after installation.
- **MSI Signing**: Automatically sign the MSI package using `SignTool` if a signing identity is provided in the configuration.

### Prerequisites

- Python 3.x
- WiX Toolset 5.0 (Make sure WiX is installed and available in your system’s PATH)
- `PyYAML` for reading the YAML configuration file
- `SignTool` (included with the Windows SDK) for signing MSI packages

### Installation

Clone the repository:

```bash
git clone https://github.com/rodchristiansen/gorillapkg.git
cd gorillapkg
```

### Usage

To create a new MSI project:

```bash
python gorillapkg.py <project_dir> --create
```

This command will create a new project directory structure at `<project_dir>`, including:

- `payload/` - Directory for the files you want to include in the MSI package.
- `scripts/` - Directory for optional pre-installation and post-installation scripts.
- `build-info.yaml` - Configuration file to control the MSI package creation.

#### build-info.yaml

The `build-info.yaml` file contains configuration settings for your project:

```yaml
product:
  name: "Foo"
  version: "1.0.0"
  manufacturer: "Company"
  identifier: "com.company.Foo"
install_path: "C:\\Program Files\\Foo"
postinstall_action: "none"  # Options: "none", "logout", "restart"
identity: "Company Certificate"  # Optional: Certificate name for signing
```

- **identifier**: A reverse domain-style identifier for the application. This remains constant across versions to allow the system to recognize updates.
- **install_path**: Default installation path (can be customized per build).
- **postinstall_action**: Action to be taken after installation (`none`, `logout`, or `restart`).
- **identity**: (Optional) The name of the certificate to be used with `SignTool` for signing the MSI package.

## Basic operation

`gorillapkg` builds MSI packages using the [WiX Toolset](https://wixtoolset.org/), a powerful set of tools for creating Windows Installer packages. WiX handles the generation of `.msi` files by compiling `.wxs` source files, which define the structure and contents of the installer.

### Package project directories

`gorillapkg` creates MSI packages from a "package project directory." At its simplest, a package project directory contains a "payload" directory, which includes the files to be packaged. More typically, the directory also includes a `build-info.yaml` file containing specific settings for the build. The package project directory may also include a "scripts" directory with any pre-installation and/or post-installation scripts to be executed during installation.

### Package project directory layout
```
project_dir/
    build-info.yaml
    payload/
    scripts/
```

### Creating a new project

`gorillapkg` can create an empty package project directory for you:

```bash
python gorillapkg.py --create Foo
```

...will create a new package project directory named "Foo" in the current working directory. This includes a starter `build-info.yaml`, empty `payload/` and `scripts/` directories, and a `.gitignore` file to ignore the `build/` directory that is created during the build process.

Once you have a project directory, you simply copy the files you wish to package into the `payload/` directory and add preinstall and/or postinstall scripts to the `scripts/` directory if needed. You may also wish to edit the `build-info.yaml` to customize your package.

### Building the MSI

To build the MSI package, use the following command:

```bash
python gorillapkg.py <project_dir> --output <output_dir> --wix-path <path_to_wix>
```

Where:
- `<project_dir>` is the directory containing your project files.
- `<output_dir>` (optional) is where the final MSI package will be saved.
- `<path_to_wix>` (optional) is the path to your WiX Toolset installation.

The script will:
1. Generate the required `.wxs` files, including `Package.wxs` using the WiX schema.
2. Compile and build the MSI using WiX Toolset.
3. Sign the MSI if the `identity` key is present in `build-info.yaml`.
4. Output the MSI to the specified directory.

For example, to create and sign an MSI package for the application located in `C:\Projects\Foo`, you would run:

```bash
python gorillapkg.py "C:\Projects\Foo" --output <output_dir> --wix-path <path_to_wix>
```

This will create and sign the MSI package, then save it to the specified `output` directory.

### Signing MSI Packages with `SignTool`

`gorillapkg` supports signing MSI packages using `SignTool` if the `identity` key is provided in the `build-info.yaml` file. Here’s how to set up and use `SignTool`:

#### 1. Install the Windows SDK
`SignTool` is included with the Windows SDK. If you don't have the SDK installed, you can download it from the [Microsoft website](https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk/).

#### 2. Add `SignTool` to Your PATH
After installing the Windows SDK, add the path to `SignTool.exe` to your system’s PATH environment variable for easy access from the command line or scripts.

The typical path for `SignTool.exe` is:

- `C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\signtool.exe`
- `C:\Program Files (x86)\Windows Kits\10\bin\<version>\x86\signtool.exe`

To add this to your PATH:
1. Right-click `This PC` or `My Computer` on your desktop or in File Explorer and choose `Properties`.
2. Click `Advanced system settings`.
3. In the System Properties window, click the `Environment Variables` button.
4. In the Environment Variables window, find the `Path` variable under `System variables`, and click `Edit`.
5. Add the path to `SignTool.exe` to the list, separated from existing entries with a semicolon.
6. Click `OK` to close all windows.

#### 3. Ensure Your Certificate Is Installed
Make sure the certificate you plan to use for signing is installed in the Windows Certificate Store under the "Personal" store.

#### 4. Test the Setup
Verify that `SignTool` is correctly installed and accessible by running the following command in your command prompt:

```bash
signtool
```

This should display a help message with usage instructions. If it doesn’t, ensure the SDK is installed and the PATH variable is correctly configured.

#### 5. Use `SignTool` in `gorillapkg`
When the `identity` key is provided in the `build-info.yaml` file, `gorillapkg` will automatically use `SignTool` to sign your MSI package. It will sign the package using the specified certificate from the Certificate Store, ensuring your package is recognized as secure and trusted.

If the `identity` key is not provided, the signing step will be skipped.

