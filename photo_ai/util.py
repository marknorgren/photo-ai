"""Shared constants, labels, and formatting utilities."""

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff", ".tif"}

ALL_TAGS = [
    "landscape", "portrait", "street", "architecture", "macro", "wildlife", "aerial",
    "concert", "night", "astro", "food", "sports", "travel", "fashion", "urban",
    "person", "animal", "building", "nature", "water", "sky", "mountain", "beach",
    "forest", "flower", "vehicle",
    "monochrome", "silhouette", "long_exposure", "dramatic", "minimalist", "vintage",
    "cinematic", "abstract", "bokeh",
    "peaceful", "energetic", "intimate", "moody",
    "fog", "rain", "snow", "storm",
]

ALL_CATEGORIES = [
    "landscape", "portrait", "street", "architecture", "macro", "wildlife", "aerial",
    "concert", "night", "astro", "food", "sports", "travel", "fashion", "urban",
    "abstract", "minimalist", "dramatic", "monochrome", "weather", "default",
]

COMPOSITION_ELEMENTS = [
    "rule_of_thirds", "leading_lines", "symmetry", "depth", "framing", "negative_space",
]

COMPOSITION_ISSUES = [
    "centered_subject", "subject_too_small", "awkward_crop", "no_lead_room",
    "centered_horizon", "tilted_horizon", "lines_exit_frame", "background_merger",
    "cluttered_background", "empty_foreground", "backlit_subject", "flat_lighting",
    "harsh_shadows", "shallow_misfocus", "low_contrast", "competing_colors",
]

SCORE_LABELS = {
    1: "Terrible",
    2: "Atrocious",
    3: "Bad",
    4: "Passable",
    5: "Good",
    6: "Excellent",
    7: "Perfect",
}


def score_label(score: int | float) -> str:
    """Return human-readable label for a composition score."""
    return SCORE_LABELS.get(int(score), "Unknown")


def format_table(headers: list[str], rows: list[list[str]], align: list[str] | None = None) -> str:
    """Format a simple text table. align is a list of '<', '>', or '^' per column."""
    if not rows:
        return "(no results)"
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    if align is None:
        align = ["<"] * len(headers)
    fmt_parts = []
    for i, w in enumerate(col_widths):
        fmt_parts.append(f"{{:{align[i]}{w}}}")
    fmt = "  ".join(fmt_parts)
    lines = [fmt.format(*headers), fmt.format(*["-" * w for w in col_widths])]
    for row in rows:
        lines.append(fmt.format(*[str(c) for c in row]))
    return "\n".join(lines)


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "photo_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["tags", "composition", "category", "description", "caption", "title", "location"],
            "additionalProperties": False,
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "enum": ALL_TAGS},
                    "maxItems": 8,
                },
                "composition": {
                    "type": "object",
                    "required": ["score", "elements", "issues", "explanation", "suggestions"],
                    "additionalProperties": False,
                    "properties": {
                        "score": {"type": "integer", "minimum": 1, "maximum": 7},
                        "elements": {
                            "type": "array",
                            "items": {"type": "string", "enum": COMPOSITION_ELEMENTS},
                        },
                        "issues": {
                            "type": "array",
                            "items": {"type": "string", "enum": COMPOSITION_ISSUES},
                        },
                        "explanation": {"type": "string"},
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3,
                        },
                    },
                },
                "category": {"type": "string", "enum": ALL_CATEGORIES},
                "description": {"type": "string"},
                "caption": {"type": "string"},
                "title": {"type": "string"},
                "location": {"type": ["string", "null"]},
            },
        },
    },
}

ANALYSIS_PROMPT_BASE = """\
Analyze this photograph and return a JSON object with exactly these keys:

1. "tags" — up to 8 tags from these categories. Be selective: only apply a tag if it is a defining characteristic of this specific image, not just vaguely present.
   Scene: landscape, portrait, street, architecture, macro, wildlife, aerial, concert, night, astro, food, sports, travel, fashion, urban
   Subject: person, animal, building, nature, water, sky, mountain, beach, forest, flower, vehicle
   Style: monochrome, silhouette, long_exposure, dramatic, minimalist, vintage, cinematic, abstract, bokeh
   Mood: dramatic, peaceful, energetic, intimate, moody
   Weather: fog, rain, snow, storm

2. "composition" — an object with:
   "score": integer 1-7 using this scale (be critical, most photos should score 3-5):
     7 = Perfect — museum-quality, exceptional in every way
     6 = Excellent — strong composition worth studying, minor imperfections
     5 = Good — solid composition, nothing distracting
     4 = Passable — acceptable but unremarkable, some compositional issues
     3 = Bad — noticeable problems (clutter, poor framing, no clear subject)
     2 = Atrocious — major compositional failures
     1 = Terrible — no compositional merit
   "elements": array of applicable strengths from [rule_of_thirds, leading_lines, symmetry, depth, framing, negative_space]
   "issues": array of detected problems from [centered_subject, subject_too_small, awkward_crop, no_lead_room, centered_horizon, tilted_horizon, lines_exit_frame, background_merger, cluttered_background, empty_foreground, backlit_subject, flat_lighting, harsh_shadows, shallow_misfocus, low_contrast, competing_colors]. Empty array if no issues.
   "explanation": one sentence explaining the score, referencing specific strengths or weaknesses
   "suggestions": 1-3 specific, actionable tips for how this photo could be improved. Each suggestion should tell the photographer what to do differently — framing, positioning, timing, or camera settings. Use these patterns:
     - centered_subject: "Move the subject to a rule-of-thirds intersection — dead center works only when symmetry is the point"
     - subject_too_small: "Move closer or zoom in — the subject is lost in the frame without contributing context"
     - awkward_crop: "Crop at mid-chest, waist, or mid-thigh — never at joints (wrist, knee, ankle)"
     - no_lead_room: "Leave space in the direction the subject faces or moves — place them looking into the frame, not out of it"
     - centered_horizon: "Push the horizon to the upper or lower third — an even split dilutes both halves"
     - tilted_horizon: "Level the horizon — a slight unintentional tilt reads as carelessness. If tilting, commit to 15-30 degrees"
     - lines_exit_frame: "Reframe so the leading line points to your subject before it exits the edge"
     - background_merger: "Step left or right to separate the subject from the background element growing from their head/body"
     - cluttered_background: "Use a wider aperture (f/1.8-2.8) to blur the background, or reposition the subject against a cleaner backdrop"
     - empty_foreground: "Get lower and find foreground interest — rocks, flowers, reflections — to add depth"
     - backlit_subject: "Use fill flash or a reflector, or reposition so light comes from the side rather than behind the subject"
     - flat_lighting: "Move the light source 45 degrees to the side for shadow and dimension. Seek open shade or golden hour"
     - harsh_shadows: "Move fully into shade or sun — avoid the split zone. Use fill flash to lift shadows"
     - shallow_misfocus: "Focus on the nearest eye in portraits. Stop down to f/2.8-4 if depth of field is too thin"
     - low_contrast: "Set a true black and white point in post — drag Blacks left and Whites right until the histogram spans the full range"
     - competing_colors: "Exclude the competing bright color by reframing, blurring it with shallow DOF, or desaturating in post"
     For a perfect 7/7 photo, suggestions can note what makes it work ("The side lighting and rule-of-thirds placement are textbook — no changes needed"). Be specific to THIS photo, not generic.

3. "category" — single best-fit from: landscape, portrait, street, architecture, macro, wildlife, aerial, concert, night, astro, food, sports, travel, fashion, urban, abstract, minimalist, dramatic, monochrome, weather, default

4. "description" — 1-2 sentence natural language description of the image

5. "caption" — a short, evocative photo caption (5-10 words) suitable for a gallery or photo book. Focus on mood, moment, or story rather than literal description. Examples: "Morning light through the fog", "The last train home"

6. "title" — a memorable, distinctive name for this specific photo (2-5 words). Should be unique enough to identify this image in a collection. Think album title or art print name. Examples: "Iron Zigzag", "Gilded Lobby", "Chowder Weather"

{location_instruction}

Return ONLY valid JSON, no markdown fences, no extra text.\
"""

LOCATION_WITH_GPS = """\
7. "location" — a human-readable place name that combines what you see in the photo with the GPS coordinates ({lat}, {lon}). \
Be specific: name the landmark, venue, park, neighborhood, or point of interest visible in the image, \
followed by city and state/country. Example: "Apple Store, Union Square, San Francisco, CA"\
"""

LOCATION_NO_GPS = """\
7. "location" — if you can identify the specific place, landmark, or venue in the photo, provide a human-readable location \
(e.g. "Golden Gate Bridge, San Francisco, CA"). If you cannot confidently identify the location, set to null.\
"""
