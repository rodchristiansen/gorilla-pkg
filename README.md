# gorilla-pkg

## Introduction

`gorilla-pkg` is a Windows tool for building `.msi` (Microsoft Installer) packages from a directory structure. It simplifies the creation of installers by automating the process using the WiX Toolset and a YAML configuration file.

This tool is particularly useful for developers and system administrators who need to create custom Windows installers in a consistent, repeatable manner.

## Prerequisites

### 1. Python 3.x

- **Download and Install**: You can download the latest version of Python 3 from [python.org](https://www.python.org/downloads/).
- **Add to PATH**: During installation, make sure to check the box that says **"Add Python 3.x to PATH"**. This will allow you to run Python from the command line.

### 2. WiX Toolset

- **Download and Install**: The WiX Toolset is required to compile the generated source files into an `.msi` package. Download it from the [WiX Toolset Releases](https://github.com/wixtoolset/wix/releases/).

## Installation

### 1. Clone the Repository

First, clone the `gorilla-pkg` repository to your local machine:

```bash
git clone https://github.com/rodchristiansen/gorilla-pkg.git
cd gorilla-pkg
```

### 2. Install Python Dependencies

Navigate to the cloned repository directory and install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

This will install `PyYAML`, which is used to parse the YAML configuration file.

### 3. (Optional) Build the Standalone Executable

If you prefer to distribute and use `gorilla-pkg` as a standalone executable without requiring Python, you can build it using `PyInstaller`:

```bash
pyinstaller --onefile --name gorillapkg gorilla-pkg.py
```

The resulting `gorillapkg.exe` will be located in the `dist` directory.

### 4. (Optional) Add the Executable to Your PATH

To make `gorillapkg.exe` accessible from any command prompt without needing to navigate to its directory, you can add it to your system’s PATH:

#### Steps to Add to PATH:

1. **Move the Executable**: Move `gorillapkg.exe` from the `dist` directory to a permanent location, such as `C:\Program Files\gorillapkg\`.

2. **Add to PATH**:
   - Right-click on the **Start** button and select **System**.
   - Click on **Advanced system settings** on the left.
   - In the System Properties window, click on the **Environment Variables** button.
   - In the **Environment Variables** window, find the **Path** variable under "System variables" and select it, then click **Edit**.
   - In the **Edit Environment Variable** dialog, click **New** and paste the path to the directory where `gorillapkg.exe` is located (e.g., `C:\Program Files\gorillapkg\`).
   - Click **OK** to close all dialog boxes.

3. **Verify the PATH**: Open a new Command Prompt and type `gorillapkg`. If it’s correctly added to the PATH, it should run without needing to specify the full path.

## Usage

To use `gorilla-pkg`, you can either run it as a Python script or as a standalone executable (if you’ve built one).

### Run as a Python Script

```bash
python gorilla-pkg.py MyMsiProject/
```

### Run as a Standalone Executable

```bash
gorillapkg MyMsiProject/
```

### Project Directory Layout

A typical project directory for `gorilla-pkg` should look like this:

```
MsiProject/
├── payload/
├── scripts/
└── build-info.yaml
```

- **`build-info.yaml`**: Configuration file that specifies the installation parameters, such as the product name, version, and the upgrade code.
- **`payload/`**: Directory containing the files to be included in the `.msi` package.
- **`scripts/`**: Directory containing `preinstall.bat` and `postinstall.bat` scripts to be executed before and after the installation process.

### Example `build-info.yaml`

Here’s an example of what your `build-info.yaml` might look like:

```yaml
product:
  name: MyApp
  version: 1.0.0
  manufacturer: MyCompany
  upgrade_code: com.domain.winadmins.myapp
```

### Smart Handling of Files and Actions

`gorilla-pkg` is designed to be smart enough to handle your project structure dynamically:

- **Files Detection**: You no longer need to manually list files in the `build-info.yaml` file. The script will automatically detect all files in the `payload` directory and include them in the package.
  
- **Actions Detection**: Similarly, `preinstall` and `postinstall` scripts in the `scripts` directory are automatically detected and included if they exist. If no scripts are found, the package will still be created without any actions.

### Payload-Free Packages

WiX allows the creation of payload-free packages, which means you can have an `.msi` installer that only runs scripts without installing any files. If the `payload` directory is empty or missing, but scripts are present, the package will still be built.

### Building the `.msi` Package

Once your project directory is set up, you can build the `.msi` package by running:

```bash
python gorilla-pkg.py MyMsiProject/
```

Or, if you built the executable:

```bash
gorillapkg MyMsiProject/
```

This command will:

1. Verify that the WiX Toolset is installed and accessible.
2. Automatically detect files in the `payload` directory and scripts in the `scripts` directory.
3. Generate the necessary WiX source files in the `src/` directory of your project.
4. Compile these files into an `.msi` package located in the `output/` directory within your project.

### Error Handling

If the WiX Toolset is not installed or not found in the expected directory, `gorilla-pkg` will display an error message and exit. You should verify the installation and the path before proceeding.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue on the [GitHub repository](https://github.com/rodchristiansen/gorilla-pkg).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.