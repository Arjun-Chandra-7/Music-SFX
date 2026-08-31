# Audio processing guide

The processor works at 48 kHz stereo and ends with a conservative limiter. Preset values are starting points, not loudness-compliance certification.

| Control | Use | Caution |
| --- | --- | --- |
| Low | Adds or removes weight near 120 Hz | Excess boost masks speech and consumes headroom |
| Presence | Changes intelligibility near 3.2 kHz | High values can sound harsh |
| Air | High-frequency shelf near 9 kHz | Can emphasize hiss and sibilance |
| Control | Increases compression depth and ratio | High values flatten transients |
| Space | Adds two-tap ambience/echo | Keep low for dialogue |
| Width | Adjusts stereo side energy | Check mono compatibility above 125% |
| Wet | Sets processed-chain gain, not dry/wet parallel mix | Below 100% lowers the rendered chain |
| Output | Final gain before limiting | Do not use as a loudness target |

Use `broadcast_voice` for isolated narration, not a complete music-and-dialogue mix. `shorts_punch` is intentionally assertive. `clean_master` is the lowest-risk general preset. `vintage_radio` and `dream_space` are creative effects and should reflect an explicit creative intent.

For formal broadcast, podcast-platform, or accessibility loudness targets, measure the rendered asset with an appropriate loudness workflow before publication; this version does not claim EBU R128, ATSC A/85, or platform-specific certification.

