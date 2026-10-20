/// pp_rng: one deterministic random stream per battle (spec 09 rule 2 and T11).
/// A linear congruential generator, so a seed and a step count always give the same numbers in GML and in
/// tools\check_data.py. Nothing here reads the clock.

#macro PP_RNG_MOD 4294967296

/// Create a stream. The seed is an integer from encounter data.
function pp_rng_new(_seed) {
    var _s = _seed mod PP_RNG_MOD;
    if (_s < 0) _s += PP_RNG_MOD;
    return { state: _s };
}

/// Advance and return a float in [0, 1).
function pp_rng_next(_rng) {
    _rng.state = (_rng.state * 1664525 + 1013904223) mod PP_RNG_MOD;
    return _rng.state / PP_RNG_MOD;
}

/// Float in [lo, hi).
function pp_rng_range(_rng, _lo, _hi) {
    return _lo + (_hi - _lo) * pp_rng_next(_rng);
}

/// Whole number in [lo, hi], inclusive.
function pp_rng_int(_rng, _lo, _hi) {
    if (_hi <= _lo) return _lo;
    return _lo + floor(pp_rng_next(_rng) * ((_hi - _lo) + 1));
}

/// True with probability p.
function pp_rng_chance(_rng, _p) {
    return pp_rng_next(_rng) < _p;
}
