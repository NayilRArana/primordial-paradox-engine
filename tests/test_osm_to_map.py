"""Tests for tools\\osm_to_map.py (MAP-OSM).

The rasteriser is measured on a SYNTHETIC way set, built from tile coordinates through the
grid's own projection, so the assertions do not depend on what OpenStreetMap returns and no
network is touched. The one test that exercises the cache stubs requests.post with a function
that raises, to prove a cached place never re-queries Overpass.
"""

from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import osm_to_map as om  # noqa: E402

BBOX = (51.5000, -0.0100, 51.5009, -0.0088)   # south, west, north, east, about 100x83 m


def way(way_id, tags, pts):
    return {"type": "way", "id": way_id, "tags": tags,
            "geometry": [{"lat": lat, "lon": lon} for lat, lon in pts]}


def latlon(grid, x, y):
    """Tile coordinates (float tiles, origin top left) back to (lat, lon)."""
    lat = grid.north - y * grid.metres_per_tile / grid.m_per_deg_lat
    lon = grid.west + x * grid.metres_per_tile / grid.m_per_deg_lon
    return lat, lon


def ring(grid, x0, y0, x1, y1):
    return [latlon(grid, x0, y0), latlon(grid, x1, y0), latlon(grid, x1, y1),
            latlon(grid, x0, y1), latlon(grid, x0, y0)]


def count_gid(tiles, name):
    gid = om.TERRAIN_GID[name]
    return sum(row.count(gid) for row in tiles)


# ---------------------------------------------------------------- classification

def test_classify_way_maps_every_class_the_card_names():
    cases = {
        "motorway": "road_major", "primary": "road_major", "secondary": "road_major",
        "tertiary": "road_minor", "residential": "road_minor", "service": "road_minor",
        "footway": "path", "path": "path",
    }
    for highway, expected in cases.items():
        got = om.classify_way({"highway": highway})
        assert got is not None, highway
        assert got[0] == expected, (highway, got)
    assert om.classify_way({"railway": "rail"})[0] == "rail"
    assert om.classify_way({"natural": "water"})[0] == "water"
    assert om.classify_way({"waterway": "river"})[0] == "water"
    assert om.classify_way({"leisure": "park"})[0] == "park"
    assert om.classify_way({"landuse": "grass"})[0] == "park"
    assert om.classify_way({"man_made": "quay"})[0] == "quay"
    assert om.classify_way({"man_made": "pier"})[0] == "quay"
    assert om.classify_way({"building": "yes"})[0] == "building"
    assert om.classify_way({"building": "house"})[0] == "building"
    assert om.classify_way({"building": "no"}) is None
    assert om.classify_way({"highway": "bus_stop"}) is None


def test_roads_are_one_or_two_tiles_wide():
    """A primary way strokes 2 tiles across, a residential one, measured across middle rows."""
    grid = om.Grid(BBOX)
    paths = [way(1, {"highway": "primary"}, [latlon(grid, 5.5, 2), latlon(grid, 5.5, 10)]),
             way(2, {"highway": "residential"}, [latlon(grid, 2.5, 2), latlon(grid, 2.5, 10)])]
    built = om.build_map(paths, BBOX)
    tiles = built["tiles"]
    major_gid = om.TERRAIN_GID["road_major"]
    minor_gid = om.TERRAIN_GID["road_minor"]
    for row in range(3, 10):
        assert tiles[row].count(major_gid) == 2, "primary road row %d is not 2 tiles wide" % row
        assert tiles[row].count(minor_gid) == 1, "residential road row %d is not 1 tile wide" % row
    columns = [x for x, v in enumerate(tiles[5]) if v == major_gid]
    assert columns == [5, 6], "the 2 tile road must be a solid band, got %s" % columns
    assert count_gid(tiles, "road_major") == 2 * len(
        [r for r in tiles if major_gid in r]), "no stray road tiles off the line"


def test_buildings_are_solid_blocks_with_one_door_on_the_street_side():
    grid = om.Grid(BBOX)
    elements = [
        way(10, {"building": "yes", "name": "synthetic block"}, ring(grid, 1, 1, 5, 4)),
        way(11, {"highway": "residential"}, [latlon(grid, 5.5, 0), latlon(grid, 5.5, 12)]),
    ]
    built = om.build_map(elements, BBOX)
    tiles = built["tiles"]
    building_gid = om.TERRAIN_GID["building"]
    door_gid = om.TERRAIN_GID["door"]
    # Solid block, not just an outline: the interior tile carries the building gid.
    assert tiles[2][2] == building_gid
    assert built["door_count"] == 1
    assert count_gid(tiles, "door") == 1
    doors = [(x, y) for y, row in enumerate(tiles) for x, v in enumerate(row) if v == door_gid]
    dx, dy = doors[0]
    # The door replaced a building tile and it touches the street.
    assert (dx - 1, dy) in [(x, y) for y, row in enumerate(tiles)
                            for x, v in enumerate(row) if v == building_gid]
    neighbours = [tiles[dy + oy][dx + ox] for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    assert om.TERRAIN_GID["road_minor"] in neighbours, "door must face the street"


def test_single_tile_buildings_get_no_door():
    grid = om.Grid(BBOX)
    small = ring(grid, 7.2, 7.2, 7.6, 7.6)
    built = om.build_map([way(20, {"building": "yes"}, small)], BBOX)
    assert built["door_count"] == 0


def test_water_and_quay_edges_are_cleaned():
    """A sub tile water sliver is dropped, a real pool stays, and no isolated edge tile is left."""
    grid = om.Grid(BBOX)
    elements = [
        way(30, {"natural": "water", "name": "sliver"}, ring(grid, 8.2, 8.2, 8.4, 8.4)),
        way(31, {"natural": "water", "name": "pool"}, ring(grid, 1, 6, 5, 10)),
        way(32, {"man_made": "quay"}, ring(grid, 1.2, 5.3, 1.6, 5.7)),
    ]
    built = om.build_map(elements, BBOX)
    tiles = built["tiles"]
    water_gid = om.TERRAIN_GID["water"]
    assert tiles[8][8] != water_gid, "isolated sub tile water island should be dropped"
    assert tiles[8][3] == water_gid, "the real pool must remain"
    assert count_gid(tiles, "quay") == 0, "isolated quay island should be dropped"
    for y, row in enumerate(tiles):
        for x, v in enumerate(row):
            if v == water_gid:
                around = [tiles[y + oy][x + ox] for ox in (-1, 0, 1) for oy in (-1, 0, 1)
                          if (ox or oy) and 0 <= x + ox < grid.width and 0 <= y + oy < grid.height]
                assert water_gid in around, "water edge left an isolated tile at %d,%d" % (x, y)


def test_quay_overrides_water_at_the_water_edge():
    grid = om.Grid(BBOX)
    elements = [
        way(40, {"natural": "water"}, ring(grid, 2, 2, 8, 8)),
        way(41, {"man_made": "quay"}, ring(grid, 4, 4, 10, 5)),
    ]
    built = om.build_map(elements, BBOX)
    tiles = built["tiles"]
    assert tiles[4][5] == om.TERRAIN_GID["quay"], "quay must sit over the water edge"
    assert tiles[2][2] == om.TERRAIN_GID["water"]


def test_railway_layer_is_drawn_under_the_roads():
    grid = om.Grid(BBOX)
    elements = [
        way(50, {"railway": "rail"}, [latlon(grid, 3.5, 0), latlon(grid, 3.5, 12)]),
        way(51, {"highway": "tertiary"}, [latlon(grid, 3.5, 5), latlon(grid, 8.5, 5)]),
    ]
    built = om.build_map(elements, BBOX)
    tiles = built["tiles"]
    assert tiles[5][3] == om.TERRAIN_GID["road_minor"], "road crosses over the railway"
    assert tiles[1][3] == om.TERRAIN_GID["rail"]


# ---------------------------------------------------------------- grid and outputs

def test_grid_is_about_eight_metres_per_tile_and_north_is_up():
    grid = om.Grid(BBOX)
    assert grid.metres_per_tile == om.METRES_PER_TILE
    assert grid.width == int(math.ceil(grid.width_m / 8.0))
    assert grid.height == int(math.ceil(grid.height_m / 8.0))
    assert grid.width * 8.0 >= grid.width_m
    x_north, y_north = grid.to_xy(grid.north, grid.west)
    assert (x_north, y_north) == (0.0, 0.0), "origin is the north west corner"
    assert "8.0 m per tile" in grid.size_report()


def test_write_place_writes_tiled_json_with_attribution_and_a_3x_preview(tmp_path):
    grid = om.Grid(BBOX)
    elements = [
        way(60, {"building": "yes"}, ring(grid, 1, 1, 5, 4)),
        way(61, {"highway": "residential"}, [latlon(grid, 5.5, 0), latlon(grid, 5.5, 12)]),
        way(62, {"natural": "water"}, ring(grid, 6, 6, 10, 10)),
    ]
    doc = {"elements": elements, "_pp_fetched_utc": "2026-10-21T00:00:00+00:00"}
    place = {"name": "synthetic", "bbox": BBOX}
    out = om.write_place("synthetic_place", place, doc, out_dir=str(tmp_path), log=lambda *a: None)
    assert os.path.exists(out["map"]) and os.path.exists(out["preview"])

    with open(out["map"], "r", encoding="utf-8") as fh:
        tiled = json.load(fh)
    props = {p["name"]: p["value"] for p in tiled["properties"]}
    assert "OpenStreetMap contributors" in props["attribution"]
    assert "ODbL" in props["attribution"]
    assert props["licence"].startswith("ODbL")
    assert props["map_size_tiles"] == "%dx%d" % (out["width"], out["height"])
    assert props["metres_per_tile"] == 8.0
    assert props["place"] == "synthetic"

    assert tiled["type"] == "map" and tiled["orientation"] == "orthogonal"
    assert tiled["width"] == out["width"] and tiled["height"] == out["height"]
    assert len(tiled["tilesets"]) == 1 and tiled["tilesets"][0]["firstgid"] == 1
    assert tiled["tilesets"][0]["tilecount"] == len(om.TERRAIN)
    layer = tiled["layers"][0]
    assert layer["type"] == "tilelayer"
    assert len(layer["data"]) == out["width"] * out["height"]
    assert set(layer["data"]) <= set(range(1, len(om.TERRAIN) + 1))
    assert layer["data"].count(om.TERRAIN_GID["building"]) > 0
    assert layer["data"].count(om.TERRAIN_GID["door"]) == 1

    from PIL import Image
    with Image.open(out["preview"]) as img:
        assert img.size == (out["width"] * om.TILE_PX * om.PREVIEW_SCALE,
                            out["height"] * om.TILE_PX * om.PREVIEW_SCALE)


def test_cached_place_never_re_queries_overpass(tmp_path, monkeypatch):
    cache = tmp_path / "osm_cache"
    cache.mkdir()
    doc = {"elements": [way(70, {"highway": "primary"}, [(51.5001, -0.0099), (51.5005, -0.0099)])],
           "_pp_fetched_utc": "2026-10-21T00:00:00+00:00"}
    with open(cache / "demo.json", "w", encoding="utf-8") as fh:
        json.dump(doc, fh)

    def boom(*a, **k):
        raise AssertionError("fetch_place must not touch the network on a cache hit")

    monkeypatch.setattr(om.requests, "post", boom)
    got = om.fetch_place("demo", BBOX, cache_dir=str(cache), log=lambda *a: None)
    assert got["elements"] == doc["elements"]


def test_overpass_query_is_one_query_per_place_and_carries_a_contact_agent():
    query = om.overpass_query(BBOX)
    assert query.count("51.500000,-0.010000,51.500900,-0.008800") == 11, \
        "every selector must use the same bbox in one query"
    assert "relation[\"natural\"=\"water\"]" in query, "water multipolygons must be requested"
    assert query.count("(") >= 11 and "out geom" in query
    assert "REPLACE_WITH_CONTACT" in om.USER_AGENT or "@" in om.USER_AGENT
    assert "openstreetmap" in om.ATTRIBUTION.lower() and "ODbL" in om.ATTRIBUTION


def test_final_clean_drops_water_specks_roads_and_buildings_cut_off():
    """Layers drawn after water can slice a river into a one or two tile speck."""
    water = om.TERRAIN_GID["water"]
    ground = om.GROUND_GID
    tiles = [[ground] * 12 for _ in range(12)]
    for y in range(9, 12):
        for x in range(12):
            tiles[y][x] = water            # a wide river along the bottom
    tiles[0][0] = water                    # a one tile speck
    tiles[0][1] = water                    # a two tile speck
    tiles[4][6] = water                    # a three tile puddle, kept
    tiles[4][7] = water
    tiles[5][6] = water
    removed = om.final_clean(tiles)
    assert tiles[0][0] == ground and tiles[0][1] == ground, "specks must go back to land"
    assert tiles[11][6] == water, "the river must survive"
    assert tiles[4][6] == water and tiles[5][7] != water, "a three tile puddle is above the limit"
    assert removed == {"water": 2}


def test_water_multipolygon_relation_is_stitched_and_filled():
    """Water in London and Southampton is a multipolygon relation split into untagged members."""
    grid = om.Grid(BBOX)
    corners = [latlon(grid, 2, 2), latlon(grid, 8, 2), latlon(grid, 8, 8), latlon(grid, 2, 8),
               latlon(grid, 2, 2)]
    members = [{"type": "way", "ref": 100 + i, "role": "outer",
                "geometry": [{"lat": la, "lon": lo} for la, lo in (corners[i], corners[i + 1])]}
               for i in range(4)]
    relation = {"type": "relation", "id": 900, "tags": {"type": "multipolygon",
                                                        "natural": "water"},
                "members": members}
    built = om.build_map([relation], BBOX)
    tiles = built["tiles"]
    water_gid = om.TERRAIN_GID["water"]
    assert tiles[5][5] == water_gid, "the stitched ring must be filled, not just outlined"
    assert count_gid(tiles, "water") > 20
    assert built["counted"].get("water_arearing") == 1

    # An unfinished chain is stroked as a line, never filled as a nonsense polygon.
    half = [{"type": "way", "ref": 1, "role": "outer",
             "geometry": [{"lat": la, "lon": lo}
                          for la, lo in (latlon(grid, 1, 1), latlon(grid, 4, 1))]}]
    rel2 = {"type": "relation", "id": 901,
            "tags": {"type": "multipolygon", "natural": "water"}, "members": half}
    built2 = om.build_map([rel2], BBOX)
    assert built2["counted"].get("water_areachain") == 1
    # A filled box of that corner would cover 36 tiles; a 2 tile stroke is a thin band.
    assert count_gid(built2["tiles"], "water") < 30, "a clipped chain must not fill the box"
    assert built2["tiles"][6][6] != water_gid, "the far interior must stay dry"


def test_three_real_places_are_declared_with_small_boxes():
    assert set(om.PLACES) == {"westminster_big_ben", "winchester_high_street",
                              "southampton_town_quay"}
    for slug, place in om.PLACES.items():
        s, w, n, e = place["bbox"]
        assert n > s and e > w, slug
        grid = om.Grid(place["bbox"])
        assert 20 <= grid.width <= 70 and 20 <= grid.height <= 70, (slug, grid.size_report())
        assert grid.width_m <= 600 and grid.height_m <= 600, (slug, grid.size_report())
