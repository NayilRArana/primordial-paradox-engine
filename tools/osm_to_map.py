"""MAP-OSM: OpenStreetMap to Final Fantasy style 16x16 tile map drafts for three real places.

Data source: OpenStreetMap, fetched ONCE per place through the Overpass API and cached as raw
JSON under data\\osm_cache\\. OpenStreetMap data is ODbL 1.0: the attribution string is written
into every map file, and every console report. Google Maps and Street View are NOT used
(PLAN-V2-2026-10-21.md section 0: their terms forbid derived maps).

Pipeline: bbox -> one Overpass query -> classify ways and areas (roads by class, buildings,
water, parks, railways, quays) -> rasterise onto a 16x16 tile grid at about 8 m per tile ->
simplify to FF style (roads 1 to 2 tiles wide, buildings as solid blocks with one door tile on
the street side, water and quay edges cleaned of isolated tiles) -> Tiled JSON map + a 3x
preview PNG in flat placeholder colours.

Usage (from the project root):
    python tools\\osm_to_map.py                 # all three places (cache first, then fetch)
    python tools\\osm_to_map.py --place winchester_high_street
    python tools\\osm_to_map.py --refresh       # ignore the cache, re-query Overpass
    python tools\\osm_to_map.py --out <dir>     # write maps somewhere else (used by tests)

Importable API used by tests\\test_osm_to_map.py: build_map(elements, bbox, ...) is pure (no
network) and takes an Overpass shaped element list, so the rasteriser is tested on synthetic
way sets.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time

try:
    import requests
except ImportError:  # pragma: no cover - the fetch path needs it, the pure path does not
    requests = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CACHE_DIR = os.path.join(ROOT, "data", "osm_cache")
MAP_DIR = os.path.join(ROOT, "data", "maps", "osm")

TILE_PX = 16                  # tile size in pixels, same as the game's tiles
METRES_PER_TILE = 8.0         # about 8 m per tile as the card asks
PREVIEW_SCALE = 3             # the card's 3x preview rule

OVERPASS_URL = os.environ.get("PP_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
# Mirrors, tried only after the main endpoint fails. The usage policy says retry with
# exponential backoff when the server reports it is at capacity, so the plan below is a short
# backoff across at most two endpoints, not a hammer.
OVERPASS_MIRRORS = ["https://overpass-api.de/api/interpreter",
                    "https://overpass.kumi.systems/api/interpreter"]
BACKOFF_SECONDS = (0, 10, 30)
# Overpass usage policy: identify the client and give a contact. Replace the placeholder or set
# PP_OSM_CONTACT before any real bulk use.
CONTACT = os.environ.get("PP_OSM_CONTACT", "REPLACE_WITH_CONTACT_EMAIL")
USER_AGENT = "PrimordialParadox-osm-to-map/0.1 (contact: %s)" % CONTACT

ATTRIBUTION = ("(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, "
               "https://www.openstreetmap.org/copyright")

# Flat placeholder colours. The first entry is the base layer that fills the whole grid.
# Order here is the tileset order and the gid order (gid = index + 1).
TERRAIN = [
    ("ground",   "#6f7a56"),   # gid 1, paving and bare ground
    ("park",     "#4b7a34"),   # gid 2, parks, grass, gardens
    ("water",    "#3b6ea5"),   # gid 3, river, docks, basins
    ("quay",     "#8b7f6b"),   # gid 4, quays, piers, breakwaters
    ("rail",     "#5a4a3a"),   # gid 5, railways
    ("path",     "#a8a08c"),   # gid 6, footways and paths
    ("road_minor", "#8c8c8c"),  # gid 7, tertiary and below, 1 tile wide
    ("road_major", "#6e6e6e"),  # gid 8, motorway to secondary, 2 tiles wide
    ("building", "#c9c2a6"),   # gid 9, buildings
    ("door",     "#6b4a2f"),   # gid 10, one door tile per building on the street side
]
TERRAIN_GID = {name: i + 1 for i, (name, _) in enumerate(TERRAIN)}
TERRAIN_RGB = {name: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for name, h in TERRAIN}
GID_NAME = {gid: name for name, gid in TERRAIN_GID.items()}
GROUND_GID = TERRAIN_GID["ground"]

# Roads 1 to 2 tiles wide: the biggest classes get 2 tiles, the rest 1.
ROAD_MAJOR = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
              "secondary", "secondary_link"}
ROAD_MINOR = {"tertiary", "tertiary_link", "residential", "unclassified", "service",
              "living_street", "road"}
PATH_CLASS = {"footway", "path", "pedestrian", "steps", "cycleway", "bridleway", "track"}
RAIL_CLASS = {"rail", "light_rail", "tram", "narrow_gauge", "subway", "funicular"}
PARK_LEISURE = {"park", "garden", "common", "recreation_ground", "pitch", "nature_reserve",
                "village_green", "playground"}
PARK_LANDUSE = {"grass", "meadow", "forest", "village_green", "recreation_ground", "cemetery"}
WATER_AREA_TAGS = {("natural", "water"), ("waterway", "riverbank"), ("waterway", "dock"),
                   ("landuse", "reservoir"), ("natural", "bay"), ("water", "river")}
WATER_LINE_TAGS = {("waterway", "river"), ("waterway", "canal"), ("waterway", "stream"),
                   ("waterway", "ditch"), ("waterway", "drain")}
QUAY_TAGS = {("man_made", "quay"), ("man_made", "pier"), ("man_made", "breakwater"),
             ("man_made", "groyne"), ("highway", "quay"), ("waterway", "quay")}

# Draw order, lowest first. Every layer overwrites whatever is beneath it.
LAYER_ORDER = ["park", "water", "quay", "rail", "path", "road_minor", "road_major",
               "building", "door"]
# Layers whose edges must be clean (island and one tile hole removal) for the FF look.
CLEAN_LAYERS = ["water", "quay"]

PLACES = {
    "westminster_big_ben": {
        "name": "Westminster around Big Ben (London)",
        "bbox": (51.4992, -0.1282, 51.5024, -0.1212),   # south, west, north, east
    },
    "winchester_high_street": {
        "name": "Winchester High Street",
        "bbox": (51.0600, -1.3195, 51.0630, -1.3145),
    },
    "southampton_town_quay": {
        "name": "Southampton Town Quay",
        # Reaches about 190 m south of the quay road so Southampton Water is in the box: the
        # quay line needs water under it or the draft reads as a wall of brown.
        "bbox": (50.8938, -1.4070, 50.8978, -1.4010),
    },
}


# --------------------------------------------------------------------------------------
# Overpass: one query per place, cached
# --------------------------------------------------------------------------------------

def overpass_query(bbox):
    s, w, n, e = bbox
    box = "%f,%f,%f,%f" % (s, w, n, e)
    return ("[out:json][timeout:120];\n(\n"
            '  way["highway"](%s);\n'
            '  way["building"](%s);\n'
            '  way["waterway"](%s);\n'
            '  way["natural"](%s);\n'
            '  way["leisure"](%s);\n'
            '  way["landuse"](%s);\n'
            '  way["railway"](%s);\n'
            '  way["man_made"](%s);\n'
            '  relation["natural"="water"](%s);\n'
            '  relation["natural"="coastline"](%s);\n'
            '  relation["waterway"](%s);\n'
            ");\nout geom;\n" % ((box,) * 11))


def cache_path(slug, cache_dir=CACHE_DIR):
    return os.path.join(cache_dir, "%s.json" % slug)


def fetch_place(slug, bbox, refresh=False, cache_dir=CACHE_DIR, timeout=180, log=print):
    """Return the parsed Overpass response for one place, hitting the network at most once.

    The cache is data\\osm_cache\\<slug>.json. A cached file is reused unless refresh is set,
    which is what keeps us inside the Overpass usage policy across runs.
    """
    path = cache_path(slug, cache_dir)
    if os.path.exists(path) and not refresh:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        log("cache hit %s (%d elements)" % (path, len(doc.get("elements", []))))
        return doc
    if requests is None:
        raise RuntimeError("requests is not installed, cannot query Overpass")
    query = overpass_query(bbox)
    endpoints = [OVERPASS_URL] + [u for u in OVERPASS_MIRRORS if u != OVERPASS_URL]
    attempts = [(wait, url) for wait in BACKOFF_SECONDS for url in endpoints]
    doc = None
    last = None
    for attempt, (wait, url) in enumerate(attempts, 1):
        if wait:
            log("overpass backoff %ds before attempt %d" % (wait, attempt))
            time.sleep(wait)
        t0 = time.time()
        try:
            resp = requests.post(url, data={"data": query},
                                 headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if resp.status_code != 200:
                raise RuntimeError("Overpass HTTP %d: %s" % (resp.status_code,
                                                             resp.text[:200]))
            doc = resp.json()
            break
        except Exception as exc:  # noqa: BLE001 - reported, then retried with backoff
            last = exc
            log("overpass attempt %d on %s failed after %.1fs: %s"
                % (attempt, url, time.time() - t0, exc))
            doc = None
    if doc is None:
        raise RuntimeError("Overpass query failed for %s after %d attempts (cache %s): %s"
                           % (slug, len(attempts), path, last))
    doc["_pp_fetched_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    doc["_pp_query"] = query
    doc["_pp_bbox"] = list(bbox)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh)
        fh.write("\n")
    log("fetched %s in %.1fs: %d elements -> %s"
        % (slug, time.time() - t0, len(doc.get("elements", [])), path))
    return doc


# --------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------

def _has(tags, pairs):
    return any(tags.get(k) == v for k, v in pairs)


def classify_way(tags):
    """One way's tags to (kind, width in tiles) or None. Pure, so it is unit testable."""
    highway = tags.get("highway")
    if highway in ROAD_MAJOR:
        return ("road_major", 2)
    if highway in ROAD_MINOR:
        return ("road_minor", 1)
    if highway in PATH_CLASS:
        return ("path", 1)
    if tags.get("railway") in RAIL_CLASS:
        return ("rail", 2)
    if _has(tags, QUAY_TAGS):
        return ("quay", 2)
    if _has(tags, WATER_AREA_TAGS):
        return ("water", 2)
    if _has(tags, WATER_LINE_TAGS):
        river = tags.get("waterway") in ("river", "canal")
        return ("water", 2 if river else 1)
    if tags.get("natural") == "coastline":
        return ("water", 2)
    if tags.get("leisure") in PARK_LEISURE or tags.get("landuse") in PARK_LANDUSE:
        return ("park", 2)
    if tags.get("building") not in (None, "no"):
        return ("building", 1)
    return None


def _near(a, b, tol=1e-7):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _closes(chain, tol=1e-7):
    return len(chain) >= 4 and _near(chain[0], chain[-1], tol)


def stitch_rings(segments, tol=1e-7):
    """Chain member ways into closed rings. Returns (rings, open_chains).

    Water in London and Southampton is mapped as multipolygon RELATIONS whose outer ring is
    split into several untagged ways, so a ways only fetch gives a map with no river or dock at
    all (measured 2026-10-21: Southampton Town Quay returned 243 ways and zero water, which is a
    quay with no water). Members arrive with out geom, so chaining them here is enough. A chain
    that does not close is returned unfinished and is stroked as a line instead of filled, so a
    ring clipped by the bounding box never fills as a nonsense polygon.
    """
    segs = [s for s in segments if len(s) >= 2]
    rings = []
    open_chains = []
    used = [False] * len(segs)
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        chain = list(segs[i])
        closed = _closes(chain, tol)
        while not closed:
            matched = False
            for j in range(len(segs)):
                if used[j]:
                    continue
                head, tail = segs[j][0], segs[j][-1]
                if _near(chain[-1], head, tol):
                    chain.extend(segs[j][1:])
                elif _near(chain[-1], tail, tol):
                    chain.extend(list(reversed(segs[j]))[1:])
                elif _near(chain[0], tail, tol):
                    chain = list(segs[j])[:-1] + chain
                elif _near(chain[0], head, tol):
                    chain = list(reversed(segs[j]))[:-1] + chain
                else:
                    continue
                used[j] = True
                matched = True
                closed = _closes(chain, tol)
                break
            if not matched:
                break
        if closed:
            rings.append(chain)
        else:
            open_chains.append(chain)
    return rings, open_chains


def is_area(kind, closed):
    """Closed ways are areas for the fill layers; the rest are drawn as lines."""
    if not closed:
        return False
    return kind in ("park", "water", "quay", "building")


def classify(elements):
    """Split Overpass elements into {"ways": [(kind, width, closed, pts)], "counted": {...}}.

    pts is a list of (lat, lon). Geometry comes from out geom, so no node resolution is needed.
    Ways are classified by their own tags; multipolygon relations (natural=water and friends)
    are classified by the relation's tags and their outer members are stitched into rings.
    """
    ways = []
    counted = {}
    for el in elements or []:
        if el.get("type") == "relation":
            tags = el.get("tags") or {}
            kind = classify_way(tags)
            if kind is None:
                continue
            k, width = kind
            segs = []
            for member in el.get("members") or []:
                if member.get("type") != "way" or member.get("role") == "inner":
                    continue
                geom = member.get("geometry") or []
                pts = [(g["lat"], g["lon"]) for g in geom if g and "lat" in g and "lon" in g]
                if len(pts) >= 2:
                    segs.append(pts)
            if not segs:
                continue
            rings, open_chains = stitch_rings(segs)
            for ring in rings:
                ways.append((k, width, True, ring))
                key = k + "_arearing"
                counted[key] = counted.get(key, 0) + 1
            for chain in open_chains:
                ways.append((k, width, False, chain))
                key = k + "_areachain"
                counted[key] = counted.get(key, 0) + 1
            continue
        if el.get("type") != "way":
            continue
        tags = el.get("tags") or {}
        kind = classify_way(tags)
        if kind is None:
            continue
        geom = el.get("geometry") or []
        pts = [(g["lat"], g["lon"]) for g in geom if g and "lat" in g and "lon" in g]
        if len(pts) < 2:
            continue
        closed = len(pts) >= 4 and abs(pts[0][0] - pts[-1][0]) < 1e-9 \
            and abs(pts[0][1] - pts[-1][1]) < 1e-9
        k, width = kind
        ways.append((k, width, closed, pts))
        key = k + ("_area" if is_area(k, closed) else "_line")
        counted[key] = counted.get(key, 0) + 1
    return {"ways": ways, "counted": counted}


# --------------------------------------------------------------------------------------
# Rasterising
# --------------------------------------------------------------------------------------

class Grid:
    """A 16x16 tile grid over a lat/lon bounding box, about 8 m per tile, north up."""

    def __init__(self, bbox, metres_per_tile=METRES_PER_TILE):
        self.south, self.west, self.north, self.east = bbox
        self.metres_per_tile = float(metres_per_tile)
        lat_mid = math.radians((self.south + self.north) / 2.0)
        self.m_per_deg_lat = 111320.0
        self.m_per_deg_lon = 111320.0 * math.cos(lat_mid)
        self.width_m = (self.east - self.west) * self.m_per_deg_lon
        self.height_m = (self.north - self.south) * self.m_per_deg_lat
        self.width = max(1, int(math.ceil(self.width_m / self.metres_per_tile)))
        self.height = max(1, int(math.ceil(self.height_m / self.metres_per_tile)))

    def to_xy(self, lat, lon):
        """Tile space in float tiles, x east and y south, origin top left."""
        x = (lon - self.west) * self.m_per_deg_lon / self.metres_per_tile
        y = (self.north - lat) * self.m_per_deg_lat / self.metres_per_tile
        return x, y

    def size_report(self):
        return ("%dx%d tiles = %dx%d m at %.1f m per tile"
                % (self.width, self.height, round(self.width_m), round(self.height_m),
                   self.metres_per_tile))


def _stamp(tiles, tx, ty, width, gid):
    """Paint a width x width block anchored at (tx, ty).

    Odd widths centre on the sampled tile; width 2 starts at it and extends one tile in +x and
    +y, so a 2 tile road can run one tile past each end of its way. That overshoot is invisible
    in a draft map and keeping the anchor fixed makes the rasteriser deterministic.
    """
    off = (width - 1) // 2
    for dy in range(width):
        for dx in range(width):
            x = tx - off + dx
            y = ty - off + dy
            if 0 <= x < len(tiles[0]) and 0 <= y < len(tiles):
                tiles[y][x] = gid


def draw_line(tiles, grid, pts, width, gid):
    """Stroke a polyline, about width tiles thick, sampled in tile space."""
    for (lat0, lon0), (lat1, lon1) in zip(pts, pts[1:]):
        x0, y0 = grid.to_xy(lat0, lon0)
        x1, y1 = grid.to_xy(lat1, lon1)
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(steps + 1):
            t = i / float(steps)
            _stamp(tiles, int(math.floor(x0 + (x1 - x0) * t)),
                   int(math.floor(y0 + (y1 - y0) * t)), width, gid)


def fill_polygon(tiles, grid, pts, gid):
    """Fill a closed ring by scanline at tile centres, then stroke its edge so slivers show."""
    ring = [grid.to_xy(lat, lon) for lat, lon in pts]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    height = len(tiles)
    width = len(tiles[0])
    for ty in range(height):
        y_c = ty + 0.5
        xs = []
        for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
            if (y0 <= y_c < y1) or (y1 <= y_c < y0):
                xs.append(x0 + (y_c - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa, xb = xs[i], xs[i + 1]
            lo = max(0, int(math.floor(xa - 0.5)))
            hi = min(width - 1, int(math.ceil(xb - 0.5)))
            for tx in range(lo, hi + 1):
                if xa <= tx + 0.5 <= xb:
                    tiles[ty][tx] = gid
    draw_line(tiles, grid, pts if pts[0] == pts[-1] else pts + [pts[0]], 1, gid)


def _neighbours(tiles, tx, ty):
    out = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            x, y = tx + dx, ty + dy
            if 0 <= x < len(tiles[0]) and 0 <= y < len(tiles):
                out.append((x, y))
    return out


def clean_layer(tiles, snapshot, gid, fill_holes=True, drop_islands=True):
    """Water and quay edges: drop one tile islands, fill one tile holes.

    snapshot is the grid as it was before this layer was drawn, so a dropped island goes back
    to what was underneath instead of leaving a hole.
    """
    height = len(tiles)
    width = len(tiles[0])
    dropped = filled = 0
    if drop_islands:
        for ty in range(height):
            for tx in range(width):
                if tiles[ty][tx] == gid:
                    if not any(tiles[y][x] == gid for x, y in _neighbours(tiles, tx, ty)):
                        tiles[ty][tx] = snapshot[ty][tx]
                        dropped += 1
    if fill_holes:
        for ty in range(height):
            for tx in range(width):
                if tiles[ty][tx] != gid:
                    n = _neighbours(tiles, tx, ty)
                    same = sum(1 for x, y in n if tiles[y][x] == gid)
                    if len(n) >= 8 and same >= 7:
                        tiles[ty][tx] = gid
                        filled += 1
    return {"dropped_islands": dropped, "filled_holes": filled}


def component_tiles(tiles, gid):
    """4 connected components of one gid, as lists of (tx, ty)."""
    seen = set()
    comps = []
    height = len(tiles)
    width = len(tiles[0])
    for ty in range(height):
        for tx in range(width):
            if tiles[ty][tx] != gid or (tx, ty) in seen:
                continue
            stack = [(tx, ty)]
            seen.add((tx, ty))
            comp = []
            while stack:
                x, y = stack.pop()
                comp.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen \
                            and tiles[ny][nx] == gid:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            comps.append(comp)
    return comps


SMALL_ISLAND_MAX = 2


def final_clean(tiles, layers=("water", "quay"), max_size=SMALL_ISLAND_MAX):
    """Drop water and quay slivers that the layers drawn on top cut off.

    clean_layer runs while each layer is being drawn, but rail, roads and buildings come later
    and can slice a river or a quay into one or two tile specks. Each component at or below
    max_size goes back to the commonest land tile beside it, so no lone blue pixel is left on
    the pavement. Returns {layer: tiles changed}.
    """
    dropped = {}
    excluded = {TERRAIN_GID["water"], TERRAIN_GID["quay"], TERRAIN_GID["door"]}
    for name in layers:
        gid = TERRAIN_GID[name]
        changed = 0
        for comp in component_tiles(tiles, gid):
            if len(comp) > max_size:
                continue
            for tx, ty in comp:
                keep = [tiles[y][x] for x, y in _neighbours(tiles, tx, ty)
                        if tiles[y][x] not in excluded]
                tiles[ty][tx] = max(sorted(keep), key=keep.count) if keep else GROUND_GID
                changed += 1
        if changed:
            dropped[name] = changed
    return dropped


def place_doors(tiles):
    """One door tile per building, on the street side.

    For each building component, the door goes on the candidate tile that touches the most road
    tiles (footways count as street), ties broken by topmost then leftmost so the result is
    deterministic. Single tile buildings keep their block and get no door.
    """
    door_gid = TERRAIN_GID["door"]
    street_gids = {TERRAIN_GID["road_major"], TERRAIN_GID["road_minor"],
                   TERRAIN_GID["path"], TERRAIN_GID["door"]}
    placed = 0
    for comp in component_tiles(tiles, TERRAIN_GID["building"]):
        if len(comp) < 2:
            continue
        best = None
        for tx, ty in comp:
            roads = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= tx + dx < len(tiles[0]) and 0 <= ty + dy < len(tiles)
                        and tiles[ty + dy][tx + dx] in street_gids)
            if roads:
                key = (-roads, ty, tx)
                if best is None or key < best[0]:
                    best = (key, tx, ty)
        if best is not None:
            _, tx, ty = best
            tiles[ty][tx] = door_gid
            placed += 1
    return placed


def build_map(elements, bbox, metres_per_tile=METRES_PER_TILE):
    """Rasterise the classified ways onto a tile grid. Pure: no network, no files.

    Returns {"grid", "tiles", "stats", "counted", "door_count"}.
    """
    grid = Grid(bbox, metres_per_tile)
    tiles = [[GROUND_GID] * grid.width for _ in range(grid.height)]
    classified = classify(elements)
    ways = classified["ways"]
    stats = {}
    for layer in LAYER_ORDER:
        if layer == "door":
            continue
        gid = TERRAIN_GID[layer]
        snapshot = [row[:] for row in tiles]
        drawn = 0
        for kind, width, closed, pts in ways:
            if kind != layer:
                continue
            if is_area(kind, closed):
                fill_polygon(tiles, grid, pts, gid)
            else:
                draw_line(tiles, grid, pts, width, gid)
            drawn += 1
        if layer in CLEAN_LAYERS and drawn:
            stats["clean_" + layer] = clean_layer(tiles, snapshot, gid)
        stats["ways_" + layer] = drawn
    removed = final_clean(tiles)
    if removed:
        stats["final_clean"] = removed
    door_count = place_doors(tiles)
    return {"grid": grid, "tiles": tiles, "stats": stats,
            "counted": classified["counted"], "door_count": door_count}


# --------------------------------------------------------------------------------------
# Output: Tiled JSON, tileset PNG, 3x preview PNG
# --------------------------------------------------------------------------------------

def tileset_columns(count=len(TERRAIN)):
    return count


def write_tileset_png(path):
    from PIL import Image
    cols = tileset_columns()
    img = Image.new("RGB", (cols * TILE_PX, TILE_PX))
    for i, (name, _hex) in enumerate(TERRAIN):
        colour = TERRAIN_RGB[name]
        for y in range(TILE_PX):
            for x in range(TILE_PX):
                img.putpixel((i * TILE_PX + x, y), colour)
    img.save(path)
    return path


def write_preview_png(path, tiles, scale=PREVIEW_SCALE, grid_lines=True):
    """The 3x preview: flat placeholder colours, one thin separator line per tile edge."""
    from PIL import Image
    height = len(tiles)
    width = len(tiles[0])
    p = TILE_PX * scale
    img = Image.new("RGB", (width * p, height * p), TERRAIN_RGB["ground"])
    line = (40, 36, 30)
    for ty in range(height):
        for tx in range(width):
            name = GID_NAME.get(tiles[ty][tx], "ground")
            colour = TERRAIN_RGB[name]
            for y in range(ty * p, (ty + 1) * p):
                for x in range(tx * p, (tx + 1) * p):
                    img.putpixel((x, y), colour)
    if grid_lines:
        for tx in range(width + 1):
            x = min(tx * p, width * p - 1)
            for y in range(height * p):
                img.putpixel((x, y), line)
        for ty in range(height + 1):
            y = min(ty * p, height * p - 1)
            for x in range(width * p):
                img.putpixel((x, y), line)
    img.save(path)
    return path


def tiled_document(tiles, grid, place_name, bbox, fetched_utc, tileset_image):
    """A Tiled JSON map: one terrain tile layer plus the OSM attribution and provenance."""
    height = len(tiles)
    width = len(tiles[0])
    flat = []
    for row in tiles:
        flat.extend(row)
    counted = {}
    for gid in sorted(set(flat)):
        name = GID_NAME.get(gid, "unknown")
        counted[name] = counted.get(name, 0) + flat.count(gid)
    return {
        "type": "map",
        "version": "1.10",
        "tiledversion": "1.11.0",
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "infinite": False,
        "width": width,
        "height": height,
        "tilewidth": TILE_PX,
        "tileheight": TILE_PX,
        "nextlayerid": 3,
        "nextobjectid": 1,
        "tilesets": [{
            "firstgid": 1,
            "name": "pp_osm_placeholder",
            "image": tileset_image,
            "imagewidth": tileset_columns() * TILE_PX,
            "imageheight": TILE_PX,
            "tilewidth": TILE_PX,
            "tileheight": TILE_PX,
            "tilecount": len(TERRAIN),
            "columns": tileset_columns(),
            "margin": 0,
            "spacing": 0,
        }],
        "layers": [{
            "id": 1,
            "name": "terrain",
            "type": "tilelayer",
            "visible": True,
            "opacity": 1,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "data": flat,
        }],
        "properties": [
            {"name": "attribution", "type": "string", "value": ATTRIBUTION},
            {"name": "licence", "type": "string", "value": "ODbL 1.0 (OpenStreetMap)"},
            {"name": "source", "type": "string",
             "value": "OpenStreetMap via the Overpass API, fetched %s" % fetched_utc},
            {"name": "place", "type": "string", "value": place_name},
            {"name": "bbox_south_west_north_east", "type": "string",
             "value": ",".join("%.6f" % v for v in bbox)},
            {"name": "metres_per_tile", "type": "float", "value": grid.metres_per_tile},
            {"name": "map_size_tiles", "type": "string",
             "value": "%dx%d" % (width, height)},
            {"name": "tile_counts", "type": "string",
             "value": json.dumps(counted, sort_keys=True)},
        ],
    }


def write_place(slug, place, doc, out_dir=MAP_DIR, metres_per_tile=METRES_PER_TILE,
                log=print):
    os.makedirs(out_dir, exist_ok=True)
    built = build_map(doc.get("elements", []), place["bbox"], metres_per_tile)
    grid = built["grid"]
    tiles = built["tiles"]
    tileset_name = "%s_tileset.png" % slug
    map_name = "%s.json" % slug
    preview_name = "%s_preview_3x.png" % slug
    write_tileset_png(os.path.join(out_dir, tileset_name))
    write_preview_png(os.path.join(out_dir, preview_name), tiles)
    tiled = tiled_document(tiles, grid, place["name"], place["bbox"],
                           doc.get("_pp_fetched_utc", "unknown"), tileset_name)
    map_path = os.path.join(out_dir, map_name)
    with open(map_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(tiled, fh, indent=1)
        fh.write("\n")
    log("MAP %s: %s" % (slug, grid.size_report()))
    log("  ways: %s" % json.dumps(built["counted"], sort_keys=True))
    log("  doors: %d, clean: %s" % (built["door_count"],
                                    json.dumps({k: v for k, v in built["stats"].items()
                                                if k.startswith("clean_")}, sort_keys=True)))
    log("  wrote %s" % map_path)
    log("  wrote %s" % os.path.join(out_dir, preview_name))
    log("  attribution: %s" % ATTRIBUTION)
    return {"slug": slug, "map": map_path, "preview": os.path.join(out_dir, preview_name),
            "tileset": os.path.join(out_dir, tileset_name),
            "width": grid.width, "height": grid.height,
            "size_report": grid.size_report(), "stats": built["stats"],
            "counted": built["counted"], "doors": built["door_count"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="OpenStreetMap to FF style tile map drafts")
    ap.add_argument("--place", action="append", default=None,
                    help="place slug, repeatable (default: all)")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-query")
    ap.add_argument("--out", default=MAP_DIR, help="output directory for maps and previews")
    ap.add_argument("--cache", default=CACHE_DIR, help="cache directory for raw Overpass JSON")
    ap.add_argument("--list", action="store_true", help="list the places and exit")
    args = ap.parse_args(argv)

    if args.list:
        for slug, place in PLACES.items():
            print("%s: %s bbox=%s" % (slug, place["name"], place["bbox"]))
        return 0

    slugs = args.place or list(PLACES)
    unknown = [s for s in slugs if s not in PLACES]
    if unknown:
        print("unknown place(s): %s" % ", ".join(unknown))
        return 2
    results = []
    for slug in slugs:
        place = PLACES[slug]
        doc = fetch_place(slug, place["bbox"], refresh=args.refresh, cache_dir=args.cache)
        results.append(write_place(slug, place, doc, out_dir=args.out))
    print("")
    print("done: %d map(s)" % len(results))
    for r in results:
        print("  %-24s %-38s %s" % (r["slug"], r["size_report"], r["map"]))
    print("attribution written into every map: %s" % ATTRIBUTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
