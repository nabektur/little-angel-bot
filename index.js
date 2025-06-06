const { AoiClient, LoadCommands } = require("aoi.js");
require("dotenv").config(); // .env loading

// Discord Client
const bot = new AoiClient({
  token: process.env.DISCORD_TOKEN,
  prefix: "!",
  intents: ["Guilds", "GuildMessages"],
  events: ["onMessage", "onInteractionCreate"],
  // mobilePlatform: true
  // database: {
  //   type: "json"
  // }
});

bot.status({
  name: "на кикстарте",
  type: "STREAMING",
  status: "idle",
  time: 12
});

// Logger
bot.readyCommand({
  channel: false,
  code: `console.log("Бот запущен как $userTag[$clientID]")`
});

// Import commands from /commands
bot.loadCommands("./commands");