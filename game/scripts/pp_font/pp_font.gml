/// pp_font: the 8x8 bitmap font, drawn from the spr_pp_font8 sprite sheet.
/// Every piece of text on the title screen goes through here, and the font is the only text in the project:
/// no draw_text, no default font, so the letters are the same pixels everywhere (spec 13, font and UI).
/// The sheet holds one frame per glyph in ASCII order, so a glyph is found by its position in the ASCII set
/// rather than by a table of offsets.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\13-8bit-look.md and the art lane's contract in TITLE-COORD.md.

/// The glyph set of spr_pp_font8, in the ASCII order the art lane uses: one frame per character.
/// The set is the characters the game can write, and the sheet has exactly one frame for each of them.
function pp_font_glyphs() {
    return " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ";
}

/// The frame number of one character, or -1 when the character is not in the sheet.
function pp_font_glyph_index(_char) {
    var _set = pp_font_glyphs();
    var _pos = string_pos(_char, _set);
    if (_pos <= 0) return -1;
    return _pos - 1;
}

/// The width in pixels of a string at the 8x8 font.
function pp_font_width(_text) {
    return string_length(_text) * 8;
}

/// Draw one line of text with the 8x8 font, left aligned, at a colour and an alpha. Returns the width drawn.
/// A character the sheet does not have is drawn as a space, so a stray character never breaks the layout.
function pp_font_draw(_text, _x, _y, _colour, _alpha) {
    var _info = pp_art_info("spr_pp_font8");
    if (is_undefined(_info)) return 0;
    var _cx = _x;
    for (var i = 0; i < string_length(_text); i += 1) {
        var _ch = string_char_at(_text, i + 1);
        var _g = pp_font_glyph_index(_ch);
        if (_g >= 0) {
            draw_sprite_part_ext(_info.sprite, 0, _g * 8, 0, 8, 8, _cx, _y, 1, 1, _colour, _alpha);
        }
        _cx += 8;
    }
    return _cx - _x;
}

/// Draw one line of text centred on a point.
function pp_font_draw_centre(_text, _centre_x, _y, _colour, _alpha) {
    var _w = pp_font_width(_text);
    return pp_font_draw(_text, _centre_x - floor(_w / 2), _y, _colour, _alpha);
}
