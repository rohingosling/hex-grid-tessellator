#-----------------------------------------------------------------------------------------------------------------------
# Project: HEX Grid Tessellator
# Version: 3.1.0
# Date:    2019-02-18
# Author:  Rohin Gosling
#
# Description:
#
#   A CLI tool that generates publication-quality hexagonal grid tessellation PNG images. Uses flat-top hexagons on an
#   axial coordinate system with supersampled anti-aliasing.
#
#   - HEX Grid Tessellator `hextessellator.exe` was created to generate transparency masks that I use for graphic
#     design projects. But can be used for anything where you need a hexagonal grid pattern.
#     e.g. game maps, data visualizations, procedural textures, etc.
#
#   - Uses flat-top hexagons on an axial coordinate system with supersampled anti-aliasing via Pillow.
#
#   - Runs as a standalone Windows `.exe` - no Python installation required.
#
# Usage Examples:
#
#   python src/main.py --debug
#   python src/main.py --width 1920 --height 1080 --circumradius 48 --antialias high --debug
#   python src/main.py --import_settings settings.json
#   python src/main.py --export_settings settings.json
#
#-----------------------------------------------------------------------------------------------------------------------

import argparse
import json
import math
import os
import re
import sys

from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from PIL    import Image
from PIL    import ImageColor
from PIL    import ImageDraw


#-----------------------------------------------------------------------------------------------------------------------
# Class: HexagonGeometry
#
# Description:
#
#   Provides vertex computation for flat-top regular hexagons.
#
#   Encapsulates circumradius and provides vertex generation for hexagons centred at arbitrary pixel coordinates using
#   the flat-top orientation.
#
# Attributes:
#
#   circumradius: The circumradius (centre-to-vertex distance) in pixels.
#
#-----------------------------------------------------------------------------------------------------------------------

class HexagonGeometry:

    #-------------------------------------------------------------------------------------------------------------------
    # Constructor: __init__
    #
    # Description:
    #
    #   Initialise hexagon geometry with a given circumradius.
    #
    # Arguments:
    #
    #   circumradius: The circumradius R of the hexagon in pixels.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def __init__ ( self, circumradius: float ) -> None:

        # Initialize hexagon geometry with a given circumradius.

        self._circumradius: float = circumradius

    #-------------------------------------------------------------------------------------------------------------------
    # Property: circumradius
    #
    # Description:
    #
    #   Return the circumradius R of the hexagon.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   The circumradius R in pixels.
    #
    #-------------------------------------------------------------------------------------------------------------------

    @property
    def circumradius ( self ) -> float:

        # Return the circumradius R of the hexagon.

        return self._circumradius

    #-------------------------------------------------------------------------------------------------------------------
    # Property: inradius
    #
    # Description:
    #
    #   Return the inradius (apothem) r of the hexagon, computed as r = R * sqrt(3)/2.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   The inradius r in pixels.
    #
    #-------------------------------------------------------------------------------------------------------------------

    @property
    def inradius ( self ) -> float:

        # Return the inradius (apothem) r of the hexagon, computed as r = R * sqrt(3)/2.

        return self._circumradius * math.sqrt ( 3 ) / 2.0

    #-------------------------------------------------------------------------------------------------------------------
    # Function: vertices
    #
    # Description:
    #
    #   Compute the 6 vertices of a flat-top hexagon centred at (cx, cy).
    #
    #   - Vertices start at the rightmost point (cx + R, cy) and proceed counter-clockwise at 60-degree intervals.
    #
    # Arguments:
    #
    #   cx: X coordinate of the hexagon centre.
    #   cy: Y coordinate of the hexagon centre.
    #
    # Returns:
    #
    #   A list of 6 (x, y) tuples representing the vertex positions.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def vertices ( self, cx: float, cy: float ) -> List [ Tuple [ float, float ] ]:

        # Compute the 6 vertices of a flat-top hexagon centred at (cx, cy).

        R = self._circumradius

        # Return vertices starting at the rightmost point and proceeding counter-clockwise at 60-degree intervals.

        return [
            (
                cx + R * math.cos ( math.pi * k / 3.0 ),
                cy + R * math.sin ( math.pi * k / 3.0 )
            )
            for k in range ( 6 )
        ]


#-----------------------------------------------------------------------------------------------------------------------
# Class: AxialGrid
#
# Description:
#
#   Axial coordinate system for hexagonal grids.
#
#   Provides coordinate-to-pixel conversion, ring traversal, concentric grid generation, and auto-fill layer
#   computation for flat-top hexagonal grids.
#
# Attributes:
#
#   spacing_radius: The effective spacing radius R_s used for layout.
#
#-----------------------------------------------------------------------------------------------------------------------

class AxialGrid:

    # Canonical ring-traversal directions (axial deltas).

    _DIRECTIONS: List [ Tuple [ int, int ] ] = [
        ( +1, -1 ), ( +1, 0 ), ( 0, +1 ),
        ( -1, +1 ), ( -1, 0 ), ( 0, -1 ),
    ]

    #-------------------------------------------------------------------------------------------------------------------
    # Constructor: __init__
    #
    # Description:
    #
    #   Initialise the axial grid with a spacing radius.
    #
    # Arguments:
    #
    #   spacing_radius: Effective spacing radius R_s = R + margin/2.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def __init__ ( self, spacing_radius: float = 1.0 ) -> None:

        # Initialise the axial grid with a spacing radius.

        self._spacing_radius: float = spacing_radius

    #-------------------------------------------------------------------------------------------------------------------
    # Function: axial_to_pixel
    #
    # Description:
    #
    #   Convert axial coordinates (q, r) to pixel coordinates on canvas.
    #
    # Arguments:
    #
    #   q: Axial q coordinate.
    #   r: Axial r coordinate.
    #   w: Canvas width in pixels.
    #   h: Canvas height in pixels.
    #
    # Returns:
    #
    #   A (px, py) tuple of pixel coordinates.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def axial_to_pixel ( self, q: int, r: int, w: int, h: int ) -> Tuple [ float, float ]:

        # Convert axial coordinates (q, r) to pixel coordinates on canvas.

        R_s = self._spacing_radius
        px  = R_s * 1.5 * q
        py  = R_s * math.sqrt ( 3 ) * ( r + q / 2.0 )

        # Return pixel coordinates with the origin (0, 0) at the canvas centre.

        return ( w / 2.0 + px, h / 2.0 + py )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: ring
    #
    # Description:
    #
    #   Generate all axial coordinates on ring at hex distance d.
    #
    #   - For d=0 returns only the origin (0, 0).
    #   - For d>=1 returns 6d cells starting at (-d, 0) and walking along the 6 canonical directions.
    #
    # Arguments:
    #
    #   d: The hex distance (ring number). Must be >= 0.
    #
    # Returns:
    #
    #   A list of (q, r) tuples for all cells on this ring.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def ring ( self, d: int ) -> List [ Tuple [ int, int ] ]:

        # If d=0 returns only the origin (0, 0). For d>=1 returns 6d cells starting at (-d, 0) and walking along the 6 canonical directions.

        if d == 0:
            return [ ( 0, 0 ) ]

        # For d >= 1, walk the ring starting at ( -d, 0 ) and following the 6 canonical directions.

        cells: List [ Tuple [ int, int ] ] = []

        # Start at ( -d, 0 ).

        q, r = -d, 0

        # Walk the ring in 6 segments of length d, following the canonical directions.

        for dq, dr in self._DIRECTIONS:
            for _ in range ( d ):
                cells.append ( ( q, r ) )
                q += dq
                r += dr

        # Return the list of (q, r) tuples for all cells on this ring.

        return cells

    #-------------------------------------------------------------------------------------------------------------------
    # Function: generate
    #
    # Description:
    #
    #   Generate all axial coordinates for a concentric grid of L layers.
    #
    #   - Layer 1 is the origin cell.
    #   - Layer l >= 2 is ring at distance l-1.
    #   - Total cells: 1 + 3*L*(L-1).
    #
    # Arguments:
    #
    #   layers: Number of concentric layers (>= 1).
    #
    # Returns:
    #
    #   A list of (q, r) tuples for all cells in the grid.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def generate ( self, layers: int ) -> List [ Tuple [ int, int ] ]:

        # Generate all axial coordinates for a concentric grid of L layers.

        cells: List [ Tuple [ int, int ] ] = []

        # Layer 1 is the origin cell. Layer l >= 2 is ring at distance l-1. Total cells: 1 + 3*L*(L-1).

        for d in range ( layers ):
            cells.extend ( self.ring ( d ) )

        # Return the list of (q, r) tuples for all cells in the grid.

        return cells

    #-------------------------------------------------------------------------------------------------------------------
    # Function: auto_fill_layers
    #
    # Description:
    #
    #   Compute the minimum layers needed to cover a canvas of size w x h.
    #
    # Arguments:
    #
    #   w:              Canvas width in pixels.
    #   h:              Canvas height in pixels.
    #   spacing_radius: The effective spacing radius R_s.
    #
    # Returns:
    #
    #   The minimum number of layers (always >= 1).
    #
    #-------------------------------------------------------------------------------------------------------------------

    def auto_fill_layers ( self, w: int, h: int, spacing_radius: float ) -> int:

        # Compute the minimum layers needed to cover a canvas of size w x h.

        R_s = spacing_radius
        L_h = math.ceil ( ( w / 2.0 ) / ( 1.5 * R_s ) )
        L_v = math.ceil ( ( h / 2.0 ) / ( math.sqrt ( 3 ) * R_s ) )
        L   = max ( L_h, L_v ) + 1

        # Return the minimum number of layers (always >= 1).

        return max ( L, 1 )


#-----------------------------------------------------------------------------------------------------------------------
# Class: ColorParser
#
# Description:
#
#   Parses color specifications from multiple string formats into RGB tuples.
#
#   Supports CSS named colours, hex codes (#RGB, #RRGGBB), and RGB comma-separated tuples (e.g. '255,128,0').
#
#-----------------------------------------------------------------------------------------------------------------------

class ColorParser:

    #-------------------------------------------------------------------------------------------------------------------
    # Function: parse
    #
    # Description:
    #
    #   Parse a color string into an (R, G, B) tuple.
    #
    #   Accepts CSS named colours, hex codes, and comma-separated RGB values.
    #
    # Arguments:
    #
    #   color_str: The color specification string.
    #
    # Returns:
    #
    #   An (R, G, B) tuple of integers in [0, 255].
    #
    # Raises:
    #
    #   ValueError: If the color string cannot be parsed.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def parse ( self, color_str: str ) -> Tuple [ int, int, int ]:

        # Parse a color string into an (R, G, B) tuple.

        s = color_str.strip ()

        # Try comma-separated RGB tuple first.

        if "," in s:
            return self._parse_rgb_tuple ( s )

        # Use Pillow's ImageColor for CSS names and hex codes.

        try:
            rgb = ImageColor.getrgb ( s )
            return ( rgb [ 0 ], rgb [ 1 ], rgb [ 2 ] )
        except ( ValueError, AttributeError ):
            raise ValueError ( f"Invalid color specification: '{color_str}'" )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _parse_rgb_tuple
    #
    # Description:
    #
    #   Parse a comma-separated RGB string like '255,128,0'.
    #
    # Arguments:
    #
    #   s: Comma-separated string with 3 integer components.
    #
    # Returns:
    #
    #   An (R, G, B) tuple.
    #
    # Raises:
    #
    #   ValueError: If parsing fails or values are out of range.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _parse_rgb_tuple ( self, s: str ) -> Tuple [ int, int, int ]:

        # Parse a comma-separated RGB string like '255,128,0'.

        parts = [ p.strip () for p in s.split ( "," ) ]

        # Validate that we have exactly 3 components.

        if len ( parts ) != 3:
            raise ValueError ( f"RGB tuple must have 3 components, got {len ( parts )}: '{s}'" )

        # Convert components to integers and validate range [0, 255].

        try:

            values = tuple ( int ( p ) for p in parts )

        except ValueError:

            raise ValueError ( f"RGB components must be integers: '{s}'" )

        # Validate that each value is in the range [0, 255].

        for v in values:
            if v < 0 or v > 255:
                raise ValueError ( f"RGB values must be in [0, 255], got {v}: '{s}'" )

        # Return the (R, G, B) tuple.

        return ( values [ 0 ], values [ 1 ], values [ 2 ] )


#-----------------------------------------------------------------------------------------------------------------------
# Class: TessellationRenderer
#
# Description:
#
#   Orchestrates the rendering pipeline for hexagonal tessellations.
#
#   Handles canvas creation, two-pass concentric stroke drawing, viewport culling, and anti-alias downsampling.
#
#-----------------------------------------------------------------------------------------------------------------------

class TessellationRenderer:

    # Anti-alias scale factors.

    _AA_SCALES: Dict [ str, int ] = {
        "off": 1,
        "low": 2,
        "medium": 4,
        "high": 8,
    }

    #-------------------------------------------------------------------------------------------------------------------
    # Function: render
    #
    # Description:
    #
    #   Render a hexagonal tessellation image.
    #
    # Arguments:
    #
    #   width:            Target image width in pixels.
    #   height:           Target image height in pixels.
    #   circumradius:     Hexagon circumradius R in pixels.
    #   margin:           Gap between hexagon edges in pixels.
    #   line_width:       Stroke width in pixels (0 = no outline).
    #   layers:           Number of concentric layers.
    #   color_fill:       Fill colour as (R, G, B).
    #   color_line:       Stroke colour as (R, G, B).
    #   color_background: Background colour as (R, G, B).
    #   antialias:        Anti-alias level ('off', 'low', 'medium', 'high').
    #   cull:             Whether to enable viewport culling.
    #
    # Returns:
    #
    #   A tuple of (PIL Image at target resolution, polygon count drawn).
    #
    #-------------------------------------------------------------------------------------------------------------------

    def render (
        self,
        width: int,
        height: int,
        circumradius: float,
        margin: float,
        line_width: int,
        layers: int,
        color_fill: Tuple [ int, int, int ],
        color_line: Tuple [ int, int, int ],
        color_background: Tuple [ int, int, int ],
        antialias: str,
        cull: bool,
    ) -> Tuple [ Image.Image, int ]:

        # Render a hexagonal tessellation image.

        k = self._AA_SCALES.get ( antialias, 1 )

        # Scale geometry for supersampling.

        sw       = width * k
        sh       = height * k
        sR       = circumradius * k
        s_margin = margin * k
        s_lw     = line_width * k

        R_s = sR + s_margin / 2.0

        # Auto-fill layers if needed.

        grid = AxialGrid ( spacing_radius = R_s )

        if layers == 0:
            layers = grid.auto_fill_layers ( sw, sh, R_s )

        # Generate grid cells.

        cells = grid.generate ( layers )

        # Convert to pixel centres.

        centres = [ grid.axial_to_pixel ( q, r, sw, sh ) for q, r in cells ]

        # Viewport culling.

        if cull:
            R_cull    = sR + s_lw / 2.0
            cull_geom = HexagonGeometry ( circumradius = R_cull )
            filtered  = []

            # Cull hexagons whose vertices are not all within the canvas bounds, accounting for stroke width.

            for cx, cy in centres:
                verts  = cull_geom.vertices ( cx, cy )
                inside = all ( 0 <= vx <= sw and 0 <= vy <= sh for vx, vy in verts )
                if inside:
                    filtered.append ( ( cx, cy ) )

            centres = filtered

        # Create canvas.

        img  = Image.new ( "RGB", ( sw, sh ), color_background )
        draw = ImageDraw.Draw ( img )

        polygon_count = 0

        # Two-pass rendering.

        if s_lw > 0:

            # Pass 1: outer fill (stroke colour).

            R_outer    = sR + s_lw / 2.0
            outer_geom = HexagonGeometry ( circumradius = R_outer )

            for cx, cy in centres:
                verts = outer_geom.vertices ( cx, cy )
                draw.polygon ( verts, fill = color_line )
                polygon_count += 1

            # Pass 2: inner fill (fill colour).

            R_inner = max ( sR - s_lw / 2.0, 0.0 )

            if R_inner > 0:
                inner_geom = HexagonGeometry ( circumradius = R_inner )

                # Draw inner polygons on top of the outer ones to create the stroke effect.
                # If R_inner is 0, skip this pass to avoid drawing degenerate polygons.

                for cx, cy in centres:
                    verts = inner_geom.vertices ( cx, cy )
                    draw.polygon ( verts, fill = color_fill )
                    polygon_count += 1
        else:

            # No outline: single fill pass at circumradius.

            fill_geom = HexagonGeometry ( circumradius = sR )

            for cx, cy in centres:
                verts = fill_geom.vertices ( cx, cy )
                draw.polygon ( verts, fill = color_fill )
                polygon_count += 1

        # Downsample if supersampled.

        if k > 1:
            img = img.resize ( ( width, height ), Image.LANCZOS )

        # Return the rendered image and the polygon count.

        return img, polygon_count


#-----------------------------------------------------------------------------------------------------------------------
# Class: SettingsManager
#
# Description:
#
#   JSON import/export of parameter sets with CLI-precedence logic.
#
#   Handles serialisation of settings to JSON files and loading them back with proper precedence: JSON overrides
#   defaults, explicit CLI args override JSON.
#
#-----------------------------------------------------------------------------------------------------------------------

class SettingsManager:

    # Keys that are persisted to JSON.

    _PERSISTED_KEYS: List [ str ] = [
        "width",
        "height",
        "circumradius",
        "margin",
        "line_width",
        "layers",
        "color_fill",
        "color_line",
        "color_background",
        "antialias",
        "file",
        "cull",
        "debug"
    ]

    #-------------------------------------------------------------------------------------------------------------------
    # Function: export_settings
    #
    # Description:
    #
    #   Export current parameters to a JSON file.
    #
    # Arguments:
    #
    #   params: The resolved argparse Namespace.
    #   path:   Output JSON file path.
    #
    # Raises:
    #
    #   IOError: If the file cannot be written.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def export_settings ( self, params: argparse.Namespace, path: str ) -> None:

        # Export current parameters to a JSON file.

        data: Dict = {}

        # Only include keys that are in the _PERSISTED_KEYS list, to avoid dumping extraneous argparse attributes.

        for key in self._PERSISTED_KEYS:
            val          = getattr ( params, key, None )
            data [ key ] = val

        # Write the data to the specified JSON file with indentation for readability.

        with open ( path, "w" ) as f:
            json.dump ( data, f, indent = 2 )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: import_settings
    #
    # Description:
    #
    #   Import settings from a JSON file.
    #
    # Arguments:
    #
    #   path: Path to the JSON settings file.
    #
    # Returns:
    #
    #   A dictionary of loaded settings.
    #
    # Raises:
    #
    #   FileNotFoundError: If the file does not exist.
    #   json.JSONDecodeError: If the file is not valid JSON.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def import_settings ( self, path: str ) -> Dict:

        # Import settings from a JSON file.

        with open ( path, "r" ) as f:
            data = json.load ( f )

        # return the loaded settings as a dictionary.

        return data

    #-------------------------------------------------------------------------------------------------------------------
    # Function: merge_settings
    #
    # Description:
    #
    #   Merge JSON settings with CLI args, respecting precedence.
    #
    #   JSON values override argparse defaults. Explicit CLI args override JSON values.
    #
    # Arguments:
    #
    #   defaults:      The argparse Namespace with default/CLI values.
    #   json_settings: Dictionary loaded from JSON.
    #   explicit_keys: Set of parameter names explicitly provided on CLI.
    #
    # Returns:
    #
    #   A merged argparse Namespace.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def merge_settings (
        self,
        defaults: argparse.Namespace,
        json_settings: Dict,
        explicit_keys: set,
    ) -> argparse.Namespace:

        # Merge JSON settings with CLI args, respecting precedence.

        for key in self._PERSISTED_KEYS:
            if key in json_settings and key not in explicit_keys:
                setattr ( defaults, key, json_settings [ key ] )

        # Return the merged argparse Namespace.

        return defaults


#-----------------------------------------------------------------------------------------------------------------------
# Function: _changelog_version
#
# Description:
#
#   Read the highest version from docs/CHANGELOG.md relative to the project root.
#
#   Scans for ``## [X.Y.Z]`` headings (skipping ``[Unreleased]``) and returns the first match, which is the highest
#   version. Returns fallback when the file is missing or contains no versioned headings (e.g. frozen .exe).
#
# Arguments:
#
#   fallback: Version string to return when no version is found.
#
# Returns:
#
#   The version string from CHANGELOG.md, or the fallback value.
#
#-----------------------------------------------------------------------------------------------------------------------

def _changelog_version ( fallback: str = "0.0.0" ) -> str:

    # Read the highest version from docs/CHANGELOG.md relative to the project root.

    changelog = os.path.join ( os.path.dirname ( os.path.dirname ( os.path.abspath ( __file__ ) ) ), "docs", "CHANGELOG.md" )

    try:

        # Scan for ``## [X.Y.Z]`` headings (skipping ``[Unreleased]``) and return the first match, which is the highest version.
        # Return fallback when the file is missing or contains no versioned headings (e.g. frozen .exe).

        with open ( changelog, "r", encoding = "utf-8" ) as fh:
            for line in fh:
                m = re.match ( r"^##\s+\[(\d+\.\d+\.\d+)\]", line )
                if m:
                    return m.group ( 1 )
    except OSError:
        pass

    # Return fallback when the file is missing or contains no versioned headings (e.g. frozen .exe).

    return fallback


#-----------------------------------------------------------------------------------------------------------------------
# Class: Application
#
# Description:
#
#   Top-level entry point for the HEX Grid Tessellator.
#
#   Orchestrates CLI argument parsing, settings loading, rendering, file output, and debug reporting.
#
#-----------------------------------------------------------------------------------------------------------------------

class Application:

    VERSION:      str = _changelog_version ( "3.1.0" )
    BUILD_DATE:   str = "2019-06-08"
    TITLE:        str = "HEX Grid Tessellator"
    AUTHOR:       str = "Rohin Gosling"
    BANNER_WIDTH: int = 60

    #-------------------------------------------------------------------------------------------------------------------
    # Function: run
    #
    # Description:
    #
    #   Execute the full application pipeline.
    #
    #   Parses CLI arguments, loads/exports settings, renders the tessellation, saves the output PNG, and prints debug
    #   information if enabled.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   None
    #
    #-------------------------------------------------------------------------------------------------------------------

    def run ( self ) -> None:

        # Execute the full application pipeline.

        # Step 1: Parse CLI arguments and detect explicit keys.

        args, explicit_keys = self._parse_args ()

        # Step 2: Import settings if requested.

        if args.import_settings:
            if not args.import_settings.lower ().endswith ( ".json" ):
                args.import_settings += ".json"
            try:
                manager   = SettingsManager ()
                json_data = manager.import_settings ( args.import_settings )
                args      = manager.merge_settings ( args, json_data, explicit_keys )
            except FileNotFoundError:
                print ( f"Error: Settings file not found: '{args.import_settings}'", file = sys.stderr )
                sys.exit ( 1 )
            except json.JSONDecodeError as e:
                print ( f"Error: Malformed JSON in settings file: {e}", file = sys.stderr )
                sys.exit ( 1 )

        # Step 3: Export settings if requested.

        if args.export_settings:

            # Ensure the export path has a .json extension for consistency, but don't modify the original argument since it may be used in debug output.
            #
            # - Append .json extension if not present, to ensure the file is saved with the correct format and to 
            #   avoid confusion. 
            #
            # - This does not modify args.export_settings, which retains the original user input for debug reporting.

            export_path = args.export_settings

            if not export_path.lower ().endswith ( ".json" ):
                export_path += ".json"

            # Export settings to the specified JSON file, handling any I/O errors that may occur.

            try:

                # Create a SettingsManager instance and export the current settings to the specified JSON file.
                # This will write the parameters to disk, and may raise an IOError if the file cannot be written (e.g. due to permissions issues or invalid path).

                manager = SettingsManager ()
                manager.export_settings ( args, export_path )

            except IOError as e:

                # Print the error message to stderr and exit with a non-zero status code if an I/O error occurs during export.

                print ( f"Error: Cannot write settings file: {e}", file = sys.stderr )
                sys.exit ( 1 )

        # Step 4: Parse colour strings.

        parser = ColorParser ()

        try:

            # Parse colour strings for fill, line, and background colours. This will raise ValueError if any string is invalid.

            color_fill       = parser.parse ( args.color_fill )
            color_line       = parser.parse ( args.color_line )
            color_background = parser.parse ( args.color_background )

        except ValueError as e:

            # Print the error message to stderr and exit with a non-zero status code.

            print ( f"Error: {e}", file = sys.stderr )
            sys.exit ( 1 )

        # Step 5: Auto-compute layers if layers == 0.
        # - If layers == 0, compute the minimum layers needed to cover the canvas using the axial grid's auto_fill_layers method.

        R_s           = args.circumradius + args.margin / 2.0
        layers        = args.layers
        auto_computed = False

        if layers == 0:

            grid          = AxialGrid ( spacing_radius = R_s )
            layers        = grid.auto_fill_layers ( args.width, args.height, R_s )
            auto_computed = True

        # Validate antialias level.

        valid_aa = { "off", "low", "medium", "high" }

        if args.antialias not in valid_aa:
            print ( f"Error: Invalid antialias level '{args.antialias}'. "
                    f"Must be one of: {', '.join ( sorted ( valid_aa ) )}", file = sys.stderr )
            sys.exit ( 1 )

        # Step 6-12: Render.

        renderer = TessellationRenderer ()

        img, polygon_count = renderer.render (
            width            = args.width,
            height           = args.height,
            circumradius     = args.circumradius,
            margin           = args.margin,
            line_width       = args.line_width,
            layers           = layers,
            color_fill       = color_fill,
            color_line       = color_line,
            color_background = color_background,
            antialias        = args.antialias,
            cull             = args.cull,
        )

        # Step 13: Ensure .png extension and save.

        out_file = args.file

        if not out_file.lower ().endswith ( ".png" ):
            out_file += ".png"

        img.save ( out_file, "PNG" )

        # Read file size.

        file_size = os.path.getsize ( out_file )

        # Banner (always shown).

        self._print_banner ()

        # Save confirmation (always shown, right after banner).

        size_str = self._format_file_size ( file_size )
        print ( f"  Saved: {out_file} ({size_str})" )

        if args.export_settings:
            export_path = args.export_settings
            if not export_path.lower ().endswith ( ".json" ):
                export_path += ".json"
            export_size_str = self._format_file_size ( os.path.getsize ( export_path ) )
            print ( f"  Saved: {export_path} ({export_size_str})" )

        # Step 14: Debug output.

        if args.debug:
            self._print_debug (
                args             = args,
                layers_resolved  = layers,
                auto_computed    = auto_computed,
                color_fill       = color_fill,
                color_line       = color_line,
                color_background = color_background,
                polygon_count    = polygon_count,
                out_file         = out_file,
                file_size        = file_size,
            )

        print ()

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _parse_args
    #
    # Description:
    #
    #   Parse CLI arguments and detect which were explicitly provided.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   A tuple of (parsed Namespace, set of explicitly-provided key names).
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _parse_args ( self ) -> Tuple [ argparse.Namespace, set ]:

        # Parse CLI arguments and detect which were explicitly provided.

        parser = self._build_parser ()
        args   = parser.parse_args ()

        # Second parse with SUPPRESS defaults to detect explicit keys.

        suppress_parser = self._build_parser ( suppress_defaults = True )
        explicit_args   = suppress_parser.parse_args ()
        explicit_keys   = set ( vars ( explicit_args ).keys () )

        return args, explicit_keys

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _build_parser
    #
    # Description:
    #
    #   Build the argparse ArgumentParser.
    #
    # Arguments:
    #
    #   suppress_defaults: If True, set all defaults to SUPPRESS to detect explicitly-provided CLI args.
    #
    # Returns:
    #
    #   A configured ArgumentParser.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _build_parser ( self, suppress_defaults: bool = False ) -> argparse.ArgumentParser:

        # Build the argparse ArgumentParser.

        S = argparse.SUPPRESS if suppress_defaults else None

        banner = self._banner_text ()

        # Inner parser class that prints the banner before help text.

        class _BannerParser ( argparse.ArgumentParser ):

            # Override print_help to include the banner at the top.

            def print_help ( self, file = None ):

                import sys as _sys

                if file is None:
                    file = _sys.stdout

                file.write ( banner + "\n\n" )
                super ().print_help ( file )

            # Override error to include the banner before the error message.

            def error ( self, message ):

                import sys as _sys

                _sys.stderr.write ( "\n" )
                self.print_usage ( _sys.stderr )
                _sys.stderr.write ( f"\n{self.prog}: error: {message}\n" )
                _sys.exit ( 2 )

        parser = _BannerParser (
            description = "HEX Grid Tessellator \u2014 generate hexagonal grid tessellation images.",
        )

        # Define CLI arguments with appropriate types, defaults, and help text.
        # - Use the same default value for all parameters when suppress_defaults is True, to simplify precedence logic in settings merging.
        # - The actual value doesn't matter since it will be overridden by JSON or CLI args, but it must be consistent across all parameters. 

        d = S  # shorthand

        parser.add_argument ( "--width", type = int, default = d if d else 1024, help = "Image width in pixels (default: 1024)" )
        parser.add_argument ( "--height", type = int, default = d if d else 768, help = "Image height in pixels (default: 768)" )
        parser.add_argument ( "--circumradius", type = float, default = d if d else 64.0, help = "Hexagon circumradius R in pixels (default: 64)" )
        parser.add_argument ( "--margin", type = float, default = d if d else 16.0, help = "Gap between hexagon edges in pixels (default: 16)" )
        parser.add_argument ( "--line_width", type = int, default = d if d else 8, help = "Stroke width in pixels, 0 = no outline (default: 8)" )
        parser.add_argument ( "--layers", type = int, default = d if d else 0, help = "Concentric layers, 0 = auto-fill (default: 0)" )
        parser.add_argument ( "--color_fill", type = str, default = d if d else "grey", help = "Hexagon fill colour (default: grey)" )
        parser.add_argument ( "--color_line", type = str, default = d if d else "black", help = "Hexagon outline colour (default: black)" )
        parser.add_argument ( "--color_background", type = str, default = d if d else "darkgrey", help = "Background colour (default: darkgrey)" )
        parser.add_argument ( "--antialias", type = str, default = d if d else "high", help = "Anti-alias level: off, low, medium, high (default: high)" )
        parser.add_argument ( "--file", type = str, default = d if d else "tessellation.png", help = "Output PNG filename (default: tessellation.png)" )
        parser.add_argument ( "--cull", type = self._parse_bool_flag, default = d if d else False, nargs = "?", const = True, help = "Enable viewport culling" )
        parser.add_argument ( "--debug", type = self._parse_bool_flag, default = d if d else False, nargs = "?", const = True, help = "Enable debug output" )
        parser.add_argument ( "--export_settings", type = str, default = None, help = "Export parameters to a JSON file" )
        parser.add_argument ( "--import_settings", type = str, default = None, help = "Import parameters from a JSON file" )

        # Return the configured ArgumentParser.

        return parser

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _parse_bool_flag
    #
    # Description:
    #
    #   Parse a boolean flag value ('true'/'false' or bare flag).
    #
    # Arguments:
    #
    #   value: String to interpret as boolean.
    #
    # Returns:
    #
    #   Boolean interpretation of the value.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _parse_bool_flag ( self, value: str ) -> bool:

        # Parse a boolean flag value ('true'/'false' or bare flag).

        if isinstance ( value, bool ):
            return value

        if value.lower () in ( "true", "1", "yes" ):
            return True

        if value.lower () in ( "false", "0", "no" ):
            return False

        # If we reach here, the value is not a valid boolean string.

        raise argparse.ArgumentTypeError ( f"Boolean value expected, got '{value}'" )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _banner_text
    #
    # Description:
    #
    #   Build the application banner as a string.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   The formatted banner string.
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _banner_text ( self ) -> str:

        # Build the application banner as a string.

        w     = self.BANNER_WIDTH
        inner = w - 2  # space between | and |

        # Construct the banner lines with box-drawing characters and formatted content.

        lines = [
            "\u250c" + "\u2500" * inner + "\u2510",
            f"\u2502{'  Program:    ' + self.TITLE:<{inner}}\u2502",
            f"\u2502{'  Version:    ' + self.VERSION:<{inner}}\u2502",
            f"\u2502{'  Build Date: ' + self.BUILD_DATE:<{inner}}\u2502",
            f"\u2502{'  Author:     ' + self.AUTHOR:<{inner}}\u2502",
            "\u2514" + "\u2500" * inner + "\u2518",
        ]

        # Return the formatted banner string.

        return "\n".join ( lines )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _print_banner
    #
    # Description:
    #
    #   Print the application banner to stdout.
    #
    # Arguments:
    #
    #   None
    #
    # Returns:
    #
    #   None
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _print_banner ( self ) -> None:

        # Print the application banner to stdout.

        print ( self._banner_text () )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _print_debug
    #
    # Description:
    #
    #   Print debug information to stdout.
    #
    # Arguments:
    #
    #   args:             The resolved parameters.
    #   layers_resolved:  The actual number of layers used.
    #   auto_computed:    Whether layers were auto-computed.
    #   color_fill:       Resolved fill colour.
    #   color_line:       Resolved line colour.
    #   color_background: Resolved background colour.
    #   polygon_count:    Number of polygons drawn.
    #   out_file:         Output PNG file path.
    #   file_size:        Output PNG file size in bytes.
    #
    # Returns:
    #
    #   None
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _print_debug (
        self,
        args: argparse.Namespace,
        layers_resolved: int,
        auto_computed: bool,
        color_fill: Tuple [ int, int, int ],
        color_line: Tuple [ int, int, int ],
        color_background: Tuple [ int, int, int ],
        polygon_count: int,
        out_file: str,
        file_size: int,
    ) -> None:

        # Print debug information to stdout.

        print ( f"\n  Image size:       {args.width} x {args.height}" )
        print ( f"  Circumradius:     {args.circumradius}" )
        print ( f"  Margin:           {args.margin}" )
        print ( f"  Line width:       {args.line_width}" )

        # Show the resolved number of layers, and indicate if it was auto-computed from 0.
        # - If layers were auto-computed from 0, indicate that in the debug output.

        layers_str = f"{layers_resolved}"

        if auto_computed:
            layers_str += f" (auto-computed from requested 0)"

        # Show the resolved number of layers, and indicate if it was auto-computed from 0.

        print ( f"  Layers:           {layers_str}" )
        print ( f"  Anti-alias:       {args.antialias}" )
        print ( f"  Cull:             {args.cull}" )
        print ( f"  Fill colour:      {args.color_fill} -> {color_fill}" )
        print ( f"  Line colour:      {args.color_line} -> {color_line}" )
        print ( f"  Background:       {args.color_background} -> {color_background}" )

        # Compute the centre pixel coordinates for reference in debug output. 

        cx, cy = args.width // 2, args.height // 2

        print ( f"  Centre pixel:     ({cx}, {cy})" )
        print ( f"  Polygons drawn:   {polygon_count}" )

        # Saved files.

        print ( f"  Saved: {out_file} ({self._format_file_size ( file_size )})" )

        # If settings were exported, show the export path and file size as well.

        if args.export_settings:

            # Ensure the export path has a .json extension for consistency in debug output, even if the user omitted it.

            export_path = args.export_settings

            # Ensure the export path has a .json extension for consistency in debug output, even if the user omitted it.

            if not export_path.lower ().endswith ( ".json" ):
                export_path += ".json"

            # Compute the export file size and format it for display. 

            export_size_str = self._format_file_size ( os.path.getsize ( export_path ) )
            print ( f"  Saved: {export_path} ({export_size_str})" )

    #-------------------------------------------------------------------------------------------------------------------
    # Function: _format_file_size
    #
    # Description:
    #
    #   Format a file size in human-readable form.
    #
    # Arguments:
    #
    #   size_bytes: File size in bytes.
    #
    # Returns:
    #
    #   Formatted string (e.g. '1.23 MB').
    #
    #-------------------------------------------------------------------------------------------------------------------

    def _format_file_size ( self, size_bytes: int ) -> str:

        # Format a file size in human-readable form.

        if size_bytes < 1024:

            # Return bytes with no decimal places for sizes under 1 KB.

            return f"{size_bytes} B"

        elif size_bytes < 1024 * 1024:

            # Return KB with 2 decimal places for sizes under 1 MB.

            return f"{size_bytes / 1024:.2f} KB"

        else:

            # Return MB with 2 decimal places for sizes 1 MB and above.

            return f"{size_bytes / ( 1024 * 1024 ):.2f} MB"


#-----------------------------------------------------------------------------------------------------------------------
# Function: main
#
# Description:
#
#   Main entry point for the HEX Grid Tessellator.
#
# Arguments:
#
#   None
#
# Returns:
#
#   None
#
#-----------------------------------------------------------------------------------------------------------------------

def main () -> None:

    # Main entry point for the HEX Grid Tessellator.

    if sys.stdout and hasattr ( sys.stdout, "reconfigure" ):
        sys.stdout.reconfigure ( encoding = "utf-8", errors = "replace" )

    # Create and run the application.

    app = Application ()
    app.run ()

if __name__ == "__main__":

    main ()
