"""
Export the default SIMBA libraries hierarchy to a compact, human- & LLM-readable
plain-text file (one block per model, one line per pin/parameter, no JSON).
"""

from aesim.simba import Library, ParameterBase

LIBRARIES_TO_EXPORT = {
    "RLC",
    "Branches",
    "Probes",
    "Semiconductors",
    "Switches",
    "Sources",
    "Logic",
}

# ────────────────────────────── Helper utilities ──────────────────────────────
def enum_to_str(value):
    try:
        return value.ToString()
    except Exception:  # noqa: BLE001
        return str(value)


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


# ──────────────────────────── Formatting utilities ────────────────────────────
def parameter_names(device):
    """Return parameter names except the special 'Name' parameter."""
    names = []
    for prop in device.GetType().GetProperties():
        if not prop.CanRead or prop.Name == "Name":
            continue
        if isinstance(safe_call(lambda: prop.GetValue(device), None), ParameterBase):
            names.append(f'"{prop.Name}"')
    return names


def format_device(device, library_path):
    """Return the textual block describing one SIMBA device."""
    w = safe_call(lambda: device.Footprint.Width, 0)
    h = safe_call(lambda: device.Footprint.Height, 0)

    lines = [
        f'Model Name: "{device.LibraryItemName}"',
        f'Library: {library_path}',
        f'Dimensions: [{w};{h}]',
        "Pins:",
    ]

    # Pins (one per line)
    for pin in safe_call(lambda: device.Pins, []):
        lines.append(
            f'- "{pin.Name}" (Type: {enum_to_str(pin.Type)}, '
            f'Location: [{pin.Position.X};{pin.Position.Y}], '
            f'Direction: {enum_to_str(pin.Direction)})'
        )

    # Parameters (only if any remain)
    pnames = parameter_names(device)
    if pnames:
        lines.append("Parameters:")
        lines.extend(f'- {p}' for p in pnames)

    # Separator
    lines.append("---\n")
    return "\n".join(lines)


# ────────────────────────────── Traversal logic ───────────────────────────────
def traverse_library(library, path_parts, out_lines):
    new_path = path_parts + [library.LibraryItemName]

    if (
        library.LibraryItemName in LIBRARIES_TO_EXPORT
        and library.Devices
        and library.Devices.Count > 0
    ):
        lib_path_str = "\\".join(new_path[1:])  # skip the root node
        for dev in library.Devices:
            out_lines.append(format_device(dev, lib_path_str))

    for sub in library.Libraries:
        traverse_library(sub, new_path, out_lines)


# ────────────────────────────────── Main script ───────────────────────────────
if __name__ == "__main__":
    blocks: list[str] = []

    traverse_library(Library.DefaultElectricalLibrary(), ["Electrical"], blocks)
    traverse_library(Library.DefaultControlLibrary(), ["Control"], blocks)

    with open("simba_libraries.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))

    print("✅ File 'simba_libraries.txt' created successfully.")