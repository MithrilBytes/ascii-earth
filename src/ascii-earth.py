import numpy as np
import curses
import time
from datetime import datetime, timezone
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import shapely.geometry as sgeom

# ASCII shading characters for land and day/night effects
ASCII_SHADES = " .:-=+*#%@"

# Projection settings
ROTATION_SPEED = 3  # Slower rotation for stability
FRAME_DELAY = 0.05  # Faster refresh for smoother animation

# Cache landmass positions to avoid redundant computations
LAND_CACHE = {}

def lat_lon_to_screen(lat, lon, width, height, longitude_shift):
    """Maps lat/lon to screen coordinates manually, ensuring longitude wraps correctly."""
    lon_shifted = (lon + longitude_shift) % 360
    if lon_shifted > 180:
        lon_shifted -= 360  # Ensure longitude remains in valid range

    x = int(((lon_shifted + 180) / 360) * width) % width
    y = int(((90 - lat) / 180) * height)
    return x, max(0, min(y, height - 1))

def generate_globe(longitude_shift, width, height):
    """Generates an ASCII representation of the globe using real-world land features."""
    global LAND_CACHE  # Use cached data to speed up rendering

    if (width, height) in LAND_CACHE:
        land_cache = LAND_CACHE[(width, height)]
    else:
        land_cache = np.full((height, width), ' ', dtype=str)  # Empty globe

        # Load natural Earth land feature
        land_feature = cfeature.NaturalEarthFeature("physical", "land", "110m")
        land_shapes = list(land_feature.geometries())

        # Increase lat/lon sampling resolution for smoother landmasses
        lat_steps = np.linspace(-90, 90, height * 2)  # Twice the height resolution
        lon_steps = np.linspace(-180, 180, width * 2)  # Twice the width resolution

        for lat in lat_steps:
            for lon in lon_steps:
                point = sgeom.Point(lon, lat)

                # Check if the lat/lon is inside land
                if any(land.contains(point) for land in land_shapes):
                    x, y = lat_lon_to_screen(lat, lon, width, height, longitude_shift)
                    land_cache[y, x] = "#"  # Landmass marker

        LAND_CACHE[(width, height)] = land_cache  # Store computed land positions

    return np.copy(land_cache)  # Return a copy to avoid modifying the cache

def apply_day_night_shading(globe, longitude_shift, width):
    """Applies day/night shading based on the current UTC time."""
    now_utc = datetime.now(timezone.utc)
    sun_longitude = (now_utc.hour * 15) % 360  # Sun moves 15° per hour

    for y in range(len(globe)):
        for x in range(width):
            lon = ((x / width) * 360 - 180 + longitude_shift) % 360
            brightness = abs(lon - sun_longitude) / 180  # Distance from the sun
            shade_index = min(int(brightness * (len(ASCII_SHADES) - 1)), len(ASCII_SHADES) - 1)
            globe[y, x] = ASCII_SHADES[shade_index] if globe[y, x] != " " else " "

    return globe

def render_globe(stdscr):
    """Main rendering loop to display the ASCII globe with smooth refresh."""
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(int(FRAME_DELAY * 1000))
    longitude_shift = 0
    prev_globe_strings = None  # Store the previous frame for better refresh handling

    while True:
        height, width = stdscr.getmaxyx()
        width = max(20, min(width - 2, 80))  # Limit width to 80 max for detail
        height = max(10, min(height - 2, 40))  # Limit height to avoid overflow

        globe = generate_globe(longitude_shift, width, height)
        globe = apply_day_night_shading(globe, longitude_shift, width)

        globe_strings = ["".join(row) for row in globe]

        # Smooth Refresh: Only update changed rows instead of clearing everything
        if prev_globe_strings:
            for i, row in enumerate(globe_strings):
                if prev_globe_strings[i] != row:  # Only update if different
                    stdscr.move(i, 0)
                    stdscr.addstr(row[:width])
        else:
            for row in globe_strings:
                stdscr.addstr(row[:width] + "\n")

        stdscr.refresh()
        prev_globe_strings = globe_strings  # Store frame for comparison

        longitude_shift = (longitude_shift + ROTATION_SPEED) % 360
        time.sleep(FRAME_DELAY)
        
        if stdscr.getch() == ord('q'):  # Press 'q' to exit
            break

if __name__ == "__main__":
    curses.wrapper(render_globe)