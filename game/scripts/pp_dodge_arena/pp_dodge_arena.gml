/// pp_dodge_arena: the box, the marker and the fairness rules (spec 08).
/// Hazards are structs in one array, not instances, so a whole phase can be simulated by the data checker and by the
/// debug preview. Geometry comes from pp_config so no number is repeated here.
/// Provenance: knowledge\PROVENANCE.md, entry "battle state machine and turn loop".

/// Inclusive box bounds in frame coordinates.
function pp_arena_geometry() {
    var _x1 = PP_ARENA_CX - PP_ARENA_W * 0.5;
    var _y1 = PP_ARENA_CY - PP_ARENA_H * 0.5;
    return { x1: _x1, y1: _y1, x2: _x1 + PP_ARENA_W, y2: _y1 + PP_ARENA_H };
}

/// The one conversion from a data recipe angle to a GameMaker direction, and the only place either handedness is named.
/// A data recipe is written the way an artist reads the box on the screen: 0 right, 90 down, 180 left, 270 up, so a
/// positive turn is clockwise. GameMaker directions run the other way: 0 right, 90 up, 180 left, 270 down (the manual's
/// direction page states it, checked 2026-10-19), so the two differ by a mirror. Every degree a recipe states passes
/// through here exactly once, at spawn:
/// - frame.angle (plus spread) is converted here,
/// - frame.curve is negated here, because a positive curve means clockwise on screen while adding to a GameMaker
///   direction turns counter-clockwise. The hazard carries the already converted curve.
/// `aim` is exempt: point_direction reads screen coordinates and already returns a GameMaker direction.
function pp_angle_to_gm(_data_angle) {
    return ((360 - (_data_angle mod 360)) mod 360);
}

/// A fresh arena for one pattern. The marker starts centred every phase (spec 08 geometry).
function pp_arena_new(_pattern, _seed, _attack_value) {
    var _g = pp_arena_geometry();
    var _cx = PP_ARENA_CX - PP_MARKER_SIZE * 0.5;
    var _cy = PP_ARENA_CY - PP_MARKER_SIZE * 0.5;
    return {
        pattern: _pattern,
        geometry: _g,
        emitter: pp_recipe_begin(_pattern, _seed),
        warn_steps: PP_ARENA_WARN_STEPS,
        phase_steps: 0,
        hazards: [],
        marker: { x: _cx, y: _cy, inv: 0, trail: [] },
        hit_flash: 0,
        hits: 0,
        cleared: false,
        ended: false,
        capped: false,
        attack: _attack_value
    };
}

/// Marker centre in frame coordinates.
function pp_arena_marker_centre(_arena) {
    return {
        x: _arena.marker.x + PP_MARKER_SIZE * 0.5,
        y: _arena.marker.y + PP_MARKER_SIZE * 0.5
    };
}

function pp_arena_add_hazard(_arena, _hz) {
    if (!variable_struct_exists(_hz, "outside_steps")) _hz.outside_steps = 0;
    array_push(_arena.hazards, _hz);
    return _hz;
}

/// Fairness rule 2 (spec 08): no hazard appears within 24 pixels of the marker. A spawn that would break it is pushed
/// away from the marker to exactly the exclusion radius, which keeps the recipe's shape intent without a silent skip.
function pp_arena_fit_spawn(_arena, _x, _y, _size) {
    var _m = pp_arena_marker_centre(_arena);
    var _hx = _x + _size * 0.5;
    var _hy = _y + _size * 0.5;
    var _d = point_distance(_m.x, _m.y, _hx, _hy);
    if (_d >= PP_SPAWN_EXCLUSION) return { x: _x, y: _y };

    if (_d < 0.001) {
        return { x: _x, y: _y - PP_SPAWN_EXCLUSION };
    }
    var _dir = point_direction(_m.x, _m.y, _hx, _hy);
    return {
        x: _m.x + lengthdir_x(PP_SPAWN_EXCLUSION, _dir) - _size * 0.5,
        y: _m.y + lengthdir_y(PP_SPAWN_EXCLUSION, _dir) - _size * 0.5
    };
}

/// Effective position of a hazard, including its wobble. Collision and drawing both use this, never the raw position.
/// The wobble offset is perpendicular to travel; a sine swings both ways, so the sign of the quarter turn does not
/// change the path and `dir + 90` stays in GameMaker terms.
function pp_arena_hazard_pos(_hz) {
    if (_hz.wobble_amp <= 0 || _hz.wobble_period <= 0) return { x: _hz.x, y: _hz.y };
    var _wob = sin(_hz.age * 360 / _hz.wobble_period) * _hz.wobble_amp;
    return {
        x: _hz.x + lengthdir_x(_wob, _hz.dir + 90),
        y: _hz.y + lengthdir_y(_wob, _hz.dir + 90)
    };
}

/// One step of the phase. Returns {hit, cleared, ended}.
/// The director applies the health loss, so the arena never touches the party.
function pp_arena_step(_arena, _vx, _vy) {
    if (_arena.ended) return { hit: false, cleared: _arena.cleared, ended: true };

    _arena.phase_steps += 1;

    if (_arena.warn_steps > 0) {
        _arena.warn_steps -= 1;
        return { hit: false, cleared: false, ended: false };
    }

    pp_arena_move_marker(_arena, _vx, _vy);
    pp_recipe_step(_arena.emitter, _arena);
    pp_arena_move_hazards(_arena);

    var _hit_now = pp_arena_check_hit(_arena);
    if (_hit_now) {
        _arena.hits += 1;
        _arena.hit_flash = 6;
        _arena.marker.inv = PP_INVULN_STEPS;
    }

    if (_arena.hit_flash > 0) _arena.hit_flash -= 1;
    if (_arena.marker.inv > 0) _arena.marker.inv -= 1;

    var _by_cap = (_arena.phase_steps >= PP_ARENA_CAP_STEPS);
    var _by_content = _arena.emitter.done && pp_arena_live_hazards(_arena) == 0;
    if (_by_cap || _by_content) {
        _arena.ended = true;
        _arena.capped = _by_cap;
        _arena.cleared = (_arena.hits == 0) && !_by_cap;
    }

    return { hit: _hit_now, cleared: _arena.cleared, ended: _arena.ended };
}

function pp_arena_move_marker(_arena, _vx, _vy) {
    var _g = _arena.geometry;
    var _m = _arena.marker;
    _m.x += _vx * PP_MARKER_SPEED;
    _m.y += _vy * PP_MARKER_SPEED;
    var _maxx = _g.x2 - PP_MARKER_SIZE;
    var _maxy = _g.y2 - PP_MARKER_SIZE;
    _m.x = clamp(_m.x, _g.x1, _maxx);
    _m.y = clamp(_m.y, _g.y1, _maxy);

    // Four step trail, newest first, snapped for drawing.
    var _trail = [{ x: floor(_m.x), y: floor(_m.y) }];
    for (var i = 0; i < min(3, array_length(_m.trail)); i++) array_push(_trail, _m.trail[i]);
    _m.trail = _trail;
}

function pp_arena_move_hazards(_arena) {
    var _g = _arena.geometry;
    var _keep = [];
    for (var i = 0; i < array_length(_arena.hazards); i++) {
        var _hz = _arena.hazards[i];
        if (!_hz.alive) continue;

        _hz.speed = max(0, _hz.speed + _hz.accel);
        // dir and curve are already in GameMaker terms: pp_recipe_spawn converted them once (pp_angle_to_gm).
        _hz.dir += _hz.curve;
        _hz.x += lengthdir_x(_hz.speed, _hz.dir);
        _hz.y += lengthdir_y(_hz.speed, _hz.dir);
        _hz.age += 1;

        // A hazard leaves when its life runs out, or when it has been fully off the arena for 12 steps.
        var _outside = (_hz.x + _hz.size < _g.x1) || (_hz.x > _g.x2) || (_hz.y + _hz.size < _g.y1) || (_hz.y > _g.y2);
        _hz.outside_steps = _outside ? (_hz.outside_steps + 1) : 0;

        if (_hz.age >= _hz.life || _hz.outside_steps > 12) {
            _hz.alive = false;
            continue;
        }
        array_push(_keep, _hz);
    }
    _arena.hazards = _keep;
}

function pp_arena_live_hazards(_arena) {
    var _n = 0;
    for (var i = 0; i < array_length(_arena.hazards); i++) {
        if (_arena.hazards[i].alive) _n += 1;
    }
    return _n;
}

/// Two pixel inset per side, on both the hazard and the marker (spec 08 geometry).
function pp_arena_check_hit(_arena) {
    if (_arena.marker.inv > 0) return false;
    var _m = pp_arena_marker_centre(_arena);
    var _mh = PP_MARKER_SIZE * 0.5 - PP_HITBOX_INSET;
    for (var i = 0; i < array_length(_arena.hazards); i++) {
        var _hz = _arena.hazards[i];
        if (!_hz.alive) continue;
        var _p = pp_arena_hazard_pos(_hz);
        var _hc = { x: _p.x + _hz.size * 0.5, y: _p.y + _hz.size * 0.5 };
        var _hh = _hz.size * 0.5 - PP_HITBOX_INSET;
        if (abs(_hc.x - _m.x) < (_hh + _mh) && abs(_hc.y - _m.y) < (_hh + _mh)) return true;
    }
    return false;
}

/// Draw the whole phase: dim, frame, hazards, marker, warning flashes, clear text.
function pp_arena_draw(_arena) {
    var _g = _arena.geometry;

    draw_set_alpha(0.6);
    draw_set_colour(pp_role_colour("ink"));
    draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false);
    draw_set_alpha(1);

    var _frame_colour = pp_role_colour("ink");
    if (_arena.warn_steps > 0 && (_arena.warn_steps div 3) mod 2 == 0) _frame_colour = pp_role_colour("warn");
    if (_arena.hit_flash > 0 && (_arena.hit_flash div 2) mod 2 == 0) _frame_colour = pp_role_colour("hazard");

    draw_set_colour(pp_role_colour("dim"));
    draw_rectangle(_g.x1 - 2, _g.y1 - 2, _g.x2 + 2, _g.y2 + 2, true);
    draw_set_colour(_frame_colour);
    draw_rectangle(_g.x1 - 1, _g.y1 - 1, _g.x2 + 1, _g.y2 + 1, true);

    var _hazard_colour = pp_role_colour("hazard");
    for (var i = 0; i < array_length(_arena.hazards); i++) {
        var _hz = _arena.hazards[i];
        if (!_hz.alive) continue;
        var _p = pp_arena_hazard_pos(_hz);
        draw_set_colour(_hazard_colour);
        draw_rectangle(floor(_p.x), floor(_p.y), floor(_p.x + _hz.size) - 1, floor(_p.y + _hz.size) - 1, false);
    }

    // Trail first, then the marker, so the marker is always the brightest thing on screen (spec 08 goal).
    for (var t = array_length(_arena.marker.trail) - 1; t >= 1; t--) {
        var _tr = _arena.marker.trail[t];
        draw_set_colour(pp_role_colour("marker_trail"));
        draw_rectangle(_tr.x, _tr.y, _tr.x + PP_MARKER_SIZE - 1, _tr.y + PP_MARKER_SIZE - 1, false);
    }

    var _blink = (_arena.marker.inv > 0) && ((_arena.marker.inv div 4) mod 2 == 0);
    if (!_blink) {
        draw_set_colour(pp_role_colour("marker"));
        var _mx = floor(_arena.marker.x);
        var _my = floor(_arena.marker.y);
        draw_rectangle(_mx, _my, _mx + PP_MARKER_SIZE - 1, _my + PP_MARKER_SIZE - 1, false);
    }

    if (_arena.ended && _arena.cleared) {
        // Card BATTLE-FONT-WIRE: the sheet's glyphs on a plate of the room's ink, because this line sits over the
        // baked field strip and the sheet has one ink that no role colour may tint.
        pp_font_draw_plated_centre("clear", PP_ARENA_CX, _g.y2 + 12, 1);
    }

    if (PP_DEBUG) {
        pp_font_draw_wrapped(_arena.pattern.id + "  step " + string(_arena.phase_steps)
            + "  live " + string(pp_arena_live_hazards(_arena)), 8, 8, pp_font_cols(PP_FRAME_W - 16), 10, 1);
    }
}
