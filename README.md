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

### Prerequisites

- Python 3.x
- WiX Toolset 5.0 (Make sure WiX is installed and available in your system’s PATH)
- `PyYAML` for reading the YAML configuration file

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
```

- **identifier**: A reverse domain-style identifier for the application. This remains constant across versions to allow the system to recognize updates.
- **install_path**: Default installation path (can be customized per build).
- **postinstall_action**: Action to be taken after installation (`none`, `logout`, or `restart`).

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
3. Output the MSI to the specified directory.

For example, to create an MSI package for the application located in `C:\Projects\Foo`, you would run:

```bash
python gorillapkg.py "C:\Projects\Foo" --output <output_dir> --wix-path <path_to_wix>
```

This will create the MSI package and save it to the specified `output` directory.