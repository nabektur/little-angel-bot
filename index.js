import { AoiClient, LoadCommands } from "aoi.js";
import "dotenv/config"; // .env loading

// Discord Client
const bot = new AoiClient({
  token: process.env.DISCORD_TOKEN,
  prefix: "!",
  intents: ["Guilds", "GuildMessages"],
  events: ["onMessage", "onInteractionCreate"],
  mobilePlatform: true
  // database: {
  //   type: "json"
  // }
});

// Logger
bot.readyCommand({
  channel: false,
  code: `console.log("Бот запущен как $userTag[$clientID]")`
});

// Import commands from /commands
new LoadCommands(bot).load(bot.cmd, "./commands", {
  filter: (cmd) =>
    cmd &&
    typeof cmd.name === "string" &&
    typeof cmd.code === "string"
});