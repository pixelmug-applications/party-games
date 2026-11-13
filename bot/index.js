import { BubbleBot, InlineKeyboard } from "@jeejio-bubble/bot/sdk";
import PixelMugS1 from "@jeejio-bubble/bot/devices/pixelmug-s1";

const mpsId = process.env.STUDIO_MPS_ID || "";
const mpsVersion = process.env.STUDIO_MPS_VERSION || "1.0.0";
const webAppUrl = launchUrl(requiredEnv("STUDIO_WEBAPP_URL"));

const bot = new BubbleBot(requiredEnv("BOT_TOKEN"), { apiBaseUrl: process.env.BOT_API_BASE_URL, webAppDeviceAccess: "any" });

const pixelMug = new PixelMugS1();
bot.registerDevices([pixelMug]);

bot.on("error", async (ctx) => console.error("[party-games-bot]", ctx.error || ctx));
bot.on("contact_added", async (ctx) => sendIntro(ctx));
bot.on("joined_group", async (ctx) => sendIntro(ctx, { mentionOnly: false }));

bot.on("message", async (ctx) => {
  const command = extractCommand(ctx.message?.content || ctx.message?.text || "");
  if (command === "/bindDevice") { await ctx.sendBindDevice({ content: "Bind a PixelMug before playing Party Games.", actionButtonTitle: "Bind PixelMug" }); return; }
  if (["/partyGames", "/webapp", "/start"].includes(command)) {
    const keyboard = new InlineKeyboard().url("Open Party Games", webAppUrl);
    await ctx.sendKeyboard("**Party Games**\nChoose Coin, Dice, RPS, Russian Roulette, or Wheel on PixelMug.", keyboard, { mentionOnly: ctx.chat?.type === "group" ? true : undefined }); return;
  }
  await ctx.sendText("Commands: /bindDevice, /partyGames");
});

await bot.setCommands([{ command: "bindDevice", description: "Bind PixelMug" }, { command: "partyGames", description: "Open Party Games WebApp" }]);
await bot.start();

console.log("mps-party-games bot is running.");
console.log(`WebApp URL: ${webAppUrl}`);

function requiredEnv(name) { const value = process.env[name]; if (!value) throw new Error(`Missing required environment variable: ${name}`); return value; }

function launchUrl(value) { const url = new URL(value); if (mpsId) url.searchParams.set("mps_id", mpsId); url.searchParams.set("mps_version", mpsVersion); return url.toString(); }

function extractCommand(value) { const match = String(value || "").trim().match(/\/[a-zA-Z0-9_-]+(?:@[a-zA-Z0-9_-]+)?/); return match ? match[0].split("@")[0] : ""; }

function sendIntro(ctx, options = {}) { return ctx.sendBindDevice({ content: "Bind a PixelMug before playing Party Games.", actionButtonTitle: "Bind PixelMug", ...options }); }
