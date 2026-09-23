# RPG presentation upgrade — ongoing

**Latest checkpoint (2026-09-22): this early log is superseded by `docs/rpg-v19-release.md`.** That document records all current gameplay, art, village events, crafting, boss magic VFX/camera, tests and remaining quality limitations. Build is now `dist/babel-rpg-v19.html` (about 21.6 MB), 421 HD mappings/286 WebPs. No pending image generation; all masters copied to art_raw/hd-v18. No commits/push/deployment. Browser server 8876. Latest requested addition was more spectacular boss map ultimates; implemented in web/boss-fx.js with core hooks and offline bundling. Any continued work must preserve current modifications and use the latest release document, not the outdated plan below.

User scope (2026-09-22): continue thread 01a017ef-eb82-7e11-a070-ef5023481b05, finish HD art incl. physically fitted hats; then unify animation, opening/interstitial cinematics, UI/inventory; walkable FF/DQ-like villages with wandering NPCs, shopping/dialogue/info/events; richer story/chapter/culture-informed music and action SFX; device-fitted interface with no page overflow or accidental text selection.

Project: this directory (yubao-tts-roguelike-publish). Existing user changes preserved. No commit/push/deployment yet. Local server port 8876.

Completed in this continuation:
- Recovered previous unfinished v18 assets from old generated_images, generated missing skins/summons, packaged 225 WebPs / 360 mappings.
- Generated 30 actual worn hero sprites (10 hats × front/side/back). Current integration specifically orange blob; other skins/colors retain existing overlay. Item icons are separate.
- Fixed connected-subject crop fragments, transparent master validation, WebP method 4 (method 6 stalled excessively).
- Wired torch, debris, summon and merchant HD sources, smoothed HD stone stairs, fixed erroneous light --ink cabinet background.
- Added qa=wear native gallery, tools/check_hd_wear.cjs and check_hd_scene.cjs. Before/after and scene screenshots in work/hd-wear.
- Offline HD embedding in tools/build_single.py; dist/babel-hd-v18.html rebuilt (15.6MB), needs final offline runtime verification.
- Existing render/heian/damage/save Node checks passed before latest world changes. Browser four scenes (temple,forest,crystal,tower), mobile390×844 loaded without page errors or HD failures.
- imagegen skill read and announced. Prompts tools/hd-art-prompts.json; canonical build spec tools/hd-art-sources.json; masters art_raw/hd-v18 ignored by Git.

Next implementation in progress:
1. New rpg-upgrade.js/css module after main script. Town canvas with collisions, player walking/pathfinding, NPC wandering, physical smith/shop/dialogues, journal and one-time bell quest. Existing vstock/vowned moved into bounded shop dialog to preserve purchase/forge rules. Village state fields need migration and persistence. Capture input so village walking cannot reach dungeon.
2. Responsive fixed viewport/safe areas; keep internal modal/list scrolling only, prevent contextmenu/select on controls with input exceptions; inventory transitions and accessible tabs.
3. Improve original BGM synth (voice/playStep around13727/13775), 16/32-bar variation and instrument envelopes/reverb/stereo, unique chapter motifs; chapter theme identity uses ACT_THEME. SFX bank around13290, motion poses9756, cinematic code191xx.
4. Test town interactions/save, layouts, input, animation sequences, audio recordings; regenerate single file after modules inlined.

A new imagegen is running: functions cell 2, result stored villageAssets and prompt villageAssetPrompt. 4×4 transparent structures sheet: rows euro/cave/edo/spire; columns forge/inn/tree/well (last row brazier). Need await, inspect, copy master, append 16 IDs, package and load. No subagents authorized.

Runtime dependencies:
Python C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
Playwright module C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
Chrome C:/Program Files/Google/Chrome/Application/chrome.exe
Use env PLAYWRIGHT_MODULE for our cjs checks.

Music research sources (primary):
- https://www.metmuseum.org/art/collection/search/324023 (Mesopotamian bovine lyres)
- https://www.penn.museum/sites/expedition/the-musical-instruments-from-ur-and-ancient-mesopotamian-music/ (lyre/harp reconstructions and tuning tablets)
- https://gagaku.stanford.edu/en/repertoire/ and https://gagaku.stanford.edu/en/orchestration/woodwinds/ (ryuteki,hichiriki melody; sho harmony)
- https://ich.unesco.org/en/RL/gagaku-00265
Do not equate generic Hijaz with historically reconstructed ancient Babylonian music. Original fantasy score informed by instrumentation, not authentic reconstruction; no available music generation connector found.
