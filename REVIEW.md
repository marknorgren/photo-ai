# Photo Analysis Review — SF Feb 2026

85 HEIC photos analyzed using `qwen/qwen3-vl-30b` via LM Studio local
inference. Single vision API call per image returns tags, composition score,
category, location, and description. Results stored in SQLite.

## What Worked

**Location identification is excellent.** Combining EXIF GPS coordinates with
visual recognition produces specific, accurate place names:

| Photo | Location |
|-------|----------|
| IMG_8825 | Apple Store, Union Square, San Francisco, CA |
| IMG_8835 | Chinatown Gate, San Francisco, CA |
| IMG_9343 | Golden Gate Bridge, San Francisco, CA |
| IMG_8927 | Painted Ladies, San Francisco, CA |
| IMG_8870 | Mr. Bing's Cocktail Lounge, Transamerica Pyramid, San Francisco, CA |

66 unique locations identified across 85 photos. 100% GPS coverage from HEIC
EXIF metadata.

**Descriptions are natural and accurate.** The model correctly identifies
landmarks, architectural styles, weather conditions, and scene context. Example:

> "A vintage red and cream streetcar travels along a city street, flanked by a
> historic red brick building on the left and a modern glass skyscraper on the
> right, under a bright blue sky with scattered clouds."

**Tags provide useful dimensions.** 510 total tag assignments (~6 per image).
Top tags reflect the actual content — SF street photography in mixed weather:

| Tag | Count | Tag | Count |
|-----|-------|-----|-------|
| building | 55 | person | 18 |
| dramatic | 52 | vehicle | 17 |
| street | 44 | architecture | 16 |
| cinematic | 41 | landscape | 14 |
| rain | 29 | fog | 14 |
| sky | 27 | water | 12 |
| moody | 23 | peaceful | 11 |
| urban | 19 | night | 11 |

**Categories are reasonable.** Distribution matches the trip itinerary — mostly
street and architecture photography with some landscape and food:

| Category | Count | Avg Score |
|----------|-------|-----------|
| street | 25 | 7.2 |
| architecture | 20 | 7.8 |
| urban | 15 | 7.7 |
| landscape | 14 | 7.8 |
| food | 4 | 8.0 |
| travel | 2 | 6.0 |
| abstract | 2 | 7.0 |
| portrait | 1 | 7.0 |
| night | 1 | 8.0 |
| concert | 1 | 7.0 |

## Neighborhood Coverage

The photos trace a journey across San Francisco:

| Neighborhood | Photos | Notable Locations |
|--------------|--------|-------------------|
| Golden Gate / Presidio | 12 | Golden Gate Bridge, Fort Point, Vista Point |
| Fisherman's Wharf | 12 | Pier 39, Musee Mecanique, Sea Lions |
| Chinatown | 9 | Chinatown Gate, markets, tunnels |
| Union Square | 6 | Apple Store, Peace Monument, Lego Store |
| Nob Hill | 6 | Fairmont Hotel, Top of the Mark |
| North Beach | 5 | Caffe Trieste, Transamerica Pyramid |
| Financial District | 4 | Wells Fargo, Love Sculpture |
| Sutro / Lands End | 2 | Sutro Baths ruins |
| Other SF | 25 | Street scenes, murals, Victorian homes |
| Outside SF | 4 | Santa Cruz, San Jose, Catalina |

## Issues

### 1. Composition scores are compressed (critical)

The 7-point Steph Ango scale was requested (1=Terrible through 7=Perfect) but
the model returned scores from 4 to 8:

| Score | Count | % | Scale Label |
|-------|-------|---|-------------|
| 8 | 53 | 62% | (above scale) |
| 7 | 27 | 32% | Perfect |
| 6 | 2 | 2% | Excellent |
| 5 | 3 | 4% | Good |
| 4 | 1 | 1% | Passable |

**Root causes:**
- Model ignores the 1-7 cap and returns 8 anyway
- Validation (`1 <= score <= 7` check) exists in code but the `--force` re-run
  likely used a cached script version
- Even within 4-8 range, 94% of photos scored 7+ which provides poor
  differentiation

**Next steps:**
- Clamp scores > 7 to 7 in validation (not reject to 0)
- Add few-shot examples to the prompt showing what a 3, 5, and 7 look like
- Consider asking for relative ranking within a batch rather than absolute scores

### 2. Style tags over-applied

`dramatic` (52/85) and `cinematic` (41/85) appear on 61% and 48% of images
respectively. While SF street photography in rain is genuinely moody, these tags
lose discriminative value when applied to the majority.

**Next step:** Add to prompt: "Apply style and mood tags only when they are the
*defining* characteristic, not merely present."

### 3. Tags returned as dict, not array

The model returns tags as `{"Scene": "street", "Subject": "building"}` instead
of the requested flat array `["street", "building"]`. Fixed in `validate_analysis`
by flattening dict values, but ideally the prompt would produce the right
structure. Consider adding an explicit JSON example to the prompt.

### 4. Some locations include raw coordinates

Two photos have locations like `"Cafe, 37.787731, -122.412894"` where the model
couldn't identify the venue and fell back to embedding the GPS numbers. These
should be caught and set to a neighborhood-level fallback.

## Pipeline Stats

- **85** images processed
- **510** tags assigned (6.0 per image)
- **66** unique locations
- **9** SF neighborhoods covered
- **100%** GPS extraction rate
- **0** errors

## Query Examples

```sql
-- Top compositions
SELECT filename, category, composition_score, location
FROM photos ORDER BY composition_score DESC LIMIT 10;

-- Photos by neighborhood (Chinatown)
SELECT filename, location, description
FROM photos WHERE location LIKE '%Chinatown%';

-- Tag co-occurrence
SELECT a.tag, b.tag, COUNT(*) as co
FROM photo_tags a
JOIN photo_tags b ON a.photo_path = b.photo_path AND a.tag < b.tag
GROUP BY a.tag, b.tag ORDER BY co DESC LIMIT 10;

-- Browse with Datasette
-- uv run datasette photo_analysis.db
```
