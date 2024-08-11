# gorillapkg

## Introduction

`gorillapkg` is a tool for building MSI packages in a consistent, repeatable manner from source files, scripts, and a YAML configuration file in a project directory.

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
git clone https://github.com/rodchristiansen/`gorillapkg`.git
cd `gorillapkg`
```

### Usage

To create a new MSI project:

```bash
python `gorillapkg`.py <project_dir> --create
```

This command will create a new project directory structure at `<project_dir>`, including:

- `payload/` - Directory for the files you want to include in the MSI package.
- `scripts/` - Directory for optional pre-installation and post-installation scripts.
- `build-info.yaml` - Configuration file to control the MSI package creation.

#### build-info.yaml

The `build-info.yaml` file contains configuration settings for your project:

```yaml
product:
  name: "MyApp"
  version: "1.0.0"
  manufacturer: "MyCompany"
  identifier: "com.example.myapp"
install_path: "C:\\Program Files\\MyApp"
postinstall_action: "none"  # Options: "none", "logout", "restart"
```

- **identifier**: A reverse domain-style identifier for the application. This remains constant across versions to allow the system to recognize updates.
- **install_path**: Default installation path (can be customized per build).
- **postinstall_action**: Action to be taken after installation (`none`, `logout`, or `restart`).

### Building the MSI

To build the MSI package:

```bash
python `gorillapkg`.py <project_dir> --output <output_dir> --wix-path <path_to_wix>
```

Where:
- `<project_dir>` is the directory containing your project files.
- `<output_dir>` is where the final MSI package will be saved.
- `<path_to_wix>` is the path to your WiX Toolset installation.

The script will:
1. Generate the required `.wxs` files, including `Package.wxs` using the correct WiX schema.
2. Compile and build the MSI using WiX Toolset.
3. Output the MSI to the specified directory.

### Example

Here's an example of a typical usage scenario:

```bash
python `gorillapkg`.py "C:\Projects\MyApp"
```

This will create an MSI package for the application located in `C:\Projects\MyApp`, and output the installer to the `output` directory.