import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { BubbleBot, InlineKeyboard } from "../../jeejio-bubble/sdk/BubbleSDK.js";
import PixelMug from "../../jeejio-bubble/devices/PixelMug_1.1.js";

const token = process.env.BUBBLE_BOT_TOKEN;
const apiBaseUrl = process.env.BUBBLE_API_BASE_URL || "https://api.devjeejio.com:5443/im/";
const staticPort = Number(process.env.WEBAPP_PORT || 8799);
const webAppHost = process.env.WEBAPP_HOST || localAddressHint();
const generatedWebAppUrl = `http://${webAppHost}:${staticPort}/index.html`;
const mpsLaunchConfig = {
  id: process.env.MPS_ID || "6595342337",
  version: process.env.MPS_VERSION || "0.0.2",
};
const webAppUrl = withMpsLaunchConfig(process.env.WEBAPP_URL || generatedWebAppUrl);
const shouldServeStatic = !process.env.WEBAPP_URL;

if (!token) {
  throw new Error("Missing BUBBLE_BOT_TOKEN. Set it before running npm run bot.");
}

const pixelMug = new PixelMug();
const bot = new BubbleBot(token, {
  apiBaseUrl,
  debug: process.env.DEBUG !== "false",
  observeWebAppDeviceCalls: true,
  webAppDeviceAccess: "any",
});

bot.registerDevices([pixelMug]);

bot.on("error", async (ctx) => {
  console.error("[party-games-bot]", ctx.error || ctx);
});

bot.on("web_app_device_call", async (ctx) => {
  const call = ctx.webAppDeviceCall || {};
  console.log("[party-games-bot] WebApp device call", {
    direction: call.direction,
    method: call.method,
    slotId: call.slotId,
    deviceId: call.deviceId,
    result: call.result,
  });
});

bot.on("device_notify", async (ctx) => {
  const rawEvents = ctx.tal?.notify || [];
  const parsedEvents = pixelMug.parseNotify(rawEvents);
  console.log("[party-games-bot] Device notify", {
    deviceId: ctx.from?.id,
    rawEvents,
    parsedEvents,
  });
});

bot.on("message", async (ctx) => {
  const command = extractCommand(ctx.message?.content || ctx.message?.text || "");

  if (command === "/bindDevice") {
    await ctx.sendBindDevice({
      content: "Bind PixelMug to this chat.",
      actionButtonTitle: "Bind PixelMug",
    });
    return;
  }

  if (command === "/partyGames" || command === "/webapp" || command === "/start") {
    const keyboard = new InlineKeyboard().url("Open Party Games", webAppUrl);
    await ctx.sendKeyboard(
      "**Party Games**\n\nOpen the WebApp to choose Coin, Dice, RPS, Russian Roulette, or Wheel, then send the game to PixelMug.",
      keyboard,
      {
        mentionOnly: ctx.chat?.type === "group" ? true : undefined,
      }
    );
    return;
  }

  await ctx.sendText("Commands: /bindDevice, /partyGames");
});

if (shouldServeStatic) {
  await startStaticServer();
}

await bot.setCommands([
  {
    command: "bindDevice",
    description: "Bind PixelMug",
  },
  {
    command: "partyGames",
    description: "Open Party Games WebApp",
  },
]);

await bot.start();

console.log("party-games bot is running.");
console.log(`WebApp URL: ${webAppUrl}`);

function extractCommand(text) {
  const match = String(text || "").trim().match(/\/[a-zA-Z0-9_-]+(?:@[a-zA-Z0-9_-]+)?/);
  if (!match) return "";
  return match[0].split("@")[0];
}

function startStaticServer() {
  const distRoot = fileURLToPath(new URL("../webapp/dist", import.meta.url));

  const server = createServer(async (req, res) => {
    try {
      const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
      const pathname = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
      const filePath = normalize(join(distRoot, decodeURIComponent(pathname)));
      const rel = relative(distRoot, filePath);

      if (rel.startsWith("..")) {
        sendStatus(res, 403, "Forbidden");
        return;
      }

      const info = await stat(filePath);
      if (!info.isFile()) {
        sendStatus(res, 404, "Not found");
        return;
      }

      res.writeHead(200, {
        "content-type": contentType(filePath),
        "cache-control": "no-store",
      });
      createReadStream(filePath).pipe(res);
    } catch (error) {
      const message = String(error?.code || error?.message || error);
      if (message.includes("ENOENT")) {
        sendStatus(res, 404, "Build not found. Run npm run build first.");
        return;
      }
      sendStatus(res, 404, "Not found");
    }
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(staticPort, "0.0.0.0", () => {
      server.off("error", reject);
      console.log(`Static WebApp server listening on http://0.0.0.0:${staticPort}`);
      resolve(server);
    });
  });
}

function sendStatus(res, status, text) {
  res.writeHead(status, { "content-type": "text/plain; charset=utf-8" });
  res.end(text);
}

function contentType(filePath) {
  switch (extname(filePath)) {
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "text/javascript; charset=utf-8";
    case ".css":
      return "text/css; charset=utf-8";
    case ".json":
      return "application/json";
    case ".svg":
      return "image/svg+xml";
    case ".png":
      return "image/png";
    case ".mp4":
      return "video/mp4";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    default:
      return "application/octet-stream";
  }
}

function withMpsLaunchConfig(url) {
  const next = new URL(url);
  next.searchParams.set("mps_id", mpsLaunchConfig.id);
  next.searchParams.set("mps_version", mpsLaunchConfig.version);
  return next.toString();
}

function localAddressHint() {
  return process.env.HOST || "127.0.0.1";
}
