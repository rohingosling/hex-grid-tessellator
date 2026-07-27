# Third-Party Licenses

The HEX Grid Tessellator is distributed under the [MIT License](LICENSE). It builds on the third-party components
listed below. This notice is provided for transparency and to satisfy the attribution requirements of those
components.

## Runtime dependencies

This package is required to run the tool from source and is bundled into the standalone Windows executable
(`dist/hextessellator.exe`). It uses a permissive license compatible with redistribution.

| Package | License | Project |
|---------|---------|---------|
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |

## Packaging

| Component | License | Notes |
|-----------|---------|-------|
| PyInstaller | GPL-2.0-or-later **with bootloader exception** | The bootloader exception explicitly permits distributing the frozen application (this executable) under any license of your choice, including the MIT License used here. PyInstaller itself is a build-time tool and no PyInstaller source is included in the shipped binary beyond the exception-covered bootloader. |

## Development-only (not shipped)

| Package | License | Notes |
|---------|---------|-------|
| pytest | MIT | Test runner listed in `venv_requirements.txt`. Not imported by the application and not bundled into the executable. |
| PyInstaller | see above | Build tooling listed in `venv_requirements.txt`. |

## Full license texts

The full text of each license is available from the corresponding project page linked above, and is included in each
package's distribution within your Python environment (typically under `*.dist-info/`).
