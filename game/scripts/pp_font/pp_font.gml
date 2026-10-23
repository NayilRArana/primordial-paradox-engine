/// pp_font: the 8x8 bitmap font, drawn from the spr_pp_font8 sprite sheet.
/// This is the game's only letters. Every screen that draws with it goes through pp_font_draw, so the letters are the
/// same pixels everywhere (spec 13, font and UI): the title screen, the drive scene and, since card t_1d828fcd, the
/// dialogue box's rows, name plate and choice labels.
/// A screen still on the GameMaker default font is a screen the font has not reached yet, and the honest list is
/// short: the boot and data error screen (pp_app), the battle board (pp_battle_director and pp_battle_text), the save
/// panel (pp_save) and one overworld hint line (pp_overworld). Those draw with draw_text and are card
/// BATTLE-FONT-WIRE's, not this module's; before that card the dialogue box was on that list, so this header used to
/// claim a thing the tree did not do.
/// The sheet holds one frame per glyph in ASCII order, so a glyph is found by its position in the ASCII set
/// rather than by a table of offsets.
/// Provenance: knowledge\PROVENANCE.md, entry "modules written from the specs alone", written from
/// specs\13-8bit-look.md and the art lane's contract in TITLE-COORD.md.

/// The glyph set of spr_pp_font8, in the ASCII order the art lane uses: one frame per character.
/// The set is the characters the game can write, and the sheet has exactly one frame for each of them.
/// 74 glyphs: space, the ten marks `!"'()*,-.:?`, the ten digits, the 26 capitals and the 26 lowercase letters.
/// Three groups were added by card t_41c97c88 because the slice prints them and the 46 glyph sheet did not have
/// them: `*` is the narration marker the dialogue data carries on every line (spec 19 Q6/D6), `"` is the quote the
/// arrival and gate lines wrap speech in, and the lowercase letters are the sentence case the authored dialogue is
/// written in (`* The deck tilts.`), which a capitals only sheet drew as spaces. The logo keeps its own 5x7
/// capitals grid in tools/art/make_title_ui.py; this sheet is the text alphabet.
/// tools/check_font_coverage.py reads this string, proves the sheet matches it frame by frame, and refuses the
/// build when a data file prints a character that is not in it.
function pp_font_glyphs() {
    return " !\"'()*,-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
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

/// Draw one line of text with the 8x8 font, left aligned, at an alpha. Returns the width drawn.
/// A character the sheet does not have is drawn as a space, so a stray character never breaks the layout.
///
/// The sheet is one row of 8x8 frames in one ink, 2C02 $20 white. There is no second weight and there is no tint. That
/// is deliberate (card t_a1170172): a tint is a multiply, and multiplying the sheet's white by the grey a
/// disabled label used to ask for produced #7b7b7b, a value no PPU can output, which is what
/// tools/nes_composite_check.py refused in the composited title frame. An "off" row is marked by a rule drawn
/// through it in the ground band's own dark green instead; see pp_title_draw_disabled.
function pp_font_draw(_text, _x, _y, _alpha) {
    var _info = pp_art_info("spr_pp_font8");
    if (is_undefined(_info)) return 0;
    var _cx = _x;
    for (var i = 0; i < string_length(_text); i += 1) {
        var _ch = string_char_at(_text, i + 1);
        var _g = pp_font_glyph_index(_ch);
        if (_g >= 0) {
            draw_sprite_part_ext(_info.sprite, 0, _g * 8, 0, 8, 8, _cx, _y, 1, 1, PP_UNTINTED, _alpha);
        }
        _cx += 8;
    }
    return _cx - _x;
}

/// Draw one line of text centred on a point.
function pp_font_draw_centre(_text, _centre_x, _y, _alpha) {
    var _w = pp_font_width(_text);
    return pp_font_draw(_text, _centre_x - floor(_w / 2), _y, _alpha);
}
