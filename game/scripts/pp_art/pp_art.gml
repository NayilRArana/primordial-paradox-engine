/// pp_art: the runtime side of the art lane.
/// The art lane (TS-A, TS-B, TS-C) writes one PNG plus one JSON per animation into game\sprites_src\title\.
/// tools\sync_art.py mirrors those PNGs into game\art\ and writes one index the engine reads at boot, so the
/// engine and the art lane never hardcode each other's file names twice.
/// An animation that is not in the index is simply not there: the caller draws a rectangle instead. That is how
/// the title screen works while the art is still landing.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\14-title-screen-drive.md and the GameMaker manual pages for sprite_add and draw_sprite_part.

/// Read one JSON file from the working directory. Returns undefined when the file is missing or unreadable.
function pp_art_read_json(_rel_path) {
    var _path = working_directory + _rel_path;
    if (!file_exists(_path)) return undefined;
    var _f = file_text_open_read(_path);
    if (_f < 0) return undefined;
    var _out = "";
    while (!file_text_eof(_f)) {
        _out += file_text_readln(_f);
        if (!file_text_eof(_f)) _out += "\n";
    }
    file_text_close(_f);
    try {
        return json_parse(_out);
    } catch (_e) {
        return undefined;
    }
}

/// Load every animation in the index. One sprite per PNG, loaded whole, and the frames inside a strip are
/// addressed by draw_sprite_part, so one file per animation is all the engine needs.
function pp_art_init() {
    var _art = { ok: false, animations: {}, names: [] };
    var _manifest = pp_art_read_json("art/title_manifest.json");
    if (is_undefined(_manifest) || !variable_struct_exists(_manifest, "animations")) {
        show_debug_message("PP art: no index at art/title_manifest.json, the title screen will draw plain bands");
        return _art;
    }
    var _rows = _manifest.animations;
    for (var i = 0; i < array_length(_rows); i += 1) {
        var _row = _rows[i];
        var _path = working_directory + "art/" + _row.file;
        if (!file_exists(_path)) {
            show_debug_message("PP art: missing " + _row.file);
            continue;
        }
        var _spr = sprite_add(_path, 1, false, false, 0, 0);
        if (_spr == -1) {
            show_debug_message("PP art: could not load " + _row.file);
            continue;
        }
        _art.animations[$ _row.name] = {
            sprite: _spr,
            frame_w: _row.frame_w,
            frame_h: _row.frame_h,
            frames: _row.frames,
            fps: _row.fps
        };
        array_push(_art.names, _row.name);
    }
    _art.ok = true;
    return _art;
}

/// The record for one animation, or undefined when it is not in the index.
function pp_art_info(_name) {
    if (!is_struct(global.pp) || !is_struct(global.pp.art)) return undefined;
    if (!variable_struct_exists(global.pp.art.animations, _name)) return undefined;
    return global.pp.art.animations[$ _name];
}

function pp_art_has(_name) {
    return !is_undefined(pp_art_info(_name));
}

/// The number of frames an animation really has, never more than the index says.
function pp_art_frames(_name) {
    var _info = pp_art_info(_name);
    if (is_undefined(_info)) return 0;
    return _info.frames;
}

/// The frame of an animation for a moment in time, wrapped into range. A still image is always frame 0.
function pp_art_frame_at(_name, _steps) {
    var _info = pp_art_info(_name);
    if (is_undefined(_info)) return 0;
    if (_info.frames <= 1) return 0;
    var _period = 60;
    if (_info.fps > 0) _period = max(1, round(60 / _info.fps));
    return floor(_steps / _period) mod _info.frames;
}

/// Draw one frame of an animation at a point, with a colour and an alpha.
function pp_art_draw(_name, _frame, _x, _y, _colour, _alpha) {
    var _info = pp_art_info(_name);
    if (is_undefined(_info)) return false;
    var _f = _frame;
    if (_f < 0) _f = 0;
    if (_f >= _info.frames) _f = _info.frames - 1;
    draw_sprite_part_ext(_info.sprite, 0, _f * _info.frame_w, 0, _info.frame_w, _info.frame_h,
                         _x, _y, 1, 1, _colour, _alpha);
    return true;
}

/// Draw a seamless layer, scrolled by a number of pixels, filling a view width. The layer is one image wider
/// than the view, so the wrap is drawn as two parts: the tail of the strip and then its head.
function pp_art_layer(_name, _frame, _y, _offset, _view_w, _view_h) {
    var _info = pp_art_info(_name);
    if (is_undefined(_info)) return false;
    var _w = _info.frame_w;
    var _off = _offset - floor(_offset / _w) * _w;
    if (_off < 0) _off += _w;
    var _src_x = _f_src_x(_name, _frame);
    var _first = min(_view_w, _w - _off);
    draw_sprite_part_ext(_info.sprite, 0, _src_x + _off, 0, _first, _view_h, 0, _y, 1, 1, c_white, 1);
    if (_first < _view_w) {
        draw_sprite_part_ext(_info.sprite, 0, _src_x, 0, _view_w - _first, _view_h, _first, _y, 1, 1, c_white, 1);
    }
    return true;
}

/// The source x of a frame inside its strip. A layer is a full frame wide, so frame 0 starts at 0.
function _f_src_x(_name, _frame) {
    var _info = pp_art_info(_name);
    if (is_undefined(_info)) return 0;
    var _f = _frame;
    if (_f < 0) _f = 0;
    if (_f >= _info.frames) _f = _info.frames - 1;
    return _f * _info.frame_w;
}
