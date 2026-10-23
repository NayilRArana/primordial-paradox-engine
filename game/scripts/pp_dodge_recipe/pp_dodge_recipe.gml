/// pp_dodge_recipe: turns one data recipe into hazards on a fixed schedule (spec 09).
/// A recipe is compiled once into a sorted spawn list, then the emitter walks that list one step at a time. Aiming at
/// the marker happens at spawn, which is why a recipe declares `aim` (spec delta T11) and why the seed is passed in.
///
/// Recipe shape (validated by tools\check_data.py):
///   { id, name, shape, length, aim (fixed|at_marker), max_concurrent,
///     frames: [ { at, count, spread, origin, speed, angle, accel, curve, life, size, delay,
///                 jitter_angle, wobble: {amp, period} } ] }
/// Angles and curve are degrees in screen terms: 0 right, 90 down, and a positive curve turns clockwise on screen.
/// pp_dodge_arena converts both to GameMaker directions exactly once, at spawn (pp_angle_to_gm), and nothing else in the
/// project mirrors an angle. Speed is pixels per step. Times are steps.

/// Compile a recipe into an emitter bound to one rng stream.
function pp_recipe_begin(_recipe, _seed) {
    return {
        recipe: _recipe,
        rng: pp_rng_new(_seed),
        pending: [],
        cursor: 0,
        elapsed: 0,
        length: _recipe.length,
        done: false
    };
}

/// The spawn point for one origin token, before the exclusion rule is applied.
/// Origin is either a named edge or a struct {x, y} in frame coordinates.
function pp_recipe_origin_point(_origin, _rng, _size) {
    var _x1 = PP_ARENA_CX - PP_ARENA_W * 0.5;
    var _y1 = PP_ARENA_CY - PP_ARENA_H * 0.5;
    var _x2 = _x1 + PP_ARENA_W;
    var _y2 = _y1 + PP_ARENA_H;

    if (is_struct(_origin)) {
        return { x: _origin.x, y: _origin.y };
    }

    switch (_origin) {
        case "top":
            return { x: pp_rng_range(_rng, _x1, _x2), y: _y1 - _size };
        case "bottom":
            return { x: pp_rng_range(_rng, _x1, _x2), y: _y2 + _size };
        case "left":
            return { x: _x1 - _size, y: pp_rng_range(_rng, _y1, _y2) };
        case "right":
            return { x: _x2 + _size, y: pp_rng_range(_rng, _y1, _y2) };
        case "centre":
            return { x: PP_ARENA_CX, y: PP_ARENA_CY };
        case "corner":
            var _corners = [
                { x: _x1 - _size, y: _y1 - _size },
                { x: _x2 + _size, y: _y1 - _size },
                { x: _x1 - _size, y: _y2 + _size },
                { x: _x2 + _size, y: _y2 + _size }
            ];
            return _corners[pp_rng_int(_rng, 0, 3)];
    }
    return { x: PP_ARENA_CX, y: _y1 - _size };
}

/// One spawn event, with everything except the aim direction resolved now. Events are produced in a stable order so
/// the same seed always produces the same list.
function pp_recipe_event(_frame, _member, _pattern_aim) {
    var _angle = _frame.angle;
    if (_frame.count > 1) {
        var _t = _member / (_frame.count - 1);
        _angle += (_t - 0.5) * _frame.spread;
    }
    // Aim is a recipe level field only (patterns.schema.json: the frame object refuses unknown keys). Reading a per frame
    // override here is what killed every first dodge frame in the 02:34 build, so the recipe value is the whole answer.
    var _aims = _pattern_aim == "at_marker";
    return {
        at: _frame.at + _member * _frame.delay,
        angle: _angle,
        speed: _frame.speed,
        accel: _frame.accel,
        curve: _frame.curve,
        life: _frame.life,
        size: _frame.size,
        origin: _frame.origin,
        jitter: _frame.jitter_angle,
        wobble_amp: _frame.wobble.amp,
        wobble_period: _frame.wobble.period,
        aim: _aims,
        index: _member
    };
}

/// Fill the pending list for a recipe. Idempotent.
function pp_recipe_compile(_emitter) {
    if (array_length(_emitter.pending) > 0) return _emitter;
    var _frames = _emitter.recipe.frames;
    for (var f = 0; f < array_length(_frames); f++) {
        var _frame = _frames[f];
        for (var m = 0; m < _frame.count; m++) {
            array_push(_emitter.pending, pp_recipe_event(_frame, m, _emitter.recipe.aim));
        }
    }
    // Insertion sort by spawn time, then by member index, so the order is stable across runs and across platforms.
    for (var i = 1; i < array_length(_emitter.pending); i++) {
        var _key = _emitter.pending[i];
        var _j = i - 1;
        while (_j >= 0 && pp_recipe_event_before(_key, _emitter.pending[_j])) {
            _emitter.pending[_j + 1] = _emitter.pending[_j];
            _j -= 1;
        }
        _emitter.pending[_j + 1] = _key;
    }
    return _emitter;
}

/// Sort predicate: earlier spawn time first, ties broken by member index.
function pp_recipe_event_before(_a, _b) {
    if (_a.at == _b.at) return _a.index < _b.index;
    return _a.at < _b.at;
}

/// Advance the emitter by one step and push any due hazards into the arena.
/// Returns the number of hazards spawned this step.
function pp_recipe_step(_emitter, _arena) {
    if (_emitter.done) return 0;
    pp_recipe_compile(_emitter);

    var _spawned = 0;
    while (_emitter.cursor < array_length(_emitter.pending)
        && _emitter.pending[_emitter.cursor].at <= _emitter.elapsed) {
        var _ev = _emitter.pending[_emitter.cursor];
        pp_recipe_spawn(_emitter, _arena, _ev);
        _emitter.cursor += 1;
        _spawned += 1;
    }

    _emitter.elapsed += 1;
    if (_emitter.elapsed >= _emitter.length && _emitter.cursor >= array_length(_emitter.pending)) {
        _emitter.done = true;
    }
    return _spawned;
}

/// Turn one event into one hazard. The marker position is read here, at spawn, never predicted.
function pp_recipe_spawn(_emitter, _arena, _ev) {
    var _rng = _emitter.rng;
    var _pt = pp_recipe_origin_point(_ev.origin, _rng, _ev.size);
    var _m = pp_arena_marker_centre(_arena);

    // Data angle to GameMaker direction, once. aim is different: point_direction already returns a GameMaker direction
    // from screen coordinates, so it is not converted again. jitter is symmetric, so adding it after the mirror leaves
    // the same spread of outcomes.
    var _dir = pp_angle_to_gm(_ev.angle);
    if (_ev.aim) {
        _dir = point_direction(_pt.x, _pt.y, _m.x, _m.y);
    }
    if (_ev.jitter > 0) {
        _dir += pp_rng_range(_rng, -_ev.jitter, _ev.jitter);
    }

    _pt = pp_arena_fit_spawn(_arena, _pt.x, _pt.y, _ev.size);

    pp_arena_add_hazard(_arena, {
        x: _pt.x,
        y: _pt.y,
        dir: _dir,
        curve: -_ev.curve,
        speed: _ev.speed,
        accel: _ev.accel,
        life: _ev.life,
        age: 0,
        size: _ev.size,
        wobble_amp: _ev.wobble_amp,
        wobble_period: _ev.wobble_period,
        alive: true
    });
}
