const { AoiClient } = require("aoi.js");
require("dotenv").config(); // .env loading

// Discord Client
const client = new AoiClient({
  token: process.env.DISCORD_TOKEN, 
  prefix: "$",
  intents: ["MessageContent", "Guilds", "GuildMessages"],
  events: ["onMessage", "onInteractionCreate"]
});

client.status({
  name: "на кикстарте",
  type: "STREAMING",
  url: "https://www.twitch.tv/deadp47_",
  status: "idle",
  time: 12
});

// Logger
client.readyCommand({
  channel: "1380518098053894146",
  code: `"Бот запущен как **$userTag[$clientID]**`
});

// Import commands from /commands
client.loadCommands("./commands");