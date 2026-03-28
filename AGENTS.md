# AGENTS.md - MaaStarResonance Project Guide

## Project Overview

**MaaStarResonance** (v0.7.1) is an automation tool for the mobile game "Star Resonance" (package: `com.tencent.wlfz`), built on [MaaFramework](https://github.com/MaaXYZ/MaaFramework) (maafw 5.9.2) with [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia) v2.11.4 as the GUI frontend. The Python agent layer (Python 3.13) provides custom actions and recognitions that extend the pipeline-based automation system.

- **License**: AGPL-3.0
- **Authors**: 233Official, AZMIAO
- **Template**: Based on [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate)

## Architecture

The project follows a **two-layer design**:

1. **Pipeline Layer** (`assets/resource/base/pipeline/`): JSONC files defining recognition + action flows using built-in MaaFramework recognizers (TemplateMatch, OCR, ColorMatch, DirectHit) and custom ones.
2. **Python Agent Layer** (`agent/`): Custom actions and recognitions registered via `@AgentServer.custom_action("name")` and `@AgentServer.custom_recognition("name")` decorators, providing complex logic that pipelines cannot express alone.

### Parameter Passing Flow

```
GUI options → interface.json (pipeline_override) → Pipeline node "attach" field
→ Python reads via context.get_node_data() in common_attach.py → drives custom logic
```

### Startup Flow

```
main.py → (optionally) init_python_env() for embedded Python releases
→ adds project root to sys.path
→ module_loader.py recursively imports all modules under agent/ subdirectories
→ AgentServer.start_up() → AgentServer.join()
```

## Directory Structure

```
MaaStarResonance/
├── agent/                          # Python agent layer (custom actions & recognitions)
│   ├── main.py                     # Entry point: env init, module loading, AgentServer startup
│   ├── module_loader.py            # NoneBot-style recursive module loader
│   ├── logger.py                   # Loguru-based logger configuration
│   ├── attach/                     # Parameter extraction from pipeline attach data
│   │   └── common_attach.py        # ~20 getter functions for GUI-configured parameters
│   ├── constant/                   # Static data and constants
│   │   ├── pages.py                # Page recognition enums and PageRecognizer class
│   │   ├── fish/fishData.json      # Fish species data across 4 fishing areas
│   │   ├── key_event/AndroidKeyEvent.json  # 138 Android key code mappings
│   │   ├── map_point/MapPoint.json         # ~44 teleport points across 3 maps
│   │   ├── map_point/NavigatePoint.json    # Navigation points for 4 maps
│   │   └── world_channel/ChannelData.json  # Chat channel UI coordinates
│   ├── custom/                     # Custom action/recognition implementations
│   │   ├── common_action.py        # Generic reusable actions (5 registrations)
│   │   ├── fishing_action.py       # Auto-fishing state machine (~811 lines)
│   │   ├── teleport_action.py      # Map teleport & navigation with OCR + fuzzy matching
│   │   ├── unstable_space.py       # Unstable Space dungeon automation
│   │   ├── beat_chen_min.py        # "Beat ChenMin" mini-game automation
│   │   ├── cocoon_action.py        # Cocoon dungeon farming (WIP)
│   │   ├── app_manage_action.py    # App start/stop/restart + login flow (4 registrations)
│   │   └── general/                # General-purpose modules
│   │       ├── general.py          # return_main_page, AllMatch, AnyMatch, ensure_main_page decorator
│   │       ├── ad_close.py         # Close ad popups
│   │       ├── chat_message.py     # Chat message sending (single + loop)
│   │       ├── move_battle.py      # Battle utilities (mount, auto-attack, rotate view, check alive)
│   │       ├── power_saving_mode.py # Power saving mode exit decorator
│   │       ├── season_center.py    # Season center operations (4 registrations)
│   │       └── world_line_switcher.py # World line switching
│   └── utils/                      # Utility modules
│       ├── param_utils.py          # CustomActionParam parser with require/optional methods
│       ├── fuzzy_utils.py          # Fuzzy string matching using rapidfuzz
│       ├── time_utlls.py           # Time formatting and conversion utilities
│       └── other_utils.py          # Miscellaneous (centered log block printer)
├── assets/
│   ├── interface.json              # MFAAvalonia interface definition (~1158 lines, 15 tasks)
│   └── resource/base/pipeline/     # Pipeline JSONC definitions
│       ├── general.json            # General pipeline nodes
│       ├── general/                # General sub-pipelines
│       ├── fishing/                # Fishing pipeline nodes
│       ├── gathering/              # Gathering pipeline nodes
│       ├── daily/                  # Daily reward pipeline nodes
│       ├── map/                    # Map teleport/navigation pipelines
│       ├── association_hunt.json   # Association hunt pipeline
│       ├── beat_chen_min.json      # Beat ChenMin pipeline
│       ├── cocoon/                 # Cocoon pipeline nodes
│       ├── roguelike.json          # Roguelike pipeline nodes
│       └── seson_center/           # Season center pipeline nodes
├── scripts/                        # Build and development scripts
│   ├── build_all_platforms.py      # Cross-platform build script
│   ├── check_resource.py           # Resource validation
│   ├── download_res.py             # Resource downloader
│   ├── download_wheels.py          # Python wheel downloader for offline install
│   ├── generate_changelog.py       # Changelog generator
│   ├── init_develop_environment.py # Dev environment initializer
│   ├── install.py                  # Installer script
│   └── migrate_pipeline_v5.py      # Pipeline migration tool (v4 → v5)
├── deps/                           # Dependencies (wheels, get-pip.py)
├── docs/                           # Docusaurus documentation site source
├── pyproject.toml                  # Python project config (deps, isort, setuptools)
└── .github/                        # GitHub CI/CD and Copilot instructions
```

## Registered Custom Actions

All custom actions are registered via `@AgentServer.custom_action("name")` and extend `maa.custom_action.CustomAction`.

### Generic Reusable Actions (`custom/common_action.py`)

| Registration Name | Class | Description |
|---|---|---|
| `run_pipeline_node` | `RunTaskPipelineAction` | Runs a named pipeline node. Param: `pipeline_node_name`. |
| `decision_router` | `DecisionRouterAction` | Conditional branching: runs a recognition judge node, then overrides next node to `success_node` or `failure_node`. |
| `wait_x_seconds` | `WaitXSecondsAction` | Waits for a specified number of seconds with progress logging. Param: `wait_seconds`. |
| `run_custom_actions_series` | `RunCustomActionsSeriesAction` | Runs a sequence of custom actions with configurable interval. Params: `actions` (list), `interval` (ms). |
| `move_wsad` | `MoveWSADAction` | Moves character in a direction (W/A/S/D) for specified milliseconds. Params: `direction` ("前"/"后"/"左"/"右"), `millisecond`. |

### Fishing (`custom/fishing_action.py`)

| Registration Name | Class | Description |
|---|---|---|
| `AutoFishing` | `AutoFishingAction` | Complex fishing state machine (~811 lines). Handles: navigation to fishing spots, equipment purchase (rod/bait via OCR + fuzzy match), casting, tension control (arrow direction detection via ColorMatch), reeling, catch confirmation, inventory management, error recovery, and statistics reporting. Reads attach params: fish navigation, fish equipment (rod/bait). |

### Map Teleport & Navigation (`custom/teleport_action.py`)

| Registration Name | Class | Description |
|---|---|---|
| `TeleportPoint` | `TeleportPointAction` | Opens map (M key), selects target map tab, OCR-scans teleport point names with fuzzy matching (rapidfuzz), clicks to teleport, waits for scene load. Reads attach: `dest_tele_map`, `dest_tele_point`. |
| `NavigatePoint` | `NavigatePointAction` | Similar to teleport but uses navigation points. Opens map, selects map, fuzzy-matches navigation point name, clicks navigate button. Reads attach: `dest_navi_map`, `dest_navigate_point`. |

### Unstable Space (`custom/unstable_space.py`)

| Registration Name | Class | Description |
|---|---|---|
| `UnstableSpacePoint` | `UnstableSpacePointAction` | Navigates to Unstable Space dungeon entrance, enters challenge, enables auto-battle, rotates view to prevent aggro loss, monitors dungeon status and character survival. Decorated with `@exit_power_saving_mode()` and `@ensure_main_page()`. |

### Beat ChenMin (`custom/beat_chen_min.py`)

| Registration Name | Class | Description |
|---|---|---|
| `BeatChenMinPoint` | `BeatChenMinPointAction` | Navigates to dimensional punishment entrance, iterates world lines 11~60 to find an available instance, enters and auto-attacks for 70s per round. Reads attach: `max_beat_count` (0 = unlimited). |

### Cocoon (`custom/cocoon_action.py`)

| Registration Name | Class | Description |
|---|---|---|
| `CocoonAction` | `CocoonActionAction` | Navigates to specified cocoon location, dismounts vehicle, switches to low-traffic world lines (1~10), monitors illusion gauge to toggle auto-battle. **Work in progress** - contains TODO placeholder coordinates. Reads attach: `cocoon_name`. |

### App Management (`custom/app_manage_action.py`)

| Registration Name | Class | Description |
|---|---|---|
| `StartTargetApp` | (function-based) | Starts specified app via controller. Param: `app_package_name`. |
| `StopTargetApp` | (function-based) | Stops specified app via controller. Param: `app_package_name`. |
| `RestartTargetApp` | (function-based) | Stops → waits 5s → starts app. Param: `app_package_name`. |
| `RestartAndLoginXHGM` | (function-based) | Full restart + login flow for Star Resonance: restart app → wait for launch → click connect → enter game → wait for main page. Reads attach: `login_timeout`, `area_change_timeout`. |

### General - Main Page & Composites (`custom/general/general.py`)

| Registration Name | Type | Class | Description |
|---|---|---|---|
| `return_main_page` | Action | `ReturnMainPageAction` | Presses ESC key up to 10 times until main page is detected via image recognition. |

Also provides:
- **`ensure_main_page()` decorator**: Wraps action `run()` methods to automatically return to main page before execution. Supports `max_retry`, `interval_sec`, and `strict` mode.

### General - Ad Close (`custom/general/ad_close.py`)

| Registration Name | Class | Description |
|---|---|---|
| `CloseAd` | `CloseAdAction` | Loops to detect and dismiss ad popups by clicking "Don't show today" then close button. |

### General - Chat Message (`custom/general/chat_message.py`)

| Registration Name | Class | Description |
|---|---|---|
| `SendMessageLoop` | (function-based) | Periodically sends chat messages across world channel lines. Supports variable substitution (`${当前人数}`, `${总人数}`, `${队伍名}`). Reads attach: `chat_channel`, `chat_channel_id_list`, `chat_loop_interval` (min 30s), `chat_loop_limit`, `chat_message_content`, `chat_message_need_team`, `full_team_force_send`. |
| `SendMessage` | (function-based) | Single-shot version of the above. |

### General - Season Center (`custom/general/season_center.py`)

| Registration Name | Class | Description |
|---|---|---|
| `open_season_center_page` | (function-based) | Opens season center page (O key + verification). |
| `claim_today_activity_rewards` | (function-based) | Claims daily activity rewards from season center. |
| `open_compensation_shop_page` | (function-based) | Opens compensation shop from season center. |
| `buy_all_gameplay_compensation_shop_items` | (function-based) | Buys all available items in gameplay compensation shop. |

All season center actions are decorated with `@exit_power_saving_mode()` and `@ensure_main_page(strict=True)`.

### General - World Line Switcher (`custom/general/world_line_switcher.py`)

| Registration Name | Class | Description |
|---|---|---|
| `SwitchLine` | `SwitchLineAction` | Opens line selection (P key), enters line number via OCR, clicks go, iterates line list until successful switch. Reads attach: `world_line_id_list`, `area_change_timeout`. |

## Registered Custom Recognitions

| Registration Name | Class | File | Description |
|---|---|---|---|
| `AllMatch` | `AllMatchRecognition` | `general/general.py` | Composite: all specified nodes must match. Param: `{"nodes": ["NodeA", "NodeB", ...]}`. Returns last node's box on success. |
| `AnyMatch` | `AnyMatchRecognition` | `general/general.py` | Composite: first matching node wins. Param: `{"nodes": ["NodeA", "NodeB", ...]}`. Returns matched node's box. |

## Utility Modules (Not Registered)

### `custom/general/move_battle.py`

Battle utility functions used across multiple action modules:
- `mount_vehicle(context, mount_type)` — Mount/dismount vehicle (0=dismount, 1=mount) via image recognition.
- `auto_attack(context, attack_type)` — Toggle auto-battle (0=off, 1=on) via image recognition.
- `attack_rotate_view(context, rotate_times, interval)` — Rotate camera during combat to prevent aggro loss (via `post_swipe`).
- `check_alive(context, only_check)` — Detect if character is alive; optionally attempt resurrection.
- `ensure_into_instance(context, timeout)` — Wait until dungeon entry is confirmed (exit button visible).

### `custom/general/power_saving_mode.py`

- `exit_power_saving_mode(exit_func=None)` — Decorator factory for action `run()` methods. Detects power saving mode via recognition and exits it before proceeding. Accepts optional custom exit function.

### `attach/common_attach.py`

~20 getter functions that extract GUI-configured parameters from pipeline `attach` data via `context.get_node_data()`:

| Function | Parameter | Default |
|---|---|---|
| `get_fish_navigation()` | Fish navigation location | "不导航" |
| `get_fish_equipment(type_str)` | Fishing equipment name | "普通{type}" |
| `get_login_timeout()` | Login timeout (seconds) | 300 |
| `get_area_change_timeout()` | Scene change timeout (seconds) | 90 |
| `get_restart_for_except()` | Restart on exception | True |
| `get_max_restart_count()` | Max restart attempts | 5 |
| `get_dest_tele_map()` | Teleport destination map | "" |
| `get_dest_tele_point()` | Teleport destination point | "" |
| `get_dest_navi_map()` | Navigation destination map | "" |
| `get_dest_navigate_point()` | Navigation destination point | "" |
| `get_chat_loop_limit()` | Chat send limit | 0 |
| `get_chat_loop_interval()` | Chat loop interval (seconds) | 120 |
| `get_chat_channel()` | Chat channel name | "世界" |
| `get_chat_channel_id_list()` | Channel line IDs (comma-separated) | [] |
| `get_chat_message_content()` | Message content | "" |
| `get_chat_message_need_team()` | Need team info in message | False |
| `get_full_team_force_send()` | Send even when team is full | False |
| `get_world_line_id_list()` | World line IDs (comma-separated) | [] |
| `get_need_cocoon_name()` | Cocoon name to farm | "" |

### `utils/param_utils.py`

- `CustomActionParam` — Parser for `custom_action_param` JSON strings. Provides `require(keys)` (raises `CustomActionParamError` on missing) and `optional(key, default)` methods.
- `CustomActionParamError` — Custom exception for parameter validation failures.

### `utils/fuzzy_utils.py`

- `fuzzy_match_best(query, candidates, threshold)` — Uses `rapidfuzz.fuzz.partial_ratio` to find the best fuzzy match from a list of candidates. Returns `(best_match, score)` or `(None, 0)` if below threshold.

### `utils/time_utlls.py`

Time formatting and conversion utilities:
- `format_seconds_to_hms()` / `format_seconds_to_ms()` — Human-readable time formatting.
- `get_current_timestamp()` / `get_current_timestamp_ms()` — Current timestamps.
- `str_to_datetime()` / `datetime_to_str()` — String ↔ datetime conversion.
- `timestamp_to_str()` / `str_to_timestamp()` — Timestamp ↔ string conversion.
- `add_days()` / `diff_days()` / `diff_seconds()` — Date arithmetic.

### `constant/pages.py`

- `GamePageEnum` — Enum for recognizable game pages (GAMEPLAY_COMPENSATION_SHOP, ACTIVITY_COMPENSATION_SHOP).
- `PAGE_NODE_MAP` — Maps enum values to pipeline recognition node names.
- `PageRecognizer` — Sequentially tries candidate pages via recognition, returns first match.

## User Tasks (interface.json)

The GUI exposes 15 automated tasks:

1. **Auto Fishing** (自动钓鱼) — Navigate to fishing spot, buy equipment, fish automatically
2. **Simple Gathering** (简单采集) — Automated resource gathering
3. **Unstable Space** (不稳定空间) — Dungeon combat automation
4. **Daily Rewards** (每日奖励) — Claim daily activity rewards
5. **Auto Team Accept** (自动接受组队) — Auto-accept team invitations
6. **Chat Message - Single** (聊天框发消息-单次) — Send message once across channels
7. **Chat Message - Periodic** (聊天框发消息-周期) — Periodically send messages
8. **Beat ChenMin** (暴打陈敏) — Mini-game automation
9. **Auto Cocoon** (自动刷茧) — Cocoon dungeon farming (WIP)
10. **Restart & Login** (重启并登录游戏) — App restart with full login flow
11. **Association Hunt** (协会狩猎) — Association activity automation
12. **Close Ads** (关闭广告) — Dismiss ad popups
13. **Map Teleport** (地图传送) — Teleport to specified map points
14. **Map Navigate** (地图导航) — Navigate to specified map points
15. **Switch World Line** (切换世界分线) — Change game world instance

## Dependencies

From `pyproject.toml`:
- `maafw==5.9.2` — MaaFramework Python binding
- `loguru>=0.7.3` — Structured logging
- `rapidfuzz>=3.14.3` — Fuzzy string matching
- `toml>=0.10.2` — TOML parsing
- `tzdata>=2025.2` — Timezone data
- `pre-commit>=4.5.0` — Git pre-commit hooks

## Development Conventions

### Code Style
- **Language**: All code (variables, functions, classes, comments) in English; user-visible strings may use Chinese.
- **Python version**: >=3.11 (targeting 3.13).
- **Import sorting**: isort with `line_length=120`, `multi_line_output=0`.
- **Formatting**: Pre-commit hooks configured (`.pre-commit-config.yaml`).

### Registration Naming
- Most custom actions use **PascalCase** (e.g., `AutoFishing`, `TeleportPoint`).
- `season_center.py` actions use **snake_case** (e.g., `open_season_center_page`).
- Generic actions use **snake_case** (e.g., `run_pipeline_node`, `wait_x_seconds`).

### Error Handling Pattern
Custom actions follow a consistent pattern:
1. Parse `custom_action_param` via `CustomActionParam`.
2. Use `require()` for mandatory params (raises `CustomActionParamError`).
3. Catch `CustomActionParamError` separately from general `Exception`.
4. Log with `logger.error()` / `logger.exception()` including stack traces.
5. Return `False` or `RunResult(success=False)` on failure.

### Decorator Patterns
Two reusable decorators are applied to action `run()` methods:
- `@exit_power_saving_mode()` — Exits power saving mode before action execution.
- `@ensure_main_page(strict=True/False)` — Returns to main page before action execution.

These are typically stacked:
```python
@exit_power_saving_mode()
@ensure_main_page(strict=True)
def run(self, context, argv):
    ...
```

### Module Loading
`module_loader.py` recursively scans `agent/` subdirectories for Python files, importing each one. This triggers decorator registration (`@AgentServer.custom_action` / `@AgentServer.custom_recognition`), making all custom handlers available to the framework without explicit registration calls.
