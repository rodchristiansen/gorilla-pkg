package main

import (
    "encoding/xml"
    "flag"
    "fmt"
    "gopkg.in/yaml.v2"
    "log"
    "os"
    "os/exec"
    "path/filepath"
    "strconv"
    "strings"
)

// BuildInfo holds package build information parsed from YAML.
type BuildInfo struct {
    InstallLocation    string `yaml:"install_location"`
    PostInstallAction  string `yaml:"postinstall_action"`
    SigningCertificate string `yaml:"signing_certificate,omitempty"`
    Product            struct {
        Identifier  string `yaml:"identifier"`
        Version     string `yaml:"version"`
        Name        string `yaml:"name"`
        Developer   string `yaml:"developer"`
        Description string `yaml:"description,omitempty"`
    } `yaml:"product"`
}

// Package defines the structure of a .nuspec package.
type Package struct {
    XMLName  xml.Name  `xml:"package"`
    Metadata Metadata  `xml:"metadata"`
    Files    []FileRef `xml:"files>file,omitempty"`
}

// Metadata stores the package metadata.
type Metadata struct {
    ID          string `xml:"id"`
    Version     string `xml:"version"`
    Authors     string `xml:"authors"`
    Description string `xml:"description"`
    Tags        string `xml:"tags,omitempty"`
    Readme      string `xml:"readme,omitempty"`
}

// FileRef defines the source and target paths for files.
type FileRef struct {
    Src    string `xml:"src,attr"`
    Target string `xml:"target,attr"`
}

// setupLogging configures log output based on verbosity.
func setupLogging(verbose bool) {
    log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)
    if verbose {
        log.SetOutput(os.Stdout)
    } else {
        log.SetOutput(os.Stderr)
    }
}

// verifyProjectStructure checks that either the payload or scripts folder exists.
func verifyProjectStructure(projectDir string) error {
    payloadPath := filepath.Join(projectDir, "payload")
    scriptsPath := filepath.Join(projectDir, "scripts")

    // Check if at least one of the two required paths exists.
    if _, err := os.Stat(payloadPath); os.IsNotExist(err) {
        if _, err := os.Stat(scriptsPath); os.IsNotExist(err) {
            return fmt.Errorf("either 'payload' or 'scripts' directory must exist in the project directory")
        }
    }

    // Ensure the build-info.yaml file exists.
    buildInfoPath := filepath.Join(projectDir, "build-info.yaml")
    if _, err := os.Stat(buildInfoPath); os.IsNotExist(err) {
        return fmt.Errorf("'build-info.yaml' file is missing in the project directory")
    }

    return nil
}

// NormalizePath ensures paths use consistent separators across platforms.
func NormalizePath(input string) string {
    return filepath.FromSlash(strings.ReplaceAll(input, "\\", "/"))
}

// readBuildInfo loads and parses build-info.yaml from the given directory.
func readBuildInfo(projectDir string) (*BuildInfo, error) {
    path := filepath.Join(projectDir, "build-info.yaml")
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("error reading build-info.yaml: %w", err)
    }

    var buildInfo BuildInfo
    if err := yaml.Unmarshal(data, &buildInfo); err != nil {
        return nil, fmt.Errorf("error parsing YAML: %w", err)
    }

    return &buildInfo, nil
}

// parseVersion converts version strings to a normalized format.
func parseVersion(versionStr string) (string, error) {
    parts := strings.Split(versionStr, ".")
    var numericParts []string

    // Convert all parts to strings to preserve the original input, ensuring they're valid numbers.
    for _, part := range parts {
        if _, err := strconv.Atoi(part); err != nil {
            return "", fmt.Errorf("invalid version part: %q is not a number", part)
        }
        numericParts = append(numericParts, part)
    }

    // Join the parts back together to form the version string.
    return strings.Join(numericParts, "."), nil
}

// createProjectDirectory ensures necessary project directories exist.
func createProjectDirectory(projectDir string) error {
    subDirs := []string{
        "payload",
        "scripts",
        "build",
    }

    for _, subDir := range subDirs {
        fullPath := filepath.Join(projectDir, subDir)
        if err := os.MkdirAll(fullPath, os.ModePerm); err != nil {
            return fmt.Errorf("failed to create directory %s: %w", fullPath, err)
        }
    }
    return nil
}

// copyFile copies a file from src to dst.
func copyFile(src, dst string) error {
    input, err := os.ReadFile(src)
    if err != nil {
        return err
    }
    if err := os.WriteFile(dst, input, 0644); err != nil {
        return err
    }
    return nil
}

// createChocolateyInstallScript generates the chocolateyInstall.ps1 script.
func createChocolateyInstallScript(buildInfo *BuildInfo, projectDir string) error {
    scriptPath := filepath.Join(projectDir, "tools", "chocolateyInstall.ps1")
    installLocation := normalizeInstallLocation(buildInfo.InstallLocation)

    var scriptBuilder strings.Builder

    // Build the PowerShell script with enhanced logging and validation
    scriptBuilder.WriteString(fmt.Sprintf(`$ErrorActionPreference = 'Stop'

$installLocation = '%s'

# Ensure the install location exists (if defined)
if ($installLocation -and $installLocation -ne '') {
    try {
        New-Item -ItemType Directory -Force -Path $installLocation | Out-Null
        Write-Host "Created or verified install location: $installLocation"
    } catch {
        Write-Error "Failed to create or access: $installLocation"
        exit 1
    }
} else {
    Write-Host "No install location specified, skipping creation of directories."
}

# Copy files from the payload folder to the install location (if payload exists)
$payloadPath = "$PSScriptRoot\..\payload"
$payloadPath = [System.IO.Path]::GetFullPath($payloadPath)
$payloadPath = $payloadPath.TrimEnd('\', '/')
if (Test-Path $payloadPath) {
    Write-Host "Payload path: $payloadPath"
    Get-ChildItem -Path $payloadPath -Recurse | ForEach-Object {
        $fullName = $_.FullName
        $relativePath = $fullName.Substring($payloadPath.Length)
        $relativePath = $relativePath.TrimStart('\', '/')
        $destinationPath = Join-Path $installLocation $relativePath

        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
            Write-Host "Created directory: $destinationPath"
        } else {
            Copy-Item -Path $fullName -Destination $destinationPath -Force
            Write-Host "Copied: $($fullName) -> $destinationPath"

            # Validate if the file was copied successfully
            if (-not (Test-Path -Path $destinationPath)) {
                Write-Error "Failed to copy: $($fullName)"
                exit 1
            }
        }
    }
} else {
    Write-Host "No payload folder found. Proceeding with script-only installation."
}
`, installLocation))

    // Handle post-install action if provided
    if action := strings.ToLower(buildInfo.PostInstallAction); action != "" {
        scriptBuilder.WriteString("\n# Executing post-install action\n")
        switch action {
        case "logout":
            scriptBuilder.WriteString("Write-Host 'Logging out...'\nshutdown /l\n")
        case "restart":
            scriptBuilder.WriteString("Write-Host 'Restarting system...'\nshutdown /r /t 0\n")
        case "none":
            scriptBuilder.WriteString("Write-Host 'No post-install action required.'\n")
        default:
            return fmt.Errorf("unsupported post-install action: %s", action)
        }
    }

    // Append custom post-install script if available
    postInstallScriptPath := filepath.Join(projectDir, "scripts", "postinstall.ps1")
    if _, err := os.Stat(postInstallScriptPath); err == nil {
        scriptBuilder.WriteString("\n# Post-install script contents\n")
        postInstallContent, err := os.ReadFile(postInstallScriptPath)
        if err != nil {
            return fmt.Errorf("failed to read postinstall.ps1: %w", err)
        }
        scriptBuilder.WriteString(string(postInstallContent))
    }

    // Write the PowerShell script to the tools directory
    if err := os.MkdirAll(filepath.Dir(scriptPath), os.ModePerm); err != nil {
        return fmt.Errorf("failed to create tools directory: %w", err)
    }

    if err := os.WriteFile(scriptPath, []byte(scriptBuilder.String()), 0644); err != nil {
        return fmt.Errorf("failed to write chocolateyInstall.ps1: %w", err)
    }
    return nil
}

// normalizeInstallLocation ensures the install location path is properly formatted.
func normalizeInstallLocation(path string) string {
    // Replace forward slashes with backslashes
    path = strings.ReplaceAll(path, "/", `\`)
    // Remove any trailing backslashes
    path = strings.TrimRight(path, `\`)
    return path
}

// includePreinstallScript copies preinstall.ps1 to tools\chocolateyBeforeModify.ps1 if it exists.
func includePreinstallScript(projectDir string) error {
    preinstallSrcPath := filepath.Join(projectDir, "scripts", "preinstall.ps1")
    preinstallDstPath := filepath.Join(projectDir, "tools", "chocolateyBeforeModify.ps1")

    if _, err := os.Stat(preinstallSrcPath); err == nil {
        // Ensure the tools directory exists
        if err := os.MkdirAll(filepath.Dir(preinstallDstPath), os.ModePerm); err != nil {
            return fmt.Errorf("failed to create tools directory: %w", err)
        }
        // Copy the preinstall.ps1 to tools\chocolateyBeforeModify.ps1
        if err := copyFile(preinstallSrcPath, preinstallDstPath); err != nil {
            return fmt.Errorf("failed to copy preinstall.ps1 to chocolateyBeforeModify.ps1: %w", err)
        }
    }
    return nil
}

// handlePostInstallScript manages the postinstall.ps1 file.
func handlePostInstallScript(action, projectDir string) error {
    postInstallPath := filepath.Join(projectDir, "scripts", "postinstall.ps1")
    var command string

    // Determine the command based on the action
    switch action {
    case "logout":
        command = "shutdown /l\n"
    case "restart":
        command = "shutdown /r /t 0\n"
    case "none":
        log.Println("No post-install action required.")
        return nil // No further action needed
    default:
        return fmt.Errorf("unknown post-install action: %s", action)
    }

    // Check if postinstall.ps1 exists and handle appropriately
    var file *os.File
    if _, err := os.Stat(postInstallPath); os.IsNotExist(err) {
        // Create a new postinstall.ps1 file
        log.Printf("Creating new postinstall.ps1: %s", postInstallPath)
        if err := os.MkdirAll(filepath.Dir(postInstallPath), os.ModePerm); err != nil {
            return fmt.Errorf("failed to create scripts directory: %v", err)
        }
        file, err = os.Create(postInstallPath)
        if err != nil {
            return fmt.Errorf("failed to create postinstall.ps1: %v", err)
        }
    } else {
        // Append to the existing postinstall.ps1 file
        log.Printf("Appending to existing postinstall.ps1: %s", postInstallPath)
        file, err = os.OpenFile(postInstallPath, os.O_APPEND|os.O_WRONLY, os.ModeAppend)
        if err != nil {
            return fmt.Errorf("failed to open postinstall.ps1: %v", err)
        }
    }
    defer file.Close()

    // Write or append the command
    if _, err := file.WriteString(command); err != nil {
        return fmt.Errorf("failed to write to postinstall.ps1: %v", err)
    }

    log.Printf("Post-install command added: %s", command)
    return nil
}

// generateNuspec builds the .nuspec file with proper payload handling.
func generateNuspec(buildInfo *BuildInfo, projectDir string) (string, error) {
    nuspecPath := filepath.Join(projectDir, buildInfo.Product.Name+".nuspec")

    // Set the package description or use a default one.
    description := buildInfo.Product.Description
    if description == "" {
        description = fmt.Sprintf(
            "%s version %s for %s by %s",
            buildInfo.Product.Name, buildInfo.Product.Version,
            buildInfo.Product.Identifier, buildInfo.Product.Developer,
        )
    }

    // Define the structure of the .nuspec package.
    nuspec := Package{
        Metadata: Metadata{
            ID:          buildInfo.Product.Identifier,
            Version:     buildInfo.Product.Version,
            Authors:     buildInfo.Product.Developer,
            Description: description,
            Tags:        "admin",
        },
    }

    // Include all files from the /payload folder in the .nuspec with correct paths.
    payloadPath := filepath.Join(projectDir, "payload")
    if _, err := os.Stat(payloadPath); !os.IsNotExist(err) {
        err := filepath.Walk(payloadPath, func(path string, info os.FileInfo, err error) error {
            if err != nil {
                return err
            }
            if !info.IsDir() {
                // Make the path relative to the project directory.
                relPath, _ := filepath.Rel(projectDir, path)
                nuspec.Files = append(nuspec.Files, FileRef{
                    Src:    relPath,
                    Target: relPath,
                })
            }
            return nil
        })
        if err != nil {
            return "", fmt.Errorf("error walking payload directory: %w", err)
        }
    }

    // Always include the chocolateyInstall.ps1 script in the package.
    nuspec.Files = append(nuspec.Files, FileRef{
        Src:    filepath.Join("tools", "chocolateyInstall.ps1"),
        Target: filepath.Join("tools", "chocolateyInstall.ps1"),
    })

    // Helper function to add scripts to the nuspec if they exist.
    addScriptToNuspec := func(nuspec *Package, projectDir, scriptName, target string) {
        scriptPath := filepath.Join(projectDir, "scripts", scriptName)
        if _, err := os.Stat(scriptPath); !os.IsNotExist(err) {
            nuspec.Files = append(nuspec.Files, FileRef{
                Src:    filepath.Join("scripts", scriptName),
                Target: filepath.Join("tools", target),
            })
        }
    }

    // Include preinstall and postinstall scripts if they exist.
    addScriptToNuspec(&nuspec, projectDir, "preinstall.ps1", "chocolateyBeforeModify.ps1")
    addScriptToNuspec(&nuspec, projectDir, "postinstall.ps1", "postinstall.ps1")

    // Create the .nuspec file.
    file, err := os.Create(nuspecPath)
    if err != nil {
        return "", fmt.Errorf("failed to create .nuspec file: %w", err)
    }
    defer file.Close()

    // Encode the .nuspec structure into the file as XML.
    encoder := xml.NewEncoder(file)
    encoder.Indent("", "  ")
    if err := encoder.Encode(nuspec); err != nil {
        return "", fmt.Errorf("failed to encode .nuspec: %w", err)
    }

    return nuspecPath, nil
}

// Helper function to add scripts to the nuspec if they exist
func addScriptToNuspec(nuspec *Package, projectDir, scriptName, target string) {
    scriptPath := filepath.Join(projectDir, "scripts", scriptName)
    if _, err := os.Stat(scriptPath); !os.IsNotExist(err) {
        nuspec.Files = append(nuspec.Files, FileRef{
            Src:    filepath.Join("scripts", scriptName),
            Target: filepath.Join("tools", target),
        })
    }
}

// runCommand executes shell commands with logging.
func runCommand(command string, args ...string) error {
    log.Printf("Running: %s %v", command, args)
    cmd := exec.Command(command, args...)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    return cmd.Run()
}

// signPackage signs the .nupkg using SignTool.
func signPackage(nupkgFile, certificate string) error {
    log.Printf("Signing package: %s with certificate: %s", nupkgFile, certificate)
    return runCommand(
        "signtool", "sign", "/n", certificate,
        "/fd", "SHA256", "/tr", "http://timestamp.digicert.com",
        "/td", "SHA256", nupkgFile,
    )
}

// check nuget is installed
func checkNuGet() {
    if err := runCommand("nuget", "locals", "all", "-list"); err != nil {
        log.Fatalf(`NuGet is not installed or not in PATH. 
You can install it via Chocolatey: 
  choco install nuget.commandline`)
    }
}

// check signtool is installed
func checkSignTool() {
    if err := runCommand("signtool", "-?"); err != nil {
        log.Fatalf("SignTool is not installed or not available: %v", err)
    }
}

func main() {
    var verbose bool

    // Parse any additional flags.
    flag.BoolVar(&verbose, "verbose", false, "Enable verbose logging")
    flag.Parse()

    // Ensure the project directory is provided as the first command-line argument.
    if flag.NArg() < 1 {
        log.Fatalf("Usage: %s <project_directory>", os.Args[0])
    }
    projectDir := NormalizePath(flag.Arg(0))

    setupLogging(verbose)

    log.Printf("Using project directory: %s", projectDir)

    // Verify the project structure exists and is valid.
    if err := verifyProjectStructure(projectDir); err != nil {
        log.Fatalf("Error verifying project structure: %v", err)
    }
    log.Println("Project structure verified. Proceeding with package creation...")

    // Read build-info.yaml from the provided project directory.
    buildInfo, err := readBuildInfo(projectDir)
    if err != nil {
        log.Fatalf("Error reading build-info.yaml: %v", err)
    }

    // Create the required directories inside the project.
    if err := createProjectDirectory(projectDir); err != nil {
        log.Fatalf("Error creating directories: %v", err)
    }
    log.Println("Directories created successfully.")

    // Include preinstall script if it exists.
    if err := includePreinstallScript(projectDir); err != nil {
        log.Fatalf("Error including preinstall script: %v", err)
    }

    // Generate the chocolateyInstall.ps1 script.
    if err := createChocolateyInstallScript(buildInfo, projectDir); err != nil {
        log.Fatalf("Error generating chocolateyInstall.ps1: %v", err)
    }

    // Generate the .nuspec file and defer its removal.
    nuspecPath, err := generateNuspec(buildInfo, projectDir)
    if err != nil {
        log.Fatalf("Error generating .nuspec: %v", err)
    }
    defer os.Remove(nuspecPath)
    log.Printf(".nuspec generated at: %s", nuspecPath)

    // Ensure NuGet is available.
    checkNuGet()

    // Set the build directory.
    buildDir := filepath.Join(projectDir, "build")

    // Define the expected filename using Product Name and Version.
    builtPkgName := buildInfo.Product.Name + "-" + buildInfo.Product.Version + ".nupkg"
    builtPkgPath := filepath.Join(buildDir, builtPkgName)

    // Run NuGet to pack the package.
    if err := runCommand("nuget", "pack", nuspecPath, "-OutputDirectory", buildDir, "-NoPackageAnalysis"); err != nil {
        log.Fatalf("Error creating package: %v", err)
    }

    // Find the generated package in case NuGet used the identifier in the name.
    searchPattern := filepath.Join(buildDir, buildInfo.Product.Identifier+"*.nupkg")
    matches, _ := filepath.Glob(searchPattern)

    var finalPkgPath string
    if len(matches) > 0 {
        // Rename the package to the correct built name.
        log.Printf("Renaming package: %s to %s", matches[0], builtPkgPath)
        if err := os.Rename(matches[0], builtPkgPath); err != nil {
            log.Fatalf("Failed to rename package: %v", err)
        }
        finalPkgPath = builtPkgPath
    } else {
        log.Printf("Package matching pattern not found, using: %s", builtPkgPath)
        finalPkgPath = builtPkgPath
    }

    // Check if signing is required, and sign the package if a certificate is provided.
    if buildInfo.SigningCertificate != "" {
        checkSignTool()
        if err := signPackage(finalPkgPath, buildInfo.SigningCertificate); err != nil {
            log.Fatalf("Failed to sign package %s: %v", finalPkgPath, err)
        }
    } else {
        log.Println("No signing certificate provided. Skipping signing.")
    }

    // Clean up the tools directory after packaging.
    toolsDir := filepath.Join(projectDir, "tools")
    if err := os.RemoveAll(toolsDir); err != nil {
        log.Printf("Warning: Failed to remove tools directory: %v", err)
    } else {
        log.Println("Tools directory removed successfully.")
    }

    // Log the successful creation with the correct built name.
    log.Printf("Package created successfully: %s", finalPkgPath)
}
