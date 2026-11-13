# Party Games

Party Games is a PixelMug Studio application that provides a collection of small group games: coin flip, dice, Rock Paper Scissors, Russian Roulette, and a decision wheel. The MicroPython runtime runs on PixelMug, while the Vue WebApp selects games, configures wheel options, and synchronizes the play history over BLE.

## Project layout

```text
party-games/
  bot/        Bot integration entry point.
  mpy/        MicroPython runtime and MPS manifest.
  webapp/     Vue WebApp controller.
```

## Development

Install dependencies from the project root and from `webapp/`:

```bash
npm install
npm --prefix webapp install
```

Run the WebApp locally:

```bash
npm run dev
```

Build the WebApp:

```bash
npm run build
```

Run the Bot:

```bash
npm run bot
```

The Bot entry point is `bot/index.js`. PixelMug Studio supplies `BOT_TOKEN`, `BOT_API_BASE_URL`, `STUDIO_WEBAPP_URL`, `STUDIO_MPS_ID`, and `STUDIO_MPS_VERSION`. Do not add a local token configuration file or commit credentials.

After a PixelMug is bound, open Party Games from the Bot. The WebApp automatically requests the MPS when the landing page opens, so the user does not need to press a separate install button. Studio installs and runs `mpy/mps.json` automatically.

## BLE protocol

The MPY runtime uses `maopaoBleApp.BleAppService` and the WebApp uses the SDK `BleAppClient`. Both sides use the application identity `PartyGames` and version `1.0.0`.

The WebApp sends these commands:

- `mpyPartyGamesSelect` selects a game and sends wheel options.
- `mpyPartyGamesGetHistory` requests recent results.
- `mpyPartyGamesClearHistory` clears stored results.

The runtime publishes game selection and result events through the BLE app state channel. The MPS dependency declaration is in `mpy/mps.json`.

## Generated files

Generated output is ignored by the project, including `webapp/dist/`, `webapp/node_modules/`, and Python `__pycache__/` directories. Remove Python cache directories before delivering the project.
