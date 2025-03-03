
<p align="center">
  <img alt="Folder Fort Sync" width="700">
</p>

<h1 align="center">Folder Fort Sync</h1>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#dependencies">Dependencies</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  A powerful yet simple tool to sync your files and folders securely from your PC to <strong>FolderFort Cloud</strong>. 
  Built with <strong>Python</strong> and <strong>CustomTkinter</strong>, it provides a sleek dark-themed interface for 
  effortless file management and synchronization.
</p>

## ✨ Features

<table>
  <tr>
    <td><b>1. 🔑 Secure Authentication</b></td>
    <td>Save and securely store API credentials for quick access</td>
  </tr>
  <tr>
    <td><b>2. 📂 Intuitive File Selection</b></td>
    <td>Browse and select local folders with a familiar interface</td>
  </tr>
  <tr>
    <td><b>3. ☁️ Cloud Integration</b></td>
    <td>Seamlessly connect to your FolderFort Cloud storage</td>
  </tr>
  <tr>
    <td><b>4. ⏯️ Complete Sync Controls</b></td>
    <td>Start, pause, resume, and stop uploads with visual animations</td>
  </tr>
  <tr>
    <td><b>5. 🔄 Auto-Retry</b></td>
    <td>Automatically retry failed transfers with detailed error reporting</td>
  </tr>
  <tr>
    <td><b>6. 📊 Real-time Tracking</b></td>
    <td>Monitor progress with detailed logs and animated progress bar</td>
  </tr>
  <tr>
    <td><b>7. 🌙 Modern Dark UI</b></td>
    <td>Sleek, eye-friendly interface designed for extended use</td>
  </tr>
</table>

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- Internet connection for API access
- FolderFort account with API token

### Option 1: Download Release (Recommended)

<details open>
<summary><b>Download and Run the Application</b></summary>

1. **Download the latest release**:
   - Visit the [Releases page](https://github.com/MridulParth/FolderFortSync/releases)
   - Download the latest ZIP file (`FolderFortSync-v1.1.zip`)

2. **Extract the downloaded ZIP file** to a location of your choice

3. **Install required packages**:
   ```bash
   pip install customtkinter requests humanize keyring
   ```

4. **Launch the application**:
   ```bash
   python sync_app.py
   ```
</details>

### Option 2: Clone the Repository

<details>
<summary><b>For Developers and Contributors</b></summary>

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MridulParth/FolderFortSync.git
   ```

2. **Navigate to the project directory**:
   ```bash
   cd FolderFortSync
   ```

3. **Install required packages**:
   ```bash
   pip install customtkinter requests humanize keyring
   ```

4. **Launch the application**:
   ```bash
   python sync_app.py
   ```
</details>



## 🎮 Usage

<p align="center">
  <img src="screenshot.png" alt="Usage Flow" width="600">
</p>

1. **Authentication**:
   - Enter your API Token in the designated field
   - Click "Save Token" to securely store it for future sessions

2. **Select Source**:
   - Click "Browse" to select the local folder containing files you want to upload
   - All files and subfolders will be included in the sync

3. **Choose Destination**:
   - Click "Refresh" to load available cloud folders
   - Select your destination folder from the dropdown menu

4. **Start Sync Process**:
   - Click "Start" to begin uploading your files
   - The progress bar will show real-time status

5. **Control Options**:
   - **Pause**: Temporarily halt uploads (in-progress transfers will complete)
   - **Resume**: Continue paused uploads
   - **Stop**: Cancel the entire sync operation
   - **Retry Failed**: Attempt to re-upload any failed files

6. **Monitor Progress**:
   - View detailed logs in the bottom panel
   - Check upload speed and estimated time remaining

## 🏗️ Project Structure

```
📁 FolderFortSync/
├── sync_app.py            # Main application entry point
├── file_uploader.py       # File upload and transfer management
├── folder_manager.py      # Cloud folder operations and structure
├── ui_components.py       # UI elements and visual components
├── icon.ico               # Application icon
└── README.md              # Documentation
```

## 📦 Dependencies

- **CustomTkinter**: Modern UI toolkit for building the interface
- **Requests**: HTTP library for API communication
- **Humanize**: Human-readable file sizes and timestamps
- **Keyring**: Secure credential storage for API tokens

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add some amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

Please ensure your code follows the project's style guidelines and includes appropriate tests.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💬 Support

If you encounter any issues or have questions, please [open an issue](https://github.com/MridulParth/FolderFortSync/issues) on GitHub.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/MridulParth">Kizzieee</a>
</p>
